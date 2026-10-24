"""Insert a small set of clearly FICTIONAL students. Safe to run repeatedly.

Usage:  python scripts/seed_database.py

It only adds records that don't exist yet (matched on student_id / email) and never
deletes or overwrites anything. It is NOT run automatically when the app starts.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings  # noqa: E402
from app.database.connection import get_session_factory, init_db  # noqa: E402
from app.schemas.student import StudentCreate  # noqa: E402
from app.services import student_service  # noqa: E402

SEED_STUDENTS = [
    ("STU1001", "Aarav Sharma", "2005-06-15", "aarav.sharma@example.com", "9876543210", "Computer Science", "Bengaluru", "2025-08-01"),
    ("STU1002", "Diya Patel", "2006-01-20", "diya.patel@example.com", "9876543211", "Computer Science", "Ahmedabad", "2025-08-01"),
    ("STU1003", "Kabir Singh", "2004-11-02", "kabir.singh@example.com", "9876543212", "Data Science", "Delhi", "2024-08-05"),
    ("STU1004", "Meera Nair", "2005-03-28", "meera.nair@example.com", "9876543213", "Electronics", "Kochi", "2024-08-05"),
    ("STU1005", "Rohan Iyer", "2003-09-09", "rohan.iyer@example.com", "9876543214", "Mechanical Engineering", "Chennai", "2023-08-07"),
    ("STU1006", "Ananya Reddy", "2006-07-14", "ananya.reddy@example.com", "9876543215", "Data Science", "Hyderabad", "2025-08-01"),
    ("STU1007", "Vihaan Gupta", "2004-05-30", "vihaan.gupta@example.com", "9876543216", "Business Administration", "Jaipur", "2024-08-05"),
    ("STU1008", "Ishita Das", "2005-12-01", "ishita.das@example.com", "9876543217", "Computer Science", "Kolkata", "2025-01-10"),
    ("STU1009", "Arjun Menon", "2007-02-18", "arjun.menon@example.com", "9876543218", "Electronics", "Thiruvananthapuram", "2025-08-01"),
    ("STU1010", "Sara Khan", "2005-08-22", None, "9876543219", "Data Science", "Lucknow", "2025-08-01"),
]


def main() -> None:
    init_db()
    print(f"Database: {get_settings().database_url}")
    added = skipped = 0
    session = get_session_factory()()
    try:
        for sid, name, dob, email, phone, course, address, enrolled in SEED_STUDENTS:
            data = StudentCreate(student_id=sid, name=name, date_of_birth=dob, email=email,
                                 phone=phone, course=course, address=address,
                                 enrollment_date=enrolled)
            try:
                student_service.create_student(session, data)
                added += 1
            except student_service.DuplicateStudentError:
                skipped += 1
    finally:
        session.close()
    print(f"Added {added} student(s), skipped {skipped} already present.")


if __name__ == "__main__":
    main()
