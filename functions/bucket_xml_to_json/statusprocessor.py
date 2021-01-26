import logging

logging.basicConfig(level=logging.INFO)


def process(data, context):
    logging.info(f"Data: {data}")
    logging.info(f"Context: {context}")
