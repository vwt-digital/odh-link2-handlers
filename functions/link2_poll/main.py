import logging
from filesharepoll import FileSharePoll

poll_object = FileSharePoll()

logging.basicConfig(level=logging.INFO)


def link2_to_bucket(request):
    if poll_object.poll() is False:
        logging.error("Object polling went wrong")
    else:
        logging.info("Function has run succesfully")
