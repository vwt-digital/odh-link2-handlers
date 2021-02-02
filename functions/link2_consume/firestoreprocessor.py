from google.cloud import firestore
import logging

logging.basicConfig(level=logging.INFO)


class FirestoreProcessor(object):
    def __init__(self):
        self.db_client = firestore.Client()

    def get_value(self, collection_name, ids: list, fs_value):
        query_fs = self.db_client.collection(collection_name)

        query_ids = ""
        if not ids:
            return False, query_ids
        for id_dict in ids:
            for fs_id in id_dict:
                # Remove brackets from ID
                value = id_dict[fs_id].replace('(', '')
                value = value.replace(')', '')
                query_fs = query_fs.where(fs_id, '==', value)
                if query_ids:
                    query_ids = query_ids + f"AND {fs_id} == {value}"
                else:
                    query_ids = query_ids + f"{fs_id} == {value}"

        docs_fs = query_fs.stream()

        if docs_fs:
            docs = []
            for doc in docs_fs:
                docs.append(doc)
            if len(docs) == 1:
                # Check if firestore value is in doc
                firestore_value = doc.get(fs_value)
                if firestore_value:
                    return True, firestore_value
            elif len(docs) == 0:
                return False, query_ids
            else:
                logging.error(f"Multiple Firestore documents belong to querie {query_ids}")
        # If no value is found, return False with the query
        return False, query_ids
