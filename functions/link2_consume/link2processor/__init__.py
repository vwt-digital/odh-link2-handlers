from config import MESSAGE_PROPERTIES, AZURE_STORAGEACCOUNT, \
                   AZURE_DESTSHARE, SOURCEPATH_FIELD, MAPPING, \
                   AZURE_DESTSHARE_FOLDERS
import os
import logging
import xmltodict
import re
import uuid

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
        self.mapping_json = MAPPING

    def get_ticket_nr(self, ticket_number_field, input_json):
        # Get all digits
        digit_list = re.findall(r'\d+', input_json[ticket_number_field])
        # Check if there's only 1 digit part
        if len(digit_list) > 1:
            logging.error("Multiple digit parts in ticket number")
        # Return ticket number
        return digit_list[0]

    def map_json(self, input_json):
        output_jsons = []
        # For every XML root
        for xml_root in self.mapping_json:
            # Get the sub element
            for xml_root_sub in self.mapping_json[xml_root]:
                # If the sub element is not 'xml_filename', 'address_split'
                # or 'ticket_number_field' or 'hardcoded_fields'
                if xml_root_sub != "xml_filename" and \
                   xml_root_sub != "address_split" and \
                   xml_root_sub != "ticket_number_field" and \
                   xml_root_sub != "hardcoded_fields":
                    json_subelement = {}
                    for field in self.mapping_json[xml_root][xml_root_sub]:
                        field_json = self.mapping_json[xml_root][xml_root_sub][field]
                        field_map = input_json.get(field_json)
                        row = {}
                        # Check if field is in "hardcoded_fields"
                        hardcoded_fields = self.mapping_json[xml_root].get("hardcoded_fields")
                        if hardcoded_fields:
                            if field in hardcoded_fields:
                                row = {field: hardcoded_fields[field]}
                        if not row:
                            # Check if field_json is "ticket_number_field"
                            if field_json == "ticket_number_field":
                                # Check what the field is that should be mapped to the ticket_number_field
                                # Check if there's an ticket number field defined
                                ticket_number_field = self.mapping_json[xml_root].get('ticket_number_field')
                                if ticket_number_field:
                                    row = {field: self.get_ticket_nr(ticket_number_field, input_json)}
                                else:
                                    logging.error("Ticket number is needed but ticket number field is not defined")
                            elif field_map == "None" or not field_map:
                                row = {field: ""}
                            else:
                                row = {field: field_map}
                        json_subelement.update(row)
                    xml_json = {xml_root: {xml_root_sub: json_subelement}}
                output_jsons.append(xml_json)
        return output_jsons

    def json_to_fileshare(self, mapped_json, destfilepath):
        # JSON to XML
        sourcefile = xmltodict.unparse(mapped_json, encoding='ISO-8859-1')
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

    def msg_to_fileshare(self, msg):
        # Check if storage account is set
        if self.storageaccount:
            # Map the message to XMLs
            mapped_jsons = self.map_json(msg)
            # For every kind of XML file
            field_count = 0
            for root in self.mapping_json:
                for root_sub in self.mapping_json[root]:
                    # If the sub element is not 'xml_filename', 'address_split'
                    # or 'ticket_number_field' or 'hardcoded_fields'
                    if root_sub != "xml_filename" and \
                       root_sub != "address_split" and \
                       root_sub != "ticket_number_field" and \
                       root_sub != "hardcoded_fields":
                        # Check if there's an address split field defined
                        address_split = self.mapping_json[root].get('address_split')
                        if address_split:
                            # for every address field
                            for address_field in address_split:
                                # Have to split address into streetname and number
                                street, number, addition = self.split_streetname_nr(msg[address_field])
                                mapped_jsons[field_count][root][root_sub][address_split[address_field]['streetname']] = street
                                mapped_jsons[field_count][root][root_sub][address_split[address_field]['number']] = number
                                mapped_jsons[field_count][root][root_sub][address_split[address_field]['addition']] = addition
                        # Get the filename field
                        file_name_field = self.mapping_json[root]['xml_filename']
                        # If filename contains "TICKETNR", it should be changed into the ticket number
                        if "TICKETNR" in file_name_field:
                            # Check if there's an ticket number field defined
                            ticket_number_field = self.mapping_json[root].get('ticket_number_field')
                            if ticket_number_field:
                                file_name_field = file_name_field.replace("TICKETNR", self.get_ticket_nr(ticket_number_field, msg))
                            else:
                                logging.error("Ticket number is needed but ticket number field is not defined")
                        # If filename contains "GUID", it should be changed into a GUID
                        if "GUID" in file_name_field:
                            guid = str(uuid.uuid4())
                            file_name_field = file_name_field.replace("GUID", guid)
                        # Make filename
                        address_destfilepath = f"{self.folder_prefix}{file_name_field}.xml"
                        # Put jsons on Azure Fileshare
                        self.json_to_fileshare(mapped_jsons[field_count], address_destfilepath)
                    field_count = field_count + 1
        else:
            logging.info("No storage account is set")

    def process(self, payload):
        selector_data = payload[self.data_selector]

        if isinstance(selector_data, list):
            for data in selector_data:
                self.msg_to_fileshare(data)
        elif isinstance(selector_data, dict):
            self.msg_to_fileshare(selector_data)
        else:
            logging.error("Message is not a list or a dictionary")
