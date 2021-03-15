import logging
from firestoreprocessor import FirestoreProcessor

logging.basicConfig(level=logging.INFO)


class FirestoreValuesProcessor(object):
    def __init__(self, link2_processor):
        self.gcp_firestore = FirestoreProcessor()
        self.link2_processor = link2_processor

    def firestore_value(self, field, firestore_fields, input_json, logbooks, added_jsons):
        field_value = ""
        # The value can be looked up in the firestore
        # Get the dictionary belonging to the value
        if not firestore_fields:
            logging.error("The config contains the value FIRESTORE but the 'firestore_fields' field is not defined")
            return False, "", []
        # Get the dictionary belonging to the XML field
        fs_dict = firestore_fields.get(field)
        if not fs_dict:
            logging.error(f"The 'firestore_fields' field does not contain key '{field}'")
            return False, "", []
        # Get the right values from the JSON
        json_values = []
        for id_dict in fs_dict['firestore_ids']:
            for fs_id in id_dict:
                json_field = id_dict[fs_id]
                # Check if json_field is a string or a dictionary
                if isinstance(json_field, str):
                    # If it is a string
                    # Check if json value exists in the input json
                    json_value = input_json.get(json_field)
                    if not json_value:
                        logging.error(f"The field {json_field} cannot be found in the message")
                        return False, "", []
                    json_values.append({fs_id: json_value})
                elif isinstance(json_field, dict):
                    # If it is a dictionary
                    # The value has to be looked up in another Firestore collection
                    success, json_value, new_logbooks = self.firestore_value(field, json_field, input_json, logbooks, added_jsons)
                    if success is False:
                        logging.error(f"The field {field} contains a field that has to be looked up in a Firestore collection"
                                      " but there was an error.")
                        return False, "", []
                    json_values.append({fs_id: json_value})
                    logbooks = new_logbooks
        # Get the value of the XML dict from the firestore
        collection_name = fs_dict['firestore_collection']
        succeeded, xml_fs_value = self.gcp_firestore.get_value(collection_name, json_values,
                                                               fs_dict['firestore_value'])
        if succeeded:
            field_value = xml_fs_value
        else:
            # Check if the field "if_not_exists" is defined
            if not fs_dict.get("if_not_exists"):
                logging.error(f"The Firestore querie '{xml_fs_value}'"
                              f" did not result in a value for XML field '{field}'"
                              f" in collection {collection_name}")
                return False, "", []
            # Check if the value of this field is not "DO_NOTHING"
            if fs_dict["if_not_exists"] != "DO_NOTHING":
                # Check if in this field, the field "make_logbook" is defined
                logbook_mapping = fs_dict["if_not_exists"].get("make_logbook")
                if not logbook_mapping:
                    logging.error(f"The Firestore querie '{xml_fs_value}'"
                                  f" did not result in a value for XML field '{field}'"
                                  f" in collection {collection_name}")
                    return False, "", []
                # If logbook has to be made
                logging.info(f"The Firestore querie '{xml_fs_value}'"
                             f" did not result in a value for XML field '{field}'"
                             f" in collection {collection_name}, "
                             "making logbook if it was not made already.")
                # Make logbooks
                mapped_logbooks = self.link2_processor.map_json(logbook_mapping, input_json, False, added_jsons)
                # Add logbook to logbooks
                logbooks.extend(mapped_logbooks)
                # If config contains "value", fill in that hardcoded value
                value_else = fs_dict["if_not_exists"].get("value")
                if value_else:
                    field_value = value_else
        return True, field_value, logbooks
