#!/usr/bin/python3
import sys

from rust_tutor import __version__


def main():
    if sys.argv[1:] == ["--version"]:
        print(__version__)
        return 0
    from rust_tutor.ui import TutorApplication

    return TutorApplication().run()


if __name__ == "__main__":
    raise SystemExit(main())
