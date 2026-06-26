import unittest
from datetime import date, datetime, time, timedelta
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models import attendance, class_group, enrollment, session, student, subject, teacher, weekly_schedule
from app.models.attendance import Attendance
from app.models.class_group import ClassGroup
from app.models.enrollment import Enrollment
from app.models.session import Session as ClassroomSession
from app.models.student import Student
from app.models.subject import Subject
from app.models.teacher import Teacher
from app.models.weekly_schedule import WeeklySchedule
from app.services import face_attendance_service, session_service


def recognized_face(label: str = "S001_TunSopheak", confidence: float = 88.5) -> dict:
    return {
        "available": True,
        "message": "Face recognition completed.",
        "faces": [
            {
                "label": label,
                "student_code": label,
                "confidence": confidence,
                "bbox": {"x": 1, "y": 2, "width": 100, "height": 120},
                "recognized": True,
                "status": "recognized",
            }
        ],
        "unknown_face_count": 0,
    }


class FaceAttendanceServiceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.db = self.SessionLocal()
        self.seed_demo_class()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def seed_demo_class(self):
        class_group_row = ClassGroup(id=1, class_code="CN-Y3", name="CN Year 3", status="active")
        teacher_row = Teacher(id=1, teacher_code="T001", first_name="Demo", last_name="Teacher", status="active")
        subject_row = Subject(id=1, code="CN", name="Computer Networks", status="active")
        schedule_row = WeeklySchedule(
            id=1,
            teacher_id=1,
            subject_id=1,
            class_group_id=1,
            day_of_week="Friday",
            start_time=time(8, 0),
            end_time=time(10, 0),
            room="Lab",
            status="active",
        )
        student_one = Student(id=1, student_code="S001", first_name="Tun", last_name="Sopheak", status="active")
        student_two = Student(id=2, student_code="S002", first_name="Missing", last_name="Student", status="active")
        enrollment_one = Enrollment(student_id=1, class_group_id=1, status="active")
        enrollment_two = Enrollment(student_id=2, class_group_id=1, status="active")
        self.db.add_all(
            [
                class_group_row,
                teacher_row,
                subject_row,
                schedule_row,
                student_one,
                student_two,
                enrollment_one,
                enrollment_two,
            ]
        )
        self.db.commit()

    def create_active_session(self, late_time: time):
        active_session = ClassroomSession(
            id=1,
            schedule_id=1,
            weekly_schedule_id=1,
            class_group_id=1,
            teacher_id=1,
            subject_id=1,
            session_date=date.today(),
            title="Demo Session",
            start_time=time(8, 0),
            late_time=late_time,
            end_time=time(10, 0),
            room="Lab",
            status="active",
        )
        self.db.add(active_session)
        self.db.commit()
        return active_session

    def test_label_candidates_prefers_student_code_before_underscore(self):
        self.assertEqual(face_attendance_service.label_candidates("S001_TunSopheak")[0], "S001")
        self.assertEqual(face_attendance_service.label_candidates("S001__TunSopheak")[0], "S001")
        self.assertIn("S001_TunSopheak", face_attendance_service.label_candidates("S001_TunSopheak"))

    def test_recognized_before_late_time_is_present(self):
        late_time = (datetime.now() + timedelta(hours=1)).time()
        self.create_active_session(late_time)

        with patch("app.services.face_attendance_service.recognize_faces", return_value=recognized_face()):
            result = face_attendance_service.mark_face_attendance(self.db, 1, b"fake-image")

        self.assertEqual(result["unknown_face_count"], 0)
        self.assertEqual(result["attendance"][0]["student_code"], "S001")
        self.assertEqual(result["attendance"][0]["student_name"], "Tun Sopheak")
        self.assertEqual(result["attendance"][0]["status"], "present")
        self.assertFalse(result["attendance"][0]["duplicate"])
        self.assertEqual(result["attendance"][0]["method"], "face")
        self.assertIn("detected_time", result["attendance"][0])
        self.assertIn("first_seen_time", result["attendance"][0])

    def test_recognized_after_late_time_is_late(self):
        late_time = (datetime.now() - timedelta(minutes=1)).time()
        self.create_active_session(late_time)

        with patch("app.services.face_attendance_service.recognize_faces", return_value=recognized_face()):
            result = face_attendance_service.mark_face_attendance(self.db, 1, b"fake-image")

        self.assertEqual(result["attendance"][0]["status"], "late")

    def test_duplicate_recognition_is_skipped(self):
        late_time = (datetime.now() + timedelta(hours=1)).time()
        self.create_active_session(late_time)

        with patch("app.services.face_attendance_service.recognize_faces", return_value=recognized_face()):
            first = face_attendance_service.mark_face_attendance(self.db, 1, b"fake-image")
            second = face_attendance_service.mark_face_attendance(self.db, 1, b"fake-image")

        self.assertFalse(first["attendance"][0]["duplicate"])
        self.assertTrue(second["attendance"][0]["duplicate"])
        self.assertEqual(self.db.query(Attendance).count(), 1)

    def test_unknown_face_does_not_create_attendance(self):
        self.create_active_session((datetime.now() + timedelta(hours=1)).time())
        face_result = {
            "available": True,
            "message": "Face recognition completed.",
            "faces": [{"recognized": False, "label": None, "confidence": 0}],
            "unknown_face_count": 1,
        }

        with patch("app.services.face_attendance_service.recognize_faces", return_value=face_result):
            result = face_attendance_service.mark_face_attendance(self.db, 1, b"fake-image")

        self.assertEqual(result["unknown_face_count"], 1)
        self.assertEqual(result["attendance"], [])
        self.assertEqual(self.db.query(Attendance).count(), 0)

    def test_recognized_label_without_student_returns_warning(self):
        self.create_active_session((datetime.now() + timedelta(hours=1)).time())

        with patch("app.services.face_attendance_service.recognize_faces", return_value=recognized_face("S999_Unknown")):
            result = face_attendance_service.mark_face_attendance(self.db, 1, b"fake-image")

        self.assertEqual(result["unknown_face_count"], 1)
        self.assertEqual(result["attendance"], [])
        self.assertIn("Student not found in database", result["warnings"][0])

    def test_closing_session_creates_absent_for_missing_students(self):
        active_session = self.create_active_session((datetime.now() + timedelta(hours=1)).time())

        with patch("app.services.face_attendance_service.recognize_faces", return_value=recognized_face()):
            face_attendance_service.mark_face_attendance(self.db, 1, b"fake-image")

        closed, error = session_service.close_session(self.db, active_session)

        self.assertIsNone(error)
        self.assertEqual(closed.status, "closed")
        absent = self.db.query(Attendance).filter(Attendance.student_id == 2).first()
        self.assertIsNotNone(absent)
        self.assertEqual(absent.status, "absent")
        self.assertEqual(absent.method, "auto_absent")


if __name__ == "__main__":
    unittest.main()
