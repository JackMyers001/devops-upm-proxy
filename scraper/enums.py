"""Various Enums to make life easier"""

from enum import Enum


class MongoPackageStatus(Enum):
    """Status of a given package in Mongo"""

    NOT_FOUND = 1
    OUT_OF_DATE = 2
    UP_TO_DATE = 3


class NetworkError(Enum):
    """What error occurred for a failed request"""

    # Request threw `requests.exceptions.Timeout`
    TIMEOUT = 1

    # Request threw `requests.exceptions.HTTPError` or `requests.exceptions.ConnectionError`
    HTTP_ERROR = 2

    # Response status code is 203
    DEVOPS_AUTH_FAILURE = 3

    # Response status code is 4xx
    STATUS_CLIENT_ERROR = 4

    # Response code is 5xx
    STATUS_SERVER_ERROR = 5


class ReturnStatus(Enum):
    """What the caller function should do"""

    RETURN = 1
    CONTINUE = 2
    PASS = 3
