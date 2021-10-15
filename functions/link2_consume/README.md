# Consume for Link2
This function consumes messages posted on a Pub/Sub Topic, the JSON data of this message is converted to 
mapped XML data. This XML data is sent to a custom API endpoint, which will put it in an Azure file share.

## Setup
1. Make sure a ```config.py``` file exists within the directory, based on the [config.example.py](config.example.py), with the correct configuration:
    ~~~
    MESSAGE_PROPERTIES = Dictionary containing the field in the message where the data can be gathered from, this data is henceforth called "message"
    MAPPING_FIELD = A field in the incoming message which value gives the right mapping
    STANDARD_MAPPING = If the mapping field cannot be found in the message, this value is used to get the right mapping
    ID = The ID in the message from where the message can be recognized, can also be an empty string.
    MAPPING = The mapping from the field of the published message to the XML file fields for Link2
    ~~~
2. Make sure the following variables are present in the environment:
    ~~~
    DATA_SELECTOR = The identifier used for this configuration
    PROJECT_ID = The project ID of the GCP project the function is deployed to
    FILE_SHARE_API_KEY_SECRET_ID = The file share API key's Google Secret ID
    ~~~
3. Deploy the function with help of the [cloudbuild.example.yaml](cloudbuild.example.yaml) to the Google Cloud Platform.

## Incoming message
To make sure the function works according to the way it was intented, the incoming messages from a Pub/Sub Topic must have the following structure based on the [company-data structure](https://vwt-digital.github.io/project-company-data.github.io/v1.1/schema):
~~~JSON
{
  "gobits": [ ],
  "message_field": [
    {
      "published_message_field_1": "published_message_value_1",
      "published_message_field_2": "published_message_value_2",
      "published_message_field_etcetera": "published_message_value_etcetera"
    }
  ]
}
~~~

## Message properties
The message properties dictionary can look as follows:
~~~JSON
{
    "message_field": {
        "entity_name": "message_field"
    }
}
~~~
Where ```entity_name``` is hardcoded and ```message_field``` is the field in the message where the data can be gathered from.

## Mapping
The mapping parameter is a dictionary which is set up as illustrated below:
~~~JSON
{
    "mapping_field_value": {
        "file_share_endpoint": "https://www.example.com/some_azure_endpoint",
        "file_share_folder_prefix": "path/to/destination/folder",
        "mapping": {
            "xml_root": {
                "xml_subroot": {
                "xml_subroot_field_1": "published_message_field_1",
                "xml_subroot_field_2": "published_message_field_2",
                "xml_subroot_field_etcetera": "published_message_field_etcetera"
                },
                "xml_filename": "xml_filename"
            }
        }
    }
}
~~~
Where ```mapping_field_value``` should at least be the value defined in the parameter ```STANDARD_MAPPING```.  
The ```xml_root``` can also be an empty string, in that case the ```xml_subroot``` value is used as XML root.

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
It should look as follows:
~~~JSON
{
  "published_message_address_field": {
      "streetname": "xml_address_field_streetname",
      "number": "xml_address_field_number",
      "addition": "xml_address_field_addition"
  }
}
~~~
```hardcoded_fields``` The field "hardcoded_fields" has XML fields which have as their value the hardcoded value they should have.  
It should look as follows:
~~~JSON
{
  "hardcoded_fields": {
      "xml_subroot_field_1": "hardcoded_value_1",
      "xml_subroot_field_2": "hardcoded_value_2",
      "xml_subroot_field_etcetera": "hardcoded_value_etcetera"
  }
}
~~~
```firestore_fields``` The field "firestore_fields" has XML fields which should be looked up in the Firestore database.  
It should look as follows:
~~~JSON
{
  "firestore_fields": {
    "xml_field": {
      "firestore_collection": "firestore_collection_name",
      "firestore_ids": [
          {"firestore_field_1": "json_field_1"},
          {"firestore_field_2": "json_field_2"},
          {"firestore_field_3": {
                        "firestore_collection": "firestore_collection_name_1",
                        "firestore_ids": [
                            {"firestore_field_1": "json_field_1"}
                        ],
                        "firestore_value": "firestore_field_value"
          }},
          {"firestore_field_etcetera": "json_field_etcetara"}
      ],
      "firestore_value": "firestore_field_value",
      "if_not_exists": {
          "make_logbook": {
              "xml_root": {
                  "xml_subroot": {
                  }
              }
          },
          "value": "hardcoded_field_value"
      }
    }
  }
}
~~~
Where:  
```xml_field``` is the field in the XML for which the value should be looked up.  
```firestore_collection``` is the collection in the firestore where the value should be looked up in.  
```firestore_ids``` are the fields in the collection which should fit the JSON value in order to give an XML value.  
The IDs in the Firestore, this ID can be:  
    - A string, then it will just be an ID in the current firestore_collection  
    - A dictionary, then the value will be looked up in another Firestore firestore_collection.
    This dictionary should look the same as a normal "firestore_fields" dictionary list item  
```firestore_value``` is the field in the collection that should be given as XML value if the right IDs are given.  
```if_not_exists``` is an optional field which gives a configuration option to add a logbook file if a value does not exist, if you do not want to create a logbook file, give the string ```DO_NOTHING``` as value.  
This field has a dictionary as value which can contain the following fields:
    - ```make_logbook``` which will make a logbook file if the value cannot be found in the firestore. The logbook field works the same as the other mapping fields.
    - ```value``` which has as value the hardcoded value that should be filled in if the Firestore value cannot be found

```combined_json_fields``` This field contains XML fields that should be combined from fields from the published message defined in
```to_combine_fields```. If this is a list with only 1 value, the combination method will be used to combine all the words in the field.  
The ```combination_method``` can be ```HYPHEN``` or ```NEWLINE```.  
If the field ```start_with_field``` is set to true, the combination will be done by first adding the field name.  
It should look as follows:
~~~JSON
{
  "combined_json_fields": {
      "xml_field": {
          "to_combine_fields": [
              "json_field_1",
              "json_field_2",
              "json_field_etcetera"
          ],
          "combination_method": "HYPHEN or NEWLINE",
          "start_with_field": true
      }
  }
}
~~~

The field ```combined_xml_fields``` combines the final XML fields. It needs an XML mapping in its 'to_combine_fields' field. For more
 information, see [mapping](#mapping).
It should look as follows:
~~~JSON
{
  "combined_json_fields": {
      "xml_field": {
          "to_combine_fields":{
                "xml_root": {
                    "xml_subroot": {
                    "xml_subroot_field_1": "published_message_field_1",
                    "xml_subroot_field_2": "published_message_field_2",
                    "xml_subroot_field_etcetera": "published_message_field_etcetera"
                    },
                    "xml_filename": "xml_filename"
                }
          },
          "combination_method": "HYPHEN or NEWLINE",
          "start_with_field": true
      }
  }
}
~~~

The field ```prefixes``` checks whether a value has a certain prefix.
It should look as follows:
~~~JSON
{
    "prefixes": {
        "xml_field_1": {
            "message_field": "json_field_1",
            "alternative_message_field": "json_field_2",
            "prefixes": [
                "prefix_value_1",
                "prefix_value_2",
                "prefix_value_etcetera"
            ]
        },
        "xml_field_2": {
            "message_field": "json_field_2",
            "alternative_message_field": "",
            "prefixes": [
                "prefix_value_1",
                "prefix_value_2",
                "prefix_value_etcetera"
            ]
        },
        "xml_field_etcetera": {
            "message_field": "json_field_etcetera",
            "prefixes": [
                "prefix_value_1",
                "prefix_value_2",
                "prefix_value_etcetera"
            ]
        }
    }
}
~~~
If the JSON message field defined in ```message_field``` does start with the prefix, it is checked whether the field ```alternative_message_field``` is defined and if it is, whether the JSON message field defined in the ```alternative_message_field``` does start with the right prefix. 

The field ```date_fields``` contains XML fields that should be in the date format ```{year}{month}{day}{hour}{minutes}{seconds}```.  
It should look as follows:
~~~JSON
{
    "date_fields": {
            "xml_field_1": {
                "json_field": "json_field_1",
                "format": [
                    "datetime-format_1",
                    "datetime-format_2",
                    "datetime-format_etcetera"
                ]
            },
            "xml_field_2": {
                "json_field": "json_field_2",
                "format": [
                    "datetime-format_1",
                    "datetime-format_2",
                    "datetime-format_etcetera"
                ]
            },
            "xml_field_etcetera": {
                "json_field": "json_field_etcetera",
                "format": [
                    "datetime-format_1",
                    "datetime-format_2",
                    "datetime-format_etcetera"
                ]
            }
        }
}
~~~
Where the value of ```json_field``` should be the field from the message which the XML field should have as a value but in the right format.  
```format``` is a list of [datetime formats](https://docs.python.org/3/library/datetime.html#strftime-and-strptime-format-codes) where the year, month, day, hour, minutes and seconds can be gotten from. For example ```%d-%m-%Y``` for the date string ```01-01-2021```.

### Extra field values
The following field values are recognized by the code:
```TICKETNR``` The value of the field in the XML should be the ticket number defined in "ticket_number_field"
```HARDCODED``` If you fill in this value, the code will look the field up in the "hardcoded_fields" fields in the mapping.
```ADDRESS_SPLIT``` If you fill in this value, the code will split the address as defined in the field "address_split".
```FIRESTORE``` If you fill in this value, the code will look up the value as defined in the field "firestore_fields".
```COMBINED_JSON``` This value shows the code that the value should be looked up in the field "combined_json_fields".
```COMBINED_XML``` This value shows the code that the value should be looked up in the field "combined_xml_fields".
```PREFIX``` If you fill in this value, the code will look up the prefix that should be used for this value in the "prefixes" field  
```DATE``` If you fill in this value, the code will turn the value of the field into the format ```{year}{month}{day}{hour}{minutes}{seconds}```.  

If multiple field values should be used, they should be split by a hyphen ('-').

### Leave a field empty
If the code has run and a value of the XML contains ```LEAVE_EMTPY``` then it automatically leaves that field empty.
### Example of mapping
Below is a full example of a mapping JSON.
~~~JSON
{
    "CREATE": {
        "file_share_endpoint": "https://www.example.com/some_azure_endpoint",
        "file_share_folder_prefix": "path/to/destination/folder",
        "mapping": {
            "Addresses": {
                    "Address": {
                        "Code": "COMBINED_XML",
                        "TicketNumber": "ticket_number",
                        "StreetName": "ADDRESS_SPLIT",
                        "Number": "ADDRESS_SPLIT",
                        "Addition": "ADDRESS_SPLIT",
                        "PostalCode": "postalcode",
                        "Land": "HARDCODED",
                        "Date": "DATE",
                        "CustomerTicket": "TICKETNR"
                    },
                    "xml_filename": "Address_TICKETNR_GUID",
                    "ticket_number_field": "ticket_number",
                    "address_split": {
                        "address": {
                            "streetname": "StreetName",
                            "number": "Number",
                            "addition": "Addition"
                        }
                    },
                    "date_fields": {
                        "Date": {
                            "json_field": "date",
                            "format": [
                                "%d-%m-%Y",
                                "%d-%m-%y"
                            ]
                        }
                    },
                    "hardcoded_fields": {
                            "Land": "NL"
                    },
                    "combined_xml_fields": {
                        "Code": {
                            "to_combine_fields": {
                                "Addresses": {
                                    "Address": {
                                        "TicketNumber": "ticket_number",
                                        "StreetName": "ADDRESS_SPLIT",
                                    },
                                    "xml_filename": "",
                                    "address_split": {
                                        "address": {
                                            "streetname": "StreetName",
                                            "number": "Number",
                                            "addition": "Addition"
                                        }
                                    }
                                }
                            },
                            "combination_method": "HYPHEN"
                        }
                    }
            },
            "Contacts": {
                "Contact": {
                    "TicketNumber": "ticket_number",
                    "Name": "name",
                    "Email": "email_address",
                    "Phonenumber": "PREFIX",
                    "JobType": "FIRESTORE",
                    "BusinessUnit": "FIRESTORE",
                    "CustomerTicket": "TICKETNR",
                    "ContactInformation": "COMBINED_JSON",
                    "NextJob": "FIRESTORE"
                },
                "xml_filename": "Activity_TICKETNR_GUID",
                "ticket_number_field": "ticket_number",
                "firestore_fields": {
                    "JobType": {
                        "firestore_collection": "job_types_collection",
                        "firestore_ids": [
                            {"incoming_job_type_firestore": "incoming_job_type"}
                        ],
                        "firestore_value": "outgoing_job_type"
                    },
                    "BusinessUnit": {
                        "firestore_collection": "business_units_collection",
                        "firestore_ids": [
                            {"incoming_job_type_firestore": "incoming_job_type"},
                            {"incoming_name_field_firestore": "incoming_name_field"}
                        ],
                        "firestore_value": "outgoing_business_unit",
                        "if_not_exists": {
                            "make_logbook": {
                                "logbooks": {
                                    "logbook": {
                                        "TicketNumber": "ticket_number",
                                        "LogboekTekst": "HARDCODED-name"
                                        },
                                        "xml_filename": "Logbook_TICKETNR_GUID",
                                        "ticket_number_field": "ticket_number",
                                        "hardcoded_fields": {
                                            "LogboekTekst": "Made logbook file for contact:"
                                        }
                                }
                            },
                            "value": "Unknown"
                        }
                    },
                    "NextJob": {
                        "firestore_collection": "jobs_collection",
                        "firestore_ids": [
                            {"incoming_name_field_firestore": "incoming_name_field"},
                            {"incoming_job_type_firestore": {
                                    "firestore_collection": "job_types_collection",
                                    "firestore_ids": [
                                        {"incoming_job_type_firestore": "incoming_job_type"}
                                    ],
                                    "firestore_value": "outgoing_job_type"
                            }},
                        ],
                        "firestore_value": "outgoing_next_job"
                    }
                },
                "combined_json_fields": {
                        "ContactInformation": {
                            "to_combine_fields": [
                                "name",
                                "email_address"
                            ],
                            "combination_method": "NEWLINE",
                            "start_with_field": false
                        }
                },
                "prefixes": {
                        "Phonenumber": {
                            "message_field": "phonenumber",
                            "prefixes": [
                                "06",
                                "00316",
                                "+316"
                            ]
                        }
                }
            }
        }
    }
}
~~~
Here the parameter ```STANDARD_MAPPING``` will be set to "CREATE".

### Example of incoming message
~~~
{
        'gobits': [
            {
            'processed': '2021-01-01T00:00:00.000Z'
            }
        ],
        'email': {
            'ticket_number': '123456',
            'postalcode': '1234HP',
            'address': 'an address 1',
            'name': 'A. nonymous',
            'email_address': 'anonymous@a.nonymous',
            'phonenumber': '0612345678',
            'incoming_job_type': 'job',
            'incoming_name_field': 'name',
            'date': '01-01-2021',
            'mapping_field': 'CREATE'
        }
}
~~~
In the configuration, the parameter ```MAPPING_FIELD``` can be set to ```mapping_field```.  
The field ```MESSAGE_PROPERTIES``` will be defined as follows:
~~~JSON
{
    "email": {
        "entity_name": "email"
    }
}
~~~

## License
This function is licensed under the [GPL-3](https://www.gnu.org/licenses/gpl-3.0.en.html) License
