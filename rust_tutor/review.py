"""Read a bounded, explicit selection from a learner's editor project."""

from dataclasses import dataclass
import os
from pathlib import Path
import stat

from .local_tutor import REVIEW_LIMIT


MAX_FILES = 4
MAX_PREVIEW_BYTES = 48 * 1024


@dataclass(frozen=True)
class ReviewFile:
    path: Path
    source: str
    size: int


def read_selection(paths):
    paths = tuple(dict.fromkeys(Path(path) for path in paths))
    if not 1 <= len(paths) <= MAX_FILES:
        raise ValueError(f"Choose between one and {MAX_FILES} files.")
    files = []
    available = MAX_PREVIEW_BYTES
    for path in paths:
        if path.suffix != ".rs" and path.name != "Cargo.toml":
            raise ValueError("Choose Rust source files or a Cargo.toml manifest.")
        with os.fdopen(os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW), "rb") as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise ValueError("Choose regular files from your project.")
            contents = stream.read(available + 1)
        if len(contents) > available:
            raise ValueError("Choose a smaller selection. Preview is limited to 48 KiB total.")
        try:
            source = contents.decode("utf-8")
        except UnicodeDecodeError:
            raise ValueError("Choose UTF-8 project files.") from None
        if "\x00" in source:
            raise ValueError("Choose plain-text project files.")
        files.append(ReviewFile(path, source, len(contents)))
        available -= len(contents)
    return tuple(files)


def review_payload(files):
    if not files or not any(item.path.suffix == ".rs" for item in files):
        raise ValueError("Select at least one Rust source file.")
    if sum(len(item.source) for item in files) > REVIEW_LIMIT:
        raise ValueError(f"Select at most {REVIEW_LIMIT:,} characters of code across your files.")
    # Number duplicate filenames without sending absolute paths or unrelated directories.
    return [{"file": item.path.name, "selection": index, "source": item.source}
            for index, item in enumerate(files, start=1)]
