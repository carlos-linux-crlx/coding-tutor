"""Exercise the real urllib redirect handler with offline publisher responses."""

from dataclasses import replace
from email.message import Message
import hashlib
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from urllib.error import URLError
from urllib.request import HTTPSHandler, ProxyHandler, build_opener
from urllib.response import addinfourl

from rust_tutor.local_tutor import Request, TutorError
from rust_tutor.model_catalog import COMPACT, LLAMA, PIPER, STANDARD, VOICE, VOICE_CONFIG
from rust_tutor.model_manager import download


class FixtureHTTPS(HTTPSHandler):
    def __init__(self, routes):
        super().__init__()
        self.routes = routes
        self.requests = []

    def https_open(self, request):
        self.requests.append(request.full_url)
        result = self.routes[request.full_url]
        if isinstance(result, Exception):
            raise result
        status, fields, body = result
        headers = Message()
        for name, value in fields.items():
            headers[name] = value
        response = addinfourl(BytesIO(body), headers, request.full_url, status)
        response.msg = "Fixture"
        return response


class DownloadTests(unittest.TestCase):
    payload = b"model download fixture"

    def setUp(self):
        folder = TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.target = Path(folder.name) / "asset"
        self.request = Request()

    def download_from(self, asset, routes):
        fixture = FixtureHTTPS(routes)
        self.requests = fixture.requests

        def opener(*handlers):
            return build_opener(ProxyHandler({}), *handlers, fixture)

        with patch("rust_tutor.model_manager.build_opener", opener):
            download(asset, self.target, self.request, self.progress)

    def progress(self, _received):
        pass

    def asset(self, asset):
        return replace(asset, size=len(self.payload), sha256=hashlib.sha256(self.payload).hexdigest())

    def test_direct_download(self):
        self.download_from(self.asset(VOICE_CONFIG), {VOICE_CONFIG.url: (200, {}, self.payload)})
        self.assertEqual(self.target.read_bytes(), self.payload)

    def test_tutor_and_speech_weights_follow_hugging_face_cdn(self):
        for asset in (COMPACT, STANDARD, VOICE):
            with self.subTest(asset=asset.destination):
                same_host = "https://huggingface.co/cache/file"
                cdn = "https://us.aws.cdn.hf.co/file?signature=fixture"
                self.download_from(self.asset(asset), {
                    asset.url: (307, {"Location": same_host}, b""),
                    same_host: (302, {"Location": cdn}, b""),
                    cdn: (200, {}, self.payload),
                })
                self.assertEqual(self.requests, [asset.url, same_host, cdn])
                self.assertEqual(self.target.read_bytes(), self.payload)
                self.target.unlink()

    def test_runtime_redirects_still_work(self):
        for asset in (LLAMA, PIPER):
            with self.subTest(asset=asset.destination):
                cdn = "https://release-assets.githubusercontent.com/release-file"
                self.download_from(self.asset(asset), {
                    asset.url: (302, {"Location": cdn}, b""),
                    cdn: (200, {}, self.payload),
                })
                self.assertEqual(self.requests, [asset.url, cdn])
                self.assertEqual(self.target.read_bytes(), self.payload)
                self.target.unlink()

    def test_invalid_or_cross_publisher_redirects_are_never_opened(self):
        for target in ("https://us.aws.cdn.hf.co.example.org/file",
                       "https://release-assets.githubusercontent.com/file",
                       "https://@us.aws.cdn.hf.co/file",
                       "https://us.aws.cdn.hf.co:8080/file",
                       "https://[bad-host/file",
                       "http://us.aws.cdn.hf.co/file"):
            with self.subTest(target=target):
                with self.assertRaisesRegex(TutorError, "redirect"):
                    self.download_from(self.asset(VOICE), {VOICE.url: (302, {"Location": target}, b"")})
                self.assertEqual(self.requests, [VOICE.url])
                self.assertFalse(self.target.exists())

    def test_redirected_http_error_reports_status_without_url(self):
        cdn = "https://us.aws.cdn.hf.co/file?signature=fixture"
        with self.assertRaisesRegex(TutorError, "HTTP 403") as error:
            self.download_from(self.asset(VOICE), {
                VOICE.url: (302, {"Location": cdn}, b""),
                cdn: (403, {}, b"expired"),
            })
        self.assertNotIn("signature", str(error.exception))
        self.assertFalse(self.target.exists())

    def test_network_error_is_reported_separately(self):
        with self.assertRaisesRegex(TutorError, "Check your network"):
            self.download_from(self.asset(VOICE), {VOICE.url: URLError("fixture failure")})

    def test_redirected_payload_still_requires_pinned_checksum(self):
        cdn = "https://us.aws.cdn.hf.co/file"
        with self.assertRaisesRegex(TutorError, "SHA-256"):
            self.download_from(self.asset(COMPACT), {
                COMPACT.url: (302, {"Location": cdn}, b""),
                cdn: (200, {}, b"x" * len(self.payload)),
            })

    def test_download_can_be_canceled_after_receiving_bytes(self):
        with patch.object(self, "progress", side_effect=lambda _received: self.request.cancel()):
            with self.assertRaisesRegex(TutorError, "Request canceled"):
                self.download_from(self.asset(VOICE), {VOICE.url: (200, {}, self.payload)})


if __name__ == "__main__":
    unittest.main()
