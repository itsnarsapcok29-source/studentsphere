"""Insert DUMMY demo students (fictional names, example.com emails).

Usage: python -m scripts.seed_data          (adds missing demo rows only)
       python -m scripts.seed_data --reset  (deletes ALL students first)
"""
import sys
from datetime import date

from app.database import SessionLocal, init_db
from app.models import Student

today = date.today()
DEMO = [
    ("STU-1001", "Aarav Demo", "2004-05-17", "aarav.demo@example.com", "+91 90000 00001", "Computer Science", "2022-08-01"),
    ("STU-1002", "Diya Sample", "2005-11-02", "diya.sample@example.com", "+91 90000 00002", "Computer Science", "2023-08-01"),
    ("STU-1003", "Kabir Test", "2006-01-21", "kabir.test@example.com", "+91 90000 00003", "Mechanical Engineering", "2024-08-01"),
    ("STU-1004", "Meera Example", "2003-07-09", "meera.example@example.com", "+91 90000 00004", "Business Administration", "2021-07-15"),
    ("STU-1005", "Rohan Placeholder", "2005-03-30", "rohan.placeholder@example.com", None, "Mechanical Engineering", "2023-08-01"),
    ("STU-1006", "Isha Fictional", "2004-09-12", "isha.fictional@example.com", "+91 90000 00006", "Electronics", "2022-08-01"),
    ("STU-1007", "Vihaan Dummy", "2006-12-05", "vihaan.dummy@example.com", "+91 90000 00007", "Computer Science", today.replace(day=1).isoformat()),
    ("STU-1008", "Anaya Mock", "2002-02-14", "anaya.mock@example.com", "+91 90000 00008", "Business Administration", "2020-07-20"),
    ("STU-1009", "Reyansh Trial", "2005-06-25", "reyansh.trial@example.com", None, "Electronics", today.replace(day=2).isoformat()),
    ("STU-1010", "Saanvi Demo", "2007-04-18", "saanvi.demo@example.com", "+91 90000 00010", "Physics", "2025-08-01"),
]


def main() -> None:
    init_db()
    with SessionLocal() as db:
        if "--reset" in sys.argv:
            db.query(Student).delete()
        added = 0
        for sid, name, dob, email, phone, course, enrolled in DEMO:
            if db.query(Student).filter((Student.student_id == sid) | (Student.email == email)).first():
                continue
            db.add(Student(student_id=sid, full_name=name, date_of_birth=date.fromisoformat(dob), email=email,
                           phone=phone, course=course, enrollment_date=date.fromisoformat(enrolled),
                           address="Dummy Address, Example City"))
            added += 1
        db.commit()
    print(f"Seed complete: {added} demo student(s) added.")


if __name__ == "__main__":
    main()
