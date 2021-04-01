import logging

from config import DEBUG_LOGGING

import statusprocessor

logging.basicConfig(level=logging.INFO)


def log(debug_message, normal_message):
    if DEBUG_LOGGING:
        logging.info(debug_message)
    else:
        logging.info(normal_message)


def status_to_json(data, context):
    # Extract subscription from subscription string
    try:
        bucket = data["bucket"]
        log(
            f"A file has been uploaded to bucket {bucket} with context {context}",
            f"A file has been uploaded to bucket {bucket}",
        )

        processed = statusprocessor.process(data, context)
        if processed is False:
            logging.info("XML file was not processed")
        else:
            logging.info("XML file is processed")

    except Exception as e:
        logging.info("Extract of subscription failed")
        logging.debug(e)
        raise e

    # Returning any 2xx status indicates successful receipt of the message.
    # 204: no content, delivery successfull, no further actions needed
    return "OK", 204
