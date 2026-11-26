# Third-party notices

Rust Tutor's original source code, authored lesson text, and documentation are
licensed under the MIT License in [LICENSE](LICENSE). The original course
explains concepts in its own words and links to the Rust project documentation;
the Rust Book and Rust reference remain the Rust project's material. No Rust
Book images or other external programming illustrations are bundled in the
source tree.

This is the current inventory of known third-party material and software
associated with the project. It is not a guarantee that every upstream package
or generated model output has been independently cleared for every use. Check
the original publisher's terms before redistributing downloaded assets or
using generated output.

## Included in the AppImage

- **AppImage Type 2 runtime** — embedded by appimagetool in the AppImage.
  The runtime is MIT licensed; its copyright and license text, plus its notices
  for statically linked libraries, are in
  [licenses/APPIMAGE-TYPE2-RUNTIME-LICENSE.txt](licenses/APPIMAGE-TYPE2-RUNTIME-LICENSE.txt).
  Upstream: https://github.com/AppImage/type2-runtime
- **Ubuntu Yaru accessories-text-editor icon** — used unmodified as the
  AppImage icon. Yaru icon assets are Copyright 2018 Sam Hewitt and licensed
  CC BY-SA 4.0. Source: https://github.com/ubuntu/yaru
  License: https://creativecommons.org/licenses/by-sa/4.0/
- The AppImage uses the host's Python, GTK 4, and libadwaita; these system
  packages are not bundled by this project and remain under their respective
  upstream licenses.

## Downloaded on the learner's request

These assets are fetched directly from their named publishers after the learner
confirms the download. They are not included in the source repository or
AppImage. Rust Tutor verifies pinned hashes and extracts the publisher's
runtime archive without intentionally removing its included files or notices.

- **llama.cpp CPU runtime**, release b12726 — upstream project license is MIT:
  https://github.com/ggml-org/llama.cpp/blob/master/LICENSE
  Release: https://github.com/ggml-org/llama.cpp/releases/tag/b12726
- **Qwen2.5-Coder 0.5B and 1.5B GGUF model weights** — Apache License 2.0;
  the model repositories contain the license text and model terms:
  https://huggingface.co/Qwen/Qwen2.5-Coder-0.5B-Instruct-GGUF
  https://huggingface.co/Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF
- **Piper 1.2.0 runtime archive**, release 2023.11.14-2 — the archived
  rhasspy/piper project is MIT licensed:
  https://github.com/rhasspy/piper
  https://github.com/rhasspy/piper/releases/tag/2023.11.14-2
  The archive can contain separately licensed dependencies and data. Preserve
  the upstream archive's notices and follow each component's license; this
  notice does not relicense the archive as a whole.
- **Piper en_US-ljspeech-medium voice and configuration** — the pinned
  rhasspy/piper-voices repository is MIT licensed; its model card identifies
  the LJ Speech training dataset as public domain. The voice files are
  downloaded separately and are not bundled:
  https://huggingface.co/rhasspy/piper-voices/tree/5ec43b186ef915a195d3ddbcfd9916e76c503c3f/en/en_US/ljspeech/medium
  Model card: https://huggingface.co/rhasspy/piper-voices/blob/5ec43b186ef915a195d3ddbcfd9916e76c503c3f/en/en_US/ljspeech/medium/MODEL_CARD

## Build-time tooling

- **appimagetool** is used only to create AppImages and is not included in the
  AppImage or source repository. Its source is MIT licensed:
  https://github.com/AppImage/appimagetool
- The AppImage runtime is embedded in the output artifact; see the notice above.
