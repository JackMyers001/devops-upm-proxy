"""Functions related to MongoDB"""

import logging

import dacite

from pymongo import collection

from enums import MongoPackageStatus
from npm_classes import NpmPackage


def check_package_status_in_mongo(
    package_name: str,
    package_latest_version: str,
    packages_collection: collection.Collection,
) -> MongoPackageStatus:
    """
    Determine if package exists in Mongo database.

    If it does, check if it is the latest version.
    """

    mongo_package = packages_collection.find_one({"name": package_name})

    if mongo_package is None:
        logging.info("Package '%s' not found in Mongo", package_name)
        return MongoPackageStatus.NOT_FOUND

    try:
        # Auto-magically convert dict to `npm_package`
        found_package = dacite.from_dict(data_class=NpmPackage, data=mongo_package)
    except dacite.WrongTypeError as err:
        logging.error(
            "Could not deserialise package '%s' from Mongo. Reason: %s",
            package_name,
            err,
        )
        return MongoPackageStatus.NOT_FOUND

    if found_package.latest_version == package_latest_version:
        logging.info(
            "Package '%s' has the same version (%s) in DevOps and Mongo",
            found_package.name,
            package_latest_version,
        )
        return MongoPackageStatus.UP_TO_DATE

    logging.info(
        "Package '%s' DevOps version (%s) is different to Mongo version (%s)",
        found_package.name,
        package_latest_version,
        found_package.latest_version,
    )
    return MongoPackageStatus.OUT_OF_DATE
