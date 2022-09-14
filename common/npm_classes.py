"""Utility classes to store NPM packge info downloaded from DevOps"""

from dataclasses import dataclass, field


@dataclass
class NpmPackageVersion:
    """Stores info about a specific version of a NPM package from DevOps"""

    version_number: str
    description: str
    publish_date: str

    dependencies: dict[str, str]

    shasum: str = None
    tarball: str = None

    author: str = None
    display_name: str = None
    unity: str = None
    category: str = None
    hide_in_editor: bool = True


@dataclass
class NpmPackage:
    """Stores info about a NPM package from DevOps"""

    name: str
    latest_version: str
    versions: dict[str, NpmPackageVersion] = field(default_factory=dict)
