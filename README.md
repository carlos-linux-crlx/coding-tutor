# Rust Tutor

Rust Tutor is a local GTK 4 and libadwaita learning app for Ubuntu. Ten authored Rust lessons introduce each idea through an explanation, a worked example, and an independent exercise. Forty-two shorter core outlines cover further Rust fundamentals and lead to command-line, local backend, and desktop projects. The course, companion reference, and progress reports work offline.

## Start on Ubuntu

Use Ubuntu 24.04 or newer with Python 3, GTK 4, and libadwaita 1.5 or newer. Install the Ubuntu packages if they are missing.

```sh
sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 python3-gi-cairo
```

From the project checkout, launch the desktop app with Ubuntu's Python.

```sh
/usr/bin/python3 main.py
```

The first five exercises work without an installed Rust toolchain. **Run sample** and **Check exercise** interpret a small Rust subset. The interpreter has no access to files, the network, or process execution. Lesson six guides you through installing Rust and VS Code or VSCodium, creating a Cargo project, running it, reading diagnostics, testing behavior, and evaluating and using a crate. External tool installation and the optional third-party crate example can require internet access. The lesson includes a standard-library alternative to the crate exercise. From lesson six onward you run projects in your own terminal and record the behavior you observed.

Open **Rust reference** to browse, search, and save a printable HTML copy. Every reference and course chapter has a cheat sheet. Open a sheet and use **Print…** for the system print dialog or **Save as PDF…** for a file. Native printing and PDF export use the Ubuntu `python3-gi-cairo` package. **Save printable HTML…** also works without that package and can be printed or saved as PDF in a browser. Application data lives under `$XDG_DATA_HOME/rust-tutor` or `~/.local/share/rust-tutor`.

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

## Milestones and course pacing

Open **Milestones and progress** for a chapter report with your behavior-check progress, concept quiz results, per-skill ratings, and the hints or retries you used. A milestone is ready when you complete every required behavior check and score at least 80% on the concept quiz. The app computes the report locally. **Ask tutor for a short chapter summary** can add prose on request using the same recorded evidence.

**Review pace and practice options** offers two short practice activities when recorded evidence shows a gap. For later chapters it can also group two adjacent skills into shared project practice. Both skills still appear with their own criteria. Grouping requires successful behavior checks for both skills, correct answers on two separately graded quizzes, at least 80% on both, and readiness on the prerequisite. Review and edit the activities before applying them. You can restore the standard pace while keeping your work and adjustment history.

## Personalize the upcoming lessons

Open **Project paths**, enter an idea, and choose the first job your project should do. **Preview authored template** shows three authored lessons. **Build a project path with the tutor** uses a configured local model to adapt the titles, practical steps, and milestones while preserving the authored concept order, explanations, examples, and reference links. The preview identifies where the proposal came from.

**Use this path** saves the approved proposal locally and makes it the active path after the Rust foundations. You can mark project pages complete, switch to another saved path, or return to the standard course. Completed core lessons and saved project paths keep their progress.

## Build and run the AppImage

The AppImage uses the host Ubuntu Python, GTK, and libadwaita packages listed above. For an x86-64 build, save the official `appimagetool-x86_64.AppImage` and `runtime-x86_64` release assets in `build/tooling/`. Compare their SHA-256 values with the release asset digests before running the tool. [appimagetool releases](https://github.com/AppImage/appimagetool/releases) · [Type 2 runtime releases](https://github.com/AppImage/type2-runtime/releases)

```sh
chmod +x build/tooling/appimagetool-x86_64.AppImage
APPIMAGE_EXTRACT_AND_RUN=1 \
  APPIMAGETOOL="$PWD/build/tooling/appimagetool-x86_64.AppImage" \
  APPIMAGETOOL_RUNTIME_FILE="$PWD/build/tooling/runtime-x86_64" \
  ./packaging/build-appimage.sh
```

Run the resulting `build/RustTutor-x86_64.AppImage` directly on a desktop with FUSE available. Use extract-and-run mode on systems without FUSE. [AppImage FUSE guide](https://docs.appimage.org/user-guide/troubleshooting/fuse.html)

```sh
APPIMAGE_EXTRACT_AND_RUN=1 ./build/RustTutor-x86_64.AppImage
```

The x86-64 build was verified with appimagetool `11d54c9` and the Type 2 runtime `fedfad5`. SquashFS inspection found the packaged launcher and desktop entry, and an extract-and-run launch opened the GTK window. The output and downloaded tools stay in Git-ignored `build/`.

To work with the staged directory separately, run `./packaging/build-appimage.sh --appdir-only` and launch `./build/RustTutor.AppDir/AppRun`.

AppImage is a distribution format. Learner code remains inside the limited interpreter. Automatic compilation of unrestricted exercise code requires a separately validated isolation mechanism.

The course data and progress are keyed by language. Future app work includes additional languages, a validated isolated Rust runner, and an optional guided connection to an LM Studio server on another computer on the same local network. That setup would explain LM Studio’s local-network settings, help enter or discover the host and port, and check reachability and available models. Current model connections use this computer.
