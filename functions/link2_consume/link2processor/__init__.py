import config
import os
import logging
import xmltodict

from azure.storage.fileshare import ShareClient, ShareLeaseClient
from azure.core.exceptions import HttpResponseError

from google.cloud import secretmanager

logging.basicConfig(level=logging.INFO)
logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.ERROR)


class Link2Processor(object):
    def __init__(self):
        self.data_selector = os.environ.get('DATA_SELECTOR', 'Required parameter is missing')
        self.meta = config.MESSAGE_PROPERTIES[self.data_selector]
        self.destshare = config.AZURE_DESTSHARE
        self.storageaccount = os.environ.get('AZURE_STORAGEACCOUNT', 'Required parameter is missing')
        self.project_id = os.environ.get('PROJECT_ID', 'Required parameter is missing')
        self.storagekey_secret_id = os.environ.get('AZURE_STORAGEKEY_SECRET_ID', 'Required parameter is missing')
        client = secretmanager.SecretManagerServiceClient()
        secret_name = f"projects/{self.project_id}/secrets/{self.storagekey_secret_id}/versions/latest"
        key_response = client.access_secret_version(request={"name": secret_name})
        self.storagekey = key_response.payload.data.decode("UTF-8")
        self.sourcepath_field = config.SOURCEPATH_FIELD
        self.mapping_json = config.MAPPING

    def map_json(self, input_json):
        output_json_subelement = {}
        for field in self.mapping_json:
            field_json = self.mapping_json[field]
            field_map = input_json.get(field_json)
            if field_map == "None" or not field_map:
                row = {field: ""}
            else:
                row = {field: field_map}
            output_json_subelement.update(row)
        output_json = {config.XML_ROOT: {config.XML_ROOT_SUBELEMENT: output_json_subelement}}
        return output_json

    def make_xml(self, selector_data, file_name):
        # First map the needed XML data to the message
        mapped_json = self.map_json(selector_data)
        # Then turn the json into an XML
        return xmltodict.unparse(mapped_json)

    def msg_to_fileshare(self, msg):
        sourcepath_field_msg = msg.get(self.sourcepath_field)
        if not sourcepath_field_msg:
            logging.error(f"The sourcepath field {sourcepath_field_msg} cannot be found in message")

        destfilepath = f"{self.data_selector}_{sourcepath_field_msg}.xml"

        logging.info(f"Putting {destfilepath} on //{self.storageaccount}/{self.destshare}")
        share = ShareClient(account_url=f"https://{self.storageaccount}.file.core.windows.net/",
                            share_name=self.destshare, credential=self.storagekey)
        file_on_share = share.get_file_client(destfilepath)
        try:
            file_on_share.create_file(size=0)
        except HttpResponseError:
            ShareLeaseClient(file_on_share).break_lease()
            file_on_share.create_file(size=0)
        file_lease = file_on_share.acquire_lease(timeout=5)
        sourcefile = self.make_xml(msg, destfilepath)
        logging.info(f"Writing to //{self.storageaccount}/{self.destshare}/{destfilepath}")
        file_on_share.upload_file(sourcefile, lease=file_lease)
        file_lease.release(timeout=5)

    def process(self, payload):
        selector_data = payload[self.data_selector]

        if isinstance(selector_data, list):
            for data in selector_data:
                self.msg_to_fileshare(data)
        elif isinstance(selector_data, dict):
            self.msg_to_fileshare(selector_data)
        else:
            logging.error("Message is not a list or a dictionary")
