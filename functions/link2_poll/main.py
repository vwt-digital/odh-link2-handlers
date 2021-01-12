import logging
from filesharepoll import FileSharePoll

poll_object = FileSharePoll()

logging.basicConfig(level=logging.INFO)


def link2_to_bucket():
    poll_object.poll()


if __name__ == '__main__':
    link2_to_bucket()
