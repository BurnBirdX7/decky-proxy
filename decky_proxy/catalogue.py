import json
from base64 import urlsafe_b64decode, urlsafe_b64encode
from binascii import Error as Base64Error
from re import fullmatch
from typing import Any

from yarl import URL

from . import constants
from .errors import InvalidCatalogueError, InvalidResourceError
from .resource_signing import sign_resource_token
from .security import parse_url

SHA256_PATTERN = r"[0-9a-fA-F]{64}"
BASE64URL_PATTERN = r"(?:[A-Za-z0-9_-]{4})*(?:[A-Za-z0-9_-]{2}==|[A-Za-z0-9_-]{3}=)?"


def substitute__plugins_list(content: bytes) -> list[dict[str, Any]]:
    try:
        catalogue = json.loads(content)
        if not isinstance(catalogue, list):
            raise TypeError("Expected a catalogue array")
        return [substitute__plugin(plugin) for plugin in catalogue]
    except (ValueError, KeyError, TypeError, InvalidResourceError) as error:
        raise InvalidCatalogueError("Invalid upstream catalogue") from error


def substitute__plugin(plugin: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(plugin, dict) or not isinstance(plugin.get("versions"), list):
        raise InvalidCatalogueError("Invalid upstream plugin")
    substituted_plugin = dict(plugin)
    substituted_plugin["versions"] = [substitute__plugin_version(version) for version in plugin["versions"]]
    substituted_plugin["image_url"] = make_base64_url(plugin["image_url"])
    return substituted_plugin


def substitute__plugin_version(version: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(version, dict):
        raise InvalidCatalogueError("Invalid upstream version")
    substituted_version = dict(version)
    substituted_version["artifact"] = make_artifact_url(version["hash"], version.get("artifact"))
    return substituted_version

def substitute__versions_dict(content: bytes) -> dict[str, list[str]] | None:
    try:
        version_dict = json.loads(content)
        if version_dict is None:
            return None
        if not isinstance(version_dict, dict):
            raise TypeError("Expected a versions object")
        return {
            name: substitute__version_tuple(version_tuple)
            for name, version_tuple in version_dict.items()
        }
    except (ValueError, KeyError, TypeError, InvalidResourceError) as error:
        raise InvalidCatalogueError("Invalid upstream versions") from error


def substitute__version_tuple(version_tuple: list[str | None]) -> list[str]:
    if (
        not isinstance(version_tuple, list)
        or len(version_tuple) not in (2, 3)
        or not all(isinstance(value, str) for value in version_tuple[:2])
    ):
        raise TypeError("Invalid upstream version tuple")

    version_number, hash_ = version_tuple[:2]
    artifact = version_tuple[2] if len(version_tuple) == 3 else None
    new_artifact = make_artifact_url(hash_, artifact)
    return [version_number, hash_, new_artifact]

def make_artifact_url(hash_: str, artifact: str | None) -> str:
    if artifact is not None:
        return make_base64_url(artifact)
    return make_hash_url(hash_)


def make_hash_url(hash_: str) -> str:
    validate_archive_hash(hash_)
    return f"https://{constants.DOMAIN}/resources/hash/{hash_}"


def make_base64_url(url: str) -> str:
    parse_url(url)  # Called to validate the resource URL.
    base64url = encode_resource_url(url)
    signature = sign_resource_token(base64url)
    return f"https://{constants.DOMAIN}/resources/base64/{base64url}.{signature}"


def encode_resource_url(url: str) -> str:
    return urlsafe_b64encode(url.encode("utf-8")).decode("ascii")


def decode_resource_url(token: str) -> URL:
    if not fullmatch(BASE64URL_PATTERN, token):
        raise InvalidResourceError("Invalid resource URL encoding")
    try:
        url = urlsafe_b64decode(token).decode("utf-8")
    except (ValueError, Base64Error) as error:
        raise InvalidResourceError("Invalid resource URL encoding") from error
    return parse_url(url)


def validate_archive_hash(archive_hash: str) -> None:
    if not isinstance(archive_hash, str) or not fullmatch(SHA256_PATTERN, archive_hash):
        raise InvalidResourceError("Expected a SHA-256 archive hash")


def build_archive_url(archive_hash: str) -> URL:
    validate_archive_hash(archive_hash)
    return parse_url(f"https://cdn.tzatzikiweeb.moe/file/steam-deck-homebrew/versions/{archive_hash}.zip")
