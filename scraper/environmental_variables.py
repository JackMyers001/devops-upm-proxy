"""Read in environmental variables"""

from dataclasses import dataclass
import logging
import os
import sys


# Environmental variable names
ENV_ORG_NAME = "ORG_NAME"
ENV_FEED_ID = "FEED_ID"
ENV_PAT = "PAT"
ENV_FALLBACK_AUTHOR = "FALLBACK_AUTHOR"
ENV_REFRESH = "REFRESH"

ENV_MONGO_HOST = "MONGO_HOST"
ENV_MONGO_PORT = "MONGO_PORT"
ENV_MONGO_USER = "MONGO_USER"
ENV_MONGO_PASS = "MONGO_PASS"
ENV_MONGO_DB = "MONGO_DB"

ENV_WIPE_DB = "WIPE_DB"

# Default values for missing / unspecified environmental variables
DEFAULT_REFRESH = 900
DEFAULT_MONGO_PORT = 27017


@dataclass
class EnvironmentalVariables:
    """Stores configurable values"""

    org_name: str
    feed: str
    pat: str
    fallback_author: str
    refresh: int

    mongo_host: str
    mongo_port: int
    mongo_user: str
    mongo_pass: str
    mongo_db: str

    wipe_db: bool = False

    feed_url: str = None
    npm_registry_base_url: str = None
    packages_url: str = None


def validate_env(env_name: str, message: str, default_value: str = None) -> str:
    """Reads in an environmental variable and ensures it is a valid string"""

    env_value = os.getenv(env_name)

    if env_value is None or len(env_value) == 0:
        # If no default value, this is *required*
        if default_value is None:
            logging.error(
                "Environmental variable '%s' empty or not set! %s", env_name, message
            )
            sys.exit(1)
        else:
            logging.warning(message)
            env_value = default_value

    return env_value


def validate_env_int(env_name: str, message: str, default_value: int = None) -> int:
    """Reads in an environmental variable and ensures it is a valid int"""

    val = validate_env(env_name, message, str(default_value))

    try:
        int_val = int(val)
        return int_val
    except ValueError:
        logging.error(
            "Failed to convert the value of environmental variable '%s' to an integer! Value is '%s'",
            env_name,
            val,
        )
        sys.exit(1)


def process_env_vars() -> EnvironmentalVariables:
    """Reads in environmental variables"""

    return EnvironmentalVariables(
        org_name=validate_env(ENV_ORG_NAME, "DevOps org name is required!"),
        feed=validate_env(ENV_FEED_ID, "DevOps feed name is required!"),
        pat=validate_env(ENV_PAT, "DevOps Personal Access Token is required!"),
        fallback_author=validate_env(
            ENV_FALLBACK_AUTHOR, "Repository author name is required!"
        ),
        refresh=validate_env_int(
            ENV_REFRESH,
            f"No refresh interval specified! Defaulting to {DEFAULT_REFRESH}s",
            DEFAULT_REFRESH,
        ),
        mongo_host=validate_env(
            ENV_MONGO_HOST, "MongoDB host IP or address is required!"
        ),
        mongo_port=validate_env_int(
            ENV_MONGO_PORT,
            f"No MongoDB port specified! Defaulting to {DEFAULT_MONGO_PORT}",
            DEFAULT_MONGO_PORT,
        ),
        mongo_user=validate_env(ENV_MONGO_USER, "MongoDB username is required!"),
        mongo_pass=validate_env(ENV_MONGO_PASS, "MongoDB password is required!"),
        mongo_db=validate_env(ENV_MONGO_DB, "MongoDB database is required!"),
        wipe_db=os.environ.get(ENV_WIPE_DB) is not None or False,
    )
