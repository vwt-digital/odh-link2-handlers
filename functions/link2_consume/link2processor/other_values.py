import re
import logging
import datetime

logging.basicConfig(level=logging.INFO)


class OtherValuesProcessor(object):
    def __init__(self, link2_processor):
        self.link2_processor = link2_processor

    def get_ticket_nr(self, ticket_number_field, input_json):
        # Get all digits
        digit_list = re.findall(r'\d+', input_json[ticket_number_field])
        # Check if there's only 1 digit part
        if len(digit_list) > 1:
            logging.error("Multiple digit parts in ticket number")
            return False
        # Return ticket number
        return digit_list[0]

    def hardcoded_value(self, mapping_json, xml_root, field):
        field_value = ""
        # Check if field is in "hardcoded_fields"
        hardcoded_fields = mapping_json[xml_root].get("hardcoded_fields")
        if hardcoded_fields:
            if field in hardcoded_fields:
                field_value = hardcoded_fields[field]
            else:
                logging.error(f"The 'hardcoded_fields' field does not contain field {field}")
                return False, field_value
        else:
            logging.error("The config contains the value HARDCODED but the 'hardcoded_fields' field is not defined")
            return False, field_value
        return True, field_value

    def address_split_value(self, field, address_street, address_number, address_addition):
        field_value = ""
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
            return False, field_value
        return True, field_value

    def ticket_number_value(self, mapping_json, xml_root, input_json):
        field_value = ""
        # Check what the field is that should be mapped to the ticket_number_field
        # Check if there's an ticket number field defined
        ticket_number_field = mapping_json[xml_root].get('ticket_number_field')
        if ticket_number_field:
            ticket_nr = self.get_ticket_nr(ticket_number_field, input_json)
            if ticket_nr:
                field_value = ticket_nr
            else:
                return False, field_value
        else:
            logging.error("Ticket number is needed but ticket number field is not defined")
            return False, field_value
        return True, field_value

    def prefix_value(self, field, prefixes_field, input_json):
        field_value = ""
        if not prefixes_field:
            logging.error("The config contains the value PREFIX but the 'prefixes' field is not defined")
            return False, field_value
        xml_dict = prefixes_field.get(field)
        if not xml_dict:
            logging.error(f"The field {field} cannot be found in the 'prefixes' field")
            return False, field_value
        # Check what the value is of the field
        message_field = xml_dict.get('message_field')
        field_value = input_json.get(message_field)
        if field_value == "None" or not field_value:
            logging.error(f"The field {field} contains value PREFIX but the message field value cannot be found ")
            return False, field_value
        # Check if the value starts with the specified prefix
        prefix = xml_dict['prefix']
        if not field_value.startswith(prefix):
            logging.error(f"The field {message_field} in the message does not start with the defined prefix in 'phonenumber_field'")
            return False, field_value
        return True, field_value

    def date_value(self, field, date_fields, input_json):
        field_value = ""
        # Get JSON field
        right_dict = date_fields.get(field)
        if not right_dict:
            logging.error(f"Field {field} cannot be found in 'date_fields' field")
            return False, field_value
        json_field = right_dict['json_field']
        # Get field from message
        success, original_value = self.message_value(input_json, json_field)
        if success is False:
            logging.error(f"Field {json_field} defined in 'date_fields' could not be found in the message")
            return False, field_value
        # Get format
        date_format = right_dict['format']
        # Turn the JSON field into the right date format
        for df in date_format:
            # Check if this is the right format
            try:
                field_value = datetime.datetime.strptime(original_value, df)
                break
            except ValueError:
                # If the right format could not be found, the field should just stay empty
                field_value = ""
        # If it resulted in a datetime object
        if isinstance(field_value, datetime.datetime):
            # Make it into the right string
            year = field_value.year
            month = field_value.month
            day = field_value.day
            hour = str(field_value.hour).zfill(2)
            minute = str(field_value.minute).zfill(2)
            seconds = str(field_value.second).zfill(2)
            field_value = f"{year}{month}{day}{hour}{minute}{seconds}"
        return True, field_value

    def message_value(self, input_json, field_json):
        field_value = ""
        field_value = input_json.get(field_json)
        if field_value == "None" or not field_value:
            field_value = ""
        return True, field_value
