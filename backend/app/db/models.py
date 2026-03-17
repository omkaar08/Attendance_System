from __future__ import annotations

import enum
from datetime import date, datetime
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, Numeric, SmallInteger, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

USERS_FK = "users.id"
DEPARTMENTS_FK = "departments.id"
SET_NULL = "SET NULL"
RESTRICT = "RESTRICT"
CASCADE = "CASCADE"


class AppRole(str, enum.Enum):
    ADMIN = "admin"
    HOD = "hod"
    FACULTY = "faculty"


class AttendanceStatus(str, enum.Enum):
    PRESENT = "present"
    LATE = "late"
    ABSENT = "absent"
    EXCUSED = "excused"


class FaceSampleSource(str, enum.Enum):
    CAMERA = "camera"
    UPLOAD = "upload"
    IMPORTED = "imported"


class FaceEmbeddingStatus(str, enum.Enum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    REJECTED = "rejected"


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hod_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey(USERS_FK, ondelete=SET_NULL), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    role: Mapped[AppRole] = mapped_column(Enum(AppRole, name="app_role", values_callable=lambda enum_cls: [item.value for item in enum_cls]), nullable=False)
    department_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey(DEPARTMENTS_FK, ondelete=SET_NULL))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Faculty(Base):
    __tablename__ = "faculty"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey(USERS_FK, ondelete=CASCADE), unique=True, nullable=False)
    department_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey(DEPARTMENTS_FK, ondelete=RESTRICT), nullable=False)
    employee_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    designation: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user: Mapped[User] = relationship(lazy="joined")


class Subject(Base):
    __tablename__ = "subjects"
    __table_args__ = (UniqueConstraint("department_id", "code", "semester", "section"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    department_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey(DEPARTMENTS_FK, ondelete=RESTRICT), nullable=False)
    faculty_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("faculty.id", ondelete=RESTRICT), nullable=False)
    semester: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    section: Mapped[str] = mapped_column(String(20), nullable=False)
    attendance_grace_minutes: Mapped[int] = mapped_column(Integer, default=15, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    faculty: Mapped[Faculty] = relationship(lazy="joined")


class Student(Base):
    __tablename__ = "students"
    __table_args__ = (
        UniqueConstraint("department_id", "roll_number"),
        UniqueConstraint("email"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    roll_number: Mapped[str] = mapped_column(String(50), nullable=False)
    department_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey(DEPARTMENTS_FK, ondelete=RESTRICT), nullable=False)
    semester: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    section: Mapped[str] = mapped_column(String(20), nullable=False)
    batch_year: Mapped[int] = mapped_column(Integer, nullable=False)
    email: Mapped[str | None] = mapped_column(String(255))
    image_url: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    created_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey(USERS_FK, ondelete=SET_NULL))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class FaceEmbedding(Base):
    __tablename__ = "face_embeddings"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    student_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("students.id", ondelete=CASCADE), nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(512), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), default="arcface", nullable=False)
    model_version: Mapped[str] = mapped_column(String(100), nullable=False)
    sample_source: Mapped[FaceSampleSource] = mapped_column(Enum(FaceSampleSource, name="face_sample_source", values_callable=lambda enum_cls: [item.value for item in enum_cls]), nullable=False)
    storage_path: Mapped[str | None] = mapped_column(Text)
    quality_score: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    landmarks: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[FaceEmbeddingStatus] = mapped_column(Enum(FaceEmbeddingStatus, name="face_embedding_status", values_callable=lambda enum_cls: [item.value for item in enum_cls]), default=FaceEmbeddingStatus.ACTIVE, nullable=False)
    created_by: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey(USERS_FK, ondelete=SET_NULL))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Attendance(Base):
    __tablename__ = "attendance"
    __table_args__ = (UniqueConstraint("student_id", "subject_id", "class_date", "session_key"),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    student_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("students.id", ondelete=RESTRICT), nullable=False)
    subject_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("subjects.id", ondelete=RESTRICT), nullable=False)
    faculty_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("faculty.id", ondelete=RESTRICT), nullable=False)
    marked_by_user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey(USERS_FK, ondelete=RESTRICT), nullable=False)
    class_date: Mapped[date] = mapped_column(Date, nullable=False)
    session_key: Mapped[str] = mapped_column(String(80), nullable=False)
    session_label: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[AttendanceStatus] = mapped_column(Enum(AttendanceStatus, name="attendance_status", values_callable=lambda enum_cls: [item.value for item in enum_cls]), default=AttendanceStatus.PRESENT, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    recognition_metadata: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    student: Mapped[Student] = relationship(lazy="joined")
    subject: Mapped[Subject] = relationship(lazy="joined")