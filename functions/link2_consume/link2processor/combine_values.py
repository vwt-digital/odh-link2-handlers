import logging

logging.basicConfig(level=logging.INFO)


class CombinedValuesProcessor(object):
    def __init__(self, link2_processor):
        self.link2_processor = link2_processor

    def combined_value(self, field, combined_fields, input_json):
        field_value = ""
        # Get the dictionary belonging to the value
        if combined_fields:
            combined_value = ""
            # Get the XML field configuration
            xml_field_config = combined_fields.get(field)
            if xml_field_config:
                # If combination method is hypen
                combination_method = xml_field_config["combination_method"]
                if combination_method == "HYPHEN":
                    com_json_fields = xml_field_config["to_combine_fields"]
                    if len(com_json_fields) == 1:
                        com_json_value = input_json[com_json_fields[0]]
                        combined_value = com_json_value.replace(" ", "-")
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
                                    combined_value = (
                                        f"{com_json_field}: {combined_value}"
                                    )
                                else:
                                    combined_value = com_json_value
                # If combination method is newline
                elif combination_method == "NEWLINE":
                    for com_json_field in xml_field_config["to_combine_fields"]:
                        # If the input_json contains the field to combine
                        if com_json_field in input_json:
                            com_json_value = input_json[com_json_field]
                            com_json_value = com_json_value.replace(".\\n", ". ")
                            com_json_value = com_json_value.replace("\\n", "")
                            if combined_value:
                                # If the combination should start with the original JSON field
                                if xml_field_config["start_with_field"]:
                                    combined_value = (
                                        combined_value
                                        + f"\n\n{com_json_field}: {com_json_value}"
                                    )
                                else:
                                    combined_value = (
                                        combined_value + f"\n\n{com_json_value}"
                                    )
                            else:
                                # If the combination should start with the original JSON field
                                if xml_field_config["start_with_field"]:
                                    combined_value = (
                                        f"{com_json_field}: {com_json_value}"
                                    )
                                else:
                                    combined_value = com_json_value
                        else:
                            logging.error(
                                f"Cannot find field {com_json_field} in provided data"
                            )
                            return False, field_value
                else:
                    logging.error(
                        f"Combination method {combination_method} defined in config is unknown"
                    )
                    return False, field_value
            else:
                logging.error(
                    f"The 'combined_json_fields' or 'combined_xml_fields' field does not contain field {field}"
                )
                return False, field_value
            field_value = combined_value
        else:
            logging.error(
                "The config contains the value COMBINED_JSON or COMBINED_XML but"
                " the 'combined_json_fields' or 'combined_xml_fields' field are not defined"
            )
            return False, field_value
        return True, field_value

    def combined_value_xml(self, field, combined_fields, input_json, added_jsons):
        # Get field from 'combined_xml_fields'
        to_combine_info = combined_fields.get(field)
        if not to_combine_info:
            logging.error(
                f"Could not find field {field} in field 'combined_xml_fields' in config"
            )
            return False, ""
        # Get 'to_combine_fields' info
        to_com_fields = to_combine_info["to_combine_fields"]
        # Get field values
        field_values = self.link2_processor.map_json(
            to_com_fields, input_json, True, added_jsons
        )
        # Combine values
        combination_method = to_combine_info["combination_method"]
        combined_value = ""
        # If combination method is hypen
        if combination_method == "HYPHEN":
            if len(field_values) == 1:
                # For every field in field_values
                for field in field_values[0]:
                    com_json_value = field_values[0][field]
                    combined_value = com_json_value.replace(" ", "-")
                    # If the combination should start with the original JSON field
                    if to_combine_info["start_with_field"]:
                        combined_value = f"{field_values[0][field]}: {combined_value}"
            else:
                for row in field_values:
                    # For every field in the row
                    for field in row:
                        com_json_value = row[field]
                        # If there is already a combined value
                        if combined_value:
                            if to_combine_info["start_with_field"]:
                                combined_value = (
                                    combined_value + f"-{field}:{com_json_value}"
                                )
                            else:
                                combined_value = combined_value + f"-{com_json_value}"
                        else:
                            # If the combination should start with the original JSON field
                            if to_combine_info["start_with_field"]:
                                combined_value = f"{field}:{com_json_value}"
                            else:
                                combined_value = com_json_value
        # If combination method is newline
        elif combination_method == "NEWLINE":
            if len(field_values) == 1:
                # For every field in field_values
                for field in field_values[0]:
                    com_json_value = field_values[0][field]
                    combined_value = com_json_value.replace(" ", "\n")
                    # If the combination should start with the original JSON field
                    if to_combine_info["start_with_field"]:
                        combined_value = f"{field_values[0][field]}: {combined_value}"
            else:
                for row in field_values:
                    # For every field in the row
                    for field in row:
                        com_json_value = row[field]
                        com_json_value = com_json_value.replace(".\\n", ". ")
                        com_json_value = com_json_value.replace("\\n", "")
                        # If there is already a combined value
                        if combined_value:
                            # If the combination should start with the original JSON field
                            if to_combine_info["start_with_field"]:
                                combined_value = (
                                    combined_value + f"\n\n{field}: {com_json_value}"
                                )
                            else:
                                combined_value = (
                                    combined_value + f"\n\n{com_json_value}"
                                )
                        else:
                            # If the combination should start with the original JSON field
                            if to_combine_info["start_with_field"]:
                                combined_value = f"{field}: {com_json_value}"
                            else:
                                combined_value = com_json_value
        else:
            logging.error(
                f"Combination method {combination_method} defined in config is unknown"
            )
            return False, ""
        return True, combined_value
