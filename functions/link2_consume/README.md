# Consume for Link2
This function consumes messages posted on a Pub/Sub Topic, turns them into XML files and puts them on an Azure fileshare.

## Setup
1. Make sure a ```config.py``` file exists within the directory, based on the [config.example.py](config.example.py), with the correct configuration:
    ~~~
    AZURE_STORAGEACCOUNT = The Azure storage account the XML file needs to be send to
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
      "published_message_field_1": "published_message_value_1",
      "published_message_field_2": "published_message_value_2",
      "published_message_field_etcetera": "published_message_value_etcetera"
    }
  ]
}
~~~

## Mapping
The mapping parameter is a dictionary which is set up as illustrated below:
~~~JSON
{
  "xml_root": {
    "xml_subroot": {
      "xml_subroot_field_1": "published_message_field_1",
      "xml_subroot_field_2": "published_message_field_2",
      "xml_subroot_field_etcetera": "published_message_field_etcetera"
    },
    "xml_filename": "xml_filename",
    "ticket_number_field": "published_message_ticket_number_field",
    "address_split": {
      "published_message_address_field": {
          "streetname": "xml_address_field_streetname",
          "number": "xml_address_field_number",
          "addition": "xml_address_field_addition"
      }
    },
    "hardcoded_fields": {
      "xml_subroot_field_1": "hardcoded_value_1",
      "xml_subroot_field_2": "hardcoded_value_2",
      "xml_subroot_field_etcetera": "hardcoded_value_etcetera"
    }
  }
}
~~~
### Required fields
The first field below the XML root field should always be the XML subroot field.

```xml_filename``` The field "xml_filename" is the field with which the XML file should start.  
It is optional to add the string ```GUID``` and/or ```TICKETNR``` to the value of this field.  
If ```GUID``` is defined in the name, it will be replaced by a [UUID](https://en.wikipedia.org/wiki/Universally_unique_identifier).  
If ```TICKETNR``` is defined, it will be replaced by getting the digits from the value of the field defined in ```ticket_number_field```.

### Optional fields
The following fields are optional:

```ticket_number_field``` The field "ticket_number_field" has as value the field in the published message where the ticket number should come from.  
```address_split``` The field "address_split" contains fields which the address should be split out into.  
```hardcoded_fields``` The field "hardcoded_fields" has XML fields which have as their value the hardcoded value they should have.

## License
This function is licensed under the [GPL-3](https://www.gnu.org/licenses/gpl-3.0.en.html) License
