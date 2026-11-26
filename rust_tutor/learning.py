"""Deterministic course progress and evidence rules."""

from dataclasses import dataclass


PASS_PERCENT = 80
LEGACY_ANSWERS = {"first-program": 0, "functions": 1, "calculator": 2}


@dataclass(frozen=True)
class SkillProgress:
    passed: int
    required: int
    tried: bool
    hints: int
    retries: int

    @property
    def demonstrated(self):
        return self.passed == self.required


def questions(milestone, form="concept"):
    if milestone.outline:
        return tuple(getattr(topic, form) for topic in milestone.outline)
    return milestone.questions


def quiz_results(course, milestone, form="concept"):
    saved = course.get("milestone_quizzes", {}).get(milestone.id, {})
    if form in saved:
        return saved[form]
    if milestone.outline or form != "concept":
        return {}
    legacy = course.get("quiz", {})
    return {item.id: legacy[item.id] == LEGACY_ANSWERS[item.id] for item in milestone.questions
            if item.id in legacy and item.id in LEGACY_ANSWERS}


def quiz_score(course, milestone, form="concept"):
    results = quiz_results(course, milestone, form)
    total = len(questions(milestone, form))
    correct = sum(results.values())
    return correct, total, len(results)


def quiz_ready(course, milestone, form="concept"):
    correct, total, answered = quiz_score(course, milestone, form)
    return answered == total and correct * 100 >= PASS_PERCENT * total


def skill_progress(course, skill_id, lessons):
    record = course.get("lessons", {}).get(skill_id, {})
    lesson = lessons.get(skill_id)
    if lesson and not lesson.editor_checks:
        required = len(lesson.cases)
        latest = record.get("latest_check")
        passed = record.get("passed_cases", 0)
        if record.get("passed") and latest != "needs practice":
            passed = required
        tried = bool(latest)
    else:
        required = len(lesson.editor_checks) if lesson else 2
        marks = record.get("observations", {})
        passed = sum(value is True for value in marks.values())
        tried = bool(marks)
    return SkillProgress(passed, required, tried,
                         record.get("hints_used", 0), record.get("failed_checks", record.get("attempts", 0)))


def milestone_ready(course, milestone, lessons):
    return (quiz_ready(course, milestone)
            and all(skill_progress(course, key, lessons).demonstrated for key in milestone.skill_ids))


def concept_evidence(course, milestone, key):
    saved = quiz_results(course, milestone)
    return tuple(saved.get(item.id) for item in questions(milestone) if item.topic == key)


def upcoming_project_topics(course, milestones, lessons):
    roadmap = tuple(stage for stage in milestones if stage.outline)
    for stage in roadmap:
        remaining = tuple(topic for topic in stage.outline
                          if not skill_progress(course, topic.id, lessons).demonstrated
                          or not all(concept_evidence(course, stage, topic.id)))
        if remaining:
            return stage, remaining[:3], False
    return roadmap[-1], roadmap[-1].outline, True


def pacing_options(course, milestone, lessons):
    """Return eligible fixed skill IDs, with the concept/behavior evidence scoped to this milestone."""
    concepts = quiz_results(course, milestone)
    practice = []
    for key in milestone.skill_ids:
        skill = skill_progress(course, key, lessons)
        missed = any(concepts.get(item.id) is False for item in questions(milestone) if item.topic == key)
        if missed or (skill.tried and not skill.demonstrated):
            practice.append(key)

    combined = []
    if milestone.outline and quiz_ready(course, milestone) and quiz_ready(course, milestone, "transfer"):
        transfer = quiz_results(course, milestone, "transfer")
        demonstrated = {
            topic.id for topic in milestone.outline
            if concepts.get(topic.concept.id) is True and transfer.get(topic.transfer.id) is True
            and skill_progress(course, topic.id, lessons).demonstrated
        }
        combined = [(left, right) for left, right in zip(milestone.skill_ids, milestone.skill_ids[1:])
                    if left in demonstrated and right in demonstrated]
    return practice, combined
