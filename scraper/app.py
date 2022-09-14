"""Program to scrape NPM package metdata from DevOps"""

import dataclasses
import datetime
import sys
import logging

from apscheduler.schedulers.blocking import BlockingScheduler
from pymongo import MongoClient, collection

from enums import MongoPackageStatus, NetworkError, ReturnStatus
from environmental_variables import EnvironmentalVariables, process_env_vars
from npm_classes import NpmPackage
from devops_scraping import (
    get_artifact_package_feed_from_devops,
    get_extra_npm_info_from_devops_npm_registry,
    get_from_devops,
    get_npm_versions_from_devops_feed,
    validate_package_versions,
)
from mongo_functions import check_package_status_in_mongo

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s.%(msecs)03d] %(levelname)s [%(funcName)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

sched = BlockingScheduler()


def download(
    env_vars: EnvironmentalVariables, packages_collection: collection.Collection
):
    """
    Downloads a list of packages from DevOps and processes them
    """

    devops_package_list_response = get_from_devops(
        env_vars.packages_url, env_vars, "DevOps package list"
    )

    if isinstance(devops_package_list_response, NetworkError):
        logging.error("Failed to download DevOps package list. Stopping this run")

    devops_package_list: list = devops_package_list_response.json().get("value")

    # Keep track of non-serious errors this run
    non_serious_error_count = 0

    for package_response in devops_package_list:
        # Read in info from repsonse
        package_name: str = package_response.get("name")
        package_latest_version: str = package_response.get("versions")[0].get("version")
        package_version_url: str = (
            package_response.get("_links").get("versions").get("href")
        )

        mongo_package_status = check_package_status_in_mongo(
            package_name, package_latest_version, packages_collection
        )

        # If package is up-to-date in Mongo, don't need to do anything
        if mongo_package_status == MongoPackageStatus.UP_TO_DATE:
            continue

        # Download version info from DevOps Artifact package feed
        package_versions = get_npm_versions_from_devops_feed(
            package_version_url, env_vars
        )

        match validate_package_versions(
            package_name,
            package_versions,
            "DevOps Artifact feed",
            "Here be dragons!",
            non_serious_error_count,
        ):
            case ReturnStatus.RETURN:
                return
            case ReturnStatus.CONTINUE:
                continue

        # Download more version infor from DevOps NPM registry
        package_versions = get_extra_npm_info_from_devops_npm_registry(
            env_vars, package_name, package_versions
        )

        match validate_package_versions(
            package_name,
            package_versions,
            "DevOps NPM registry",
            "This is probably because all package versions only exist in DevOps Artifact feed, with none in the DevOps NPM registry",
            non_serious_error_count,
        ):
            case ReturnStatus.RETURN:
                return
            case ReturnStatus.CONTINUE:
                continue

        new_package = NpmPackage(
            package_name,
            package_latest_version,
            package_versions,
        )

        # Delete the old version of the package on Mongo
        # TODO: don't do this; update existing Mongo entry with new versions
        if mongo_package_status == MongoPackageStatus.OUT_OF_DATE:
            logging.info(
                "Deleting package '%s' from Mongo as it is out of date", package_name
            )
            packages_collection.delete_one({"name": package_name})

        logging.info("Uploading package '%s' to Mongo", package_name)

        # Upload package to Mongo
        new_package_as_json = dataclasses.asdict(new_package)
        packages_collection.insert_one(new_package_as_json)

    logging.info("Finished processing all packages on DevOps!")


def main():
    """Set up program and start sync task"""

    logging.info("Application start!")

    env_vars = process_env_vars()

    env_vars.feed_url = f"https://feeds.dev.azure.com/{env_vars.org_name}/_apis/packaging/feeds/{env_vars.feed}?api-version=6.0-preview.1"
    env_vars.npm_registry_base_url = f"https://pkgs.dev.azure.com/{env_vars.org_name}/_packaging/{env_vars.feed}/npm/registry"

    packages_url = get_artifact_package_feed_from_devops(env_vars)

    if isinstance(packages_url, NetworkError):
        # TODO: change behaviour based on if network error or authentication error
        logging.error(
            "Unable to get DevOps Artifact feed URL. This is potentially fatal. Exiting!"
        )
        sys.exit(1)

    env_vars.packages_url = packages_url

    client = MongoClient(
        f"mongodb://{env_vars.mongo_user}:{env_vars.mongo_pass}@{env_vars.mongo_host}:{env_vars.mongo_port}/"
    )

    database = client[env_vars.mongo_db]
    packages_collection = database.packages

    if env_vars.wipe_db:
        packages_collection.drop()

    # Continually download pacakges
    sched.add_job(
        id="Download latest NPM package info from DevOps",
        func=download,
        args=[env_vars, packages_collection],
        trigger="interval",
        seconds=env_vars.refresh,
        next_run_time=datetime.datetime.now(),
    )

    sched.start()


if __name__ == "__main__":
    main()
