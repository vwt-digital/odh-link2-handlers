[![CodeFactor](https://www.codefactor.io/repository/github/vwt-digital-solutions/link2-handlers/badge)](https://www.codefactor.io/repository/github/vwt-digital-solutions/link2-handlers)

# link2-handlers
This repository contains handlers for Link2.

## Functions
The functions folder contains Cloud Functions.

### Link2 consume
This folder contains the code to consume messages from the ODH and send them to Link2. [Here](https://github.com/vwt-digital-solutions/link2-handlers/tree/develop/functions/link2_consume) its README can be found.


### Link2 poll
This folder contains the code to poll files from Link2. [Here](https://github.com/vwt-digital-solutions/link2-handlers/tree/develop/functions/link2_poll) its README can be found.

### Bucket XML to JSON
This folder contains the code that should get triggered when a file is placed on a Google Cloud Platform (GCP) storage bucket. It checks whether it is an XML file, makes it a JSON and sends it to a GCP topic. [Here](https://github.com/vwt-digital-solutions/link2-handlers/tree/develop/functions/bucket_xml_to_json) its README can be found.