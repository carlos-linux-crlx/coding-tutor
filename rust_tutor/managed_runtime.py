"""Run verified local models in short-lived child processes."""

from contextlib import suppress
import http.client
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
from tempfile import TemporaryDirectory
from time import monotonic

from .local_tutor import TutorError, completion_payload, decode_completion, request_json
from .model_manager import asset_path, need_resources, ready


WORKER = Path(__file__).with_name("runtime_worker.py").resolve()


def runtime_command(executable, directory, memory_mib, threads, arguments):
    command = [sys.executable, str(WORKER), str(os.getpid()), str(memory_mib), str(threads),
               str(executable), *arguments]
    env = {"PATH": os.defpath, "HOME": str(directory), "TMPDIR": str(directory), "LC_ALL": "C.UTF-8",
           "LD_LIBRARY_PATH": str(executable.parent), "OMP_NUM_THREADS": str(threads)}
    return command, env


class PrivateConnection(http.client.HTTPConnection):
    def __init__(self, path, timeout):
        super().__init__("localhost", timeout=timeout)
        self.path = path

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect(self.path)


def wait_ready(process, endpoint, request):
    deadline = monotonic() + 55
    while monotonic() < deadline:
        request.check()
        code = process.poll()
        if code is not None:
            raise TutorError(f"The built-in tutor could not start within the selected resource limits (exit {code}).")
        try:
            result = request_json(PrivateConnection(endpoint, 0.75), "/health", request=request)
            if result.get("status") == "ok":
                return
        except TutorError:
            request.check()
        request.cancelled.wait(0.2)
    raise TutorError("The built-in model took too long to load. Try the compact preset or free some RAM.")


def stop(process):
    if process.poll() is not None:
        return
    with suppress(ProcessLookupError):
        process.terminate()
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        with suppress(ProcessLookupError):
            process.kill()
        process.wait()


def generate_managed(preset, request, task):
    if not ready(preset):
        raise TutorError("The selected files are missing. Open Model setup to reinstall them.")
    reason = need_resources(preset, ())
    if reason:
        raise TutorError(reason)
    request.check()
    runtime, model = preset.assets
    executable = asset_path(runtime) / runtime.executable
    with TemporaryDirectory(prefix="rust-tutor-", dir="/tmp") as directory:
        root = Path(directory)
        endpoint = str(root / "tutor.sock")
        token = secrets.token_urlsafe(32)
        token_file = root / "session-key"
        token_file.write_text(token + "\n", encoding="ascii")
        arguments = [
            "--model", str(asset_path(model)), "--alias", "rust-tutor", "--host", endpoint,
            "--api-key-file", str(token_file), "--offline", "--no-webui", "--no-slots",
            "--ctx-size", "4096", "--parallel", "1", "--threads", "2", "--threads-batch", "2",
            "--threads-http", "1", "--n-gpu-layers", "0", "--batch-size", "128", "--ubatch-size", "128",
        ]
        command, env = runtime_command(executable, root, preset.limit_mib, 2, arguments)
        try:
            process = subprocess.Popen(command, cwd=directory, env=env, stdin=subprocess.DEVNULL,
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError:
            raise TutorError("Could not launch the built-in tutor runtime.") from None
        try:
            wait_ready(process, endpoint, request)
            payload = completion_payload("rust-tutor", task)
            # llama.cpp documents the schema directly inside response_format.
            payload["response_format"] = {"type": "json_schema", "schema": task.schema}
            response = request_json(PrivateConnection(endpoint, 150), "/v1/chat/completions", payload,
                                    token=token, request=request, service="The built-in tutor")
            request.check()
            return decode_completion(response, task), "The built-in tutor process stopped after this request."
        finally:
            stop(process)
