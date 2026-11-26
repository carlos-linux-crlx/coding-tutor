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
3. Select **Use installed model**. Each explicit chat, review, lesson drafting, or chapter summary request starts a disposable CPU-only process with a private Unix socket. The built-in tutor uses a 4,096-token context, at most two logical CPUs, reduced scheduling priority, and an address-space limit chosen for the preset. The process exits when the request completes or is canceled. Actual fit, latency, and answer quality depend on the machine and model. Authored hints and lesson checks are available if the machine has too little headroom.

The built-in tutor uses the downloaded model offline. Questions and feedback are kept in the tutor page for follow-up during that visit. Exercise checks determine whether the code passes. AI feedback is advisory.

The **Use LM Studio on this computer or on your LAN** panel is an optional alternative for models you already manage. On the same computer, start LM Studio’s loopback server, check the connection, and choose an installed GGUF instruction model. The app asks LM Studio to unload models it loads. LM Studio manages the server and any models it had already loaded. [LM Studio server setup](https://lmstudio.ai/docs/developer/rest/quickstart)

### Use another computer on your home network

1. In LM Studio 0.4 or newer on the other computer, open **Developer → Server Settings**. Enable **Serve on Local Network** and **Require Authentication**, create an API token via **Manage Tokens**, and start the server. Copy the private IPv4 address and port from the API URL. [LAN setup](https://lmstudio.ai/docs/developer/core/server/serve-on-network) · [API authentication](https://lmstudio.ai/docs/developer/core/authentication)
2. In Rust Tutor, choose **Another computer on my home network**, enter the address, port, and token, then select **Check connection and models**. This lists models without loading one. Choose a model and select **Use selected model**. The selected address, port, model, and context are saved locally. The token stays in memory for this app session and is tied to that address and port.
3. Use a trusted home network. Keep the server off the internet and avoid router port forwarding. Connections use HTTP, so anyone able to inspect the traffic can read the token and request contents. Tutor pages show the destination before sending requests. Use the built-in tutor if source or progress should stay on your computer. Speech stays on this computer with either tutor backend.

## Optional speech

Use the separate built-in Piper download in **Model setup** on x86-64 Ubuntu. A fresh speech install is about 90 MB. Select the installed voice, then use **Read aloud** on a lesson or reference page. Piper runs on one logical CPU, writes a temporary WAV, and exits. GTK handles playback. You can also use a Piper CLI and voice you installed yourself under **Use an existing Piper voice**. [Piper runtime](https://github.com/rhasspy/piper/releases/tag/2023.11.14-2) · [LJ Speech voice](https://huggingface.co/rhasspy/piper-voices/tree/5ec43b186ef915a195d3ddbcfd9916e76c503c3f/en/en_US/ljspeech/medium)

## Review a file from VS Code or VSCodium

Save your work in the editor, then open **Review from editor** and choose up to four related `.rs` files or a `Cargo.toml`. You can preview each selected file in memory. Choose a lesson to apply its bounded exercise checks to the .rs file you’re previewing. Run full Cargo builds and tests in your project terminal.

**Review selected files with the tutor** sends up to 6,000 characters across that selection, the file names without their directories, optional expected behavior, and any shown check results to the displayed tutor destination. Review gives a hint and a suggested next check. For a future VS Code-compatible extension, use an explicit selection and a local handoff to the same preview and review flow.

## Milestones and course pacing

Open **Milestones and progress** for a chapter report with a behavior-check bar and concept results for each skill, the milestone quiz, and a suggested next step. A milestone is ready when you complete every required behavior check and score at least 80% on the concept quiz. Hints and retries describe support used. The app computes the report locally. **Ask tutor for a short chapter summary** can add prose on request using the same recorded evidence.

**Review pace and practice options** offers two short lesson pages when recorded evidence shows a gap. After approval they appear after the affected core lesson, before the next topic. For later chapters it can also group two adjacent skills into shared project practice. Both skills keep their own criteria. Grouping requires successful behavior checks for both skills, correct answers on two separately graded quizzes, at least 80% on both, and readiness on the prerequisites. Preview and edit the proposal before applying it. Restore the standard pace to return to the original sequence and retain your work and adjustment history.

## Personalize the upcoming lessons

Open **Project paths**, enter an idea, and choose the first job your app should do. **Preview authored template** shows three offline lessons. **Build a project path with the tutor** uses the next unfinished roadmap chapter and saved check and quiz evidence. The tutor drafts up to three lesson pages with a concept explanation, a worked example, an independent exercise, and a hint. The skills, prerequisites, and behavior criteria come from the standard roadmap.

Edit the proposal in the preview, then select **Use this path**. The approved pages appear next to their core topics once prerequisites are ready. Mark project pages complete separately from core checks. You can switch paths or return to the standard course while keeping your progress.

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

The course data and progress are keyed by language. Future app work includes additional languages and a validated isolated Rust runner.
