from config import MESSAGE_PROPERTIES, AZURE_STORAGEACCOUNT, \
                   AZURE_DESTSHARE, SOURCEPATH_FIELD, MAPPING, \
                   AZURE_DESTSHARE_FOLDERS
import os
import logging
import xmltodict
import re
import uuid

from firestoreprocessor import FirestoreProcessor

from azure.storage.fileshare import ShareClient, ShareLeaseClient
from azure.core.exceptions import HttpResponseError

from google.cloud import secretmanager

logging.basicConfig(level=logging.INFO)
logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.ERROR)


class Link2Processor(object):
    def __init__(self):
        self.data_selector = os.environ.get('DATA_SELECTOR', 'Required parameter is missing')
        self.meta = MESSAGE_PROPERTIES[self.data_selector]
        self.destshare = AZURE_DESTSHARE
        self.folder_prefix = AZURE_DESTSHARE_FOLDERS
        self.storageaccount = AZURE_STORAGEACCOUNT
        self.project_id = os.environ.get('PROJECT_ID', 'Required parameter is missing')
        self.storagekey_secret_id = os.environ.get('AZURE_STORAGEKEY_SECRET_ID', 'Required parameter is missing')
        self.storagekey = None
        if self.storageaccount:
            client = secretmanager.SecretManagerServiceClient()
            secret_name = f"projects/{self.project_id}/secrets/{self.storagekey_secret_id}/versions/latest"
            key_response = client.access_secret_version(request={"name": secret_name})
            self.storagekey = key_response.payload.data.decode("UTF-8")
            self.share = ShareClient(account_url=f"https://{self.storageaccount}.file.core.windows.net/",
                                     share_name=self.destshare, credential=self.storagekey)
        self.sourcepath_field = SOURCEPATH_FIELD
        self.mapping = MAPPING
        self.gcp_firestore = FirestoreProcessor()

    def get_ticket_nr(self, ticket_number_field, input_json):
        # Get all digits
        digit_list = re.findall(r'\d+', input_json[ticket_number_field])
        # Check if there's only 1 digit part
        if len(digit_list) > 1:
            logging.error("Multiple digit parts in ticket number")
            return False
        # Return ticket number
        return digit_list[0]

    def map_json(self, mapping_json, input_json):
        output_jsons = []
        logbooks = []
        # For every XML root
        for xml_root in mapping_json:
            address_street = []
            address_number = []
            address_addition = []
            # Check if there's an address split field defined in the mapping json
            address_split = mapping_json[xml_root].get('address_split')
            if address_split:
                # for every address field
                for address_field in address_split:
                    # Have to split address into streetname and number
                    street, number, addition = self.split_streetname_nr(input_json[address_field])
                    address_street = [address_split[address_field]['streetname'], street]
                    address_number = [address_split[address_field]['number'], number]
                    address_addition = [address_split[address_field]['addition'], addition]
            firestore_fields = mapping_json[xml_root].get('firestore_fields')
            combined_fields = mapping_json[xml_root].get('combined_fields')
            # Get the sub element
            for xml_root_sub in mapping_json[xml_root]:
                # If the sub element is not 'xml_filename', 'address_split'
                # or 'ticket_number_field' or 'hardcoded_fields'
                # or 'firestore_fields' or 'combined_fields'
                if xml_root_sub != "xml_filename" and \
                   xml_root_sub != "address_split" and \
                   xml_root_sub != "ticket_number_field" and \
                   xml_root_sub != "hardcoded_fields" and \
                   xml_root_sub != "firestore_fields" and \
                   xml_root_sub != "combined_fields":
                    json_subelement = {}
                    for field in mapping_json[xml_root][xml_root_sub]:
                        field_json = mapping_json[xml_root][xml_root_sub][field]
                        field_value = ""
                        row = {}
                        # If value in mapping json is "HARDCODED"
                        if field_json == "HARDCODED":
                            # Check if field is in "hardcoded_fields"
                            hardcoded_fields = mapping_json[xml_root].get("hardcoded_fields")
                            if hardcoded_fields:
                                if field in hardcoded_fields:
                                    field_value = hardcoded_fields[field]
                        # If value in mapping json is "ADDRESS_SPLIT"
                        elif field_json == "ADDRESS_SPLIT":
                            # Check if address, number and addition are defined
                            if address_street and address_number and address_addition:
                                if field == address_street[0]:
                                    field_value = address_street[1]
                                elif field == address_number[0]:
                                    field_value = address_number[1]
                                elif field == address_addition[0]:
                                    field_value = address_addition[1]
                            else:
                                logging.error("Field should be split conform address split but address_split field is not defined")
                                return False
                        # If value in mapping json is "FIRESTORE"
                        elif field_json == "FIRESTORE":
                            # The value can be looked up in the firestore
                            # Get the dictionary belonging to the value
                            if firestore_fields:
                                # Get the dictionary belonging to the XML field
                                fs_dict = firestore_fields.get(field)
                                if fs_dict:
                                    # Get the right values from the JSON
                                    json_values = []
                                    for id_dict in fs_dict['firestore_ids']:
                                        for fs_id in id_dict:
                                            json_field = id_dict[fs_id]
                                            # Check if json value exists in the input json
                                            json_value = input_json.get(json_field)
                                            if json_value:
                                                json_values.append({fs_id: json_value})
                                    # Get the value of the XML dict from the firestore
                                    collection_name = fs_dict['firestore_collection']
                                    succeeded, xml_fs_value = self.gcp_firestore.get_value(collection_name, json_values,
                                                                                           fs_dict['firestore_value'])
                                    if succeeded:
                                        field_value = xml_fs_value
                                    else:
                                        # Check if the field "if_not_exists" is defined
                                        if fs_dict.get("if_not_exists"):
                                            # Check if in this field, the field "make_logbook" is defined
                                            logbook_mapping = fs_dict["if_not_exists"].get("make_logbook")
                                            if logbook_mapping:
                                                logging.info(f"The Firestore querie '{xml_fs_value}'"
                                                             f" did not result in a value for XML field '{field}'"
                                                             f" in collection {collection_name}, "
                                                             "making logbook.")
                                                # Make logbooks
                                                mapped_logbooks = self.map_json(logbook_mapping, input_json)
                                                # Add logbook to logbooks
                                                logbooks.extend(mapped_logbooks)
                                            else:
                                                logging.error(f"The Firestore querie '{xml_fs_value}'"
                                                              f" did not result in a value for XML field '{field}'"
                                                              f" in collection {collection_name}")
                                                return False
                                        else:
                                            logging.error(f"The Firestore querie '{xml_fs_value}'"
                                                          f" did not result in a value for XML field '{field}'"
                                                          f" in collection {collection_name}")
                                            return False
                                else:
                                    logging.error(f"The firestore_fields field does not contain key '{field}'")
                                    return False
                            else:
                                logging.error("The config contains the value FIRESTORE but the firestore_fields field is not defined")
                                return False
                        # If value in mapping json in "COMBINED"
                        elif field_json == "COMBINED":
                            # Get the dictionary belonging to the value
                            if combined_fields:
                                combined_value = ""
                                # Get the XML field configuration
                                xml_field_config = combined_fields.get(field)
                                if xml_field_config:
                                    # If combination method is hypen
                                    if xml_field_config["combination_method"] == "HYPHEN":
                                        com_json_fields = xml_field_config["json_fields"]
                                        if len(com_json_fields) == 1:
                                            com_json_value = input_json[com_json_fields[0]]
                                            combined_value = com_json_value.replace(' ', '-')
                                            # If the combination should start with the original JSON field
                                            if xml_field_config["start_with_field"]:
                                                combined_value = f"{com_json_fields[0]}: {combined_value}"
                                        else:
                                            for com_json_field in com_json_fields:
                                                com_json_value = input_json[com_json_field]
                                                if combined_value:
                                                    combined_value = combined_value + f"-{com_json_value}"
                                                else:
                                                    # If the combination should start with the original JSON field
                                                    if xml_field_config["start_with_field"]:
                                                        combined_value = f"{com_json_field}: {combined_value}"
                                                    else:
                                                        combined_value = com_json_value
                                    # If combination method is newline
                                    elif xml_field_config["combination_method"] == "NEWLINE":
                                        for com_json_field in xml_field_config["json_fields"]:
                                            com_json_value = input_json[com_json_field]
                                            com_json_value = com_json_value.replace('.\\n', '. ')
                                            com_json_value = com_json_value.replace('\\n', '')
                                            if combined_value:
                                                # If the combination should start with the original JSON field
                                                if xml_field_config["start_with_field"]:
                                                    combined_value = combined_value + f"\n\n{com_json_field}: {com_json_value}"
                                                else:
                                                    combined_value = combined_value + f"\n\n{com_json_value}"
                                            else:
                                                # If the combination should start with the original JSON field
                                                if xml_field_config["start_with_field"]:
                                                    combined_value = f"{com_json_field}: {com_json_value}"
                                                else:
                                                    combined_value = com_json_value
                                    else:
                                        logging.error(f"Combination method for field {field} is not recognized")
                                        return False
                                else:
                                    logging.error(f"The combined_fields field does not contain XML field {field}")
                                    return False
                                field_value = combined_value
                            else:
                                logging.error("The config contains the value COMBINED but the combined_fields field is not defined")
                                return False
                        # If value in mapping json is "TICKETNR"
                        elif field_json == "TICKETNR":
                            # Check what the field is that should be mapped to the ticket_number_field
                            # Check if there's an ticket number field defined
                            ticket_number_field = mapping_json[xml_root].get('ticket_number_field')
                            if ticket_number_field:
                                ticket_nr = self.get_ticket_nr(ticket_number_field, input_json)
                                if ticket_nr:
                                    field_value = ticket_nr
                                else:
                                    return False
                            else:
                                logging.error("Ticket number is needed but ticket number field is not defined")
                                return False
                        else:
                            field_value = input_json.get(field_json)
                            if field_value == "None" or not field_value:
                                field_value = ""
                        row = {field: field_value}
                        json_subelement.update(row)
                    xml_json = {xml_root: {xml_root_sub: json_subelement}}
            # Append the filled out json and its filename
            xml_and_fn = []
            xml_and_fn.append(xml_json)
            filename_xml = self.make_filename(mapping_json[xml_root], input_json)
            xml_and_fn.append(filename_xml)
            output_jsons.append(xml_and_fn)
        output_jsons.extend(logbooks)
        return output_jsons

    def json_to_fileshare(self, mapped_json, destfilepath):
        sourcefile = xmltodict.unparse(mapped_json, encoding='ISO-8859-1', pretty=True)
        # Put file on fileshare
        logging.info(f"Putting {destfilepath} on //{self.storageaccount}/{self.destshare}")
        file_on_share = self.share.get_file_client(destfilepath)
        try:
            file_on_share.create_file(size=0)
        except HttpResponseError:
            ShareLeaseClient(file_on_share).break_lease()
            file_on_share.create_file(size=0)
        file_lease = file_on_share.acquire_lease(timeout=5)
        logging.info(f"Writing to //{self.storageaccount}/{self.destshare}/{destfilepath}")
        file_on_share.upload_file(sourcefile, lease=file_lease)
        file_lease.release(timeout=5)

    def split_streetname_nr(self, address):
        # Get street, number and addition from address
        address_reg = re.split(r'(\d+)', address)
        addition = ""
        if len(address_reg) <= 1:
            logging.error("Address misses street or number")
        elif len(address_reg) == 2:
            street = address_reg[0]
            number = address_reg[1]
        elif len(address_reg) == 3:
            street = address_reg[0]
            number = address_reg[1]
            addition = address_reg[2]
        else:
            logging.error("Address has more values than street, number and addition")
        # Remove whitespace
        street = street.replace(" ", "")
        number = number.replace(" ", "")
        addition = addition.replace("-", "")
        addition = addition.replace(" ", "")
        return street, number, addition

    def make_filename(self, sub_root_mapping, msg):
        # Get the filename field
        file_name_field = sub_root_mapping['xml_filename']
        # If filename contains "TICKETNR", it should be changed into the ticket number
        if "TICKETNR" in file_name_field:
            # Check if there's an ticket number field defined
            ticket_number_field = sub_root_mapping.get('ticket_number_field')
            if ticket_number_field:
                file_name_field = file_name_field.replace("TICKETNR", self.get_ticket_nr(ticket_number_field, msg))
            else:
                logging.error("Ticket number is needed but ticket number field is not defined")
                return False
        # If filename contains "GUID", it should be changed into a GUID
        if "GUID" in file_name_field:
            guid = str(uuid.uuid4())
            file_name_field = file_name_field.replace("GUID", guid)
        return file_name_field

    def msg_to_fileshare(self, mapping_json, msg):
        # Check if storage account is set
        if self.storageaccount:
            # Map the message to XMLs
            mapped_jsons = self.map_json(mapping_json, msg)
            if not mapped_jsons:
                return False
            # For every kind of XML file
            for dict_and_fn in mapped_jsons:
                filled_in_json = dict_and_fn[0]
                xml_filename = dict_and_fn[1]
                # Make filename
                address_destfilepath = f"{self.folder_prefix}{xml_filename}.xml"
                # Put jsons on Azure Fileshare
                self.json_to_fileshare(filled_in_json, address_destfilepath)
        else:
            logging.info("No storage account is set")
        return True

    def process(self, payload):
        selector_data = payload[self.data_selector]

        if isinstance(selector_data, list):
            for data in selector_data:
                if not self.msg_to_fileshare(self.mapping, data):
                    logging.error("Message is not processed")
        elif isinstance(selector_data, dict):
            if not self.msg_to_fileshare(self.mapping, selector_data):
                logging.error("Message is not processed")
        else:
            logging.error("Message is not a list or a dictionary")
