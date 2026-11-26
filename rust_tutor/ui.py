"""Native GTK and libadwaita interface for Rust Tutor."""

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
from .learning import (
    concept_evidence, milestone_ready, pacing_options, questions, quiz_results, quiz_score,
    skill_progress, upcoming_project_topics,
)
from .local_tutor import CONTEXTS, DEFAULT_PORT, LOOPBACK, REVIEW_LIMIT, Request, Settings, TutorError, generate, list_models
from .managed_runtime import generate_managed
from .model_catalog import LLAMA_RELEASE, PIPER_RELEASE, SPEECH, TUTORS
from .model_manager import install, model_directory, need_resources, ready, remaining
from .project_path import FOCUSES, propose_path, propose_roadmap_path, remedial_pages
from .reference import print_sheet, printable_reference, printable_sheet
from .review import MAX_FILES, read_selection, review_payload
from .speech import Narrator
from .state import Progress
from .tutor_tasks import PAGE_FIELDS, guidance_task, pace_task, project_task, report_task


MANUAL_FIELDS = {"title": "Title", "explanation": "Concept", "example": "Worked example",
                 "exercise": "Try it yourself", "hint": "Hint"}
CORE_PATH = "Core app-building path"
ADVANCED_PATH = "Advanced Rust continuation"


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
        self.milestones = {stage.id: stage for stage in (*self.course["milestones"], *self.course["advanced_milestones"])}
        self.topics = {topic.id: topic for stage in self.milestones.values() for topic in stage.outline}
        self.progress = Progress()
        self.narrator = Narrator()
        self.tutor_job = None
        self.tutor_session = None
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
        self.nav_row("quiz", "Milestones and progress", self.open_milestones)
        self.navigation.append(Gtk.Separator(margin_top=12, margin_bottom=12))
        separator = self.navigation.get_row_at_index(len(self.sidebar_rows))
        separator.set_selectable(False)
        separator.set_activatable(False)
        self.nav_row("reference", "Rust reference", self.open_reference, "help-browser-symbolic")
        self.nav_row("next", "Course roadmap", self.open_path, "folder-documents-symbolic")
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
        status.set_tooltip_text("Exercise complete")
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
            passed = self.foundation_complete(lesson.id)
            self.sidebar_rows[lesson.id][1].set_visible(passed)
            complete += int(passed)
        self.summary.set_text(f"{complete} of {len(self.lessons)} foundations complete")

    def document(self, key, title, show=True):
        self.narrator.stop()
        self.page_revision += 1
        self.cancel_tutor()
        self.page.set_title(title)
        if key is not None:
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
        host, port = config.get("host", LOOPBACK), config.get("port")
        needs_token = host != LOOPBACK or config.get("requires_token")
        return bool(config.get("model") and (not needs_token or self.session_token(host, port)))

    def session_token(self, host, port):
        if self.tutor_session and self.tutor_session[:2] == (host, port):
            return self.tutor_session[2]
        return ""

    def tutor_destination(self):
        config = self.progress.data.get("tutor", {})
        if config.get("backend") == "managed":
            return "Rust Tutor on this computer"
        host = config.get("host", LOOPBACK)
        return "LM Studio on this computer" if host == LOOPBACK else f"LM Studio at {host}:{config['port']} over your LAN"

    def tutor_settings(self):
        config = self.progress.data.get("tutor", {})
        if not config.get("model"):
            raise TutorError("Tutor not configured. Check the LM Studio server and choose a model in Model setup.")
        host, port = config.get("host", LOOPBACK), config["port"]
        return Settings(port, config["model"], config["context"], self.session_token(host, port), host)

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
        destination = self.tutor_destination() if self.tutor_configured() else "the selected model once configured"
        shared = "Your question and the current lesson draft" if review else "Your question"
        explanation = f"Ask about a Rust concept, an error, or a next step. {shared} will be sent to {destination}."
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
            record = self.progress.lesson(self.language, lesson.id) if lesson else {}
            attempts = record.get("failed_checks", 0) if lesson and lesson.editor_checks else record.get("attempts", 0)
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
        walkthrough_text = "".join(f"{name}. {description} " for name, description in lesson.walkthrough)
        article.append(self.speech_controls(f"{lesson.title}. {lesson.question} {lesson.explanation} "
                                            f"{lesson.example_description} {walkthrough_text}{lesson.exercise}"))
        steps = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE, column_spacing=8, row_spacing=8)
        steps.set_max_children_per_line(3)
        for step in lesson.flow:
            steps.append(label(step, "step"))
        article.append(steps)
        article.append(label("Example", "title-3"))
        example, _ = code_view(lesson.example)
        article.append(example)
        article.append(label(lesson.example_description, "dim-label"))
        if lesson.walkthrough:
            article.append(label("Walk through the example", "title-3"))
            for name, description in lesson.walkthrough:
                article.append(label(name, "heading"))
                article.append(label(description, "learning-body"))
        article.append(button("Open related reference", lambda: self.open_reference(lesson.reference), "flat"))
        if lesson.id == "cargo-setup":
            article.append(button("Crate documentation and Rust tools", lambda: self.open_reference("resources"), "flat"))

        article.append(Gtk.Separator())
        article.append(label("Practice", "title-2"))
        article.append(label(lesson.exercise, "learning-body"))
        if lesson.editor_checks:
            self.editor_practice(article, lesson, record)
        else:
            self.in_app_practice(article, lesson, record)
        article.append(button("Ask the local tutor", lambda: self.open_tutor(lesson), "flat"))
        stage = next(stage for stage in self.milestones.values() if lesson.id in stage.skill_ids)
        self.insert_practice(article, stage, lesson.id, lambda: self.open_lesson(lesson))
        article.append(button("Chapter cheat sheet", lambda: self.open_cheat_sheet(
            stage.title, stage.cheat_sheet, lambda: self.open_lesson(lesson)), "flat"))
        if lesson.id == stage.skill_ids[-1]:
            article.append(button("Open milestone and progress", lambda: self.open_milestone(stage), "suggested-action"))
        ids = list(self.lessons)
        index = ids.index(lesson.id)
        if index < len(ids) - 1:
            article.append(button("Next lesson", lambda: self.open_lesson(self.lessons[ids[index + 1]]), "flat"))
        else:
            article.append(button("Open the course roadmap", self.open_path, "flat"))

    def editor_practice(self, article, lesson, record):
        article.append(label("Run your code in the Cargo project you open in VS Code or VSCodium. "
                             "Record the behavior you observed. Rust Tutor leaves the project execution to you.", "dim-label"))
        if lesson.starter:
            starter, _ = code_view(lesson.starter)
            article.append(starter)
        self.practice_observations(article, lesson.editor_checks, record, self.update_progress)
        tip = label()
        count = 0

        def hint():
            nonlocal count
            if count < len(lesson.hints):
                tip.set_text(lesson.hints[count])
                count += 1
                record["hints_used"] = record.get("hints_used", 0) + 1
                self.save()

        article.append(button("Get a hint", hint, "flat"))
        article.append(tip)
        article.append(button("Review a saved Rust file", self.open_editor_review, "flat"))

    def practice_observations(self, article, criteria, record, refresh):
        marks = record.get("observations", {})
        choices = ("Unrecorded", "Observed as expected", "Tried, needs practice")
        for index, criterion in enumerate(criteria):
            key = str(index)
            article.append(label(criterion))
            value = marks.get(key)
            field = Gtk.DropDown(model=Gtk.StringList.new(choices),
                                 selected=0 if value is None else 1 if value else 2,
                                 halign=Gtk.Align.START)
            field.set_tooltip_text(criterion)

            def changed(control, _property, item=key):
                selected = control.get_selected()
                saved = record.setdefault("observations", {})
                if not selected:
                    saved.pop(item, None)
                else:
                    saved[item] = selected == 1
                    if selected == 2:
                        record["failed_checks"] = record.get("failed_checks", 0) + 1
                if all(saved.get(str(index)) is True for index in range(len(criteria))):
                    record["passed"] = True
                self.save()
                refresh()

            field.connect("notify::selected", changed)
            article.append(field)

    def in_app_practice(self, article, lesson, record):
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
        solution_button = None
        if lesson.solution is not None:
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
                    message = lesson.success_tip or (
                        "Your implementation met the exercise checks. For a follow-up, pick an input "
                        "and explain how each statement or branch leads to its result."
                    )
                else:
                    message = f"Hint {index + 1} of {len(lesson.hints)}\n{lesson.hints[index]}"
                    if action == "hint":
                        record["hints_used"] = record.get("hints_used", 0) + 1
                        self.save()
                feedback.set_text(message)
                if solution_button is not None:
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

    def run_exercise(self, lesson, source, record, action, title, output):
        sample = action == "run"
        passed_cases = 0
        try:
            results = check(lesson, source, sample=sample)
            rows = []
            for case, actual in results:
                arguments = " ".join(case.arguments) or "Program output"
                if sample:
                    rows.append(f"{arguments}\n{actual or '(no output)'}")
                elif case.matches(actual):
                    passed_cases += 1
                    rows.append(f"Pass · {arguments}\n{actual or '(no output)'}")
                else:
                    rows.append(f"Try again · {arguments}\nExpected: {case.expected}\nGot: {actual or '(no output)'}")
            output.set_text("\n\n".join(rows))
            passed = bool(results) and (sample or passed_cases == len(results))
            title.set_text("Sample output" if sample else "All checks passed" if passed else "Check the expected behavior")
        except ExerciseError as error:
            title.set_text("Practice editor diagnostic")
            output.set_text(str(error))
            passed = False
        if action in {"run", "hint"}:
            return passed
        if action in {"check", "review"}:
            record["latest_check"] = "passed" if passed else "needs practice"
            record["passed_cases"] = passed_cases
        if passed:
            record["passed"] = True
            record["attempts"] = 0
            record.pop("last_failure", None)
        else:
            fingerprint = hashlib.sha256(source.encode("utf-8")).hexdigest()
            if record.get("last_failure") != fingerprint:
                record["attempts"] = record.get("attempts", 0) + 1
                record["failed_checks"] = record.get("failed_checks", 0) + 1
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
            article.append(button("Return to lesson", return_action, "flat"))
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
            if chapter.id == "cargo":
                content.append(button("Open the Rust resources directory",
                                      lambda: self.open_reference("resources"), "flat"))
            content.append(button("Open chapter cheat sheet", lambda: self.open_cheat_sheet(
                chapter.title, chapter.cheat_sheet, lambda: self.open_reference(chapter.id, return_action)), "flat"))

        def filter_row(row):
            query = search.get_text().strip().casefold()
            chapter = row.chapter
            text = f"{chapter.title} {chapter.summary} {chapter.sections} {chapter.cheat_sheet}"
            return all(word in text.casefold() for word in query.split())

        topics.set_filter_func(filter_row)
        search.connect("search-changed", lambda _entry: topics.invalidate_filter())
        topics.connect("row-activated", lambda _list, row: render(row.chapter))
        first = rows.get(chapter_id) or next(iter(rows.values()))
        topics.select_row(first)
        render(first.chapter)

    def export_reference(self):
        content = printable_reference(self.chapters.values(), self.milestones.values())
        self.export_printable("rust-reference.html", content)

    def open_cheat_sheet(self, title, entries, back):
        article = self.document(None, title)
        article.append(label(title, "title-1"))
        article.append(label("Rust cheat sheet", "title-3"))
        for term, idea in entries:
            article.append(label(term, "heading"))
            article.append(label(idea, "learning-body"))
        article.append(self.speech_controls(" ".join([title, *(f"{term}. {idea}" for term, idea in entries)])))
        status = label()

        def print_copy(pdf_path=None):
            try:
                done = print_sheet(self, title, entries, pdf_path)
            except (ImportError, ValueError):
                status.set_text("For the system print dialog or direct PDF export, install python3-gi-cairo. "
                                "You can save the printable copy and use your browser’s Print or Save as PDF.")
            except (GLib.Error, OSError) as error:
                status.set_text(f"Couldn’t print this sheet. {error}")
            else:
                status.set_text("PDF saved." if done and pdf_path else "")

        def save_pdf():
            dialog = Gtk.FileDialog(title="Save Rust cheat sheet as PDF", initial_name="rust-cheat-sheet.pdf")

            def selected(chooser, result):
                try:
                    location = chooser.save_finish(result)
                    if location and location.get_path():
                        print_copy(location.get_path())
                except GLib.Error as error:
                    if not error.matches(Gtk.DialogError.quark(), Gtk.DialogError.DISMISSED):
                        status.set_text(error.message)

            dialog.save(self, None, selected)

        article.append(button("Print…", print_copy, "suggested-action"))
        article.append(button("Save as PDF…", save_pdf))
        article.append(button("Save printable HTML…", lambda: self.export_printable(
            "rust-cheat-sheet.html", printable_sheet(title, entries)), "flat"))
        article.append(status)
        article.append(button("Back to chapter", back, "flat"))

    def export_printable(self, filename, content):
        dialog = Gtk.FileDialog(title="Save printable copy", initial_name=filename)

        def save_file(chooser, result):
            try:
                file = chooser.save_finish(result)
                if not file or not file.get_path():
                    return
                Path(file.get_path()).write_text(content, encoding="utf-8")
                self.toasts.add_toast(Adw.Toast(title="Saved. Open the file in your browser to print or save as PDF."))
            except GLib.Error as error:
                if not error.matches(Gtk.DialogError.quark(), Gtk.DialogError.DISMISSED):
                    self.toasts.add_toast(Adw.Toast(title=error.message))
            except OSError as error:
                self.toasts.add_toast(Adw.Toast(title=str(error)))

        dialog.save(self, None, save_file)

    def open_milestones(self):
        article = self.document("quiz", "Milestones and progress")
        article.append(label("Milestones and progress", "title-1"))
        article.append(label("Ready to move on means all required behavior checks passed and a complete concept quiz "
                             "with at least 80% correct. Hints and retries describe support used."))
        course = self.progress.course(self.language)
        for title, path in ((CORE_PATH, "milestones"), (ADVANCED_PATH, "advanced_milestones")):
            article.append(label(title, "title-2"))
            for stage in self.course[path]:
                ready = milestone_ready(course, stage, self.lessons)
                article.append(button(f"{stage.title} · {'Ready to move on' if ready else 'View progress'}",
                                      lambda item=stage: self.open_milestone(item), "flat"))

    def open_milestone(self, stage):
        article = self.document("quiz", stage.title)
        course = self.progress.course(self.language)
        plan = self.active_pace(stage)
        advanced = stage in self.course["advanced_milestones"]
        article.append(label(stage.title, "title-1"))
        if advanced:
            article.append(label(ADVANCED_PATH, "dim-label"))
        if stage.prerequisite:
            prior = self.milestones[stage.prerequisite]
            article.append(button(f"Prerequisite · {prior.title}", lambda: self.open_milestone(prior), "flat"))
        article.append(label(f"What you’re working toward · {stage.endpoint}"))
        report = column(8)
        report.add_css_class("card")
        report.add_css_class("lesson-card")
        article.append(report)
        report_note = label()
        status = label()
        cancel = self.cancel_control(status)

        def refresh():
            report_note.set_text("")
            while (child := report.get_first_child()) is not None:
                report.remove(child)
            skills = {key: skill_progress(course, key, self.lessons) for key in stage.skill_ids}
            correct, total, answered = quiz_score(course, stage)
            ready = milestone_ready(course, stage, self.lessons)
            evidence = quiz_results(course, stage)
            opened = bool(answered or any(skill.tried or skill.passed for skill in skills.values()))
            status_text = "Ready to move on" if ready else "Needs more practice" if opened else "Not yet covered"
            report.append(label(status_text, "title-2"))
            report.append(label("Skills · behavior checks and concept answers", "heading"))
            report.append(label(f"Concept quiz · {correct * 100 // total}% ({correct}/{total} correct, "
                                f"{answered}/{total} answered)" if answered else "Concept quiz · No answers recorded"))
            for key, skill in skills.items():
                title = (self.lessons.get(key) or self.topics[key]).title
                answers = [evidence.get(item.id) for item in questions(stage) if item.topic == key]
                if skill.demonstrated and all(answers):
                    rating = "Covered & demonstrated"
                elif skill.tried or skill.passed or any(answer is not None for answer in answers):
                    rating = "Needs practice"
                else:
                    rating = "Not yet covered"
                if plan and plan["kind"] == "combine" and key in plan["skills"]:
                    rating += f" · Combined into {plan['title']}"
                report.append(label(f"{title} · {rating}"))
                graph = Gtk.ProgressBar(show_text=True, fraction=skill.passed / skill.required,
                                        text=f"Behavior {skill.passed}/{skill.required} · "
                                             f"Concept {sum(answer is True for answer in answers)}/{len(answers)}")
                graph.set_tooltip_text(f"{title}. {graph.get_text()}")
                report.append(graph)
            hints = sum(skill.hints for skill in skills.values())
            retries = sum(skill.retries for skill in skills.values())
            report.append(label(f"Support used · {hints} hints · {retries} unsuccessful check attempts", "dim-label"))
            if stage.outline or any(self.lessons[key].editor_checks for key in stage.skill_ids):
                report.append(label("Cargo checks are observations you record after running your own code.", "dim-label"))
            next_step = "Carry the demonstrated skills into the next project." if ready else (
                "Revisit a skill marked for practice, then try one small behavior check or retake the quiz.")
            report.append(label(f"Next step · {next_step}"))

        def ask_for_summary():
            evidence = quiz_results(course, stage)
            summary = []
            for key in stage.skill_ids:
                item = self.lessons.get(key) or self.topics[key]
                skill = skill_progress(course, key, self.lessons)
                summary.append({"id": key, "title": item.title, "checks_passed": skill.passed,
                                "checks_required": skill.required, "hints": skill.hints, "failed_checks": skill.retries,
                                "quiz": [evidence.get(q.id) for q in questions(stage) if q.topic == key]})
            correct, total, answered = quiz_score(course, stage)
            data = {"milestone": stage.title, "project": stage.endpoint, "skills": summary,
                    "quiz": {"correct": correct, "total": total, "answered": answered},
                    "ready": milestone_ready(course, stage, self.lessons)}

            def receive(response):
                advice, model_status = response
                report_note.set_text(advice)
                status.set_text(model_status)

            self.ask_model(lambda: report_task(data), receive, status, cancel)

        refresh()
        article.append(button("Take concept quiz", lambda: self.open_quiz(stage), "suggested-action"))
        if stage.outline:
            correct, total, answered = quiz_score(course, stage, "transfer")
            text = f"Follow-up quiz · {correct}/{total} correct" if answered else "Take follow-up quiz"
            article.append(button(text, lambda: self.open_quiz(stage, "transfer"), "flat"))
        article.append(button("Open chapter cheat sheet", lambda: self.open_cheat_sheet(
            stage.title, stage.cheat_sheet, lambda: self.open_milestone(stage)), "flat"))
        article.append(button("Review pace and practice options", lambda: self.open_pacing(stage), "flat"))
        personalize = button("Ask tutor for a short chapter summary", ask_for_summary, "flat")
        personalize.set_sensitive(self.tutor_configured())
        article.append(personalize)
        if self.tutor_configured():
            article.append(label(f"The summary uses the chapter evidence shown above and goes to "
                                 f"{self.tutor_destination()} when requested.", "dim-label"))
        article.append(cancel)
        article.append(status)
        article.append(report_note)

        if not stage.outline:
            for key in stage.skill_ids:
                lesson = self.lessons[key]
                article.append(button(lesson.title, lambda item=lesson: self.open_lesson(item), "flat"))
                self.insert_practice(article, stage, key, lambda: self.open_milestone(stage))
        else:
            article.append(label("Advanced lesson outlines" if advanced else "Core lesson outlines", "title-2"))
            article.append(label("Study each idea and try its two checks in a local Cargo project. "
                                 "You can use the chapter project to demonstrate both."))
            combined_skills = plan["skills"] if plan and plan["kind"] == "combine" else ()
            shared = column(12)
            for topic in stage.outline:
                if combined_skills and topic.id == combined_skills[0]:
                    shared.add_css_class("card")
                    shared.add_css_class("lesson-card")
                    shared.append(label(plan["title"], "title-2"))
                    shared.append(label(plan["reason"], "dim-label"))
                    self.pace_activities(shared, plan)
                    article.append(shared)
                section = column(8)
                if topic.id not in combined_skills:
                    section.add_css_class("card")
                section.add_css_class("lesson-card")
                section.append(label(topic.title, "title-3"))
                section.append(label(topic.goal))
                section.append(label(topic.quick_reference, "learning-body"))
                record = self.progress.lesson(self.language, topic.id)
                self.practice_observations(section, topic.checks, record, refresh)
                (shared if topic.id in combined_skills else article).append(section)
                self.insert_practice(article, stage, topic.id, lambda: self.open_milestone(stage))
                self.insert_project_page(article, stage, topic.id)
        if stage.sources:
            article.append(label("References", "title-3"))
            for title, url in stage.sources:
                article.append(Gtk.LinkButton(uri=url, label=title, halign=Gtk.Align.START))
        following = next((item for item in self.milestones.values() if item.prerequisite == stage.id), None)
        if following:
            caption = "Explore advanced Rust" if not advanced and following in self.course["advanced_milestones"] else "Next milestone"
            article.append(button(f"{caption} · {following.title}", lambda: self.open_milestone(following), "flat"))
        article.append(button("Back to milestone list", self.open_milestones, "flat"))

    def open_quiz(self, stage, form="concept"):
        article = self.document("quiz", stage.title)
        article.append(label("Concept quiz" if form == "concept" else "Follow-up quiz", "title-1"))
        article.append(label(stage.title, "title-3"))
        article.append(label("Use the results to choose what to revisit. Core skills also require demonstrated behavior."))
        course = self.progress.course(self.language)
        previous = quiz_results(course, stage, form)
        controls = []
        for item in questions(stage, form):
            group = column(7)
            group.add_css_class("card")
            group.add_css_class("lesson-card")
            group.append(label(item.prompt, "heading"))
            choices = list(item.alternatives)
            slot = hashlib.sha256(item.id.encode()).digest()[0] % (len(choices) + 1)
            choices.insert(slot, item.answer)
            radios = []
            for choice in choices:
                radio = Gtk.CheckButton(label=choice)
                if radios:
                    radio.set_group(radios[0])
                radios.append(radio)
                group.append(radio)
            feedback = label("Previously correct" if previous.get(item.id) is True else
                             "Previously marked for practice" if previous.get(item.id) is False else "")
            group.append(feedback)
            controls.append((item, slot, radios, feedback))
            article.append(group)

        def grade():
            selected = [next((i for i, radio in enumerate(radios) if radio.get_active()), None)
                        for _, _, radios, _ in controls]
            if None in selected:
                summary.set_text("Answer every question to record the result.")
                return
            answers = {}
            for (item, slot, _, feedback), choice in zip(controls, selected, strict=True):
                correct = choice == slot
                answers[item.id] = correct
                feedback.set_text("Correct." if correct else f"Revisit this concept. {item.answer}")
            course.setdefault("milestone_quizzes", {}).setdefault(stage.id, {})[form] = answers
            self.save()
            summary.set_text(f"{sum(answers.values())}/{len(controls)} correct. Open your milestone to see what to practice.")

        summary = label()
        article.append(button("Review answers", grade, "suggested-action"))
        article.append(summary)
        article.append(button("Return to milestone", lambda: self.open_milestone(stage), "flat"))

    def open_pacing(self, stage):
        article = self.document("quiz", "Pace and practice")
        course = self.progress.course(self.language)
        article.append(label(f"Pace and practice · {stage.title}", "title-1"))
        article.append(label("Every core skill stays in the standard course. You can add short practice or use "
                             "one larger project to demonstrate two related skills. Local code checks and quiz results "
                             "guide these choices. Editor-project checks are observations you record."))
        adjustment = course.setdefault("pacing", {}).setdefault(stage.id, {"active": None, "saved": {}})
        current = adjustment["saved"].get(adjustment["active"])
        if current:
            article.append(label(f"Active adjustment · {current['title']}", "title-2"))
            article.append(label(current["reason"]))
            if current.get("pages"):
                self.practice_page_links(article, stage, current, lambda: self.open_pacing(stage))
            else:
                self.pace_activities(article, current)

            def restore():
                adjustment["active"] = None
                self.save()
                self.open_pacing(stage)

            article.append(button("Restore standard pace", restore, "flat"))
        practice, combined = pacing_options(course, stage, self.lessons)
        prior = stage.prerequisite
        while combined and prior:
            prerequisite = self.milestones[prior]
            if not milestone_ready(course, prerequisite, self.lessons):
                combined = []
            prior = prerequisite.prerequisite
        options = [("practice", (key,)) for key in practice] + [("combine", pair) for pair in combined]
        titles = {key: (self.lessons.get(key) or self.topics[key]).title for key in stage.skill_ids}
        prompts = ["More practice · " + titles[key] for key in practice]
        prompts.extend("Combine · " + " + ".join(titles[key] for key in pair) for pair in combined)
        article.append(label("Combination requires both skills’ checks to pass, correct answers for each skill on "
                             "two separately graded quizzes, at least 80% on both, and readiness on the prerequisites.",
                             "dim-label"))
        if not options:
            article.append(label("Record a behavior check or take the quiz to see evidence-based practice options."))
        else:
            chooser = Gtk.DropDown(model=Gtk.StringList.new(prompts), halign=Gtk.Align.START)
            chooser.set_tooltip_text("Choose a practice or combination to preview")
            article.append(chooser)
            result = column(8)
            status = label()
            cancel = self.cancel_control(status)

            def make_plan():
                kind, keys = options[chooser.get_selected()]
                plan = {"kind": kind, "skills": list(keys), "done": [], "origin": "Authored lesson"}
                if kind == "practice":
                    key = keys[0]
                    item = self.lessons.get(key) or self.topics[key]
                    return {**plan, "title": f"Practice {titles[key]}",
                            "reason": "A saved answer or behavior check points to this skill for practice.",
                            "pages": remedial_pages(key, item, authored=key in self.lessons)}
                return {**plan, "title": "Shared project practice",
                        "reason": "Both skills met their behavior checks and their concept and follow-up quiz criteria.",
                        "steps": [f"Use this project: {stage.endpoint} Explain where each skill appears in your implementation.",
                                  "Run the normal and edge cases for each skill. Record the results separately."]}

            def clear(*_args):
                while (child := result.get_first_child()) is not None:
                    result.remove(child)
                status.set_text("")

            def preview(plan):
                clear()
                result.append(label("Preview and edit", "title-2"))
                result.append(label(" · ".join(titles[key] for key in plan["skills"])))
                result.append(label(plan["reason"]))
                result.append(label(plan["origin"], "dim-label"))
                fields = []
                page_editors = []
                if plan.get("pages"):
                    for page in plan["pages"]:
                        page_editors.append(self.edit_manual_page(result, page))
                else:
                    for name, value in zip(("Title", "First activity", "Second activity"),
                                           (plan["title"], *plan["steps"]), strict=True):
                        result.append(label(name, "heading"))
                        entry = Gtk.Entry(text=value, max_length=400)
                        entry.set_tooltip_text(name)
                        result.append(entry)
                        fields.append(entry)

                def apply():
                    try:
                        if page_editors:
                            approved = {**plan, "pages": self.edited_manual_pages(plan["pages"], page_editors)}
                        else:
                            title, *steps = [field.get_text().strip() for field in fields]
                            if not title or not all(steps):
                                raise ValueError("Enter a title and both activity descriptions.")
                            approved = {**plan, "title": title, "steps": steps}
                    except ValueError as error:
                        status.set_text(str(error))
                        return
                    key = uuid4().hex
                    adjustment["saved"][key] = approved
                    adjustment["active"] = key
                    self.save()
                    self.open_pacing(stage)

                result.append(button("Apply this pace adjustment", apply, "suggested-action"))

            def ask():
                clear()
                plan = make_plan()
                items = []
                concept = quiz_results(course, stage)
                follow_up = quiz_results(course, stage, "transfer") if stage.outline else {}
                for key in plan["skills"]:
                    item = self.lessons.get(key) or self.topics[key]
                    skill = skill_progress(course, key, self.lessons)
                    items.append({"id": key, "title": titles[key], "goal": item.question if key in self.lessons else item.goal,
                                  "checks": f"{skill.passed}/{skill.required}", "hints": skill.hints, "retries": skill.retries,
                                  "concept_quiz": [concept.get(q.id) for q in questions(stage) if q.topic == key],
                                  "follow_up_quiz": follow_up.get(item.transfer.id) if key in self.topics else None})
                data = {"kind": plan["kind"], "skills": items, "reason": plan["reason"], "project": stage.endpoint,
                        "prerequisite": stage.prerequisite, "outline": plan.get("steps", [])}

                def receive(response):
                    adapted, model_status = response
                    change = {"pages": adapted} if plan.get("pages") else adapted
                    preview({**plan, **change, "origin": "Tutor proposal"})
                    status.set_text(model_status)

                self.ask_model(lambda: pace_task(data, plan.get("pages")), receive, status, cancel)

            def selection_changed(*_args):
                self.cancel_tutor()
                clear()

            chooser.connect("notify::selected", selection_changed)
            article.append(button("Preview suggested pages or activities", lambda: preview(make_plan())))
            tutor_button = button("Ask tutor to draft this adjustment", ask)
            tutor_button.set_sensitive(self.tutor_configured())
            article.append(tutor_button)
            if self.tutor_configured():
                article.append(label(f"The selected skill and saved check and quiz evidence go to "
                                     f"{self.tutor_destination()} when you ask.", "dim-label"))
            article.append(cancel)
            article.append(status)
            article.append(result)

        archived = [plan for key, plan in adjustment["saved"].items() if key != adjustment["active"]]
        if archived:
            history = Gtk.Expander(label="Previous adjustments and progress")
            entries = column(8)
            for old in reversed(archived):
                entries.append(label(old["title"], "heading"))
                entries.append(label(f"{len(old['done'])} of {len(old.get('pages') or old['steps'])} activities completed"))
            history.set_child(entries)
            article.append(history)
        article.append(button("Back to milestone", lambda: self.open_milestone(stage), "flat"))

    def active_pace(self, stage):
        adjustment = self.progress.course(self.language).get("pacing", {}).get(stage.id, {})
        return adjustment.get("saved", {}).get(adjustment.get("active"))

    def insert_practice(self, article, stage, key, back):
        plan = self.active_pace(stage)
        if not plan or plan["kind"] != "practice" or key not in plan["skills"]:
            return
        if plan.get("pages"):
            self.practice_page_links(article, stage, plan, back)
        else:
            self.pace_activities(article, plan)

    def practice_page_links(self, article, stage, plan, back):
        for index, page in enumerate(plan["pages"]):
            done = " · Complete" if index in plan["done"] else ""
            article.append(button(f"Extra lesson · {page['title']}{done}",
                                  lambda i=index: self.open_practice_page(stage, plan, i, back), "flat"))

    def open_practice_page(self, stage, plan, index, back):
        page = plan["pages"][index]
        article = self.document("quiz", page["title"])
        article.append(label(stage.title + " · Extra lesson", "dim-label"))
        self.show_manual_page(article, page)
        lesson = self.lessons.get(plan["skills"][0])
        if lesson:
            article.append(button("Open related reference", lambda: self.open_reference(
                lesson.reference, lambda: self.open_practice_page(stage, plan, index, back)), "flat"))
        else:
            article.append(button("Open chapter cheat sheet", lambda: self.open_cheat_sheet(
                stage.title, stage.cheat_sheet, lambda: self.open_practice_page(stage, plan, index, back)), "flat"))
        complete = Gtk.CheckButton(label="Mark this extra lesson complete", active=index in plan["done"])

        def mark(control):
            if control.get_active():
                plan["done"].append(index)
            else:
                plan["done"].remove(index)
            self.save()

        complete.connect("toggled", mark)
        article.append(complete)
        if index + 1 < len(plan["pages"]):
            article.append(button("Next extra lesson", lambda: self.open_practice_page(stage, plan, index + 1, back),
                                  "suggested-action"))
        article.append(button("Return to course", back, "flat"))

    def show_manual_page(self, article, page):
        article.append(label(page["title"], "title-1"))
        if page.get("skill_title"):
            article.append(label(f"Core skill · {page['skill_title']}", "dim-label"))
        article.append(self.speech_controls(" ".join(page[key] for key in ("title", "explanation", "example", "exercise"))))
        for key in ("explanation", "example", "exercise"):
            article.append(label(MANUAL_FIELDS[key], "title-3"))
            article.append(label(page[key], "learning-body"))
            if key == "example" and page.get("example_code"):
                example, _ = code_view(page["example_code"])
                article.append(example)
        article.append(label("Check the behavior", "title-3"))
        for criterion in page["checks"]:
            article.append(label(criterion))
        hint = Gtk.Expander(label="Show a hint")
        hint.set_child(label(page["hint"]))
        article.append(hint)

    def edit_manual_page(self, article, page):
        card = Gtk.Expander(label=page["title"], expanded=True)
        content = column(6)
        buffers = {}
        if page.get("skill_title"):
            content.append(label(f"Core skill · {page['skill_title']}", "heading"))
        for key, field in MANUAL_FIELDS.items():
            content.append(label(field, "heading"))
            view = Gtk.TextView(wrap_mode=Gtk.WrapMode.WORD_CHAR)
            view.set_tooltip_text(field)
            view.set_size_request(-1, 30 if key == "title" else 55)
            view.get_buffer().set_text(page[key])
            buffers[key] = view.get_buffer()
            content.append(view)
        for criterion in page["checks"]:
            content.append(label(criterion, "dim-label"))
        card.set_child(content)
        article.append(card)
        return buffers

    def edited_manual_pages(self, pages, editors):
        approved = []
        for page, buffers in zip(pages, editors, strict=True):
            updated = page.copy()
            for key, buffer in buffers.items():
                value = " ".join(buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), True).split())
                if not 0 < len(value) <= PAGE_FIELDS[key]:
                    raise ValueError(f"Enter up to {PAGE_FIELDS[key]} characters for {MANUAL_FIELDS[key].lower()} on each page.")
                updated[key] = value
            approved.append(updated)
        return approved

    def pace_activities(self, article, plan):
        for index, step in enumerate(plan["steps"]):
            article.append(label(step, "learning-body"))
            done = Gtk.CheckButton(label="Activity complete", active=index in plan["done"])

            def mark(control, item=index):
                if control.get_active():
                    plan["done"].append(item)
                else:
                    plan["done"].remove(item)
                self.save()

            done.connect("toggled", mark)
            article.append(done)
        article.append(label("Keep each core skill’s evidence in the milestone. Activity completion adds to your "
                             "practice history.", "dim-label"))

    def open_path(self):
        article = self.document("next", "Course roadmap")
        article.append(label("Rust course roadmap", "title-1"))
        article.append(button("Read the Ubuntu and editor setup guide", lambda: self.open_reference("cargo"), "flat"))
        article.append(button("Review a file from your editor", self.open_editor_review, "flat"))
        article.append(label(CORE_PATH, "title-2"))
        article.append(label("Ten offline foundations and 42 shorter topics prepare you for command-line, backend, "
                             "and desktop projects. This path ends with the application capstone."))
        self.roadmap_cards(article, self.course["milestones"])
        article.append(label("Optional app project path", "title-3"))
        projects = self.project_progress()
        active = projects["saved"].get(projects.get("active"))
        if active:
            article.append(label(active["idea"]))
            self.add_project_lessons(article, projects["active"], active)
        article.append(button("Plan my project", self.open_project_paths))
        article.append(label(ADVANCED_PATH, "title-2"))
        article.append(label("Continue after the capstone with six milestones in ownership, concurrency, macros, "
                             "async, and unsafe Rust. Use the prerequisites, checks, and references to guide further study."))
        self.roadmap_cards(article, self.course["advanced_milestones"])
        article.append(label("Optional specialization · Foreign function interface (FFI)", "title-3"))
        article.append(label("Explore FFI if your project needs to call code built in another language."))
        for title, url in self.course["optional_references"]:
            article.append(Gtk.LinkButton(uri=url, label=title, halign=Gtk.Align.START))

    def roadmap_cards(self, article, milestones):
        for stage in milestones:
            section = column(5)
            section.add_css_class("card")
            section.add_css_class("lesson-card")
            section.append(button(stage.title, lambda item=stage: self.open_milestone(item), "flat"))
            section.append(label(stage.endpoint))
            titles = [(self.lessons.get(key) or self.topics[key]).title for key in stage.skill_ids]
            section.append(label(" · ".join(titles), "dim-label"))
            article.append(section)

    def project_progress(self):
        course = self.progress.course(self.language)
        return course.setdefault("project_paths", {"active": None, "saved": {}})

    def foundation_complete(self, key):
        course = self.progress.course(self.language)
        return (bool(course.get("lessons", {}).get(key, {}).get("passed"))
                or skill_progress(course, key, self.lessons).demonstrated)

    def foundations_complete(self):
        return all(self.foundation_complete(key) for key in self.lessons)

    def project_page_prerequisite(self, plan, index):
        pages = plan["pages"]
        if pages[index]["id"] in plan["completed"]:
            return ""
        if plan.get("schema") != 2:
            return ("Finish the ten foundation exercises first."
                    if not plan["completed"] and not self.foundations_complete() else "")
        course = self.progress.course(self.language)
        for stage in self.milestones.values():
            if stage.id == plan["milestone"]:
                break
            if not milestone_ready(course, stage, self.lessons):
                return f"Finish the checks and quiz for {stage.title} first."
        if index and pages[index - 1]["id"] not in plan["completed"]:
            return f"Complete the previous project page first."
        return ""

    def add_project_lessons(self, container, plan_id, plan):
        for index, page in enumerate(plan["pages"]):
            done = " · Complete" if page["id"] in plan["completed"] else ""
            prerequisite = self.project_page_prerequisite(plan, index)
            if prerequisite:
                container.append(label(f"{page['title']} · {prerequisite}", "dim-label"))
            else:
                container.append(button(page["title"] + done,
                                        lambda item=index: self.open_project_lesson(plan_id, item), "flat"))

    def insert_project_page(self, container, stage, key):
        projects = self.project_progress()
        plan_id = projects.get("active")
        plan = projects["saved"].get(plan_id, {})
        if plan.get("milestone") != stage.id:
            return
        for index, page in enumerate(plan["pages"]):
            if page["skill"] == key:
                prerequisite = self.project_page_prerequisite(plan, index)
                if prerequisite:
                    container.append(label(f"Project lesson · {page['title']} · {prerequisite}", "dim-label"))
                else:
                    container.append(button(f"Project lesson · {page['title']}",
                                            lambda i=index: self.open_project_lesson(plan_id, i), "flat"))

    def open_project_paths(self):
        article = self.document("projects", "Project paths")
        article.append(label("Plan a project you want to build", "title-1"))
        article.append(label("Preview an offline starter template, or ask the tutor to teach your next roadmap "
                             "skills through your own app idea. Project pages follow the same prerequisites "
                             "and have separate completion marks."))
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
            if plan.get("schema") == 2:
                stage = self.milestones[plan["milestone"]]
                route = "Optional extension" if plan.get("extension") else "Next roadmap chapter"
                proposal.append(label(f"{route} · {stage.title}", "heading"))
                prior = self.milestones[plan["prerequisite"]]
                proposal.append(label(f"Prerequisite · {prior.title}", "dim-label"))
                editors = [self.edit_manual_page(proposal, page) for page in plan["pages"]]
            else:
                editors = []
                proposal.append(label("Authored offline template", "dim-label"))
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
                try:
                    approved = ({**plan, "pages": self.edited_manual_pages(plan["pages"], editors)}
                                if editors else plan)
                except ValueError as error:
                    status.set_text(str(error))
                    return
                key = uuid4().hex
                projects["saved"][key] = approved
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
            course = self.progress.course(self.language)
            stage, topics, extension = upcoming_project_topics(course, self.course["milestones"], self.lessons)
            try:
                draft = propose_roadmap_path(idea.get_text(), focus_key(), stage, topics, extension)
            except ValueError as error:
                status.set_text(str(error))
                return
            evidence = []
            for topic in topics:
                progress = skill_progress(course, topic.id, self.lessons)
                evidence.append({"skill": topic.id, "behavior": f"{progress.passed}/{progress.required}",
                                 "concept": concept_evidence(course, stage, topic.id)})

            def receive(response):
                pages, model_status = response
                render_plan({**draft, "pages": pages}, f"Review and edit the tutor’s proposed pages. {model_status}")

            self.ask_model(lambda: project_task(draft, evidence, self.chapters["resources"]), receive, status, cancel)

        def edit(*_args):
            self.cancel_tutor()
            clear_proposal()

        idea.connect("changed", edit)
        focus.connect("notify::selected", edit)
        article.append(button("Preview authored template", preview))
        build_ai = button("Build a project path with the tutor", adapt, "suggested-action")
        build_ai.set_sensitive(self.tutor_configured())
        article.append(build_ai)
        if self.tutor_configured():
            article.append(label(f"The idea, planned skills, and relevant check and quiz evidence go to "
                                 f"{self.tutor_destination()} when requested.", "dim-label"))
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
        if self.project_page_prerequisite(plan, index):
            self.open_project_paths()
            return
        page = plan["pages"][index]
        article = self.document("projects", page["title"])
        article.append(label(plan["idea"], "dim-label"))
        if plan.get("schema") == 2:
            self.show_manual_page(article, page)
            stage = self.milestones[plan["milestone"]]
            article.append(button("Open chapter cheat sheet", lambda: self.open_cheat_sheet(
                stage.title, stage.cheat_sheet, lambda: self.open_project_lesson(plan_id, index)), "flat"))
            article.append(button("Open the core chapter and record its checks", lambda: self.open_milestone(
                stage), "flat"))
        else:
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
            next_page = button("Next project lesson", lambda: self.open_project_lesson(plan_id, index + 1),
                               "suggested-action")
            next_page.set_sensitive(not self.project_page_prerequisite(plan, index + 1))
            complete.connect("toggled", lambda _control: next_page.set_sensitive(
                not self.project_page_prerequisite(plan, index + 1)))
            article.append(next_page)
        article.append(button("Return to project paths", self.open_project_paths, "flat"))

    def open_editor_review(self):
        article = self.document("handoff", "Review from editor")
        revision = self.page_revision
        article.append(label("Review code from VS Code or VSCodium", "title-1"))
        article.append(label("Save your work in the editor, then choose up to four .rs files or a Cargo.toml. "
                             "Choose just the related files. Rust Tutor previews the selection in memory without changing "
                             "your project, walking folders, or launching your code."))
        previews, buffer = code_view("")
        scroller = previews.get_child()
        scroller.set_min_content_height(175)
        scroller.set_max_content_height(285)
        scroller.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        file_status = label("No project files selected.", "dim-label")
        display_choice = Gtk.DropDown()
        display_choice.set_tooltip_text("Preview a selected file")
        output_title, output = label(), label()
        output.set_selectable(True)
        behavior = Gtk.Entry(placeholder_text="What should this code do?", max_length=400)
        review_status, answer = label(), column()
        cancel = self.cancel_control(review_status)
        files = ()
        evidence = None
        entries = tuple(lesson for lesson in self.lessons.values() if not lesson.editor_checks)
        exercise_choice = Gtk.DropDown(model=Gtk.StringList.new(["Select an optional lesson check"]
                                                               + [entry.title for entry in entries]))

        def clear_review(*_args):
            self.cancel_tutor()
            while (child := answer.get_first_child()) is not None:
                answer.remove(child)
            review_status.set_text("")

        def preview(*_args):
            nonlocal evidence
            evidence = None
            clear_review()
            output_title.set_text("")
            output.set_text("")
            index = display_choice.get_selected()
            item = files[index] if index < len(files) else None
            buffer.set_text(item.source if item else "")
            check_button.set_sensitive(bool(item and item.path.suffix == ".rs" and exercise_choice.get_selected()))

        def set_files(selection):
            nonlocal files
            files = selection
            names = [f"{index}. {item.path.name} · {item.size:,} bytes" for index, item in enumerate(files, start=1)]
            display_choice.set_model(Gtk.StringList.new(names or ["No file selected"]))
            file_status.set_text(f"{len(files)} file(s) · {sum(len(item.source) for item in files):,}/{REVIEW_LIMIT:,} "
                                 "characters for tutor review" if files else "No project files selected.")
            review_button.set_sensitive(self.tutor_configured() and any(item.path.suffix == ".rs" for item in files)
                                        and sum(len(item.source) for item in files) <= REVIEW_LIMIT)
            preview()

        def choose_files():
            dialog = Gtk.FileDialog(title="Choose saved Rust project files")
            rust_filter = Gtk.FileFilter(name="Rust sources and Cargo manifest")
            rust_filter.add_pattern("*.rs")
            rust_filter.add_pattern("Cargo.toml")
            filters = Gio.ListStore.new(Gtk.FileFilter)
            filters.append(rust_filter)
            dialog.set_filters(filters)

            def opened(chooser, result):
                if revision != self.page_revision:
                    return
                try:
                    selection = chooser.open_multiple_finish(result)
                    if selection is None:
                        return
                    if selection.get_n_items() > MAX_FILES:
                        raise ValueError(f"Choose at most {MAX_FILES} project files.")
                    paths = [selection.get_item(i).get_path() for i in range(selection.get_n_items())]
                    if not all(paths):
                        raise ValueError("Choose project files on this computer.")
                    set_files(read_selection(paths))
                except GLib.Error as error:
                    if not error.matches(Gtk.DialogError.quark(), Gtk.DialogError.DISMISSED):
                        review_status.set_text(error.message)
                except (OSError, ValueError) as error:
                    review_status.set_text(f"Could not open selection. {error}")

            dialog.open_multiple(self, None, opened)

        def check_file():
            nonlocal evidence
            index, exercise = display_choice.get_selected(), exercise_choice.get_selected()
            if not exercise or index >= len(files) or files[index].path.suffix != ".rs":
                return
            clear_review()
            lesson, item = entries[exercise - 1], files[index]
            record = self.progress.lesson(self.language, lesson.id)
            self.run_exercise(lesson, item.source, record, "review", output_title, output)
            evidence = f"Selection {index + 1} ({item.path.name})\n{output_title.get_text()}\n{output.get_text()}"[:700]

        def review():
            def task():
                index = exercise_choice.get_selected()
                lesson = entries[index - 1] if index else None
                return guidance_task(self.chapters.values(), behavior.get_text().strip(), lesson=lesson,
                                     files=review_payload(files), evidence=evidence)

            def receive(response):
                value, model_status = response
                while (child := answer.get_first_child()) is not None:
                    answer.remove(child)
                self.show_guidance(answer, value)
                review_status.set_text(model_status)

            self.ask_model(task, receive, review_status, cancel)

        check_button = button("Run lesson checks on the previewed file", check_file)
        review_button = button("Review selected files with the tutor", review, "suggested-action")
        display_choice.connect("notify::selected", preview)
        exercise_choice.connect("notify::selected", preview)
        behavior.connect("changed", clear_review)
        set_files(())
        article.append(button("Choose saved project files…", choose_files))
        article.append(button("Clear selection", lambda: set_files(()), "flat"))
        article.append(file_status)
        article.append(display_choice)
        article.append(previews)
        article.append(exercise_choice)
        article.append(check_button)
        article.append(output_title)
        article.append(output)
        article.append(Gtk.Separator())
        article.append(label("Review with the tutor", "title-3"))
        if self.tutor_configured():
            article.append(label(f"Review sends the selected file names and contents, your expected behavior, and any "
                                 f"shown lesson checks to {self.tutor_destination()}."))
        else:
            article.append(button("Configure the tutor", self.open_models, "flat"))
        article.append(label("Use your editor terminal to run the full project and its tests.", "dim-label"))
        article.append(behavior)
        article.append(review_button)
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
        external = Gtk.Expander(label="Use LM Studio on this computer or on your LAN",
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
                self.tutor_session = None
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
                self.tutor_session = None
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
        saved_host = config.get("host", LOOPBACK)
        saved_port = config.get("port", DEFAULT_PORT)
        article.append(label("Start the LM Studio server in the Developer tab. Download a GGUF instruction model "
                             "in LM Studio first. Checking the connection only lists models."))
        mode = Gtk.DropDown(model=Gtk.StringList.new(["This computer", "Another computer on my home network"]),
                            selected=int(saved_host != LOOPBACK))
        guide = column(8)
        guide.append(label("On the other computer, open Developer → Server Settings. Turn on Serve on Local Network "
                           "and Require Authentication, then use Manage Tokens to create an API token for Rust Tutor. "
                           "Start the server. Copy the private IPv4 address and port shown in the API URL. "
                           "If LM Studio shows 0.0.0.0, find the other computer’s IPv4 address in its Wi-Fi or Ethernet settings."))
        guide.append(label("Use a trusted home network and keep the server off the internet. Avoid port forwarding. "
                           "This connection uses HTTP, so devices that can inspect network traffic can read the token "
                           "and anything you send. To keep files on this computer, use the built-in tutor."))
        guide.append(Gtk.LinkButton(uri="https://lmstudio.ai/docs/developer/core/server/serve-on-network",
                                    label="LM Studio LAN setup", halign=Gtk.Align.START))
        host = Gtk.Entry(text=saved_host if saved_host != LOOPBACK else "", max_length=15,
                         placeholder_text="Example 192.168.1.25")
        guide.append(label("IPv4 address from LM Studio"))
        guide.append(host)
        port = Gtk.Entry(text=str(saved_port), max_length=5, input_purpose=Gtk.InputPurpose.DIGITS)
        token = Gtk.PasswordEntry(text=self.session_token(saved_host, saved_port), show_peek_icon=True, hexpand=True)
        selection = Gtk.DropDown()
        context = Gtk.DropDown(model=Gtk.StringList.new(["4,096 tokens", "8,192 tokens"]),
                               selected=int(config.get("context") == CONTEXTS[1]))
        status = label()
        recommendation = label(style="dim-label")
        selected_model = label(style="heading")
        models = []
        checked_endpoint = None
        cancel = self.cancel_control(status, "Cancel connection check")

        def reflect_saved():
            if config.get("model"):
                text = f"Selected model · {config['model']} · {saved_host}:{saved_port}"
                if (saved_host != LOOPBACK or config.get("requires_token")) and not self.session_token(saved_host, saved_port):
                    text += " · re-enter token to reconnect"
                selected_model.set_text(text)
            else:
                selected_model.set_text("No separate server selected")

        def endpoint():
            try:
                value = int(port.get_text().strip())
            except ValueError:
                raise TutorError("Enter the port number shown by LM Studio.") from None
            address = host.get_text().strip() if mode.get_selected() == 1 else LOOPBACK
            if mode.get_selected() == 1 and address == LOOPBACK:
                raise TutorError("Enter the private IPv4 address of the other computer.")
            return Settings(value, "", CONTEXTS[context.get_selected()], token.get_text().strip(), address)

        def invalidate(*_args):
            nonlocal checked_endpoint
            self.cancel_tutor()
            checked_endpoint = None
            models.clear()
            selection.set_model(Gtk.StringList.new(["Check the connection to list models"]))
            save_model.set_sensitive(False)
            recommendation.set_text("")
            status.set_text("")

        def changed(*_args):
            guide.set_visible(mode.get_selected() == 1)
            token.set_text("")
            invalidate()

        def refresh():
            invalidate()
            try:
                settings = endpoint()
            except TutorError as error:
                status.set_text(str(error))
                return

            def receive(installed):
                nonlocal checked_endpoint
                checked_endpoint = settings
                models[:] = installed
                selection.set_model(Gtk.StringList.new([model.description for model in installed]
                                                       or ["No supported models found"]))
                save_model.set_sensitive(bool(installed))
                if not installed:
                    status.set_text("Server reached. Download a GGUF instruction model in LM Studio, then check again.")
                    return
                preferred = next((model for model in installed
                                  if (settings.host, settings.port) == (saved_host, saved_port)
                                  and model.key == config.get("model")), installed[0])
                selection.set_selected(installed.index(preferred))
                status.set_text(f"Server reached at {settings.host}:{settings.port}. Choose a model.")
                if settings.host == LOOPBACK:
                    _, available = memory()
                    if available is not None and preferred.size / 1024 ** 3 >= max(available - 2, 0):
                        recommendation.set_text("This computer may need a smaller model. Check available RAM before loading.")
                else:
                    recommendation.set_text("Model RAM and GPU use are on the other computer. Start with a small model "
                                            "and 4,096 tokens if its capacity is uncertain.")

            self.start_tutor_job(lambda job: list_models(settings, job), receive, status,
                                 f"Checking {settings.host}:{settings.port}…", cancel)

        def configure():
            try:
                settings = endpoint()
            except TutorError as error:
                status.set_text(str(error))
                return
            index = selection.get_selected()
            if (index >= len(models) or checked_endpoint is None
                    or (settings.host, settings.port, settings.token) !=
                       (checked_endpoint.host, checked_endpoint.port, checked_endpoint.token)):
                status.set_text("Check the current connection before selecting a model.")
                return
            self.tutor_session = (settings.host, settings.port, settings.token)
            self.progress.data["tutor"] = {"backend": "lmstudio", "host": settings.host, "port": settings.port,
                                           "model": models[index].key, "context": settings.context,
                                           "requires_token": bool(settings.token)}
            self.save()
            self.open_models()

        def disable():
            self.cancel_tutor()
            if self.progress.data.get("tutor", {}).get("backend") != "managed":
                self.progress.data.pop("tutor", None)
            self.tutor_session = None
            self.save()
            self.open_models()

        save_model = button("Use selected model", configure)
        invalidate()
        reflect_saved()
        guide.set_visible(mode.get_selected() == 1)
        mode.connect("notify::selected", changed)
        for field in (host, port):
            field.connect("changed", changed)
        token.connect("changed", invalidate)
        article.append(selected_model)
        article.append(label("Where is LM Studio running?"))
        article.append(mode)
        article.append(guide)
        article.append(label("Server port"))
        article.append(port)
        article.append(label("API token (required on the LAN, kept only for this app session)"))
        article.append(token)
        article.append(button("Check connection and models", refresh, "suggested-action"))
        article.append(cancel)
        article.append(selection)
        article.append(recommendation)
        article.append(label("Context for a model loaded by Rust Tutor"))
        article.append(context)
        article.append(save_model)
        article.append(button("Disconnect LM Studio", disable, "flat"))
        article.append(status)
        article.append(label("Rust Tutor requests inference when you ask and asks LM Studio to unload any instance "
                             "it loaded. A model already loaded stays under your control in LM Studio.", "dim-label"))
        article.append(Gtk.LinkButton(uri="https://lmstudio.ai/docs/developer/rest/quickstart",
                                      label="LM Studio server setup", halign=Gtk.Align.START))
