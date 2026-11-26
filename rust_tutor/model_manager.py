"""Install pinned assets only after the settings UI obtains consent."""

import fcntl
import hashlib
from http.client import HTTPException
import os
from pathlib import Path
import platform
import shutil
import tarfile
from tempfile import TemporaryDirectory
import time
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import build_opener, HTTPRedirectHandler, Request as DownloadRequest

from .hardware import memory
from .local_tutor import TutorError
from .state import data_directory


def model_directory():
    return data_directory() / "models"


def asset_path(asset):
    return model_directory() / asset.destination


def installed(asset):
    path = asset_path(asset)
    if asset.executable:
        return (path / asset.executable).is_file() and os.access(path / asset.executable, os.X_OK)
    try:
        return path.is_file() and path.stat().st_size == asset.size
    except OSError:
        return False


def ready(preset):
    return all(installed(asset) for asset in preset.assets)


def remaining(preset):
    return [asset for asset in preset.assets if not installed(asset)]


def compatible():
    return platform.system() == "Linux" and platform.machine() == "x86_64"


def disk_needed(assets):
    return sum(asset.size + asset.unpacked_limit for asset in assets) + 64 * 1024 ** 2


def need_resources(preset, assets):
    if not compatible():
        return "Managed models currently support Ubuntu on x86-64."
    _, available = memory()
    if available is None or available < preset.ram_gib:
        return f"Free up about {preset.ram_gib:.1f} GiB of available RAM before starting this model."
    directory = model_directory()
    if assets:
        try:
            ancestor = next(path for path in (directory, *directory.parents) if path.exists())
            if shutil.disk_usage(ancestor).free < disk_needed(assets):
                return f"Free up about {disk_needed(assets) / 1024 ** 3:.1f} GiB on the model storage drive."
        except OSError:
            return "Could not check free space on the model storage drive."
    return ""


PUBLISHER_HOSTS = {
    "github.com": {"github.com", "release-assets.githubusercontent.com", "objects.githubusercontent.com"},
    "huggingface.co": {
        "huggingface.co",
        "us.aws.cdn.hf.co",
        "us.gcp.cdn.hf.co",
        "cdn-lfs-us-1.hf.co",
        "cdn-lfs-eu-1.hf.co",
        "cdn-lfs.huggingface.co",
        "cdn-lfs-us-1.huggingface.co",
        "cas-bridge.xethub.hf.co",
        "transfer.xethub.hf.co",
        "transfer.xethub-eu.hf.co",
    },
}


def https_download_host(url):
    try:
        target = urlsplit(url)
        if (target.scheme == "https" and target.port in (None, 443)
                and target.username is None and target.password is None):
            return target.hostname
    except ValueError:
        pass
    return None


class PublisherRedirect(HTTPRedirectHandler):
    def __init__(self, host):
        self.allowed_hosts = PUBLISHER_HOSTS[host]

    def http_error_302(self, req, fp, code, msg, headers):
        try:
            return super().http_error_302(req, fp, code, msg, headers)
        except ValueError:
            fp.close()
            raise TutorError("The publisher sent an invalid HTTPS download redirect.") from None

    http_error_301 = http_error_303 = http_error_307 = http_error_308 = http_error_302

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        host = https_download_host(newurl)
        if host is None:
            fp.close()
            raise TutorError("The publisher sent an invalid HTTPS download redirect.")
        if host not in self.allowed_hosts:
            fp.close()
            raise TutorError("The publisher redirected the download outside its approved CDN hosts.")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def download(asset, target, request, progress):
    request.check()
    publisher = https_download_host(asset.url)
    if publisher not in PUBLISHER_HOSTS:
        raise TutorError(f"{asset.name} does not have an approved HTTPS download source.")
    opener = build_opener(PublisherRedirect(publisher))
    web_request = DownloadRequest(asset.url, headers={"User-Agent": "RustTutor-model-manager"})
    try:
        response = opener.open(web_request, timeout=12)
    except HTTPError as error:
        error.close()
        request.check()
        raise TutorError(f"The publisher could not serve {asset.name} (HTTP {error.code}).") from None
    except (OSError, HTTPException):
        request.check()
        raise TutorError(f"Could not connect to the publisher for {asset.name}. Check your network and retry.") from None

    digest = hashlib.sha256()
    received = 0
    last_update = 0.0
    try:
        with response:
            request.check()
            if response.status != 200:
                raise TutorError(f"The publisher did not return a full download for {asset.name} (HTTP {response.status}).")
            with target.open("xb") as output:
                while True:
                    request.check()
                    try:
                        chunk = response.read1(1024 * 1024)
                    except (OSError, HTTPException):
                        request.check()
                        raise TutorError(f"The download of {asset.name} was interrupted. Check your network and retry.") from None
                    if not chunk:
                        break
                    received += len(chunk)
                    if received > asset.size:
                        raise TutorError(f"{asset.name} exceeded its pinned download size.")
                    output.write(chunk)
                    digest.update(chunk)
                    now = time.monotonic()
                    if now - last_update >= 0.2:
                        progress(received)
                        last_update = now
                output.flush()
                os.fsync(output.fileno())
    except OSError:
        request.check()
        raise TutorError(f"Could not save {asset.name}. Check free disk space and storage permissions.") from None
    request.check()
    if received != asset.size or digest.hexdigest() != asset.sha256:
        raise TutorError(f"{asset.name} did not match its pinned size and SHA-256. Retry from Model setup.")
    progress(received)


def unpack(asset, archive, staging):
    with tarfile.open(archive, "r:gz") as source:
        members = source.getmembers()
        if (len(members) > 3000 or sum(member.size for member in members) > asset.unpacked_limit
                or any(Path(member.name).parts[:1] != (asset.destination,) for member in members)):
            raise TutorError("The runtime archive has an unexpected layout or expanded size.")
        source.extractall(staging, members=members, filter="data")
    folder = staging / asset.destination
    executable = folder / asset.executable
    if not executable.is_file() or not os.access(executable, os.X_OK):
        raise TutorError("The verified archive did not contain the expected runtime executable.")
    return folder


def install(preset, assets, request, progress):
    # The UI passes the exact set and size that the learner approved.
    reason = need_resources(preset, assets)
    if reason:
        raise TutorError(reason)
    directory = model_directory()
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    total = sum(asset.size for asset in assets)
    done = 0
    try:
        with (directory / ".download.lock").open("ab") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise TutorError("Another model download is in progress.") from None
            with TemporaryDirectory(prefix=".install-", dir=directory) as staging:
                for asset in assets:
                    request.check()
                    if not installed(asset):
                        payload = Path(staging) / "payload"
                        download(asset, payload, request,
                                 lambda received: progress(done + received, total, asset.name))
                        result = unpack(asset, payload, Path(staging)) if asset.executable else payload
                        request.check()
                        os.replace(result, asset_path(asset))
                        if asset.executable:
                            payload.unlink()
                    done += asset.size
                    progress(done, total, asset.name)
    except (OSError, tarfile.TarError):
        raise TutorError("The verified model files could not be installed in local storage.") from None
    request.check()
    if not ready(preset):
        raise TutorError("Some model files are still missing. Review the download again.")
    return preset
