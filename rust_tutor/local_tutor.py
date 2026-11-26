"""On-demand LM Studio client for loopback or a selected home-network address."""

from dataclasses import dataclass, field
import http.client
from ipaddress import IPv4Address, IPv4Network
import json
import socket
from threading import Event, Lock


DEFAULT_PORT = 1234
LOOPBACK = "127.0.0.1"
HOME_NETWORKS = tuple(map(IPv4Network, ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")))
CONTEXTS = (4096, 8192)
REVIEW_LIMIT = 6_000


class TutorError(RuntimeError):
    pass


def lan_address(value):
    if not isinstance(value, str):
        raise TutorError("Enter the home-network IPv4 address shown by LM Studio.")
    try:
        address = IPv4Address(value)
    except (ValueError, TypeError):
        raise TutorError("Enter the home-network IPv4 address shown by LM Studio, without http:// or the port.") from None
    if not any(address in network for network in HOME_NETWORKS):
        raise TutorError("Choose a private home-network IPv4 address, such as 192.168.1.25.")
    return str(address)


@dataclass(frozen=True)
class Model:
    key: str
    name: str
    size: int
    max_context: int | None
    instance: str | None

    @property
    def description(self):
        state = "loaded" if self.instance else "on disk"
        return f"{self.name} · {self.size / 1024 ** 3:.1f} GiB · {state}"


@dataclass(frozen=True)
class Settings:
    port: int
    model: str
    context: int
    token: str = field(default="", repr=False)
    host: str = LOOPBACK

    def __post_init__(self):
        if self.host != LOOPBACK:
            lan_address(self.host)
            if not self.token:
                raise TutorError("Enter the LM Studio API token for this LAN server.")
        if type(self.port) is not int or not 1 <= self.port <= 65535:
            raise TutorError("Enter a server port from 1 to 65535.")
        if self.context not in CONTEXTS:
            raise TutorError("Choose one of the listed context sizes.")
        if len(self.token) > 1024 or any(not 33 <= ord(char) <= 126 for char in self.token):
            raise TutorError("Enter the LM Studio API token without spaces.")


class Request:
    """Cancel generation while allowing pending model loads to return their instance ID."""

    def __init__(self):
        self.cancelled = Event()
        self._lock = Lock()
        self._socket = None

    def check(self):
        if self.cancelled.is_set():
            raise TutorError("Request canceled.")

    def attach(self, connection):
        with self._lock:
            self.check()
            self._socket = connection.sock

    def detach(self):
        with self._lock:
            self._socket = None

    def cancel(self):
        self.cancelled.set()
        with self._lock:
            if self._socket:
                try:
                    self._socket.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass


def api(settings, path, payload=None, *, timeout=4, request=None):
    # HTTPConnection doesn't use proxies, resolve a user-supplied hostname, or follow redirects.
    connection = http.client.HTTPConnection(settings.host, settings.port, timeout=timeout)
    return request_json(connection, path, payload, token=settings.token, request=request,
                        service=f"LM Studio at {settings.host}:{settings.port}")


def request_json(connection, path, payload=None, *, token="", request=None, service="The local runtime"):
    headers = {"Accept": "application/json"}
    body = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        if request:
            connection.connect()
            request.attach(connection)
        connection.request("GET" if payload is None else "POST", path, body, headers)
        response = connection.getresponse()
        if response.status in {401, 403}:
            raise TutorError(f"{service} requires a valid API token. Check Model setup.")
        if response.status in {400, 413, 422}:
            raise TutorError(f"{service} rejected the request. Check the model’s context and structured output support.")
        if response.status != 200:
            raise TutorError(f"{service} returned HTTP {response.status}. Check Model setup.")
        data = response.read(512 * 1024 + 1)
        if len(data) > 512 * 1024:
            raise TutorError(f"{service} returned an unexpectedly large response.")
        value = json.loads(data)
        if not isinstance(value, dict):
            raise TutorError(f"{service} did not return a JSON object.")
        return value
    except TimeoutError:
        if request:
            request.check()
        raise TutorError(f"{service} timed out. Check its connection and model state in Model setup.") from None
    except (OSError, http.client.HTTPException):
        if request:
            request.check()
        raise TutorError(f"Could not reach {service}. Check Model setup.") from None
    except (ValueError, RecursionError):
        raise TutorError(f"{service} did not return valid JSON.") from None
    finally:
        if request:
            request.detach()
        connection.close()


def completion_payload(instance, task):
    return {
        "model": instance,
        "messages": task.messages,
        "response_format": {"type": "json_schema", "json_schema": {
            "name": task.name, "strict": True, "schema": task.schema,
        }},
        "temperature": 0.2,
        "max_tokens": task.max_tokens,
        "stream": False,
    }


def decode_completion(answer, task):
    try:
        choice = answer["choices"][0]
        if choice.get("finish_reason") == "length":
            raise TutorError("The model ran out of response space. Try a smaller request or a model with more context.")
        return task.validate(json.loads(choice["message"]["content"]))
    except (KeyError, IndexError, AttributeError, TypeError, ValueError, RecursionError):
        raise TutorError("The model did not return usable structured guidance. Try again or choose another local model.") from None


def list_models(settings, request=None):
    body = api(settings, "/api/v1/models", request=request)
    entries = body.get("models")
    if not isinstance(entries, list):
        raise TutorError("Model listing requires LM Studio’s v1 API. Check the server and version.")
    found = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        key, size = entry.get("key"), entry.get("size_bytes")
        if (entry.get("type") != "llm" or entry.get("format") != "gguf"
                or not isinstance(key, str) or not key or type(size) is not int or size <= 0):
            continue
        name = entry.get("display_name")
        maximum = entry.get("max_context_length")
        instances = entry.get("loaded_instances")
        if not isinstance(instances, list):
            raise TutorError("LM Studio did not report model load state. Update the runtime before using the tutor.")
        loaded = [item["id"] for item in instances
                  if isinstance(item, dict) and isinstance(item.get("id"), str) and item["id"]]
        if len(loaded) != len(instances):
            raise TutorError("LM Studio returned incomplete model load information.")
        found[key] = Model(key, name if isinstance(name, str) and name else key, size,
                           maximum if type(maximum) is int and maximum > 0 else None,
                           loaded[0] if loaded else None)
    return sorted(found.values(), key=lambda model: (model.size, model.name.casefold()))


def generate(settings, request, task):
    models = list_models(settings, request)
    model = next((item for item in models if item.key == settings.model), None)
    if model is None:
        raise TutorError("The configured model is missing from the server’s model list. Choose an installed model in Model setup.")

    request.check()
    instance = model.instance
    owned_instance = None
    warning = ""
    error = None
    value = None
    try:
        if instance is None:
            context = min(settings.context, model.max_context or settings.context)
            try:
                result = api(settings, "/api/v1/models/load",
                             {"model": model.key, "context_length": context}, timeout=75)
                instance = result.get("instance_id")
                if not isinstance(instance, str) or not instance:
                    raise TutorError("LM Studio did not return the loaded instance ID.")
            except TutorError as problem:
                raise TutorError(f"{problem} Check LM Studio for any model left loaded.") from None
            owned_instance = instance
        request.check()
        answer = api(settings, "/v1/chat/completions", completion_payload(instance, task), timeout=120, request=request)
        request.check()
        value = decode_completion(answer, task)
    except TutorError as problem:
        error = problem
    finally:
        if owned_instance:
            try:
                unloaded = api(settings, "/api/v1/models/unload", {"instance_id": owned_instance}, timeout=15)
                if unloaded.get("instance_id") != owned_instance:
                    raise TutorError("Unexpected unload response.")
            except TutorError:
                warning = "LM Studio did not confirm unload. Check its loaded models before retrying."
    if model.instance and not error:
        warning = "The model was already loaded when this request started. Manage it in LM Studio."
    if error:
        raise TutorError(" ".join(part for part in (str(error), warning) if part))
    return value, warning or "The model loaded for this request was unloaded."
