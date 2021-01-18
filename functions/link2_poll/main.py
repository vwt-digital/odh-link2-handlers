import logging
from filesharepoll import FileSharePoll

poll_object = FileSharePoll()

logging.basicConfig(level=logging.INFO)


def link2_to_bucket(request):
    poll_object.poll()
