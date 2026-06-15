from pydantic import BaseModel, ConfigDict, Field


class ClassGroupCreate(BaseModel):
    class_code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=100)
    academic_year: str | None = Field(default=None, max_length=20)
    semester: str | None = Field(default=None, max_length=20)


class ClassGroupUpdate(ClassGroupCreate):
    status: str = Field(default="active", pattern="^(active|inactive)$")


class StudentCreate(BaseModel):
    student_code: str = Field(min_length=1, max_length=50)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: str | None = Field(default=None, max_length=255)


class StudentUpdate(StudentCreate):
    status: str = Field(default="active", pattern="^(active|inactive)$")


class EnrollmentCreate(BaseModel):
    student_id: int
    class_group_id: int


class EnrollmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    class_group_id: int
    status: str


class TeacherCreate(BaseModel):
    teacher_code: str = Field(min_length=1, max_length=50)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: str | None = Field(default=None, max_length=255)
    department: str | None = Field(default=None, max_length=100)


class TeacherUpdate(TeacherCreate):
    status: str = Field(default="active", pattern="^(active|inactive)$")


class SubjectCreate(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=500)


class SubjectUpdate(SubjectCreate):
    status: str = Field(default="active", pattern="^(active|inactive)$")


class WeeklyScheduleCreate(BaseModel):
    teacher_id: int
    subject_id: int
    class_group_id: int
    day_of_week: str = Field(min_length=1, max_length=20)
    start_time: str = Field(min_length=1, max_length=5)
    end_time: str = Field(min_length=1, max_length=5)
    room: str = Field(min_length=1, max_length=100)


class WeeklyScheduleUpdate(WeeklyScheduleCreate):
    status: str = Field(default="active", pattern="^(active|inactive)$")
