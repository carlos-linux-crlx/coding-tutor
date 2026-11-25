"""Install pinned assets only after the settings UI obtains consent."""

import fcntl
import hashlib
import os
from pathlib import Path
import platform
import shutil
import tarfile
from tempfile import TemporaryDirectory
import time
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


class PublisherRedirect(HTTPRedirectHandler):
    def __init__(self, host):
        self.host = host

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        destination = urlsplit(newurl)
        permitted = ({"github.com", "release-assets.githubusercontent.com", "objects.githubusercontent.com"}
                     if self.host == "github.com"
                     else {"huggingface.co", "cdn-lfs.huggingface.co", "cdn-lfs-us-1.huggingface.co",
                           "cas-bridge.xethub.hf.co", "transfer.xethub.hf.co"})
        if (destination.scheme != "https" or destination.hostname not in permitted
                or destination.username or destination.password):
            raise TutorError("The publisher redirected to an unexpected download host.")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def download(asset, target, request, progress):
    opener = build_opener(PublisherRedirect(urlsplit(asset.url).hostname))
    web_request = DownloadRequest(asset.url, headers={"User-Agent": "RustTutor-model-manager"})
    digest = hashlib.sha256()
    received = 0
    last_update = 0.0
    try:
        request.check()
        with opener.open(web_request, timeout=12) as response, target.open("xb") as output:
            if response.status != 200:
                raise TutorError(f"The publisher returned HTTP {response.status}.")
            while True:
                request.check()
                chunk = response.read1(1024 * 1024)
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
        raise TutorError(f"Could not download {asset.name}. Check the connection and free disk space.") from None
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
