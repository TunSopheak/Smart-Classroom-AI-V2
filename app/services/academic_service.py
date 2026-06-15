from datetime import time
import re

from sqlalchemy import and_, func
from sqlalchemy.orm import Session, joinedload

from app.models.class_group import ClassGroup
from app.models.enrollment import Enrollment
from app.models.student import Student
from app.models.subject import Subject
from app.models.teacher import Teacher
from app.models.weekly_schedule import WeeklySchedule
from app.schemas.academic import (
    ClassGroupCreate,
    ClassGroupUpdate,
    EnrollmentCreate,
    StudentCreate,
    StudentUpdate,
    SubjectCreate,
    SubjectUpdate,
    TeacherCreate,
    TeacherUpdate,
    WeeklyScheduleCreate,
    WeeklyScheduleUpdate,
)


ACTIVE = "active"
INACTIVE = "inactive"


def clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def next_code(existing_codes: list[str], prefix: str, width: int) -> str:
    pattern = re.compile(rf"^{re.escape(prefix)}(\d+)$", re.IGNORECASE)
    highest = 0
    for code in existing_codes:
        match = pattern.match(code or "")
        if match:
            highest = max(highest, int(match.group(1)))
    return f"{prefix}{highest + 1:0{width}d}"


def generate_next_student_code(db: Session) -> str:
    codes = [row[0] for row in db.query(Student.student_code).all()]
    return next_code(codes, "STU", 4)


def generate_next_teacher_code(db: Session) -> str:
    codes = [row[0] for row in db.query(Teacher.teacher_code).all()]
    return next_code(codes, "T", 3)


def department_prefix(department: str | None) -> str:
    department = clean_optional(department) or "Computer Science"
    known = {
        "computer science": "CS",
        "mathematics": "MATH",
        "math": "MATH",
        "information systems": "IS",
        "information system": "IS",
        "applied statistics": "AS",
    }
    lowered = department.lower()
    if lowered in known:
        return known[lowered]

    words = re.findall(r"[A-Za-z0-9]+", department.upper())
    if len(words) >= 2:
        return "".join(word[0] for word in words[:2])
    return (words[0][:4] if words else "CLS").upper()


def normalize_semester(semester: str | None) -> str:
    semester = clean_optional(semester) or "1"
    match = re.search(r"\d+", semester)
    return match.group(0) if match else semester.upper().removeprefix("S")


def generate_class_code(department: str | None, group_code: str | None, academic_year: str | None, semester: str | None) -> str:
    prefix = department_prefix(department)
    group = (clean_optional(group_code) or "M4").upper()
    year = clean_optional(academic_year) or "2025-2026"
    sem = normalize_semester(semester)
    return f"{prefix}-{group}-{year}-S{sem}"


def default_class_name(department: str | None, group_code: str | None, academic_year: str | None, semester: str | None) -> str:
    department = clean_optional(department) or "Computer Science"
    group = (clean_optional(group_code) or "M4").upper()
    year = clean_optional(academic_year) or "2025-2026"
    sem = normalize_semester(semester)
    return f"{department} {group} {year} Semester {sem}"


def generate_subject_code(db: Session) -> str:
    codes = [row[0] for row in db.query(Subject.code).filter(Subject.code.ilike("SUB%")).all()]
    return next_code(codes, "SUB", 4)


def list_classes(db: Session) -> list[ClassGroup]:
    return db.query(ClassGroup).order_by(ClassGroup.name.asc()).all()


def get_class(db: Session, class_id: int) -> ClassGroup | None:
    return (
        db.query(ClassGroup)
        .options(joinedload(ClassGroup.enrollments).joinedload(Enrollment.student))
        .filter(ClassGroup.id == class_id)
        .first()
    )


def find_class_by_code(db: Session, class_code: str, exclude_id: int | None = None) -> ClassGroup | None:
    query = db.query(ClassGroup).filter(func.lower(ClassGroup.class_code) == class_code.strip().lower())
    if exclude_id is not None:
        query = query.filter(ClassGroup.id != exclude_id)
    return query.first()


def find_class_by_name(db: Session, name: str, exclude_id: int | None = None) -> ClassGroup | None:
    query = db.query(ClassGroup).filter(func.lower(ClassGroup.name) == name.strip().lower())
    if exclude_id is not None:
        query = query.filter(ClassGroup.id != exclude_id)
    return query.first()


def create_class(db: Session, payload: ClassGroupCreate) -> tuple[ClassGroup | None, str | None]:
    class_code = payload.class_code.strip()
    class_name = payload.name.strip()
    if find_class_by_code(db, class_code):
        return None, "Class code already exists. Please choose a different code."
    if find_class_by_name(db, class_name):
        return None, "Class name already exists. Please choose a different name."

    class_group = ClassGroup(
        class_code=class_code,
        name=class_name,
        department=clean_optional(payload.department),
        group_code=clean_optional(payload.group_code),
        academic_year=clean_optional(payload.academic_year),
        semester=clean_optional(payload.semester),
        status=ACTIVE,
    )
    db.add(class_group)
    db.commit()
    db.refresh(class_group)
    return class_group, None


def update_class(db: Session, class_group: ClassGroup, payload: ClassGroupUpdate) -> tuple[ClassGroup | None, str | None]:
    if find_class_by_code(db, payload.class_code, exclude_id=class_group.id):
        return None, "Class code already exists. Please choose a different code."
    if find_class_by_name(db, payload.name, exclude_id=class_group.id):
        return None, "Class name already exists. Please choose a different name."

    class_group.class_code = payload.class_code.strip()
    class_group.name = payload.name.strip()
    class_group.department = clean_optional(payload.department)
    class_group.group_code = clean_optional(payload.group_code)
    class_group.academic_year = clean_optional(payload.academic_year)
    class_group.semester = clean_optional(payload.semester)
    class_group.status = payload.status
    db.commit()
    db.refresh(class_group)
    return class_group, None


def set_class_status(db: Session, class_group: ClassGroup, status: str) -> ClassGroup:
    class_group.status = status
    db.commit()
    db.refresh(class_group)
    return class_group


def active_class_members(class_group: ClassGroup) -> list[Student]:
    return [
        enrollment.student
        for enrollment in class_group.enrollments
        if enrollment.status == ACTIVE and enrollment.student is not None
    ]


def list_students(db: Session) -> list[Student]:
    return (
        db.query(Student)
        .options(joinedload(Student.enrollments).joinedload(Enrollment.class_group))
        .order_by(Student.student_code.asc())
        .all()
    )


def get_student(db: Session, student_id: int) -> Student | None:
    return (
        db.query(Student)
        .options(joinedload(Student.enrollments).joinedload(Enrollment.class_group))
        .filter(Student.id == student_id)
        .first()
    )


def find_student_by_code(db: Session, student_code: str, exclude_id: int | None = None) -> Student | None:
    query = db.query(Student).filter(func.lower(Student.student_code) == student_code.strip().lower())
    if exclude_id is not None:
        query = query.filter(Student.id != exclude_id)
    return query.first()


def find_student_by_email(db: Session, email: str | None, exclude_id: int | None = None) -> Student | None:
    email = clean_optional(email)
    if email is None:
        return None

    query = db.query(Student).filter(func.lower(Student.email) == email.lower())
    if exclude_id is not None:
        query = query.filter(Student.id != exclude_id)
    return query.first()


def create_student(db: Session, payload: StudentCreate) -> tuple[Student | None, str | None]:
    student_code = payload.student_code.strip() if payload.student_code else generate_next_student_code(db)
    if find_student_by_code(db, student_code):
        return None, "Student ID already exists. Please choose a different ID."
    if find_student_by_email(db, payload.email):
        return None, "Student email already exists. Please choose a different email."

    student = Student(
        student_code=student_code,
        first_name=payload.first_name.strip(),
        last_name=payload.last_name.strip(),
        email=clean_optional(payload.email),
        status=ACTIVE,
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    return student, None


def update_student(db: Session, student: Student, payload: StudentUpdate) -> tuple[Student | None, str | None]:
    if find_student_by_code(db, payload.student_code, exclude_id=student.id):
        return None, "Student ID already exists. Please choose a different ID."
    if find_student_by_email(db, payload.email, exclude_id=student.id):
        return None, "Student email already exists. Please choose a different email."

    student.student_code = payload.student_code.strip()
    student.first_name = payload.first_name.strip()
    student.last_name = payload.last_name.strip()
    student.email = clean_optional(payload.email)
    student.status = payload.status
    db.commit()
    db.refresh(student)
    return student, None


def set_student_status(db: Session, student: Student, status: str) -> Student:
    student.status = status
    db.commit()
    db.refresh(student)
    return student


def current_enrollment_for_student(student: Student) -> Enrollment | None:
    active = [enrollment for enrollment in student.enrollments if enrollment.status == ACTIVE]
    return max(active, key=lambda enrollment: enrollment.enrolled_at) if active else None


def get_active_enrollment(db: Session, student_id: int) -> Enrollment | None:
    return (
        db.query(Enrollment)
        .options(joinedload(Enrollment.class_group), joinedload(Enrollment.student))
        .filter(and_(Enrollment.student_id == student_id, Enrollment.status == ACTIVE))
        .first()
    )


def list_enrollments(db: Session) -> list[Enrollment]:
    return (
        db.query(Enrollment)
        .options(joinedload(Enrollment.student), joinedload(Enrollment.class_group))
        .order_by(Enrollment.enrolled_at.desc())
        .all()
    )


def create_enrollment(db: Session, payload: EnrollmentCreate) -> tuple[Enrollment | None, str | None]:
    student = db.get(Student, payload.student_id)
    class_group = db.get(ClassGroup, payload.class_group_id)

    if student is None:
        return None, "Please choose a valid student."
    if class_group is None:
        return None, "Please choose a valid class."
    if student.status != ACTIVE:
        return None, "This student is inactive. Activate the student before enrolling."
    if class_group.status != ACTIVE:
        return None, "This class is inactive. Activate the class before enrolling students."

    current = get_active_enrollment(db, student.id)
    if current is not None:
        return None, f"{student.student_code} is already actively enrolled in {current.class_group.class_code}."

    existing_pair = (
        db.query(Enrollment)
        .filter(
            Enrollment.student_id == student.id,
            Enrollment.class_group_id == class_group.id,
            Enrollment.status == ACTIVE,
        )
        .first()
    )
    if existing_pair is not None:
        return None, "This student already has an active enrollment in that class."

    enrollment = Enrollment(student_id=student.id, class_group_id=class_group.id, status=ACTIVE)
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)
    return enrollment, None


def deactivate_enrollment(db: Session, enrollment: Enrollment) -> Enrollment:
    enrollment.status = INACTIVE
    db.commit()
    db.refresh(enrollment)
    return enrollment


def list_teachers(db: Session) -> list[Teacher]:
    return db.query(Teacher).order_by(Teacher.teacher_code.asc()).all()


def get_teacher(db: Session, teacher_id: int) -> Teacher | None:
    return db.get(Teacher, teacher_id)


def find_teacher_by_code(db: Session, teacher_code: str, exclude_id: int | None = None) -> Teacher | None:
    query = db.query(Teacher).filter(func.lower(Teacher.teacher_code) == teacher_code.strip().lower())
    if exclude_id is not None:
        query = query.filter(Teacher.id != exclude_id)
    return query.first()


def find_teacher_by_email(db: Session, email: str | None, exclude_id: int | None = None) -> Teacher | None:
    email = clean_optional(email)
    if email is None:
        return None

    query = db.query(Teacher).filter(func.lower(Teacher.email) == email.lower())
    if exclude_id is not None:
        query = query.filter(Teacher.id != exclude_id)
    return query.first()


def create_teacher(db: Session, payload: TeacherCreate) -> tuple[Teacher | None, str | None]:
    teacher_code = payload.teacher_code.strip() if payload.teacher_code else generate_next_teacher_code(db)
    if find_teacher_by_code(db, teacher_code):
        return None, "Teacher code already exists. Please choose a different code."
    if find_teacher_by_email(db, payload.email):
        return None, "Teacher email already exists. Please choose a different email."

    teacher = Teacher(
        teacher_code=teacher_code,
        first_name=payload.first_name.strip(),
        last_name=payload.last_name.strip(),
        email=clean_optional(payload.email),
        department=clean_optional(payload.department),
        status=ACTIVE,
    )
    db.add(teacher)
    db.commit()
    db.refresh(teacher)
    return teacher, None


def update_teacher(db: Session, teacher: Teacher, payload: TeacherUpdate) -> tuple[Teacher | None, str | None]:
    if find_teacher_by_code(db, payload.teacher_code, exclude_id=teacher.id):
        return None, "Teacher code already exists. Please choose a different code."
    if find_teacher_by_email(db, payload.email, exclude_id=teacher.id):
        return None, "Teacher email already exists. Please choose a different email."

    teacher.teacher_code = payload.teacher_code.strip()
    teacher.first_name = payload.first_name.strip()
    teacher.last_name = payload.last_name.strip()
    teacher.email = clean_optional(payload.email)
    teacher.department = clean_optional(payload.department)
    teacher.status = payload.status
    db.commit()
    db.refresh(teacher)
    return teacher, None


def set_teacher_status(db: Session, teacher: Teacher, status: str) -> Teacher:
    teacher.status = status
    db.commit()
    db.refresh(teacher)
    return teacher


def list_subjects(db: Session) -> list[Subject]:
    return db.query(Subject).order_by(Subject.code.asc()).all()


def get_subject(db: Session, subject_id: int) -> Subject | None:
    return db.get(Subject, subject_id)


def find_subject_by_code(db: Session, code: str, exclude_id: int | None = None) -> Subject | None:
    query = db.query(Subject).filter(func.lower(Subject.code) == code.strip().lower())
    if exclude_id is not None:
        query = query.filter(Subject.id != exclude_id)
    return query.first()


def find_subject_by_name(db: Session, name: str, exclude_id: int | None = None) -> Subject | None:
    query = db.query(Subject).filter(func.lower(Subject.name) == name.strip().lower())
    if exclude_id is not None:
        query = query.filter(Subject.id != exclude_id)
    return query.first()


def create_subject(db: Session, payload: SubjectCreate) -> tuple[Subject | None, str | None]:
    code = payload.code.strip() if payload.code else generate_subject_code(db)
    if find_subject_by_code(db, code):
        return None, "Subject code already exists. Please choose a different code."
    if find_subject_by_name(db, payload.name):
        return None, "Subject name already exists. Please choose a different name."

    subject = Subject(
        code=code,
        name=payload.name.strip(),
        description=clean_optional(payload.description),
        status=ACTIVE,
    )
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return subject, None


def update_subject(db: Session, subject: Subject, payload: SubjectUpdate) -> tuple[Subject | None, str | None]:
    if find_subject_by_code(db, payload.code, exclude_id=subject.id):
        return None, "Subject code already exists. Please choose a different code."
    if find_subject_by_name(db, payload.name, exclude_id=subject.id):
        return None, "Subject name already exists. Please choose a different name."

    subject.code = payload.code.strip()
    subject.name = payload.name.strip()
    subject.description = clean_optional(payload.description)
    subject.status = payload.status
    db.commit()
    db.refresh(subject)
    return subject, None


def set_subject_status(db: Session, subject: Subject, status: str) -> Subject:
    subject.status = status
    db.commit()
    db.refresh(subject)
    return subject


def parse_schedule_time(value: str) -> time | None:
    try:
        hour, minute = value.strip().split(":")
        return time(hour=int(hour), minute=int(minute))
    except (AttributeError, TypeError, ValueError):
        return None


def list_schedules(db: Session) -> list[WeeklySchedule]:
    return (
        db.query(WeeklySchedule)
        .options(
            joinedload(WeeklySchedule.teacher),
            joinedload(WeeklySchedule.subject),
            joinedload(WeeklySchedule.class_group),
        )
        .order_by(WeeklySchedule.day_of_week.asc(), WeeklySchedule.start_time.asc())
        .all()
    )


def get_schedule(db: Session, schedule_id: int) -> WeeklySchedule | None:
    return (
        db.query(WeeklySchedule)
        .options(
            joinedload(WeeklySchedule.teacher),
            joinedload(WeeklySchedule.subject),
            joinedload(WeeklySchedule.class_group),
        )
        .filter(WeeklySchedule.id == schedule_id)
        .first()
    )


def schedule_conflict(
    db: Session,
    class_group_id: int,
    day_of_week: str,
    start_time: time,
    end_time: time,
    exclude_id: int | None = None,
) -> WeeklySchedule | None:
    query = db.query(WeeklySchedule).filter(
        WeeklySchedule.class_group_id == class_group_id,
        func.lower(WeeklySchedule.day_of_week) == day_of_week.strip().lower(),
        WeeklySchedule.status == ACTIVE,
        WeeklySchedule.start_time < end_time,
        WeeklySchedule.end_time > start_time,
    )
    if exclude_id is not None:
        query = query.filter(WeeklySchedule.id != exclude_id)
    return query.first()


def validate_schedule_payload(
    db: Session,
    payload: WeeklyScheduleCreate | WeeklyScheduleUpdate,
    exclude_id: int | None = None,
) -> tuple[time | None, time | None, str | None]:
    start = parse_schedule_time(payload.start_time)
    end = parse_schedule_time(payload.end_time)
    if start is None or end is None:
        return None, None, "Please enter a valid start and end time."
    if start >= end:
        return start, end, "Start time must be before end time."

    teacher = db.get(Teacher, payload.teacher_id)
    subject = db.get(Subject, payload.subject_id)
    class_group = db.get(ClassGroup, payload.class_group_id)
    if teacher is None:
        return start, end, "Please choose a valid teacher."
    if subject is None:
        return start, end, "Please choose a valid subject."
    if class_group is None:
        return start, end, "Please choose a valid class."
    if teacher.status != ACTIVE:
        return start, end, "This teacher is inactive. Activate the teacher before scheduling."
    if subject.status != ACTIVE:
        return start, end, "This subject is inactive. Activate the subject before scheduling."
    if class_group.status != ACTIVE:
        return start, end, "This class is inactive. Activate the class before scheduling."

    conflict = schedule_conflict(db, class_group.id, payload.day_of_week, start, end, exclude_id=exclude_id)
    if conflict is not None:
        return start, end, (
            f"{class_group.class_code} already has an active schedule on "
            f"{conflict.day_of_week} from {conflict.start_time.strftime('%H:%M')} "
            f"to {conflict.end_time.strftime('%H:%M')}."
        )

    return start, end, None


def create_schedule(db: Session, payload: WeeklyScheduleCreate) -> tuple[WeeklySchedule | None, str | None]:
    start, end, error = validate_schedule_payload(db, payload)
    if error:
        return None, error

    schedule = WeeklySchedule(
        teacher_id=payload.teacher_id,
        subject_id=payload.subject_id,
        class_group_id=payload.class_group_id,
        day_of_week=payload.day_of_week.strip(),
        start_time=start,
        end_time=end,
        room=payload.room.strip(),
        status=ACTIVE,
    )
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return schedule, None


def update_schedule(
    db: Session,
    schedule: WeeklySchedule,
    payload: WeeklyScheduleUpdate,
) -> tuple[WeeklySchedule | None, str | None]:
    start, end, error = validate_schedule_payload(db, payload, exclude_id=schedule.id)
    if error:
        return None, error

    schedule.teacher_id = payload.teacher_id
    schedule.subject_id = payload.subject_id
    schedule.class_group_id = payload.class_group_id
    schedule.day_of_week = payload.day_of_week.strip()
    schedule.start_time = start
    schedule.end_time = end
    schedule.room = payload.room.strip()
    schedule.status = payload.status
    db.commit()
    db.refresh(schedule)
    return schedule, None


def set_schedule_status(db: Session, schedule: WeeklySchedule, status: str) -> WeeklySchedule:
    schedule.status = status
    db.commit()
    db.refresh(schedule)
    return schedule
