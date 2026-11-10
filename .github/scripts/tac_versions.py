"""Print a JSON list of the latest patch of each twilio-agent-connect minor in range.

Reads the package's simple index page from UV_INDEX_URL (set by the Artifactory
OIDC action on internal runners, where pypi.org may not be reachable), falling
back to pypi.org. Usage: tac_versions.py [SPECIFIER]
"""

from __future__ import annotations

import base64
import json
import os
import re
import sys
import urllib.parse
import urllib.request

import tomllib
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.version import InvalidVersion, Version

PACKAGE = "twilio-agent-connect"
FILENAME = re.compile(r"twilio[_-]agent[_-]connect-([^-/#\"']+?)(?:-py|\.tar\.gz|\.zip)", re.I)


def declared_spec() -> SpecifierSet:
    with open("pyproject.toml", "rb") as f:
        dependencies = tomllib.load(f)["project"]["dependencies"]
    for dependency in dependencies:
        requirement = Requirement(dependency)
        if requirement.name == PACKAGE:
            return requirement.specifier
    sys.exit(f"{PACKAGE} not found in pyproject.toml dependencies")


def fetch_index(index_url: str) -> str:
    parts = urllib.parse.urlsplit(index_url.rstrip("/") + f"/{PACKAGE}/")
    headers = {"Accept": "text/html"}
    if parts.username is not None or parts.password is not None:
        creds = f"{parts.username or ''}:{parts.password or ''}"
        headers["Authorization"] = "Basic " + base64.b64encode(creds.encode()).decode()
        parts = parts._replace(netloc=parts.hostname + (f":{parts.port}" if parts.port else ""))
    request = urllib.request.Request(urllib.parse.urlunsplit(parts), headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode()


def latest_patches(versions: set[Version], spec: SpecifierSet) -> list[str]:
    latest: dict[tuple[int, int], Version] = {}
    for version in versions:
        if version.is_prerelease or version.is_devrelease or version not in spec:
            continue
        key = (version.major, version.minor)
        if key not in latest or version > latest[key]:
            latest[key] = version
    return [str(latest[key]) for key in sorted(latest)]


def main() -> None:
    spec = SpecifierSet(sys.argv[1]) if len(sys.argv) > 1 else declared_spec()
    index_url = os.environ.get("UV_INDEX_URL") or "https://pypi.org/simple/"
    versions: set[Version] = set()
    for match in FILENAME.finditer(fetch_index(index_url)):
        try:
            versions.add(Version(match.group(1)))
        except InvalidVersion:
            continue
    result = latest_patches(versions, spec)
    if not result:
        sys.exit(f"No {PACKAGE} releases match {spec}")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
