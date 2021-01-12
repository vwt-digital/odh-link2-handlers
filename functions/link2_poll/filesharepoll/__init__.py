from config import AZURE_SOURCESHARE, REQUIRED_NAME_START, REQUIRED_EXTENSION, GCP_STORAGE_BUCKET, PROCESSED_FILES_FOLDER
import os
import logging

from azure.storage.fileshare import ShareClient, ShareLeaseClient, ShareFileClient
from azure.core.exceptions import ResourceNotFoundError, HttpResponseError

from google.cloud import secretmanager, storage

logging.basicConfig(level=logging.INFO)
logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.ERROR)


class FileSharePoll(object):
    def __init__(self):
        self.sourceshare = AZURE_SOURCESHARE
        self.storageaccount = os.environ.get('AZURE_STORAGEACCOUNT', 'Required parameter is missing')
        self.project_id = os.environ.get('PROJECT_ID', 'Required parameter is missing')
        self.storagekey_secret_id = os.environ.get('AZURE_STORAGEKEY_SECRET_ID', 'Required parameter is missing')
        client = secretmanager.SecretManagerServiceClient()
        secret_name = f"projects/{self.project_id}/secrets/{self.storagekey_secret_id}/versions/latest"
        key_response = client.access_secret_version(request={"name": secret_name})
        self.storagekey = key_response.payload.data.decode("UTF-8")
        self.required_extension = REQUIRED_EXTENSION
        self.required_name_start = REQUIRED_NAME_START
        self.gcp_bucket_name = GCP_STORAGE_BUCKET
        self.share = ShareClient(account_url=f"https://{self.storageaccount}.file.core.windows.net/",
                                 share_name=self.sourceshare, credential=self.storagekey)
        self.processed_files_folder = PROCESSED_FILES_FOLDER

    def poll(self):
        # First check if a file exists on the given File Share path
        files_found = self.check_for_files()
        correct_files = []
        for file_found in files_found:
            # Then add every file that has the correct extension, is not a directory and starts with the correct value to a list
            if file_found['name'].endswith(self.required_extension) and \
               file_found['is_directory'] is False and \
               file_found['name'].startswith(self.required_name_start):
                correct_files.append(file_found['name'])
        # Go through list with correct files
        for correct_file in correct_files:
            # Get file from share
            file_on_share = self.share.get_file_client(correct_file)
            file_lease = None
            if self.check_file_exists(file_on_share):
                # Put a file lease on the file so that it cannot be touched
                file_lease = self.try_file_lease(file_on_share)
            if file_lease:
                stream = file_on_share.download_file()
                fileshare_file = stream.readall()
                # Then put the file on the GCP bucket
                self.put_file_on_bucket(correct_file, fileshare_file)
                # Then put the file to another bucket to signify that it has been put on the GCP bucket
                self.put_files_in_folder(correct_file, fileshare_file)
                # Release the file lease
                file_lease.break_lease(timeout=5)
                # Remove the original file from the File Share
                file_on_share.delete_file()

    def put_files_in_folder(self, file_name, file_body):
        destfilepath = "{}/{}".format(self.processed_files_folder, os.path.basename(file_name))
        file_on_share = self.share.get_file_client(destfilepath)
        try:
            file_on_share.create_file(size=0)
        except HttpResponseError:
            ShareLeaseClient(file_on_share).break_lease()
            file_on_share.create_file(size=0)
        file_lease = file_on_share.acquire_lease(timeout=5)
        logging.info("Writing to FileShare")
        file_on_share.upload_file(file_body, lease=file_lease)
        file_lease.release(timeout=5)

    def put_file_on_bucket(self, file_name, file_body):
        client = storage.Client()
        bucket = client.get_bucket(self.gcp_bucket_name)
        blob = bucket.blob(file_name)
        blob.upload_from_string(file_body, content_type="text/xml")

    def check_file_exists(self, file_on_share: ShareFileClient):
        try:
            file_on_share.get_file_properties()
        except ResourceNotFoundError:
            return False
        return True

    def try_file_lease(self, file_on_share: ShareFileClient):
        file_lease = None
        try:
            file_lease = file_on_share.acquire_lease(timeout=5)
        except HttpResponseError:
            logging.error("File exists, but still locked.")
            return None
        return file_lease

    def check_for_files(self):
        logging.info("Polling files from FileShare")
        azure_files = list(self.share.list_directories_and_files())
        return azure_files
