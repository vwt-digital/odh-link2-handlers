import requests

from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry


def get_requests_session(retries=6, backoff=10, status_forcelist=(404, 500, 502, 503, 504)):
    """
    Returns a requests session with retry enabled.
    """

    session = requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff,
        status_forcelist=status_forcelist,
    )

    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)

    return session
