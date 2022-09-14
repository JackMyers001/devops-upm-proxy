"""Functions for scraping data from DevOps"""

import base64
from collections import OrderedDict
import logging

import requests

from enums import NetworkError, ReturnStatus
from environmental_variables import EnvironmentalVariables
from npm_classes import NpmPackageVersion


class DevOpsAuthToken(requests.auth.AuthBase):
    """
    `requests` helper class for authenticating with DevOps services, given
    a Personal Access Token (`pat`)
    """

    def __init__(self, pat):
        self.token = pat

    def __call__(self, r):
        r.headers["Authorization"] = "Basic " + base64.b64encode(
            (f":{self.token}").encode("utf-8")
        ).decode("utf-8")
        return r


def get_from_devops(
    url: str,
    env_vars: EnvironmentalVariables,
    description: str,
    request_timeout: int = 10,
) -> requests.Response | NetworkError:
    """
    Try to get data from DevOps.

    Handles authentication, network and timeout errors
    """

    request_failure_prefix = f"Failed to get {description}"

    try:
        response = requests.get(
            url, auth=DevOpsAuthToken(env_vars.pat), timeout=request_timeout
        )
    except requests.exceptions.Timeout:
        logging.error("%s due to request exceeding timeout", request_failure_prefix)
        return NetworkError.TIMEOUT
    except requests.exceptions.HTTPError as err:
        logging.error("%s due to HTTP error: %s", request_failure_prefix, err)
        return NetworkError.HTTP_ERROR
    except requests.exceptions.ConnectionError:
        logging.error("%s due to connection error", request_failure_prefix)
        return NetworkError.HTTP_ERROR

    # Authentication failure in DevOps returns 203 ¯\_(ツ)_/¯
    if response.status_code == 203:
        logging.error(
            "%s due to DevOps authentication error! Is the provided PAT valid and does it have the correct scopes?",
            request_failure_prefix,
        )
        return NetworkError.DEVOPS_AUTH_FAILURE

    if response.status_code in range(400, 500):
        logging.error(
            "%s due to receiving HTTP status code %s",
            request_failure_prefix,
            response.status_code,
        )
        return NetworkError.STATUS_CLIENT_ERROR

    if response.status_code in range(500, 600):
        logging.error(
            "%s due to receiving HTTP status code %s",
            request_failure_prefix,
            response.status_code,
        )
        return NetworkError.STATUS_SERVER_ERROR

    return response


def get_artifact_package_feed_from_devops(
    env_vars: EnvironmentalVariables,
) -> str | NetworkError:
    """Get actual artifact package feed (i.e. JSON document containing all packages)"""

    artifact_feed_response = get_from_devops(
        env_vars.feed_url, env_vars, "DevOps Artifact feed URL"
    )

    if isinstance(artifact_feed_response, NetworkError):
        return artifact_feed_response

    package_feed_url: str = (
        artifact_feed_response.json().get("_links").get("packages").get("href")
    )

    return package_feed_url


def get_npm_versions_from_devops_feed(
    package_version_url: str, env_vars: EnvironmentalVariables
) -> dict[str, NpmPackageVersion] | NetworkError:
    """Get info for every version of a package from DevOps Artifact feed"""

    devops_feed_response = get_from_devops(
        package_version_url, env_vars, "DevOps Artifact feed"
    )

    if isinstance(devops_feed_response, NetworkError):
        return devops_feed_response

    devops_versions: list = devops_feed_response.json().get("value")

    processed_versions: dict[str, NpmPackageVersion] = {}

    for devops_version in devops_versions:
        version_number: str = devops_version.get("version")
        description: str = devops_version.get("description") or ""
        publish_date: str = devops_version.get("publishDate")

        dependencies = OrderedDict()

        for dep in devops_version.get("dependencies"):
            package_name: str = dep.get("packageName")
            version_range: str = dep.get("versionRange")

            dependencies[package_name] = version_range

        new_version = NpmPackageVersion(
            version_number=version_number,
            description=description,
            publish_date=publish_date,
            dependencies=dependencies,
        )

        processed_versions[version_number] = new_version

    return processed_versions


def get_extra_npm_info_from_devops_npm_registry(
    env_vars: EnvironmentalVariables,
    package_name: str,
    package_versions: dict[str, NpmPackageVersion],
) -> dict[str, NpmPackageVersion] | NetworkError:
    """
    Get additional info for every version of a package from DevOps NPM registry that can't be found
    in DevOps Artifact feed (e.g. download URL + shasum, UPM extra properties)
    """

    npm_registry_url = f"{env_vars.npm_registry_base_url}/{package_name}"

    devops_registry_response = get_from_devops(
        npm_registry_url, env_vars, "DevOps NPM registry"
    )

    if isinstance(devops_registry_response, NetworkError):
        return devops_registry_response

    devops_versions = devops_registry_response.json().get("versions")

    updated_package_versions = {}

    for ver_num, npm_pkg_version in package_versions.items():
        json_version = devops_versions.get(ver_num)

        # For some reason, it is possible for NPM package to exist in DevOps Artifact feed but not
        # DevOps NPM registry?
        if json_version is None:
            logging.warning(
                "Package '%s', version %s exists in DevOps Artifact feed but not in DevOps NPM registry! This version will not be uploaded to Mongo",
                package_name,
                ver_num,
            )
            continue

        # Read in extra info from DevOps NPM registry
        dist = json_version.get("dist")

        npm_pkg_version.shasum = dist.get("shasum")
        npm_pkg_version.tarball = dist.get("tarball")

        author = json_version.get("author")
        npm_pkg_version.author = (
            author.get("name") if author is not None else env_vars.fallback_author
        )

        npm_pkg_version.display_name = json_version.get("displayName") or package_name

        npm_pkg_version.unity = json_version.get("unity") or "Unknown Unity Version"

        category = json_version.get("category")

        # If no category, package is likely from a 3rd party. Use author name if possible
        if category is None and author is not None:
            category = author.get("name")

        npm_pkg_version.category = category or "Unknown"

        npm_pkg_version.hide_in_editor = json_version.get("hideInEditor") or False

        # Copy modified package to new package list
        updated_package_versions[ver_num] = package_versions[ver_num]

    return updated_package_versions


def validate_package_versions(
    package_name: str,
    package_versions: dict[str, NpmPackageVersion] | NetworkError,
    download_location: str,
    error_message: str,
    non_serious_error_count: int,
) -> ReturnStatus:
    """
    Determine if a downloaded `package_versions` is valid.
    """

    if isinstance(package_versions, NetworkError):
        net_error_msg = f"while trying to download version info for package '{package_name}' from the {download_location} (see above log for more details)"

        match package_versions:
            case NetworkError.DEVOPS_AUTH_FAILURE:
                logging.error(
                    "Failed to authenticate to DevOps %s. Not going to download more package versions this run",
                    net_error_msg,
                )
                return ReturnStatus.RETURN
            case _:
                non_serious_error_count += 1

                if non_serious_error_count == 5:
                    logging.error(
                        "A non-serious error has occurred 5 times. Stopping this run."
                    )
                    return ReturnStatus.RETURN

                logging.warning(
                    "A non-serious issue occurred %s. Will continue to try downloading more more package versions. This has happened %s time(s) this run",
                    net_error_msg,
                    non_serious_error_count,
                )
                return ReturnStatus.CONTINUE

    if len(package_versions) == 0:
        logging.warning("Package %s has no versions! %s", package_name, error_message)
        return ReturnStatus.CONTINUE

    return ReturnStatus.PASS
