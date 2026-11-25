"""Pinned, publisher-supplied assets offered by the model manager."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Asset:
    name: str
    url: str
    size: int
    sha256: str
    destination: str
    executable: str = ""
    unpacked_limit: int = 0


@dataclass(frozen=True)
class Preset:
    key: str
    title: str
    tradeoff: str
    ram_gib: float
    limit_mib: int
    assets: tuple[Asset, ...]
    source: str
    license: str


LLAMA_RELEASE = "https://github.com/ggml-org/llama.cpp/releases/tag/b12726"
LLAMA = Asset(
    "llama.cpp CPU runtime",
    "https://github.com/ggml-org/llama.cpp/releases/download/b12726/llama-b12726-bin-ubuntu-x64.tar.gz",
    23_396_793, "cbfac3a6328b62f33239698f6b4daca58597a7be9f2e67b53ac1d28877908f71",
    "llama-b12726", "llama-server", 70 * 1024 ** 2,
)


def qwen_asset(parameters, revision, size, digest):
    file = f"qwen2.5-coder-{parameters}-instruct-q4_k_m.gguf"
    source = f"https://huggingface.co/Qwen/Qwen2.5-Coder-{parameters.upper()}-Instruct-GGUF"
    return Asset("Qwen model weights", f"{source}/resolve/{revision}/{file}", size, digest, file), source


COMPACT, COMPACT_SOURCE = qwen_asset(
    "0.5b", "ebb2015119c907b064c512bf053e945850b5875f", 491_400_064,
    "1d9614638d18024d0fbb36575a15f1302a3adf044df10345688ec4f6e1c4ff32",
)
STANDARD, STANDARD_SOURCE = qwen_asset(
    "1.5b", "f86cb2c1fa58255f8052cc32aeede1b7482d4361", 1_117_320_768,
    "cc324af070c2ecbfd324a30884d2f951a7ff756aba85cb811a6ec436933bb046",
)
TUTORS = (
    Preset("compact", "Qwen2.5-Coder 0.5B · Compact",
           "Suitable for short questions. More complex reviews and project paths may need a retry or an authored template.",
           2.75, 2304, (LLAMA, COMPACT), COMPACT_SOURCE, "Apache-2.0 model · MIT runtime"),
    Preset("standard", "Qwen2.5-Coder 1.5B · More capable",
           "More capacity for explanations and plans. It needs more memory, time, and disk space.",
           5.0, 3840, (LLAMA, STANDARD), STANDARD_SOURCE, "Apache-2.0 model · MIT runtime"),
)

PIPER_RELEASE = "https://github.com/rhasspy/piper/releases/tag/2023.11.14-2"
PIPER = Asset(
    "Piper CPU runtime",
    "https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_linux_x86_64.tar.gz",
    26_460_462, "a50cb45f355b7af1f6d758c1b360717877ba0a398cc8cbe6d2a7a3a26e225992",
    "piper", "piper", 60 * 1024 ** 2,
)
VOICE_BASE = "https://huggingface.co/rhasspy/piper-voices"
VOICE_REV = "5ec43b186ef915a195d3ddbcfd9916e76c503c3f"
VOICE_FOLDER = "en/en_US/ljspeech/medium"
VOICE_FILE = "en_US-ljspeech-medium.onnx"
VOICE_URL = f"{VOICE_BASE}/resolve/{VOICE_REV}/{VOICE_FOLDER}/{VOICE_FILE}"
VOICE = Asset("LJ Speech ONNX voice", VOICE_URL, 63_531_379,
              "6f52a751e2349abe7a76735eb09dc1875298c77ea2342ffd2fef79ff81b87f22", VOICE_FILE)
VOICE_CONFIG = Asset("LJ Speech voice configuration", f"{VOICE_URL}.json", 4972,
                     "141d612cc0a95ed7efc1ca936b845c2364967f2e9217c5dbfcf69fc4d6c65860", f"{VOICE_FILE}.json")
SPEECH = Preset(
    "speech", "Piper · LJ Speech (US English)",
    "A separate one-CPU voice for lesson and reference prose. It loads only for read-aloud.",
    1.25, 1024, (PIPER, VOICE, VOICE_CONFIG), f"{VOICE_BASE}/tree/{VOICE_REV}/{VOICE_FOLDER}",
    "MIT runtime and voice release · public-domain training data",
)
