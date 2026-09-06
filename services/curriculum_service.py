"""Curriculum thin wrapper (kept separate per spec)."""
from .skill_gap_service import course_alignment


def analyze_course(course_id):
    return course_alignment(course_id)
