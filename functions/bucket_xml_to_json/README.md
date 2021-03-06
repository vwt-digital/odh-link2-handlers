# Bucket XML to JSON
This function consumes messages gotten via a Google Cloud Platform (GCP) bucket trigger. It gets the file from the storage bucket and checks whether it is an XML file, makes it a JSON and sends it to a GCP topic.
## Setup
1. Make sure a ```config.py``` file exists within the directory, based on the [config.example.py](config.example.py), with the correct configuration:
    ~~~
    REQUIRED_FIELDS = The fields of the XML file that should be in the json, other fields should be skipped. Do not forget to add the root and subroots
    TOPIC_PROJECT_ID = The GCP project ID where the topic resends where the JSON made from the XML file needs to be send to
    TOPIC_NAME = The topic name of the topic where the JSON made from the XML file needs to be send to
    TOPIC_FIELD = The message that is send to the topic contains two fields, one field has the gobits of the message. The other, which name should be defined here, contains the JSON made from the XML.
    TOPIC_MESSAGE_MAPPING = A dictionary that maps the XML fields to JSON message fields
    ~~~
2. Deploy the function with help of the [cloudbuild.example.yaml](cloudbuild.example.yaml) to the Google Cloud Platform.

## Incoming message
The incoming message should be gotten from a [pub sub bucket trigger](https://cloud.google.com/storage/docs/pubsub-notifications).
It should at least contain the following values:
~~~JSON
{
  "bucket": "bucket-name", 
  "name": "file-name"
}
~~~
and
~~~JSON
{
  "event_id": 0, 
  "event_type": "event-type"
}
~~~

## License
This function is licensed under the [GPL-3](https://www.gnu.org/licenses/gpl-3.0.en.html) License
