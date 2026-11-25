"""Local drafts and learning signals."""

import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile


def data_directory():
    return Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share") / "rust-tutor"


class Progress:
    def __init__(self):
        self.path = data_directory() / "progress.json"
        self.data = {}
        if self.path.is_file():
            try:
                self.data = json.loads(self.path.read_text(encoding="utf-8"))
                if not isinstance(self.data, dict):
                    raise ValueError("Expected an object")
            except (OSError, ValueError):
                raise RuntimeError(f"Could not read progress at {self.path}.") from None

    def course(self, language):
        return self.data.setdefault("courses", {}).setdefault(language, {})

    def lesson(self, language, lesson_id):
        return self.course(language).setdefault("lessons", {}).setdefault(lesson_id, {})

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(dir=self.path.parent, mode="w", encoding="utf-8", delete=False) as stream:
            staged = Path(stream.name)
            try:
                json.dump(self.data, stream, ensure_ascii=False, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
                os.replace(staged, self.path)
            finally:
                staged.unlink(missing_ok=True)
