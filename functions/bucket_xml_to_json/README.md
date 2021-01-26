# Consume for Link2
This function consumes messages posted on a Pub/Sub Topic, turns them into XML files and puts them on an Azure fileshare.

## Setup
1. Make sure a ```config.py``` file exists within the directory, based on the [config.example.py](config.example.py), with the correct configuration:
    ~~~

    ~~~
2. Make sure the following variables are present in the environment:
    ~~~

    ~~~
3. Deploy the function with help of the [cloudbuild.example.yaml](cloudbuild.example.yaml) to the Google Cloud Platform.

## Incoming message
The incoming message should be gotten from a [pub sub bucket trigger](https://cloud.google.com/storage/docs/pubsub-notifications).
It looks as follows:
~~~JSON
{
  "bucket": "bucket-name", 
  "name": "file-name"}, 
  {
    "event_id": 0, 
    "event_type": "event-type"
  }
~~~

## License
This function is licensed under the [GPL-3](https://www.gnu.org/licenses/gpl-3.0.en.html) License
