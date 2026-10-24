"""Turns a natural-language question into a *safe, predefined* query plan.

This is deliberately rule-based and never calls the LLM or builds SQL. The output is a
`StudentFilters` object whose values are later bound as ORM parameters, so neither the
user's question nor the model can influence the SQL that runs.
"""

import re
from dataclasses import dataclass, field
from datetime import date
from typing import Literal

from app.services.student_service import StudentFilters

_COUNT = re.compile(r"\b(how many|number of|count|total)\b", re.I)
_LIST = re.compile(
    r"\b(list|show|find|display|give|get|search|who|which|fetch|retrieve|tell me)\b", re.I
)
_STUDENT_ID = re.compile(r"\b([A-Za-z]{2,10}[-_]?\d{2,})\b")
_NAME = re.compile(
    r"""(?:names?\s+(?:contains?|containing|includes?|including|like|with|starts?\s+with)|named|called)
        \s+(?:"([^"]{1,60})"|'([^']{1,60})'|([A-Za-z][A-Za-z'\-]{0,59}))""",
    re.I | re.X,
)
_COURSE_FALLBACK = re.compile(
    r"(?:enrolled|studying|registered)\s+(?:in|for|on)\s+(?:the\s+)?(.+?)"
    r"(?:\s+(?:course|program|programme|and|who|born)\b|[?.!,;]|$)",
    re.I,
)
_BORN_FULL = re.compile(r"born\s+(after|before)\s+(\d{4}-\d{2}-\d{2})", re.I)
_BORN_AFTER = re.compile(r"born\s+(?:after|since)\s+(?:the\s+)?(?:year\s+)?(\d{4})\b(?!-)", re.I)
_BORN_BEFORE = re.compile(
    r"born\s+(?:before|prior\s+to|earlier\s+than)\s+(?:the\s+)?(?:year\s+)?(\d{4})\b(?!-)", re.I
)
_BORN_IN = re.compile(r"born\s+in\s+(?:the\s+)?(?:year\s+)?(\d{4})\b", re.I)


@dataclass
class QueryPlan:
    intent: Literal["count", "list", "unknown"]
    filters: StudentFilters = field(default_factory=StudentFilters)


def _valid_year(year: int) -> bool:
    return 1900 <= year <= 2100


def _parse_dob(question: str, filters: StudentFilters) -> None:
    if m := _BORN_FULL.search(question):
        try:
            parsed = date.fromisoformat(m.group(2))
        except ValueError:
            return
        if m.group(1).lower() == "after":
            filters.dob_after = parsed
        else:
            filters.dob_before = parsed
        return
    if (m := _BORN_AFTER.search(question)) and _valid_year(int(m.group(1))):
        filters.dob_after = date(int(m.group(1)), 12, 31)  # "after 2005" => from 2006 on
    if (m := _BORN_BEFORE.search(question)) and _valid_year(int(m.group(1))):
        filters.dob_before = date(int(m.group(1)), 1, 1)
    if (m := _BORN_IN.search(question)) and _valid_year(int(m.group(1))):
        year = int(m.group(1))
        filters.dob_after = date(year - 1, 12, 31)
        filters.dob_before = date(year + 1, 1, 1)


def parse_question(question: str, known_courses: list[str]) -> QueryPlan:
    text = " ".join(question.split())
    lowered = text.lower()
    filters = StudentFilters()

    for course in sorted(known_courses, key=len, reverse=True):
        if re.search(rf"\b{re.escape(course.lower())}\b", lowered):
            filters.course = course
            break
    if filters.course is None and (m := _COURSE_FALLBACK.search(text)):
        # A course the database doesn't know about: filter on it anyway (=> 0 matches)
        # instead of silently answering about *all* students.
        filters.course = m.group(1).strip()[:100] or None

    if m := _NAME.search(text):
        filters.name = next(g for g in m.groups() if g).strip()
    if m := _STUDENT_ID.search(text):
        filters.student_id = m.group(1)
    _parse_dob(text, filters)

    # Ambiguity guard: the question refers to a concept we could not turn into a filter.
    if re.search(r"\b(born|birth|birthday)\b", lowered) and not (filters.dob_after or filters.dob_before):
        return QueryPlan("unknown")
    if re.search(r"\b(named|called|names?)\b", lowered) and not filters.name:
        if not re.search(r"\blist\b.*\bnames\b|\bnames of\b", lowered):
            return QueryPlan("unknown")

    has_filter = any(vars(filters).values())
    mentions_students = bool(re.search(r"\bstudents?\b", lowered))
    if _COUNT.search(lowered) and (mentions_students or has_filter):
        return QueryPlan("count", filters)
    if _LIST.search(lowered) and (mentions_students or has_filter):
        return QueryPlan("list", filters)
    if mentions_students and has_filter:
        return QueryPlan("list", filters)
    return QueryPlan("unknown")
