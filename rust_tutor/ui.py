"""Native GTK and libadwaita interface for the first Rust milestone."""

import hashlib
import logging
from pathlib import Path
from threading import Thread
from uuid import uuid4

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib, Gtk

from .course import COURSES
from .exercises import ExerciseError, check
from .hardware import assessment, memory, piper_command, valid_voice
from .local_tutor import CONTEXTS, DEFAULT_PORT, REVIEW_LIMIT, Request, Settings, TutorError, cli_available, generate, list_models
from .managed_runtime import generate_managed
from .model_catalog import LLAMA_RELEASE, PIPER_RELEASE, SPEECH, TUTORS
from .model_manager import install, model_directory, need_resources, ready, remaining
from .project_path import FOCUSES, propose_path
from .reference import printable_reference
from .speech import Narrator
from .state import Progress
from .tutor_tasks import guidance_task, project_task


def column(spacing=12):
    return Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=spacing)


def line(spacing=8):
    return Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=spacing)


def label(text="", style=None):
    widget = Gtk.Label(label=text, xalign=0, wrap=True)
    if style:
        widget.add_css_class(style)
    return widget


def button(text, callback, style=None):
    widget = Gtk.Button(label=text)
    widget.connect("clicked", lambda _button: callback())
    if style:
        widget.add_css_class(style)
    return widget


def code_view(text, editable=False):
    view = Gtk.TextView(monospace=True, editable=editable, cursor_visible=editable)
    view.set_accepts_tab(False)
    view.set_wrap_mode(Gtk.WrapMode.NONE)
    view.set_top_margin(12)
    view.set_bottom_margin(12)
    view.set_left_margin(14)
    view.set_right_margin(14)
    view.get_buffer().set_text(text)
    scroller = Gtk.ScrolledWindow()
    scroller.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC if editable else Gtk.PolicyType.NEVER)
    scroller.set_propagate_natural_height(True)
    if editable:
        scroller.set_min_content_height(182)
        scroller.set_max_content_height(270)
    scroller.set_child(view)
    frame = Gtk.Frame()
    frame.add_css_class("code-surface")
    frame.set_child(scroller)
    return frame, view.get_buffer()


class TutorApplication(Adw.Application):
    def __init__(self):
        super().__init__(application_id="local.rusttutor.Learn",
                         flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        self.window = None

    def do_activate(self):
        if self.window is None:
            self.window = TutorWindow(self)
        self.window.present()


class TutorWindow(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="Rust Tutor", default_width=1090, default_height=820)
        self.language = "rust"
        self.course = COURSES[self.language]
        self.lessons = {lesson.id: lesson for lesson in self.course["lessons"]}
        self.chapters = {chapter.id: chapter for chapter in self.course["chapters"]}
        self.progress = Progress()
        self.narrator = Narrator()
        self.tutor_job = None
        self.tutor_token = ""
        self.page_revision = 0
        self.draft_timer = 0
        self.sidebar_rows = {}

        self.split = Adw.NavigationSplitView(min_sidebar_width=245, max_sidebar_width=275,
                                            sidebar_width_fraction=0.245)
        self.toasts = Adw.ToastOverlay(child=self.split)
        self.set_content(self.toasts)
        breakpoint = Adw.Breakpoint.new(Adw.BreakpointCondition.parse("max-width: 720sp"))
        breakpoint.add_setter(self.split, "collapsed", True)
        self.add_breakpoint(breakpoint)

        left_toolbar = Adw.ToolbarView()
        left_toolbar.add_top_bar(Adw.HeaderBar(show_end_title_buttons=False))
        left_toolbar.set_content(self.sidebar())
        self.split.set_sidebar(Adw.NavigationPage.new(left_toolbar, "Rust Tutor"))

        self.page_toolbar = Adw.ToolbarView()
        self.page_toolbar.add_top_bar(Adw.HeaderBar(show_start_title_buttons=False))
        self.page = Adw.NavigationPage.new(self.page_toolbar, "Lesson")
        self.split.set_content(self.page)
        self.connect("close-request", self.on_close)

        provider = Gtk.CssProvider()
        provider.load_from_string("""
            .code-surface textview, .code-surface textview text { background: transparent; }
            .code-surface { background: alpha(currentColor, 0.045); border-radius: 10px; }
            .learning-body { line-height: 1.4; }
            .lesson-card { padding: 14px 16px; }
            .step { padding: 7px 11px; border-radius: 6px; background: alpha(currentColor, 0.06); }
        """)
        Gtk.StyleContext.add_provider_for_display(self.get_display(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        course = self.progress.course(self.language)
        lesson_id = course.get("current")
        self.open_lesson(self.lessons.get(lesson_id) or next(iter(self.lessons.values())), show=False)

    def sidebar(self):
        outer = column(18)
        outer.set_margin_top(18)
        outer.set_margin_bottom(16)
        outer.set_margin_start(12)
        outer.set_margin_end(12)
        title = label("Beginner Rust", "title-3")
        title.set_margin_start(8)
        outer.append(title)
        self.summary = label(style="dim-label")
        self.summary.set_margin_start(8)
        outer.append(self.summary)
        self.navigation = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE)
        self.navigation.add_css_class("navigation-sidebar")
        outer.append(self.navigation)
        for lesson in self.lessons.values():
            self.nav_row(lesson.id, lesson.title, lambda item=lesson: self.open_lesson(item))
        self.nav_row("quiz", "Milestone quiz", self.open_quiz)
        self.navigation.append(Gtk.Separator(margin_top=12, margin_bottom=12))
        separator = self.navigation.get_row_at_index(len(self.sidebar_rows))
        separator.set_selectable(False)
        separator.set_activatable(False)
        self.nav_row("reference", "Rust reference", self.open_reference, "help-browser-symbolic")
        self.nav_row("next", "Path and editor setup", self.open_path, "folder-documents-symbolic")
        self.nav_row("projects", "Project paths", self.open_project_paths, "document-new-symbolic")
        self.nav_row("tutor", "Ask tutor", self.open_tutor, "help-about-symbolic")
        self.nav_row("handoff", "Review from editor", self.open_editor_review, "document-open-symbolic")
        self.nav_row("models", "Model setup", self.open_models, "preferences-system-symbolic")
        self.navigation.connect("row-activated", self.navigate)
        scroller = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER)
        scroller.set_child(outer)
        return scroller

    def nav_row(self, key, text, callback, icon=None):
        row = Gtk.ListBoxRow()
        row.callback = callback
        body = line()
        body.set_margin_top(7)
        body.set_margin_bottom(7)
        body.set_margin_start(8)
        body.set_margin_end(8)
        if icon:
            body.append(Gtk.Image.new_from_icon_name(icon))
        title = label(text)
        title.set_hexpand(True)
        body.append(title)
        status = Gtk.Image.new_from_icon_name("object-select-symbolic")
        status.set_tooltip_text("Exercise passed")
        status.set_visible(False)
        body.append(status)
        row.set_child(body)
        self.navigation.append(row)
        self.sidebar_rows[key] = (row, status)

    def navigate(self, _listbox, row):
        row.callback()

    def save(self):
        try:
            self.progress.save()
        except OSError as error:
            self.toasts.add_toast(Adw.Toast(title=f"Could not save progress: {error}"))

    def schedule_draft_save(self, buffer, record):
        record["draft"] = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), True)
        if self.draft_timer:
            GLib.source_remove(self.draft_timer)
        self.draft_timer = GLib.timeout_add(600, self.flush_draft)

    def flush_draft(self):
        self.draft_timer = 0
        self.save()
        return GLib.SOURCE_REMOVE

    def on_close(self, _window):
        self.narrator.stop()
        self.cancel_tutor()
        self.save()
        return False

    def update_progress(self):
        complete = 0
        for lesson in self.lessons.values():
            record = self.progress.lesson(self.language, lesson.id)
            passed = bool(record.get("passed"))
            self.sidebar_rows[lesson.id][1].set_visible(passed)
            complete += int(passed)
        self.summary.set_text(f"{complete} of {len(self.lessons)} exercises complete")

    def document(self, key, title, show=True):
        self.narrator.stop()
        self.page_revision += 1
        self.cancel_tutor()
        self.page.set_title(title)
        self.navigation.select_row(self.sidebar_rows[key][0])
        if show:
            self.split.set_show_content(True)

        article = column(16)
        article.set_margin_top(28)
        article.set_margin_bottom(38)
        article.set_margin_start(22)
        article.set_margin_end(22)
        clamp = Adw.Clamp(maximum_size=786, tightening_threshold=650, child=article)
        scroller = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER)
        scroller.set_child(clamp)
        self.page_toolbar.set_content(scroller)
        self.update_progress()
        return article

    def cancel_tutor(self):
        if self.tutor_job:
            self.tutor_job.cancel()

    def tutor_configured(self):
        config = self.progress.data.get("tutor", {})
        if config.get("backend") == "managed":
            return any(preset.key == config.get("model") and ready(preset) for preset in TUTORS)
        return bool(config.get("model"))

    def tutor_settings(self):
        config = self.progress.data.get("tutor", {})
        if not config.get("model"):
            raise TutorError("Tutor not configured. Check the LM Studio server and choose a model in Model setup.")
        return Settings(config["port"], config["model"], config["context"], self.tutor_token)

    def start_tutor_job(self, work, receive, status, pending, cancel=None, settled=None):
        if self.tutor_job:
            status.set_text("Another model operation is still finishing.")
            return
        job = Request()
        self.tutor_job = job
        page = self.page_revision
        status.set_text(pending)
        if cancel is not None:
            cancel.set_sensitive(True)

        def finished(result, error):
            self.tutor_job = None
            if self.page_revision == page:
                if cancel is not None:
                    cancel.set_sensitive(False)
                if settled is not None:
                    settled()
                if error or job.cancelled.is_set():
                    status.set_text(error or "Request canceled.")
                else:
                    receive(result)
            return GLib.SOURCE_REMOVE

        def worker():
            try:
                result = work(job)
            except TutorError as error:
                GLib.idle_add(finished, None, str(error))
            except Exception:
                logging.exception("Unexpected local tutor error")
                GLib.idle_add(finished, None, "The local tutor could not finish this request.")
            else:
                GLib.idle_add(finished, result, None)

        Thread(target=worker, name="rust-tutor-local").start()

    def cancel_control(self, status, title="Cancel request"):
        def cancel_job():
            self.cancel_tutor()
            status.set_text("Canceling the model operation…")

        cancel = button(title, cancel_job, "flat")
        cancel.set_sensitive(False)
        return cancel

    def ask_model(self, make_task, receive, status, cancel):
        try:
            task = make_task()
            config = self.progress.data.get("tutor", {})
            if config.get("backend") == "managed":
                preset = next((item for item in TUTORS if item.key == config.get("model")), None)
                if not preset:
                    raise TutorError("Choose a built-in model in Model setup.")
                work = lambda job: generate_managed(preset, job, task)
            else:
                settings = self.tutor_settings()
                work = lambda job: generate(settings, job, task)
        except (TutorError, ValueError) as error:
            status.set_text(str(error))
            return
        if not self.tutor_job:
            self.narrator.stop()
        self.start_tutor_job(work, receive, status, "Waiting for the local model…", cancel)

    def show_guidance(self, target, result):
        guidance, next_step, chapter_id = result
        target.append(label(guidance, "learning-body"))
        target.append(label(next_step))
        chapter = self.chapters[chapter_id]
        target.append(button(f"Reference · {chapter.title}", lambda: self.open_reference(chapter_id), "flat"))

    def open_tutor(self, lesson=None, review=None):
        article = self.document("tutor", "Ask tutor")
        article.append(label("Ask the local Rust tutor", "title-1"))
        explanation = ("Your question and the current lesson draft go to the local model when you ask."
                       if review else "Ask about a Rust concept, an error, or a next step. Your question goes to the "
                                      "model on this computer when you ask.")
        article.append(label(explanation))
        if lesson:
            article.append(label(lesson.title, "heading"))
        question = Gtk.Entry(placeholder_text="Example: Why does this function return a value without return?",
                             max_length=640)
        article.append(question)
        status = label()
        cancel = self.cancel_control(status)
        answer = column()
        previous = None
        if not self.tutor_configured():
            status.set_text("Tutor not configured.")

        def task(text):
            if not text and review:
                text = "What should I check or improve next?"
            if not text:
                raise ValueError("Enter a Rust question.")
            if review and len(review[0]) > REVIEW_LIMIT:
                raise ValueError(f"Keep the lesson draft to {REVIEW_LIMIT:,} characters for tutor review.")
            attempts = self.progress.lesson(self.language, lesson.id).get("attempts", 0) if lesson else 0
            return guidance_task(self.chapters.values(), text, lesson=lesson, attempt=attempts,
                                 source=review[0] if review else None, evidence=review[1] if review else None,
                                 previous=previous)

        def ask():
            text = question.get_text().strip()

            def receive(response):
                nonlocal previous
                value, model_status = response
                previous = (text or "Review this Rust draft.", value[0])
                while (child := answer.get_first_child()) is not None:
                    answer.remove(child)
                self.show_guidance(answer, value)
                status.set_text(model_status)
                if question.get_text().strip() == text:
                    question.set_text("")
                    question.set_placeholder_text("Ask a follow-up")

            self.ask_model(lambda: task(text), receive, status, cancel)

        ask_button = button("Ask tutor", ask, "suggested-action")
        ask_button.set_sensitive(self.tutor_configured())
        article.append(ask_button)
        article.append(cancel)
        article.append(status)
        article.append(answer)
        if lesson:
            article.append(button("Return to lesson", lambda: self.open_lesson(lesson), "flat"))
        article.append(button("Model setup", self.open_models, "flat"))

    def speech_controls(self, text):
        container = column(5)
        row = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE, column_spacing=8, row_spacing=6)
        row.set_max_children_per_line(3)
        row.set_homogeneous(False)
        status = label(style="dim-label")
        def speak():
            if self.tutor_job:
                status.set_text("Let the current model operation finish before starting speech.")
                return
            self.narrator.start(text, self.progress.data.get("speech_voice"), status,
                                managed=self.progress.data.get("speech_backend") == "managed")

        row.append(button("Read aloud", speak))
        row.append(button("Pause / resume", self.narrator.pause_or_resume, "flat"))
        row.append(button("Stop", self.narrator.stop, "flat"))
        container.append(row)
        container.append(status)
        return container

    def open_lesson(self, lesson, show=True):
        self.progress.course(self.language)["current"] = lesson.id
        record = self.progress.lesson(self.language, lesson.id)
        article = self.document(lesson.id, lesson.title, show=show)
        article.append(label(lesson.title, "title-1"))
        article.append(label(lesson.question, "title-3"))
        article.append(label(lesson.explanation, "learning-body"))
        article.append(self.speech_controls(f"{lesson.title}. {lesson.question} {lesson.explanation} "
                                            f"{lesson.example_description} {lesson.exercise}"))
        steps = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE, column_spacing=8, row_spacing=8)
        steps.set_max_children_per_line(3)
        for step in lesson.flow:
            steps.append(label(step, "step"))
        article.append(steps)
        article.append(label("Example", "title-3"))
        example, _ = code_view(lesson.example)
        article.append(example)
        article.append(label(lesson.example_description, "dim-label"))
        article.append(button("Open related reference", lambda: self.open_reference(lesson.reference), "flat"))

        article.append(Gtk.Separator())
        article.append(label("Practice", "title-2"))
        article.append(label(lesson.exercise, "learning-body"))
        article.append(label("Run and Check use a limited Rust interpreter. They evaluate the exercise in the app "
                             "without invoking rustc or launching your code. The editor guide covers compiling full Rust projects.", "dim-label"))
        editor_frame, buffer = code_view(record.get("draft", lesson.starter), editable=True)
        editor_frame.get_child().get_child().set_tooltip_text("Edit your Rust exercise")
        buffer.connect("changed", self.schedule_draft_save, record)
        article.append(editor_frame)
        result_card = column(7)
        result_card.add_css_class("card")
        result_card.add_css_class("lesson-card")
        result_title = label("Exercise output", "heading")
        result_card.append(result_title)
        output = label("Run a sample to see what your program does.")
        output.add_css_class("monospace")
        output.set_selectable(True)
        result_card.append(output)

        tutor = Gtk.Revealer()
        tutor_body = column(8)
        tutor_body.add_css_class("card")
        tutor_body.add_css_class("lesson-card")
        tutor_body.append(label("Lesson help", "title-3"))
        tutor_body.append(label("Authored guidance based on the exercise and reference.", "dim-label"))
        feedback = label()
        tutor_body.append(feedback)
        checked_source = None
        solution_button = button("View worked solution…", lambda: self.confirm_solution(lesson, tutor_body))
        solution_button.set_visible(False)
        tutor_body.append(solution_button)

        def ask_about_draft():
            source = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), True)
            evidence = f"{result_title.get_text()}\n{output.get_text()}"[:700] if source == checked_source else None
            self.open_tutor(lesson, (source, evidence))

        tutor_body.append(button("Ask tutor about this draft", ask_about_draft, "flat"))
        tutor.set_child(tutor_body)

        actions = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE, column_spacing=8, row_spacing=8)
        actions.set_max_children_per_line(4)

        def perform(action):
            nonlocal checked_source
            source = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), True)
            passed = self.run_exercise(lesson, source, record, action, result_title, output)
            checked_source = source
            if action in {"hint", "review"}:
                attempts = record.get("attempts", 0)
                index = min(max(attempts - 1, 0), len(lesson.hints) - 1)
                if passed:
                    message = ("Your implementation met the exercise checks. For a follow-up, pick an input "
                               "and explain how each statement or branch leads to its result.")
                else:
                    message = f"Hint {index + 1} of {len(lesson.hints)}\n{lesson.hints[index]}"
                feedback.set_text(message)
                solution_button.set_visible(not passed and attempts >= len(lesson.hints))
                tutor.set_reveal_child(True)
            else:
                tutor.set_reveal_child(False)

        actions.append(button("Run sample", lambda: perform("run")))
        actions.append(button("Check exercise", lambda: perform("check"), "suggested-action"))
        actions.append(button("Get a hint", lambda: perform("hint"), "flat"))
        actions.append(button("Review my code", lambda: perform("review"), "flat"))
        article.append(actions)
        article.append(result_card)
        article.append(tutor)
        article.append(button("Ask the local tutor", lambda: self.open_tutor(lesson), "flat"))
        ids = list(self.lessons)
        index = ids.index(lesson.id)
        if index < len(ids) - 1:
            article.append(button("Next lesson", lambda: self.open_lesson(self.lessons[ids[index + 1]]), "flat"))
        else:
            article.append(button("Open milestone quiz", self.open_quiz, "flat"))

    def run_exercise(self, lesson, source, record, action, title, output):
        sample = action == "run"
        try:
            results = check(lesson, source, sample=sample)
            passed = all(expected.expected == actual for expected, actual in results)
            rows = []
            for case, actual in results:
                arguments = " ".join(case.arguments) or "Program output"
                if sample:
                    rows.append(f"{arguments}\n{actual or '(no output)'}")
                elif actual == case.expected:
                    rows.append(f"Pass · {arguments}\n{actual or '(no output)'}")
                else:
                    rows.append(f"Try again · {arguments}\nExpected: {case.expected}\nGot: {actual or '(no output)'}")
            output.set_text("\n\n".join(rows))
            title.set_text("Sample output" if sample else "All checks passed" if passed else "Check the expected behavior")
        except ExerciseError as error:
            title.set_text("Practice editor diagnostic")
            output.set_text(str(error))
            passed = False
        if sample:
            return passed
        if action in {"check", "review"}:
            record["latest_check"] = "passed" if passed else "needs practice"
        if passed:
            record["passed"] = True
            record["attempts"] = 0
            record.pop("last_failure", None)
        elif action != "hint":
            fingerprint = hashlib.sha256(source.encode("utf-8")).hexdigest()
            if record.get("last_failure") != fingerprint:
                record["attempts"] = record.get("attempts", 0) + 1
                record["last_failure"] = fingerprint
        if action == "review":
            record["review"] = "passed" if passed else "needs practice"
        self.update_progress()
        self.save()
        return passed

    def confirm_solution(self, lesson, target):
        if getattr(target, "solution_shown", False):
            return
        dialog = Adw.AlertDialog.new("Show a worked solution?",
                                     "You can continue with the current hint or read one complete implementation and its explanation.")
        dialog.add_response("cancel", "Keep trying")
        dialog.add_response("show", "Show solution")

        def respond(_dialog, response):
            if response == "show":
                target.solution_shown = True
                solution, _ = code_view(lesson.solution)
                target.append(solution)
                target.append(label(lesson.solution_explanation))

        dialog.connect("response", respond)
        dialog.present(self)

    def open_reference(self, chapter_id=None, return_action=None):
        article = self.document("reference", "Rust reference")
        article.append(label("Rust reference", "title-1"))
        article.append(label("Browse the concepts from the course or keep a printable copy."))
        search = Gtk.SearchEntry(placeholder_text="Search reference topics")
        article.append(search)
        article.append(button("Save printable copy…", self.export_reference, "flat"))
        if return_action is not None:
            article.append(button("Return to project lesson", return_action, "flat"))
        elif chapter_id in self.chapters:
            origin = self.progress.course(self.language).get("current")
            if origin in self.lessons:
                article.append(button("Return to lesson", lambda: self.open_lesson(self.lessons[origin]), "flat"))
        topics = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE)
        topics.add_css_class("boxed-list")
        article.append(topics)
        content = column(13)
        article.append(content)
        rows = {}
        for chapter in self.chapters.values():
            row = Adw.ActionRow(title=chapter.title, subtitle=chapter.summary, activatable=True)
            row.chapter = chapter
            row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
            rows[chapter.id] = row
            topics.append(row)
        def render(chapter):
            self.narrator.stop()
            while (child := content.get_first_child()) is not None:
                content.remove(child)
            content.append(label(chapter.title, "title-2"))
            content.append(label(chapter.summary, "dim-label"))
            for title, text in chapter.sections:
                content.append(label(title, "heading"))
                content.append(label(text, "learning-body"))
            content.append(self.speech_controls(" ".join(
                [chapter.title] + [f"{title}. {text}" for title, text in chapter.sections])))
            content.append(label("Example", "heading"))
            example, _ = code_view(chapter.example)
            content.append(example)
            for title, url in chapter.sources:
                source = Gtk.LinkButton(uri=url, label=title, halign=Gtk.Align.START)
                content.append(source)

        def filter_row(row):
            query = search.get_text().strip().casefold()
            chapter = row.chapter
            text = f"{chapter.title} {chapter.summary} {chapter.sections}"
            return all(word in text.casefold() for word in query.split())

        topics.set_filter_func(filter_row)
        search.connect("search-changed", lambda _entry: topics.invalidate_filter())
        topics.connect("row-activated", lambda _list, row: render(row.chapter))
        first = rows.get(chapter_id) or next(iter(rows.values()))
        topics.select_row(first)
        render(first.chapter)

    def export_reference(self):
        dialog = Gtk.FileDialog(title="Save printable Rust reference", initial_name="rust-reference.html")

        def save_file(chooser, result):
            try:
                file = chooser.save_finish(result)
                if not file or not file.get_path():
                    return
                Path(file.get_path()).write_text(printable_reference(self.chapters.values()), encoding="utf-8")
                self.toasts.add_toast(Adw.Toast(title="Reference saved. Open it in your browser to print or save as PDF."))
            except GLib.Error as error:
                if not error.matches(Gtk.DialogError.quark(), Gtk.DialogError.DISMISSED):
                    self.toasts.add_toast(Adw.Toast(title=error.message))
            except OSError as error:
                self.toasts.add_toast(Adw.Toast(title=str(error)))

        dialog.save(self, None, save_file)

    def open_quiz(self):
        article = self.document("quiz", "Milestone quiz")
        article.append(label("Rust foundations quiz", "title-1"))
        article.append(label("Use these three questions to decide what to revisit after the calculator. "
                             "Your project checks are the main sign of progress."))
        controls = []
        course = self.progress.course(self.language)
        previous = course.get("quiz", {})
        for lesson_id, question, choices, correct, explanation in self.course["quiz"]:
            group = column(8)
            group.add_css_class("card")
            group.add_css_class("lesson-card")
            group.append(label(question, "heading"))
            radios = []
            for index, choice in enumerate(choices):
                radio = Gtk.CheckButton(label=choice)
                if radios:
                    radio.set_group(radios[0])
                radios.append(radio)
                radio.set_active(previous.get(lesson_id) == index)
                group.append(radio)
            feedback = label()
            group.append(feedback)
            controls.append((lesson_id, correct, explanation, radios, feedback))
            article.append(group)

        recommendation = label()
        plan = column(5)

        def recap():
            while (child := plan.get_first_child()) is not None:
                plan.remove(child)
            review = self.practice_recommendations()
            recommendation.set_text("Suggested practice" if review else "")
            for lesson in review:
                plan.append(button(lesson.title, lambda item=lesson: self.open_lesson(item), "flat"))

        def grade():
            answers = {}
            for lesson_id, correct, explanation, radios, feedback in controls:
                choice = next((i for i, radio in enumerate(radios) if radio.get_active()), None)
                if choice is None:
                    feedback.set_text("Choose an answer when you are ready.")
                    continue
                answers[lesson_id] = choice
                feedback.set_text(("Correct. " if choice == correct else "Revisit this concept. ") + explanation)
            course["quiz"] = answers
            self.save()
            recap()

        article.append(button("Review answers", grade, "suggested-action"))
        article.append(recommendation)
        article.append(plan)
        recap()

    def practice_recommendations(self):
        quiz = self.progress.course(self.language).get("quiz", {})
        answer_key = {item[0]: item[3] for item in self.course["quiz"]}
        recommendations = []
        for lesson in self.lessons.values():
            record = self.progress.lesson(self.language, lesson.id)
            missed = lesson.id in quiz and quiz[lesson.id] != answer_key[lesson.id]
            needs_review = record.get("latest_check") == "needs practice" and (
                record.get("review") == "needs practice" or record.get("attempts", 0) >= 2
            )
            if missed or needs_review:
                recommendations.append(lesson)
        return recommendations

    def open_path(self):
        article = self.document("next", "Path and editor setup")
        article.append(label("From practice to projects", "title-1"))
        article.append(label("Finish the calculator, then use a local editor to create and run a real Cargo project. "
                             "The setup guide walks through installing the tools and reading your first diagnostics."))
        article.append(button("Read the Ubuntu and editor setup guide", lambda: self.open_reference("cargo"), "suggested-action"))
        article.append(button("Review a file from your editor", self.open_editor_review))
        projects = self.project_progress()
        active = projects["saved"].get(projects.get("active"))
        if active:
            article.append(label("Your next lessons", "title-3"))
            article.append(label(active["idea"]))
            self.add_project_lessons(article, projects["active"], active)
        else:
            article.append(label("Standard course direction", "title-3"))
            article.append(label("The next course projects will use a command-line tool to teach file input and error handling, "
                                 "a desktop project to teach events and state, and a local backend to teach requests and responses."))
        article.append(button("Plan my project", self.open_project_paths))
        recommendations = self.practice_recommendations()
        if recommendations:
            article.append(label("Suggested practice", "title-3"))
            for lesson in recommendations:
                article.append(button(lesson.title, lambda item=lesson: self.open_lesson(item), "flat"))

    def project_progress(self):
        course = self.progress.course(self.language)
        return course.setdefault("project_paths", {"active": None, "saved": {}})

    def add_project_lessons(self, container, plan_id, plan):
        for index, page in enumerate(plan["pages"]):
            complete = " · Complete" if page["id"] in plan["completed"] else ""
            container.append(button(page["title"] + complete,
                                    lambda item=index: self.open_project_lesson(plan_id, item), "flat"))

    def open_project_paths(self):
        article = self.document("projects", "Project paths")
        article.append(label("Plan a project you want to build", "title-1"))
        article.append(label("Start with the calculator lessons, then use your idea to practice in VS Code or VSCodium. "
                             "Preview a three-lesson template, or ask the local tutor to adapt it to your idea."))
        projects = self.project_progress()
        idea = Gtk.Entry(placeholder_text="Example: A weekly grocery planner", max_length=180)
        focus = Gtk.DropDown(model=Gtk.StringList.new(["Choose a first task", *FOCUSES.values()]))
        idea.set_tooltip_text("Describe the useful app you want to build")
        focus.set_tooltip_text("Choose what the smallest useful version should do first")
        article.append(label("What would you like to build?", "heading"))
        article.append(idea)
        article.append(label("What should the first version do?", "heading"))
        article.append(focus)
        status = label()
        cancel = self.cancel_control(status)
        proposal = column(12)

        def clear_proposal(*_args):
            while (child := proposal.get_first_child()) is not None:
                proposal.remove(child)
            status.set_text("")

        def render_plan(plan, note):
            clear_proposal()
            status.set_text(note)
            proposal.append(label(plan["idea"], "title-2"))
            origin = "Adapted by the local tutor" if plan.get("origin") == "local tutor" else "Authored template"
            proposal.append(label(origin, "dim-label"))
            for page in plan["pages"]:
                section = column(6)
                section.add_css_class("card")
                section.add_css_class("lesson-card")
                section.append(label(page["title"], "heading"))
                section.append(label(page["goal"]))
                section.append(label("Concepts · " + ", ".join(page["concepts"]), "dim-label"))
                for step in page["steps"]:
                    section.append(label(step))
                section.append(label("Milestone · " + page["milestone"], "dim-label"))
                proposal.append(section)

            def apply_path():
                key = uuid4().hex
                projects["saved"][key] = plan
                self.select_project_path(key)

            proposal.append(button("Use this path", apply_path, "suggested-action"))

        def focus_key():
            return (None, *FOCUSES)[focus.get_selected()]

        def preview():
            self.cancel_tutor()
            clear_proposal()
            try:
                plan = propose_path(idea.get_text(), focus_key())
            except ValueError as error:
                status.set_text(str(error))
                return
            render_plan(plan, "Preview your upcoming lessons before applying the path.")

        def adapt():
            clear_proposal()

            def receive(response):
                plan, model_status = response
                render_plan(plan, f"Review the local tutor’s proposal before applying it. {model_status}")

            self.ask_model(lambda: project_task(idea.get_text(), focus_key(), self.chapters.values()),
                           receive, status, cancel)

        def edit(*_args):
            self.cancel_tutor()
            clear_proposal()

        idea.connect("changed", edit)
        focus.connect("notify::selected", edit)
        article.append(button("Preview authored template", preview))
        build_ai = button("Build a project path with the tutor", adapt, "suggested-action")
        build_ai.set_sensitive(self.tutor_configured())
        article.append(build_ai)
        article.append(label("The model receives the idea, first-task choice, and course reference material on this computer.",
                             "dim-label"))
        if not self.tutor_configured():
            article.append(button("Configure the local tutor", self.open_models, "flat"))
        article.append(cancel)
        article.append(status)
        article.append(proposal)
        if projects["saved"]:
            article.append(Gtk.Separator())
            article.append(label("Saved project paths", "title-3"))
            if projects.get("active"):
                article.append(button("Return to standard path", lambda: self.select_project_path(None), "flat"))
            for key, plan in reversed(list(projects["saved"].items())):
                article.append(label(plan["idea"], "heading"))
                if key == projects.get("active"):
                    article.append(label("Active project path", "dim-label"))
                    self.add_project_lessons(article, key, plan)
                else:
                    article.append(button("Use this saved path", lambda item=key: self.select_project_path(item)))

    def select_project_path(self, key):
        self.project_progress()["active"] = key
        self.save()
        self.open_path()

    def open_project_lesson(self, plan_id, index):
        plan = self.project_progress()["saved"][plan_id]
        page = plan["pages"][index]
        article = self.document("projects", page["title"])
        article.append(label(plan["idea"], "dim-label"))
        article.append(label(page["title"], "title-1"))
        article.append(label(page["goal"], "title-3"))
        article.append(label(page["explanation"], "learning-body"))
        article.append(self.speech_controls(f"{page['title']}. {page['explanation']} " + " ".join(page["steps"])))
        article.append(label("Example", "title-3"))
        example, _ = code_view(page["example"])
        article.append(example)
        article.append(button("Open related reference", lambda: self.open_reference(
            page["reference"], lambda: self.open_project_lesson(plan_id, index)), "flat"))
        article.append(label("Try this in your editor", "title-3"))
        for step in page["steps"]:
            article.append(label(step, "learning-body"))
        article.append(label("Project milestone", "title-3"))
        article.append(label(page["milestone"]))
        complete = Gtk.CheckButton(label="Mark this page complete", active=page["id"] in plan["completed"])

        def update_progress(control):
            if control.get_active():
                plan["completed"].append(page["id"])
            else:
                plan["completed"].remove(page["id"])
            self.save()

        complete.connect("toggled", update_progress)
        article.append(complete)
        if index + 1 < len(plan["pages"]):
            article.append(button("Next project lesson", lambda: self.open_project_lesson(plan_id, index + 1),
                                  "suggested-action"))
        article.append(button("Return to project paths", self.open_project_paths, "flat"))

    def open_editor_review(self):
        article = self.document("handoff", "Review from editor")
        article.append(label("Review code from your editor", "title-1"))
        article.append(label("Save your file in VS Code or VSCodium, then choose it here. "
                             "Rust Tutor reads the selected .rs file for this session. It leaves the project "
                             "and lesson drafts alone and keeps the file on this computer."))
        article.append(label("If the file follows a lesson's exercise signature, select that lesson and run "
                             "its checks. For a full Cargo project, run cargo check and cargo test in your editor."))

        preview, buffer = code_view("", editable=False)
        preview.get_child().set_min_content_height(175)
        preview.get_child().set_max_content_height(285)
        preview.get_child().set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        file_status = label("No Rust file selected.", "dim-label")
        output_title = label()
        output = label()
        output.set_selectable(True)
        source = None
        behavior = Gtk.Entry(placeholder_text="Optional: What should this code do?", max_length=400)
        review_status = label()
        answer = column()
        cancel = self.cancel_control(review_status)
        entries = tuple(self.lessons.values())
        exercise_choice = Gtk.DropDown(model=Gtk.StringList.new(["Select a lesson"] + [entry.title for entry in entries]))
        exercise_choice.set_tooltip_text("Choose which exercise requirements the selected file should meet")

        def choose_file():
            dialog = Gtk.FileDialog(title="Choose a saved Rust source file")
            rust_filter = Gtk.FileFilter(name="Rust source files")
            rust_filter.add_pattern("*.rs")
            filters = Gio.ListStore.new(Gtk.FileFilter)
            filters.append(rust_filter)
            dialog.set_filters(filters)

            def opened(chooser, result):
                nonlocal source
                try:
                    selected = chooser.open_finish(result)
                except GLib.Error as error:
                    if not error.matches(Gtk.DialogError.quark(), Gtk.DialogError.DISMISSED):
                        file_status.set_text(error.message)
                    return
                clear_review()
                output_title.set_text("")
                output.set_text("")
                try:
                    if not selected or not selected.get_path():
                        raise ValueError("Choose a local Rust source file.")
                    path = Path(selected.get_path())
                    if path.suffix != ".rs" or not path.is_file():
                        raise ValueError("Choose a regular .rs source file.")
                    with path.open("rb") as stream:
                        contents = stream.read(48 * 1024 + 1)
                    if len(contents) > 48 * 1024:
                        raise ValueError("Choose a source file under 48 KiB.")
                    candidate = contents.decode("utf-8")
                    if "\x00" in candidate:
                        raise ValueError("Choose a text source file.")
                except (OSError, ValueError) as error:
                    source = None
                    buffer.set_text("")
                    check_button.set_sensitive(False)
                    file_status.set_text(f"Could not open the file. {error}")
                    return
                source = candidate
                buffer.set_text(source)
                file_status.set_text(f"Selected {path.name} · {len(contents):,} bytes · read-only")
                output_title.set_text("")
                output.set_text("")
                check_button.set_sensitive(exercise_choice.get_selected() != 0)

            dialog.open(self, None, opened)

        def check_file():
            index = exercise_choice.get_selected()
            if source is None or index == 0:
                return
            lesson = entries[index - 1]
            record = self.progress.lesson(self.language, lesson.id)
            self.run_exercise(lesson, source, record, "review", output_title, output)

        check_button = button("Run selected lesson's checks", check_file, "suggested-action")
        check_button.set_sensitive(False)

        def clear_review(*_args):
            self.cancel_tutor()
            while (child := answer.get_first_child()) is not None:
                answer.remove(child)
            review_status.set_text("")

        def select_lesson(chooser, _property):
            clear_review()
            output_title.set_text("")
            output.set_text("")
            check_button.set_sensitive(source is not None and chooser.get_selected() != 0)

        exercise_choice.connect("notify::selected", select_lesson)
        behavior.connect("changed", clear_review)

        def review():
            def task():
                if not source:
                    raise ValueError("Choose a saved Rust source file first.")
                if len(source) > REVIEW_LIMIT:
                    raise ValueError(f"Choose a Rust file of at most {REVIEW_LIMIT:,} characters for tutor review.")
                index = exercise_choice.get_selected()
                lesson = entries[index - 1] if index else None
                evidence = f"{output_title.get_text()}\n{output.get_text()}"[:700] if output_title.get_text() else None
                return guidance_task(self.chapters.values(), behavior.get_text().strip(), lesson=lesson,
                                     source=source, evidence=evidence)

            def receive(response):
                value, model_status = response
                while (child := answer.get_first_child()) is not None:
                    answer.remove(child)
                self.show_guidance(answer, value)
                review_status.set_text(model_status)

            self.ask_model(task, receive, review_status, cancel)

        article.append(button("Choose a saved Rust file…", choose_file))
        article.append(file_status)
        article.append(preview)
        article.append(exercise_choice)
        article.append(check_button)
        article.append(output_title)
        article.append(output)
        article.append(Gtk.Separator())
        article.append(label("Review with the local tutor", "title-3"))
        article.append(label("Review gives the local model the selected file, your expected behavior, and any shown lesson checks. "
                             "The tutor reads one file. You run project tests in your editor."))
        article.append(behavior)
        review_ai = button("Review project with the tutor", review)
        review_ai.set_sensitive(self.tutor_configured())
        article.append(review_ai)
        if not self.tutor_configured():
            article.append(button("Configure the local tutor", self.open_models, "flat"))
        article.append(cancel)
        article.append(review_status)
        article.append(answer)
        article.append(button("Read about testing a Cargo project", lambda: self.open_reference("cargo"), "flat"))

    def open_models(self):
        article = self.document("models", "Local model setup")
        article.append(label("Local model setup", "title-1"))
        article.append(label("Analyze this computer to see available CPU, memory, disk, and graphics information. "
                             "The information stays here. Other applications can affect how well a model fits."))
        facts = label()
        tutor_recommendation = label()
        speech_recommendation = label()

        def analyze():
            try:
                summary, tutor, speech = assessment(Path.home())
                facts.set_text(summary)
                tutor_recommendation.set_text(tutor)
                speech_recommendation.set_text(speech)
            except OSError:
                facts.set_text("Some hardware information was unavailable.")

        article.append(button("Analyze this computer", analyze, "suggested-action"))
        article.append(facts)
        article.append(Gtk.Separator())
        article.append(label("Tutor reasoning and code review", "title-3"))
        article.append(tutor_recommendation)
        self.managed_model_setup(article, "tutor", TUTORS, LLAMA_RELEASE)
        tutor = self.progress.data.get("tutor", {})
        external = Gtk.Expander(label="Use a separate LM Studio server",
                                expanded=bool(tutor and tutor.get("backend") != "managed"))
        external_controls = column(10)
        external_controls.set_margin_top(10)
        self.tutor_setup(external_controls)
        external.set_child(external_controls)
        article.append(external)
        article.append(Gtk.Separator())
        article.append(label("Speech and read-aloud", "title-3"))
        article.append(speech_recommendation)
        self.managed_model_setup(article, "speech", (SPEECH,), PIPER_RELEASE)
        voice_options = Gtk.Expander(label="Use an existing Piper voice")
        voice_controls = column(10)
        voice_controls.set_margin_top(10)
        voice_controls.append(label("Choose a local voice and its adjacent configuration for a Piper CLI you already installed."))
        speech_status = label()
        voice_controls.append(speech_status)

        def update_speech():
            selected = self.progress.data.get("speech_voice")
            voice = "no voice selected"
            if selected:
                try:
                    model = valid_voice(selected)
                    voice = f"{model.name} ({model.stat().st_size / 1024 ** 2:.1f} MiB on disk)"
                except (OSError, ValueError):
                    voice = "selected voice is unavailable"
            status = "Piper found" if piper_command() else "Piper is unavailable"
            speech_status.set_text(f"{status} · {voice}")

        def choose():
            dialog = Gtk.FileDialog(title="Choose a Piper .onnx voice")

            def finish(chooser, result):
                try:
                    chosen = chooser.open_finish(result)
                    if chosen and chosen.get_path():
                        voice = valid_voice(chosen.get_path())
                        self.progress.data["speech_voice"] = str(voice)
                        self.progress.data["speech_backend"] = "external"
                        self.save()
                        self.open_models()
                except GLib.Error as error:
                    if not error.matches(Gtk.DialogError.quark(), Gtk.DialogError.DISMISSED):
                        speech_status.set_text(error.message)
                except (OSError, ValueError) as error:
                    speech_status.set_text(str(error))

            dialog.open(self, None, finish)

        def remove_voice():
            self.narrator.stop()
            self.progress.data.pop("speech_voice", None)
            if self.progress.data.get("speech_backend") == "external":
                self.progress.data.pop("speech_backend", None)
            self.save()
            update_speech()

        voice_controls.append(button("Choose a local voice…", choose))
        voice_controls.append(button("Clear voice selection", remove_voice, "flat"))
        voice_controls.append(Gtk.LinkButton(uri="https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/CLI.md",
                                             label="Piper installation and voices", halign=Gtk.Align.START))
        voice_options.set_child(voice_controls)
        article.append(voice_options)
        article.append(self.speech_controls("Rust uses types to describe the values a program can work with."))
        update_speech()

    def managed_model_setup(self, article, role, presets, runtime_source):
        status = label()
        cancel = self.cancel_control(status, "Cancel download")
        bar = Gtk.ProgressBar(show_text=True, visible=False)
        selection = Gtk.DropDown(model=Gtk.StringList.new([preset.title for preset in presets]))
        detail = label()
        source = Gtk.LinkButton(label="Model source and license", halign=Gtk.Align.START)
        active = self.progress.data.get("tutor", {})
        active_key = active.get("model") if active.get("backend") == "managed" else None
        fitting = [preset for preset in presets if not need_resources(preset, remaining(preset))]
        recommended = fitting[-1] if fitting else None
        selected = (next((preset for preset in presets if preset.key == active_key), None)
                    or recommended or presets[0])
        selection.set_selected(presets.index(selected))
        is_tutor = role == "tutor"
        if recommended:
            article.append(label(f"Recommended on this computer · {recommended.title}", "dim-label"))
        article.append(selection)
        article.append(detail)
        article.append(source)
        article.append(Gtk.LinkButton(uri=runtime_source, label="Runtime release and source", halign=Gtk.Align.START))

        def current():
            return presets[selection.get_selected()]

        def update(*_args):
            preset = current()
            assets = remaining(preset)
            source.set_uri(preset.source)
            reason = need_resources(preset, assets)
            size = sum(asset.size for asset in assets)
            state = f"{size / 1_000_000:,.1f} MB to download" if assets else "Installed"
            active_now = ((self.progress.data.get("tutor", {}).get("backend") == "managed"
                           and self.progress.data["tutor"].get("model") == preset.key) if is_tutor
                          else self.progress.data.get("speech_backend") == "managed")
            if active_now and not assets:
                state = "Installed and selected"
            detail.set_text(
                f"{state} · {preset.ram_gib:.1f} GiB available RAM recommended\n"
                f"{preset.tradeoff}\n{preset.license}" + (f"\n{reason}" if reason else "")
            )
            download_button.set_sensitive(bool(assets) and not reason)
            use_button.set_sensitive(not assets and not active_now)

        def use():
            preset = current()
            if not ready(preset):
                return
            if is_tutor:
                self.tutor_token = ""
                self.progress.data["tutor"] = {"backend": "managed", "model": preset.key}
            else:
                self.narrator.stop()
                self.progress.data["speech_backend"] = "managed"
            self.save()
            self.open_models()

        def disable():
            self.cancel_tutor()
            self.narrator.stop()
            if is_tutor:
                self.tutor_token = ""
                self.progress.data.pop("tutor", None)
            else:
                self.progress.data.pop("speech_backend", None)
                self.progress.data.pop("speech_voice", None)
            self.save()
            self.open_models()

        def confirm():
            preset = current()
            assets = remaining(preset)
            if not assets:
                update()
                return
            size = sum(asset.size for asset in assets)
            breakdown = "\n".join(f"{asset.name} · {asset.size / 1_000_000:,.1f} MB" for asset in assets)
            dialog = Adw.AlertDialog.new(f"Download {size / 1_000_000:,.1f} MB?",
                                         f"{breakdown}\n\n{preset.license}\n"
                                         f"Files are verified and saved in {model_directory()}.")
            dialog.add_response("cancel", "Cancel")
            dialog.add_response("download", "Download")
            dialog.set_default_response("cancel")
            dialog.set_close_response("cancel")
            revision = self.page_revision

            def report(received, total, name):
                def apply_progress():
                    if self.page_revision == revision:
                        bar.set_fraction(received / total)
                        bar.set_text(f"{name} · {received / 1_000_000:,.1f} of {total / 1_000_000:,.1f} MB")
                    return GLib.SOURCE_REMOVE
                GLib.idle_add(apply_progress)

            def finished(installed_preset):
                status.set_text(f"{installed_preset.title} is installed. Select it when you are ready to use it.")

            def respond(_dialog, response):
                if response != "download" or self.page_revision != revision:
                    return
                if self.tutor_job:
                    status.set_text("Another model operation is still finishing.")
                    return
                self.narrator.stop()
                bar.set_visible(True)
                bar.set_fraction(0.0)
                bar.set_text("Preparing download…")
                def settled():
                    bar.set_visible(False)
                    update()

                self.start_tutor_job(lambda job: install(preset, assets, job, report),
                                     finished, status, "Downloading model files…", cancel, settled)

            dialog.connect("response", respond)
            dialog.present(self)

        download_button = button("Review download…", confirm, "suggested-action")
        use_button = button("Use installed model", use)
        article.append(download_button)
        article.append(use_button)
        has_selection = bool(active) if is_tutor else bool(self.progress.data.get("speech_backend")
                                                          or self.progress.data.get("speech_voice"))
        if has_selection:
            article.append(button("Turn tutor off" if is_tutor else "Turn speech off", disable, "flat"))
        article.append(cancel)
        article.append(bar)
        article.append(status)
        selection.connect("notify::selected", update)
        update()

    def tutor_setup(self, article):
        config = self.progress.data.get("tutor", {})
        if config.get("backend") == "managed":
            config = {}
        article.append(label("Start LM Studio’s local server with local-network sharing off. "
                             "Rust Tutor connects to 127.0.0.1. Choose a GGUF model you already downloaded in LM Studio. "
                             "Exercise checks and authored hints remain available while the tutor is off."))
        cli_status = "LM Studio CLI found" if cli_available() else "LM Studio CLI not detected"
        article.append(label(cli_status, "dim-label"))
        port = Gtk.Entry(text=str(config.get("port", DEFAULT_PORT)), max_length=5,
                         input_purpose=Gtk.InputPurpose.DIGITS)
        token = Gtk.PasswordEntry(text=self.tutor_token, show_peek_icon=True, hexpand=True)
        selection = Gtk.DropDown()
        context = Gtk.DropDown(model=Gtk.StringList.new(["4,096 tokens", "8,192 tokens"]))
        context.set_selected(1 if config.get("context") == CONTEXTS[1] else 0)
        status = label()
        recommendation = label(style="dim-label")
        configured = label(style="heading")
        models = []

        def reflect_saved():
            saved = self.progress.data.get("tutor")
            enabled = saved and saved.get("backend") != "managed"
            configured.set_text(f"Configured model · {saved['model']}" if enabled else "Separate server disabled")

        def endpoint():
            try:
                value = int(port.get_text().strip())
            except ValueError:
                raise TutorError("Enter a numeric local server port.") from None
            return Settings(value, "", CONTEXTS[context.get_selected()], token.get_text().strip())

        def reset_models(*_args):
            self.cancel_tutor()
            models.clear()
            selection.set_model(Gtk.StringList.new(["Check the connection to list models"]))
            save_model.set_sensitive(False)
            recommendation.set_text("")
            status.set_text("")

        def refresh():
            try:
                settings = endpoint()
            except TutorError as error:
                status.set_text(str(error))
                return

            def receive(installed):
                models[:] = installed
                save_model.set_sensitive(bool(installed))
                selection.set_model(Gtk.StringList.new([model.description for model in installed]
                                                       or ["No supported models found"]))
                if not installed:
                    status.set_text("Server available. Download a GGUF instruction model yourself in LM Studio, then recheck.")
                    recommendation.set_text("")
                    return
                _, available = memory()
                suggested = next((model for model in installed
                                  if available is not None and model.size / 1024 ** 3 < max(available - 2, 0)), None)
                current = self.progress.data.get("tutor", {})
                saved = current.get("model") if current.get("port") == settings.port else None
                preferred = next((model for model in installed if model.key == saved), None) or suggested or installed[0]
                selection.set_selected(installed.index(preferred))
                status.set_text("Server available. Choose which model to use for the tutor.")
                if suggested:
                    recommendation.set_text(f"Low-memory starting point · {suggested.name} with 4,096 tokens. "
                                            "Model file size gives a rough estimate. Actual RAM and GPU use can be higher.")
                else:
                    recommendation.set_text("Available RAM does not clearly fit even the smallest listed model. "
                                            "Try an especially small model or use authored hints and checks.")

            self.start_tutor_job(lambda job: list_models(settings, job), receive, status,
                                 "Checking the local server…")

        def configure():
            index = selection.get_selected()
            if index >= len(models):
                return
            try:
                settings = endpoint()
            except TutorError as error:
                status.set_text(str(error))
                return
            self.tutor_token = settings.token
            self.progress.data["tutor"] = {"backend": "lmstudio", "port": settings.port, "model": models[index].key,
                                           "context": settings.context}
            self.save()
            self.open_models()

        def disable():
            self.cancel_tutor()
            if self.progress.data.get("tutor", {}).get("backend") != "managed":
                self.progress.data.pop("tutor", None)
            self.tutor_token = ""
            token.set_text("")
            reset_models()
            self.save()
            reflect_saved()
            status.set_text("The tutor is off. Manage any independently loaded models in LM Studio.")

        save_model = button("Use selected model", configure)
        reset_models()
        reflect_saved()
        port.connect("changed", reset_models)
        token.connect("changed", reset_models)
        article.append(configured)
        article.append(label("Port on 127.0.0.1"))
        article.append(port)
        article.append(label("API token if required (current app session only)"))
        article.append(token)
        article.append(button("Check connection and models", refresh, "suggested-action"))
        article.append(selection)
        article.append(recommendation)
        article.append(label("Context for a model loaded by Rust Tutor"))
        article.append(context)
        article.append(save_model)
        article.append(button("Turn local tutor off", disable, "flat"))
        article.append(status)
        article.append(label("A request loads the chosen model only when needed and asks LM Studio to unload it afterward. "
                             "A model already loaded in LM Studio stays under your control. You can stop the server there.",
                             "dim-label"))
        article.append(Gtk.LinkButton(uri="https://lmstudio.ai/docs/developer/rest/quickstart",
                                      label="LM Studio’s local server setup", halign=Gtk.Align.START))
