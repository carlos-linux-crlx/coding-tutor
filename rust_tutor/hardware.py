"""Read-only local hardware signals for optional model setup."""
import json
import os
from pathlib import Path
import shutil


def memory():
    try:
        entries = Path("/proc/meminfo").read_text().splitlines()
        values = {key: int(text.split()[0]) / 1024 ** 2
                  for key, text in (entry.split(":", 1) for entry in entries)
                  if key in {"MemTotal", "MemAvailable"}}
        return values.get("MemTotal"), values.get("MemAvailable")
    except (OSError, ValueError):
        return None, None


def graphics():
    devices = []
    for device in sorted(Path("/sys/class/drm").glob("card[0-9]*/device")):
        try:
            vendor = (device / "vendor").read_text().strip()
        except OSError:
            continue
        name = {"0x10de": "NVIDIA", "0x1002": "AMD", "0x8086": "Intel"}.get(vendor, vendor)
        try:
            gib = int((device / "mem_info_vram_total").read_text()) / 1024 ** 3
            name += f" ({gib:.1f} GiB reported VRAM)"
        except (OSError, ValueError):
            name += " (VRAM unknown)"
        devices.append(name)
    return ", ".join(devices) or "No GPU information available"


def assessment(directory):
    total, available = memory()
    disk = shutil.disk_usage(directory).free / 1024 ** 3
    summary = [f"CPU threads visible: {os.cpu_count() or 'unknown'}"]
    summary.append(f"RAM: {available:.1f} GiB available of {total:.1f} GiB"
                   if total is not None and available is not None else "RAM: unavailable")
    summary.extend((f"Disk space free: {disk:.1f} GiB", f"Graphics: {graphics()}"))
    if available is None or available < 4 or disk < 4:
        tutor = "This snapshot favors authored hints and checks. Use a measured memory budget before loading a tutor model."
    elif available < 8 or disk < 8:
        tutor = ("For the tutor, start by evaluating a 1–3B parameter quantized model with short context. "
                 "A smaller model is easier to load and may give less detailed Rust feedback.")
    else:
        tutor = ("For the tutor, evaluate a 3–7B parameter quantized model with short context and memory "
                 "headroom. Longer code reviews can need more memory. GPU acceleration still needs a runtime check.")
    if available is None or available < 2 or disk < 1:
        speech = ("Try an extra-low or low CPU voice and use the playback sample to check how it performs. "
                  "Keep speech optional if memory or disk space is tight.")
    else:
        speech = ("A low-size CPU voice is a good starting point for these lessons. "
                  "Use the playback sample to check clarity and startup time.")
    return "\n".join(summary), tutor, speech


def piper_command():
    command = shutil.which("piper")
    fallback = Path.home() / ".local/bin/piper"
    if not command and fallback.is_file() and os.access(fallback, os.X_OK):
        command = str(fallback)
    return command


def valid_voice(path):
    voice = Path(path)
    config = voice.with_suffix(".onnx.json")
    if voice.suffix != ".onnx" or not voice.is_file() or not config.is_file():
        raise ValueError("Choose a local .onnx voice with its .onnx.json file alongside it.")
    try:
        if config.stat().st_size > 2 * 1024 ** 2:
            raise ValueError
        if not isinstance(json.loads(config.read_text(encoding="utf-8")), dict):
            raise ValueError
    except (OSError, ValueError):
        raise ValueError("Piper could not use this voice because its configuration file is unreadable or invalid.") from None
    return voice
