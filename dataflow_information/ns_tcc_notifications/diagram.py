from diagrams import Cluster, Diagram, Edge

from diagrams.gcp.analytics import PubSub
from diagrams.gcp.compute import Functions
from diagrams.gcp.storage import Storage

from diagrams.azure.storage import BlobStorage

from diagrams.generic.storage import Storage as GenericStorage

with Diagram("NS TCC Notifications to Link2", show=False):
    with Cluster("GCP Operational Data Hub Platform"):
        with Cluster("Operational Data Hub"):
            with Cluster("vwt-p-gew1-\nodh-hub-\nns-tcc-notifications"):
                pubsub_1 = PubSub("vwt-p-gew1-\nodh-hub-\nns-tcc-notifications-link2-push-sub")

        with Cluster("vwt-p-gew1-ns-checkmk-int"):
            function_1 = Functions("Restingest")
            function_2 = Functions("vwt-p-gew1-\nns-checkmk-int-\npublish-func-ns-tcc-notifications")
            storage_1 = Storage("vwt-p-gew1-\nns-checkmk-int-stg/\nsource/checkmk/checkmk-notifications")

            storage_1 >> Edge(label="Bucket Trigger") >> function_2 >> Edge(label="Publish") >> pubsub_1
            function_1 >> storage_1

        with Cluster("vwt-p-gew1-ns-link2-int"):
            function_3 = Functions("vwt-p-gew1-\nns-link2-int-\nconsume-tcc-notifications-to-link2-func")

    with Cluster("Azure"):
        with Cluster("infrasal2fst01"):
            with Cluster("serviceglast01"):
                storage_2 = BlobStorage("Link2-\nService-Glas-Test/\nImport")

    with Cluster("Link2"):
        storage_3 = GenericStorage("Import")

    pubsub_1 >> Edge(label="Consume") >> function_3 >> storage_2 >> Edge(label="Link2 import script from VWT Operations") >> storage_3
