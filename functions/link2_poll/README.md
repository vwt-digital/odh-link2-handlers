# Link2 Poll
This function polls from [Azure Fileshare](https://docs.microsoft.com/en-us/azure/storage/files/storage-files-introduction),
 gets the files with a predefined extension that start with a predefined string and puts them on a
 [Google Cloud Platform Storage](https://cloud.google.com/storage) bucket.

## Setup
1. Make sure a ```config.py``` file exists within the directory, based on the [config.example.py](config.example.py), with the correct configuration:
    ~~~
    AZURE_SOURCESHARE = Name of the share storage where the file needs to be polled 
    REQUIRED_NAME_START = The string which the file to be polled needs to start with
    REQUIRED_EXTENSION = The extension which the file to be polled needs to have
    PROCESSED_FILES_FOLDER = The folder in the Azure FileShare where the polled file needs to be put after it is processed
    GCP_STORAGE_BUCKET = The Google Cloud Platform Storage Bucket the polled file needs to be put in
    ~~~
2. Make sure the following variables are present in the environment:
    ~~~
    AZURE_STORAGEACCOUNT = The Azure storage account the XML file needs to be send to
    AZURE_STORAGEKEY_SECRET_ID = The Azure storage key
    ~~~
3. Deploy the function with help of the [cloudbuild.example.yaml](cloudbuild.example.yaml) to the Google Cloud Platform.

## License
This function is licensed under the [GPL-3](https://www.gnu.org/licenses/gpl-3.0.en.html) License
