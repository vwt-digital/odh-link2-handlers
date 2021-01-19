from config import AZURE_SOURCESHARE, REQUIRED_NAME_START, REQUIRED_EXTENSION, GCP_STORAGE_BUCKET, AZURE_PATH, GCP_STORAGE_BUCKET_FOLDER
import os
import logging
from datetime import datetime

from azure.storage.fileshare import ShareFileClient, ShareDirectoryClient
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
        self.gcp_folder = GCP_STORAGE_BUCKET_FOLDER
        self.azure_path = AZURE_PATH
        self.azure_directory = None
        if self.storageaccount:
            self.azure_directory = ShareDirectoryClient(account_url=f"https://{self.storageaccount}.file.core.windows.net/",
                                                        share_name=self.sourceshare, directory_path=self.azure_path,
                                                        credential=self.storagekey)

    def poll(self):
        # Check if storage account is set
        if self.storageaccount and self.azure_directory:
            # First check if a file exists on the given File Share path
            files_found = self.check_for_files()
            correct_files = []
            for file_found in files_found:
                # Then add every file that has the correct extension, is not a directory, starts with the correct value to a list
                # and has a size of more than 0
                if file_found['name'].endswith(self.required_extension) and \
                   file_found['is_directory'] is False and \
                   file_found['name'].startswith(self.required_name_start) and \
                   file_found['size'] > 0:
                    correct_files.append(file_found['name'])
            # Go through list with correct files
            for correct_file in correct_files:
                # Get file from share
                file_on_share = self.azure_directory.get_file_client(correct_file)
                file_lease = None
                if self.check_file_exists(file_on_share):
                    # Put a file lease on the file so that it cannot be touched
                    file_lease = self.try_file_lease(file_on_share)
                if file_lease:
                    stream = file_on_share.download_file()
                    fileshare_file = stream.readall()
                    # Then put the file on the GCP bucket
                    self.put_file_on_bucket(correct_file, fileshare_file)
                    # Remove the original file from the File Share
                    logging.info("Deleting file from Azure Fileshare")
                    file_on_share.delete_file(lease=file_lease)
        else:
            logging.info("No storage account is set")

    def put_file_on_bucket(self, file_name, file_body):
        # Get today's date
        today = datetime.today()
        day = today.day
        month = today.month
        year = today.year
        # Add folder on GCP to filename
        file_name = f"{self.gcp_folder}/{year}/{month}/{day}/{file_name}"
        logging.info("Putting file on GCP bucket")
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

    def try_file_lease(self, file_on_share: ShareDirectoryClient):
        file_lease = None
        try:
            file_lease = file_on_share.acquire_lease(timeout=5)
        except HttpResponseError:
            logging.info("File exists, but still locked.")
            return None
        return file_lease

    def check_for_files(self):
        logging.info("Polling files from FileShare")
        azure_files = list(self.azure_directory.list_directories_and_files())
        return azure_files
