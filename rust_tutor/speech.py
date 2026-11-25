"""On-demand local narration through an installed Piper CLI."""
from pathlib import Path
from tempfile import TemporaryDirectory

from gi.repository import Gio, GLib, Gtk

from .hardware import piper_command, valid_voice
from .local_tutor import TutorError
from .managed_runtime import runtime_command
from .model_catalog import PIPER, SPEECH, VOICE
from .model_manager import asset_path, need_resources, ready


class Narrator:
    def __init__(self):
        self.process = None
        self.media = None
        self.folder = None
        self.timer = 0
        self.status = None

    def stop(self, message=""):
        process, self.process = self.process, None
        if process is not None:
            process.force_exit()
        if self.timer:
            GLib.source_remove(self.timer)
            self.timer = 0
        media, self.media = self.media, None
        if media is not None:
            media.pause()
            media.clear()
        if self.folder:
            self.folder.cleanup()
            self.folder = None
        if self.status is not None:
            self.status.set_text(message)
            self.status = None

    def timeout(self):
        self.timer = 0
        self.stop("Speech synthesis timed out. Try a shorter passage or smaller voice.")
        return GLib.SOURCE_REMOVE

    def pause_or_resume(self):
        if self.media is not None:
            if self.media.get_playing():
                self.media.pause()
                self.status.set_text("Paused")
            else:
                self.media.play()
                self.status.set_text("Playing on this computer")

    def start(self, text, voice_path, status, managed=False):
        self.stop()
        command = str(asset_path(PIPER) / PIPER.executable) if managed else piper_command()
        if managed:
            reason = need_resources(SPEECH, ())
            if reason or not ready(SPEECH):
                status.set_text(reason or "Install the built-in speech files in Model setup.")
                return
            voice_path = asset_path(VOICE)
        elif not command or not voice_path:
            status.set_text("Set up the local Piper program and a voice in Model setup to listen.")
            return
        try:
            voice = valid_voice(voice_path)
            folder = TemporaryDirectory(prefix="rust-tutor-speech-")
            folder_path = Path(folder.name)
            output = folder_path / "read-aloud.wav"
            flags = Gio.SubprocessFlags.STDIN_PIPE | Gio.SubprocessFlags.STDOUT_SILENCE | Gio.SubprocessFlags.STDERR_SILENCE
            arguments = ["-m", str(voice), "-f", str(output)]
            try:
                if managed:
                    arguments += ["--espeak_data", str(Path(command).parent / "espeak-ng-data")]
                    launch, env = runtime_command(Path(command), folder_path, SPEECH.limit_mib, 1, arguments)
                    launcher = Gio.SubprocessLauncher.new(flags)
                    launcher.set_environ([f"{key}={value}" for key, value in env.items()])
                    launcher.set_cwd(str(folder_path))
                    process = launcher.spawnv(launch)
                else:
                    process = Gio.Subprocess.new([command, *arguments], flags)
            except GLib.Error:
                folder.cleanup()
                raise
        except (OSError, ValueError, GLib.Error, TutorError) as error:
            status.set_text(f"Speech setup: {error}")
            return
        self.process = process
        self.folder = folder
        self.status = status
        status.set_text("Preparing local audio…")
        self.timer = GLib.timeout_add_seconds(35, self.timeout)
        process.communicate_utf8_async(text.replace("\n", " ") + "\n", None, self.ready, output)

    def ready(self, process, result, output):
        try:
            process.communicate_utf8_finish(result)
            successful = process.get_successful()
        except GLib.Error:
            successful = False
        if process is not self.process:
            return
        self.process = None
        if self.timer:
            GLib.source_remove(self.timer)
            self.timer = 0
        if not successful or not output.is_file():
            self.stop("Piper could not create audio. Check the executable and voice in Model setup.")
            return
        self.media = Gtk.MediaFile.new_for_filename(str(output))
        self.media.connect("notify::ended", self.media_changed)
        self.media.connect("notify::error", self.media_changed)
        self.status.set_text("Playing on this computer")
        self.media.play()

    def media_changed(self, media, _property):
        if media is not self.media:
            return
        if media.get_error():
            self.stop("Audio playback is unavailable on this desktop.")
        elif media.get_ended():
            self.stop("Playback finished")
