import logging
from google.cloud import storage, pubsub_v1
import xmltodict
import json
from config import REQUIRED_FIELDS, TOPIC_PROJECT_ID, TOPIC_NAME, TOPIC_FIELD, TOPIC_MESSAGE_MAPPING
from gobits import Gobits

logging.basicConfig(level=logging.INFO)


def process(data, context):
    # Get file from bucket
    bucket = data['bucket']
    file_path = data['name']
    # Check if file is a xml file
    if file_path.endswith(".xml"):
        client = storage.Client()
        bucket = client.get_bucket(bucket)
        blob = bucket.get_blob(file_path)
        # XML to JSON
        xml_json = xml_to_json(blob.download_as_string())
        # JSON to topic
        if xml_json:
            return_bool = json_to_topic(xml_json, context)
            return return_bool
        else:
            logging.info("No field in the XML was a required field")


def json_to_topic(xml_json, context):
    gobits = Gobits.from_context(context=context)
    msg = {
            "gobits": [gobits.to_json()],
            TOPIC_FIELD: xml_json
    }
    # Publish to topic
    try:
        publisher = pubsub_v1.PublisherClient()
        topic_path = "projects/{}/topics/{}".format(
            TOPIC_PROJECT_ID, TOPIC_NAME)
        # print(json.dumps(msg, indent=4, sort_keys=True))
        future = publisher.publish(
            topic_path, bytes(json.dumps(msg).encode('utf-8')))
        future.add_done_callback(
            lambda x: logging.info('Published JSON made from XML on topic {}'.format(TOPIC_NAME))
        )
        return True
    except Exception as e:
        logging.exception('Unable to publish JSON made from XML ' +
                          'to topic because of {}'.format(e))
    return False


def xml_to_json(xml):
    xml_json = xmltodict.parse(xml)
    # Make sure that only the fields that are needed are in the JSON
    new_xml_json = check_xml(xml_json)
    # Map fields to json message fields
    xml_json_mapped = map_fields(new_xml_json)
    return xml_json_mapped


# Recursive function that checks whether a field of the given JSON
# is in required fields
def check_xml(xml_json):
    xml_json_copy = xml_json.copy()
    for field, value in xml_json.items():
        if field not in REQUIRED_FIELDS:
            del xml_json_copy[field]
        elif isinstance(value, dict):
            xml_json_copy[field] = check_xml(xml_json_copy[field])
    return xml_json_copy


def map_fields(xml_json):
    xml_json_mapped = {}
    for field in xml_json:
        mapped_field = TOPIC_MESSAGE_MAPPING.get(field)
        if not mapped_field:
            logging.error(f"Could not find {field} in topic message mapping.")
        value = xml_json[field]
        # If value is dictionary
        if isinstance(value, dict):
            # Call function again with value
            value = map_fields(value)
        xml_json_mapped.update({mapped_field: value})
    return xml_json_mapped
