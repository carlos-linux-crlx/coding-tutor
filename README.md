# Rust Tutor

Rust Tutor is a local GTK 4 and libadwaita learning app for Ubuntu. The first milestone covers running a program, understanding functions, and building a calculator. The app includes an offline reference, printable HTML export, a milestone quiz, and local drafts and progress.

## Start on Ubuntu

Use Ubuntu 24.04 or newer with Python 3, GTK 4, and libadwaita 1.5 or newer. Install the Ubuntu packages if they are missing.

```sh
sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1
```

From the project checkout, launch the desktop app with Ubuntu's Python.

```sh
/usr/bin/python3 main.py
```

The three practice exercises work without an installed Rust toolchain. **Run sample** and **Check exercise** interpret a small Rust subset in the app. The interpreter has no access to files, the network, or process execution. A real Rust compiler may give additional diagnostics. For full projects, the in-app editor guide walks through installing Rust and VS Code or VSCodium, creating a Cargo project, and compiling and running it in your own terminal.

Open **Rust reference** to browse, search, and save a printable HTML copy. Open that file in your browser and print it or use the browser's **Save as PDF** option. Application data lives under `$XDG_DATA_HOME/rust-tutor` or `~/.local/share/rust-tutor`.

## Optional local tutor

1. In **Model setup**, choose a built-in tutor preset on x86-64 Ubuntu. The compact Qwen2.5-Coder 0.5B preset is about 515 MB for a fresh install, and the 1.5B preset is about 1.14 GB. The app shows current disk and RAM guidance, expected downloads, publisher links, and licenses before confirmation. [llama.cpp CPU runtime](https://github.com/ggml-org/llama.cpp/releases/tag/b12726) · [Qwen compact model](https://huggingface.co/Qwen/Qwen2.5-Coder-0.5B-Instruct-GGUF) · [Qwen larger model](https://huggingface.co/Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF)
2. Select **Review download…** and confirm if you want to proceed. Downloads can be canceled. Each completed file is checked against a pinned SHA-256 and saved under `$XDG_DATA_HOME/rust-tutor/models` or `~/.local/share/rust-tutor/models`. Finished, verified files can be reused after cancellation.
3. Select **Use installed model**. **Ask tutor**, **Review project with the tutor**, and **Build a project path with the tutor** start a disposable CPU-only process with a private Unix socket. The built-in tutor uses a 4,096-token context, at most two logical CPUs, reduced scheduling priority, and an address-space limit chosen for the preset. The process exits when the request completes or is canceled. Actual fit, latency, and answer quality depend on the machine and model. Authored hints and lesson checks are available if the machine has too little headroom.

The built-in tutor uses the downloaded model offline. Questions and feedback are kept in the tutor page for follow-up during that visit. Exercise checks determine whether the code passes. AI feedback is advisory.

The **Use a separate LM Studio server** panel is an optional alternative for models you already manage. Start its loopback server, check the connection, and choose an installed model. An API token, if needed, lasts for the current app session. The app requests unload for models it loads. LM Studio manages the server and any models it had already loaded. [LM Studio local server setup](https://lmstudio.ai/docs/developer/rest/quickstart)

## Optional speech

Use the separate built-in Piper download in **Model setup** on x86-64 Ubuntu. A fresh speech install is about 90 MB. Select the installed voice, then use **Read aloud** on a lesson or reference page. Piper runs on one logical CPU, writes a temporary WAV, and exits. GTK handles playback. You can also use a Piper CLI and voice you installed yourself under **Use an existing Piper voice**. [Piper runtime](https://github.com/rhasspy/piper/releases/tag/2023.11.14-2) · [LJ Speech voice](https://huggingface.co/rhasspy/piper-voices/tree/5ec43b186ef915a195d3ddbcfd9916e76c503c3f/en/en_US/ljspeech/medium)

## Review a file from VS Code or VSCodium

Save your Rust file in the editor, then open **Review from editor** and deliberately choose that `.rs` file. The app previews the selected file in memory. If it contains one of the lesson exercises, choose the lesson and apply its behavior checks. The project file and lesson draft remain independent. For a general Cargo project, use the in-app guide and run `cargo check` or `cargo test` from the project terminal.

With a configured model, **Review project with the tutor** sends one selected Rust file of up to 6,000 characters, optional expected behavior, and any displayed lesson check results to the local server. The tutor gives advisory feedback and a suggested next check. Run the full project and its tests in your editor. Multi-file context and editor extensions are future work.

## Personalize the upcoming lessons

Open **Project paths**, enter an idea, and choose the first job your project should do. **Preview authored template** shows three authored lessons. **Build a project path with the tutor** uses a configured local model to adapt the titles, practical steps, and milestones while preserving the authored concept order, explanations, examples, and reference links. The preview identifies where the proposal came from.

**Use this path** saves the approved proposal locally and makes it the active path after the Rust foundations. You can mark project pages complete, switch to another saved path, or return to the standard course. Completed core lessons and saved project paths keep their progress.

## AppImage staging

The packaging recipe stages a runnable AppDir using the Ubuntu packages listed above and a stock icon from the installed Ubuntu theme. From the project checkout, run these commands to stage and launch it.

```sh
./packaging/build-appimage.sh --appdir-only
./build/RustTutor.AppDir/AppRun
```

The current build stops at the AppDir because `appimagetool` is unavailable. Producing a distributable `.AppImage` requires `appimagetool` on PATH and a separate run of `./packaging/build-appimage.sh`. The recipe writes `build/RustTutor-<architecture>.AppImage`. [AppImage packaging tool](https://github.com/AppImage/appimagetool)

AppImage is a distribution format. Learner code remains inside the limited interpreter. Automatic compilation of unrestricted exercise code requires a separately validated isolation mechanism.

The course data and progress are keyed by language. A later milestone can add full GUI and backend projects, additional languages, and a validated isolated Rust runner.
