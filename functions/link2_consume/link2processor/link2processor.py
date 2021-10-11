import logging
import os
import re
import uuid
import xmltodict

from requests.exceptions import ConnectionError, HTTPError, RetryError

from config import (
    DEBUG_LOGGING,
    ID,
    MAPPING,
    MAPPING_FIELD,
    MESSAGE_PROPERTIES,
    STANDARD_MAPPING
)

from functions.common.utils import get_secret
from functions.common.requests_retry_session import get_requests_session
from .combine_values import CombinedValuesProcessor
from .firestore_values import FirestoreValuesProcessor
from .other_values import OtherValuesProcessor

logging.basicConfig(level=logging.INFO)
logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(
    logging.ERROR
)


class Link2Processor(object):
    def __init__(self):
        self.session = get_requests_session()
        self.data_selector = os.environ.get(
            "DATA_SELECTOR", "Required parameter is missing"
        )
        self.meta = MESSAGE_PROPERTIES[self.data_selector]

        self.file_share_api_key = get_secret(
            os.environ["PROJECT_ID"],
            os.environ["FILE_SHARE_API_KEY_SECRET_ID"]
        )

        self.mapping_field = MAPPING_FIELD
        self.standard_mapping = STANDARD_MAPPING
        self.mapping = MAPPING
        self.other_values_processor = OtherValuesProcessor(self)
        self.firestore_values_processor = FirestoreValuesProcessor(self)
        self.combined_values_processor = CombinedValuesProcessor(self)
        self.debug_logging = DEBUG_LOGGING
        self.data_id = ID

    def _log(self, debug_message, normal_message):
        if self.debug_logging:
            logging.info(debug_message)
        else:
            logging.info(normal_message)

    def map_json(self, mapping_json, input_json, only_values_bool, added_jsons):
        output_list = []
        logbooks = []
        # For every XML root
        for xml_root in mapping_json:
            address_street = []
            address_number = []
            address_addition = []
            # Check if there's an address split field defined in the mapping json
            address_split = mapping_json[xml_root].get("address_split")
            if address_split:
                # for every address field
                for address_field in address_split:
                    # Have to split address into streetname and number
                    street, number, addition = self._split_streetname_nr(
                        input_json[address_field]
                    )
                    address_street = [
                        address_split[address_field]["streetname"],
                        street,
                    ]
                    address_number = [address_split[address_field]["number"], number]
                    address_addition = [
                        address_split[address_field]["addition"],
                        addition,
                    ]
            firestore_fields = mapping_json[xml_root].get("firestore_fields")
            combined_json_fields = mapping_json[xml_root].get("combined_json_fields")
            combined_xml_fields = mapping_json[xml_root].get("combined_xml_fields")
            prefixes_field = mapping_json[xml_root].get("prefixes")
            date_fields = mapping_json[xml_root].get("date_fields")
            # Get the sub element
            for xml_root_sub in mapping_json[xml_root]:
                # If the sub element is not 'xml_filename', 'address_split'
                # or 'ticket_number_field' or 'hardcoded_fields'
                # or 'firestore_fields' or 'combined_fields'
                # or 'phonenumber'
                if (
                    xml_root_sub != "xml_filename"
                    and xml_root_sub != "address_split"
                    and xml_root_sub != "ticket_number_field"
                    and xml_root_sub != "hardcoded_fields"
                    and xml_root_sub != "firestore_fields"
                    and xml_root_sub != "combined_json_fields"
                    and xml_root_sub != "combined_xml_fields"
                    and xml_root_sub != "prefixes"
                    and xml_root_sub != "date_fields"
                ):
                    json_subelement = {}
                    for field in mapping_json[xml_root][xml_root_sub]:
                        field_json = mapping_json[xml_root][xml_root_sub][field]
                        row = {}
                        field_value = ""
                        # Split field json on "_" to get a list
                        field_json_list = field_json.split("-")
                        # For every part of field_json
                        field_value, logbooks = self._get_value_from_field(
                            field_value,
                            field_json_list,
                            mapping_json,
                            xml_root,
                            input_json,
                            field,
                            address_street,
                            address_number,
                            address_addition,
                            logbooks,
                            firestore_fields,
                            added_jsons,
                            combined_json_fields,
                            combined_xml_fields,
                            prefixes_field,
                            date_fields,
                        )
                        # Check if the value contains "LEAVE_EMPTY" because then the whole value should stay empty
                        if "LEAVE_EMPTY" in field_value:
                            field_value = ""
                        row = {field: field_value}
                        if only_values_bool is True:
                            output_list.append(row)
                        else:
                            json_subelement.update(row)
                    # Make xml_json
                    xml_json = self._make_xml_json(
                        xml_root, xml_root_sub, json_subelement, only_values_bool
                    )
            # Update output list by checking if a root is necessary
            output_list = self._make_output_list(
                input_json,
                xml_json,
                xml_root,
                added_jsons,
                mapping_json,
                output_list,
                only_values_bool,
            )
        if only_values_bool is False:
            output_list.extend(logbooks)
        return output_list

    @staticmethod
    def _make_xml_json(xml_root, xml_root_sub, json_subelement, only_values_bool):
        xml_json = {}
        # Check if there should be a root or not
        if only_values_bool is False:
            # If there is a xml root defined
            if xml_root:
                xml_json = {xml_root: {xml_root_sub: json_subelement}}
            # If there is not
            else:
                xml_json = {xml_root_sub: json_subelement}
        return xml_json

    def _make_output_list(
        self,
        input_json,
        xml_json,
        xml_root,
        added_jsons,
        mapping_json,
        output_list,
        only_values_bool,
    ):
        # Check if there should be a root or not
        if only_values_bool is False:
            # Add JSON if it not already in list
            if xml_json not in added_jsons:
                added_jsons.append(xml_json)
                # Append the filled out json and its filename
                xml_and_fn = []
                xml_and_fn.append(xml_json)
                filename_xml = self._make_filename(mapping_json[xml_root], input_json)
                xml_and_fn.append(filename_xml)
                output_list.append(xml_and_fn)
        return output_list

    def _get_value_from_field(  # noqa: C901
        self,
        field_value,
        field_json_list,
        mapping_json,
        xml_root,
        input_json,
        field,
        address_street,
        address_number,
        address_addition,
        logbooks,
        firestore_fields,
        added_jsons,
        combined_json_fields,
        combined_xml_fields,
        prefixes_field,
        date_fields,
    ):
        for fj_part in field_json_list:
            success = False
            # If field_value is not empty
            if field_value:
                # Add a white space after the last found value
                field_value = f"{field_value} "
            # If value in part of field_json is "HARDCODED"
            if fj_part == "HARDCODED":
                (success, new_value,) = self.other_values_processor.hardcoded_value(
                    mapping_json, xml_root, field
                )
                if success:
                    field_value = field_value + new_value
                else:
                    return ""
            # If value in part of field_json is "ADDRESS_SPLIT"
            elif fj_part == "ADDRESS_SPLIT":
                (success, new_value,) = self.other_values_processor.address_split_value(
                    field,
                    address_street,
                    address_number,
                    address_addition,
                )
                if success:
                    field_value = field_value + new_value
                else:
                    return ""
            # If value in part of field_json is "FIRESTORE"
            elif fj_part == "FIRESTORE":
                (
                    success,
                    new_value,
                    new_logbooks,
                ) = self.firestore_values_processor.firestore_value(
                    field,
                    firestore_fields,
                    input_json,
                    logbooks,
                    added_jsons,
                )
                if success:
                    logbooks = new_logbooks
                    field_value = field_value + new_value
                else:
                    return ""
            # If value in part of field_json in "COMBINED_JSON"
            elif fj_part == "COMBINED_JSON":
                (success, new_value,) = self.combined_values_processor.combined_value(
                    field, combined_json_fields, input_json
                )
                if success:
                    field_value = field_value + new_value
                else:
                    return ""
            # If value in part of field_json in "COMBINED_XML"
            elif fj_part == "COMBINED_XML":
                (
                    success,
                    new_value,
                ) = self.combined_values_processor.combined_value_xml(
                    field, combined_xml_fields, input_json, added_jsons
                )
                if success:
                    field_value = field_value + new_value
                else:
                    return ""
            # If value in part of field_json is "TICKETNR"
            elif fj_part == "TICKETNR":
                (success, new_value,) = self.other_values_processor.ticket_number_value(
                    mapping_json, xml_root, input_json
                )
                if success:
                    field_value = field_value + new_value
                else:
                    return ""
            # If value in part of field_json is "PREFIX"
            elif fj_part == "PREFIX":
                (success, new_value,) = self.other_values_processor.prefix_value(
                    field, prefixes_field, input_json
                )
                if success:
                    field_value = field_value + new_value
                else:
                    return ""
            # If value in part of field_json is "DATE"
            elif fj_part == "DATE":
                (success, new_value,) = self.other_values_processor.date_value(
                    field, date_fields, input_json
                )
                if success:
                    field_value = field_value + new_value
                else:
                    return ""
            elif success is False:
                (
                    success,
                    new_value,
                ) = self.other_values_processor.message_value(input_json, fj_part)
                if success:
                    field_value = field_value + new_value
                else:
                    return ""
        return field_value, logbooks

    def _split_streetname_nr(self, address):
        # Get street, number and addition from address
        address_reg = re.split(r"(\d+|\D+)", address)
        address_reg = list(filter(None, address_reg))
        address_reg = [addr for addr in address_reg if addr.strip()]
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
        if street.endswith(" "):
            street = street[:-1]
        number = number.replace(" ", "")
        addition = addition.replace("-", "")
        addition = addition.replace(" ", "")
        return street, number, addition

    def _make_filename(self, sub_root_mapping, msg):
        # Get the filename field
        file_name_field = sub_root_mapping["xml_filename"]
        # If filename contains "TICKETNR", it should be changed into the ticket number
        if "TICKETNR" in file_name_field:
            # Check if there's an ticket number field defined
            ticket_number_field = sub_root_mapping.get("ticket_number_field")
            if ticket_number_field:
                file_name_field = file_name_field.replace(
                    "TICKETNR",
                    self.other_values_processor.get_ticket_nr(ticket_number_field, msg),
                )
            else:
                logging.error(
                    "Ticket number is needed but ticket number field is not defined"
                )
                return False
        # If filename contains "GUID", it should be changed into a GUID
        if "GUID" in file_name_field:
            guid = str(uuid.uuid4())
            file_name_field = file_name_field.replace("GUID", guid)
        return file_name_field

    def process(self, payload):
        selector_data = payload[self.data_selector]
        if self.data_id:
            logging.info(f"Message contains ID {selector_data[self.data_id]}")

        data_list = None
        if isinstance(selector_data, list):
            data_list = selector_data
        elif isinstance(selector_data, dict):
            data_list = [selector_data]

        if data_list is not None:
            for data in data_list:
                # Check if mapping type is specified, else use default.
                mapping_type = data.get(self.mapping_field, self.standard_mapping)
                mapping_config = self.mapping[mapping_type]

                file_share_endpoint = mapping_config["file_share_endpoint"]
                file_share_folder_prefix = mapping_config["file_share_folder_prefix"]

                mapped_json_objects = self.map_json(mapping_config["mapping"], data, False, [])
                if mapped_json_objects:
                    for mapped_json, file_name in mapped_json_objects:
                        destination_file_path = f"{file_share_folder_prefix}{file_name}.xml"
                        xml_data = xmltodict.unparse(mapped_json, encoding="ISO-8859-1", pretty=True)
                        self._xml_content_to_file_share_api(
                            api_endpoint=file_share_endpoint,
                            api_key=self.file_share_api_key,
                            xml_data=xml_data,
                            destination_file_path=destination_file_path
                        )
                else:
                    logging.error("Mapped JSON objects are empty.")
        else:
            logging.error("Message is not a list or a dictionary")

    def _xml_content_to_file_share_api(
            self,
            api_endpoint: str,
            api_key: str,
            xml_data: str,
            destination_file_path: str
    ) -> bool:
        """
        Sends XML content to a file share API.

        :param api_endpoint: The URI of the API's endpoint.
        :type api_endpoint: str
        :param api_key: The API key/token.
        :type api_key: str
        :param xml_data: The XML data to send to the endpoint.
        :type xml_data: str
        :param destination_file_path: The file location where the XML contents will be stored on the file share.
        :type destination_file_path: str
        :return: True when successful, False otherwise.
        :rtype: bool
        """
        self._log(
            f"Uploading file to file share ({destination_file_path})",
            "Uploading file to file share."
        )

        headers = {
            "Content-Type": "application/xml",
            "Content-Disposition": f"attachment;filename=\"{destination_file_path}\"",
            "X-API-KEY": f"{api_key}"
        }

        try:
            response = self.session.post(
                url=api_endpoint,
                data=xml_data,
                headers=headers
            )
            if response.status_code == 200:
                return True
            else:
                logging.error(f"File share API returned unexpected status code '{response.status_code}'.")
        except (
            ConnectionError,
            HTTPError,
            RetryError,
        ) as exception:
            logging.error(f"Could not upload {destination_file_path} to file share API: {str(exception)}")

        return False
