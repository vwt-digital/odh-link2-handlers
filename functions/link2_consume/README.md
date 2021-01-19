# Consume for Link2
This function consumes messages posted on a Pub/Sub Topic, turns them into XML files and puts them on an Azure fileshare.

## Setup
1. Make sure a ```config.py``` file exists within the directory, based on the [config.example.py](config.example.py), with the correct configuration:
    ~~~
    AZURE_DESTSHARE = Name of the share storage where the file needs to go to
    AZURE_DESTSHARE_FOLDERS = Prefix of the file containing the folders the file needs to be placed in
    SOURCEPATH_FIELD = Field in the published message from which the Azure sourcefilepath can be created
    XML_ROOT = The root field of the XML file
    XML_ROOT_SUBELEMENT = The first subelement of the root
    MAPPING = The mapping from the field of the published message to the XML file fields for Link2
    ~~~
2. Make sure the following variables are present in the environment:
    ~~~
    DATA_SELECTOR = The identifier used for this configuration
    PROJECT_ID = The project ID of the GCP project the function is deployed to
    AZURE_STORAGEACCOUNT = The Azure storage account the XML file needs to be send to
    AZURE_STORAGEKEY_SECRET_ID = The Azure storage key
    ~~~
3. Deploy the function with help of the [cloudbuild.example.yaml](cloudbuild.example.yaml) to the Google Cloud Platform.

## Incoming message
To make sure the function works according to the way it was intented, the incoming messages from a Pub/Sub Topic must have the following structure based on the [company-data structure](https://vwt-digital.github.io/project-company-data.github.io/v1.1/schema):
~~~JSON
{
  "gobits": [ ],
  "notifications": [
    {
      "published-message-field-1": "published-message-field-1",
      "published-message-field-2": "published-message-field-2"
    }
  ]
}
~~~

## License
This function is licensed under the [GPL-3](https://www.gnu.org/licenses/gpl-3.0.en.html) License
