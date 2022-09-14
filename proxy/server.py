"""NPM metadata proxy server"""

from collections import OrderedDict
import logging
import os
import random
import string
import time

import dacite

from flask import Flask, make_response, jsonify
from flask_pymongo import PyMongo

from npm_classes import NpmPackage

LICENSE = "proprietary"

app = Flask(__name__)

MONGO_HOST = os.environ.get("MONGO_HOST", "mongo")
MONGO_PORT = os.environ.get("MONGO_PORT", 27017)
MONGO_USER = os.environ.get("MONGO_USER")
MONGO_PASS = os.environ.get("MONGO_PASS")
MONGO_DB = os.environ.get("MONGO_DB")

app.config["JSON_SORT_KEYS"] = False
app.config[
    "MONGO_URI"
] = f"mongodb://{MONGO_USER}:{MONGO_PASS}@{MONGO_HOST}:{MONGO_PORT}/{MONGO_DB}"

mongo = PyMongo(app, authSource="admin")
db = mongo.db

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s.%(msecs)03d] %(levelname)s [%(funcName)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


@app.route("/")
def index_route():
    """Home route"""
    return jsonify(db_name="unity_proxy_mirror")


@app.route("/<package_name>")
def package_route(package_name: str):
    """
    Returns all info (incl. versions) about a specific package from Mongo
    """

    mongo_package = db.packages_collection.find_one({"name": package_name})

    if mongo_package is None:
        return make_response(jsonify(error="Not found"), 404)

    try:
        # Auto-magically convert dict to `npm_package`
        package = dacite.from_dict(data_class=NpmPackage, data=mongo_package)
    except dacite.WrongTypeError as err:
        logging.error(
            "Could not deserialise package '%s' from Mongo. Reason: %s",
            package_name,
            err,
        )
        return make_response(jsonify(err="Could not deserialise from database"), 500)

    latest_version = package.versions[package.latest_version]

    all_versions = OrderedDict()
    version_times = OrderedDict()

    for _, version in package.versions.items():
        version_times[version.version_number] = version.publish_date

        all_versions[version.version_number] = OrderedDict(
            {
                "_id": f"{package_name}@{version.version_number}",
                "_shasum": version.shasum,
                "name": package_name,
                "author": version.author,
                "dependencies": version.dependencies,
                "description": version.description,
                "directories": None,
                "dist": OrderedDict(
                    {"shasum": version.shasum, "tarball": version.tarball}
                ),
                "license": LICENSE,
                "version": version.version_number,
                "displayName": version.display_name,
                "unity": version.unity,
                "category": version.category,
                "hideInEditor": version.hide_in_editor,
            }
        )

    response = OrderedDict(
        {
            "_id": package_name,
            "_rev": "".join(
                random.choices(string.ascii_lowercase + string.digits, k=32)
            ),
            "name": package_name,
            "description": latest_version.description,
            "license": LICENSE,
            "dist-tags": {"latest": latest_version.version_number},
            "versions": all_versions,
            "time": version_times,
            "displayName": latest_version.display_name,
            "unity": latest_version.unity,
            "category": latest_version.category,
            "hideInEditor": latest_version.hide_in_editor,
            "author": latest_version.author,
        }
    )

    return jsonify(response)


@app.route("/-/all")
def all_packages_route():
    """
    Returns basic info about all packages in Mongo
    """

    all_packages = OrderedDict({"_updated": int(time.time())})

    mongo_packages = db.packages_collection.find()

    for mongo_package in mongo_packages:
        try:
            # Auto-magically convert dict to `npm_package`
            package = dacite.from_dict(data_class=NpmPackage, data=mongo_package)
        except dacite.WrongTypeError as err:
            logging.error(
                "Could not deserialise package from Mongo. Reason: %s",
                err,
            )
            return make_response(
                jsonify(err="Could not deserialise from database"), 500
            )

        latest_version = package.versions[package.latest_version]

        all_packages[package.name] = OrderedDict(
            {
                "name": package.name,
                "description": latest_version.description,
                "dist-tags": {"latest": latest_version.version_number},
                "license": LICENSE,
                "time": latest_version.publish_date,
                "versions": {latest_version.version_number: "latest"},
                "displayName": latest_version.display_name,
                "unity": latest_version.unity,
                "category": latest_version.category,
                "hideInEditor": latest_version.hide_in_editor,
            }
        )

    return jsonify(all_packages)


if __name__ == "__main__":
    logging.info("Application start!")

    SERVER_PORT = os.environ.get("SERVER_PORT", 8080)

    app.run(host="0.0.0.0", port=SERVER_PORT, debug=True)
