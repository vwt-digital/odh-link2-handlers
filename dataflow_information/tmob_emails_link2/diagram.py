from diagrams import Cluster, Diagram, Edge

from diagrams.gcp.analytics import PubSub
from diagrams.gcp.compute import Functions
from diagrams.gcp.storage import Storage
from diagrams.gcp.database import Firestore

from diagrams.azure.storage import BlobStorage

from diagrams.generic.storage import Storage as GenericStorage

publish_edge = Edge(label="Publish")
consume_edge = Edge(label="Consume")
import_edge = Edge(label="Link2 import script from VWT Operations")
export_edge = Edge(label="Link2 export script from VWT Operations")
bucket_trigger_edge = Edge(label="Bucket trigger")

with Diagram("JSON message to Link2", show=False):

    with Cluster("GCP Operational Data Hub Platform"):

        with Cluster("Operational Data Hub"):
            with Cluster("vwt-p-gew1-\nodh-hub-\ntmobile-parsed-problem-emails "):
                mail_parser_pubsub = PubSub("vwt-p-gew1-\nodh-hub-\ntmobile-parsed-problem-emails-link2-\npush-sub")

            with Cluster("vwt-p-gew1-\nodh-hub-\nns-link2-statuses "):
                link2_statuses_pubsub = PubSub("vwt-p-gew1-\nodh-hub-\nns-link2-statuses-\npush-sub")

        with Cluster("vwt-p-gew1-ns-link2-int"):
            consume_mail_function = Functions("vwt-p-gew1-\nns-link2-int-\nconsume-parsed-emails-to-link2-func")

            mail_parser_pubsub >> consume_mail_function

            firestore = Firestore("Firestore")

            consume_mail_function >> firestore
            firestore >> consume_mail_function

            link2_poll_function = Functions("vwt-p-gew1-\nns-link2-int-\npoll-from-link2-func")

            link2_status_bucket = Storage("vwt-p-gew1-\nns-link2-int-\nlink2-files-stg/\nsource/\nLink2-Service-Glas/\nExport")

            link2_poll_function >> link2_status_bucket

            link2_publish_status_function = Functions("vwt-p-gew1-\nns-link2-int-\nbucket-xml-to-json-func")

            link2_status_bucket >> bucket_trigger_edge >> link2_publish_status_function
            link2_publish_status_function >> publish_edge >> link2_statuses_pubsub

    with Cluster("Azure"):
        with Cluster("infrasal2fsp01"):
            with Cluster("serviceglasp01"):
                azure_import = BlobStorage("Link2-\nService-Glas/\nImport")
                azure_export = BlobStorage("Link2-\nService-Glas/\nExport")

        consume_mail_function >> azure_import
        azure_export >> link2_poll_function

    with Cluster("Link2"):
        import_storage_link2 = GenericStorage("Import")
        export_storage_link2 = GenericStorage("Export")

        azure_import >> import_storage_link2
        export_storage_link2 >> azure_export
