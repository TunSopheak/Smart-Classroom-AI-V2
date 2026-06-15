from sqlalchemy import and_, func
from sqlalchemy.orm import Session, joinedload

from app.models.class_group import ClassGroup
from app.models.enrollment import Enrollment
from app.models.student import Student
from app.schemas.academic import ClassGroupCreate, ClassGroupUpdate, EnrollmentCreate, StudentCreate, StudentUpdate


ACTIVE = "active"
INACTIVE = "inactive"


def clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


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
    if find_class_by_code(db, payload.class_code):
        return None, "Class code already exists. Please choose a different code."
    if find_class_by_name(db, payload.name):
        return None, "Class name already exists. Please choose a different name."

    class_group = ClassGroup(
        class_code=payload.class_code.strip(),
        name=payload.name.strip(),
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
    if find_student_by_code(db, payload.student_code):
        return None, "Student ID already exists. Please choose a different ID."
    if find_student_by_email(db, payload.email):
        return None, "Student email already exists. Please choose a different email."

    student = Student(
        student_code=payload.student_code.strip(),
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
