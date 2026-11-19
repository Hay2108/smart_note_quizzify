"""SQLAlchemy models compatible with the supplied database.py and smart_note.db.

Table and column names are deliberately unchanged. create_all adds missing tables;
it does NOT migrate existing columns or delete any data.
"""
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text, create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


def generate_uuid():
    return str(uuid4())


def utc_now():
    # Existing SQLite schema stores naive timestamps; values are always UTC.
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"
    user_id = Column(String, primary_key=True, default=generate_uuid)
    username = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=utc_now)


class Document(Base):
    __tablename__ = "documents"
    doc_id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.user_id"))
    file_name = Column(String(255))
    extracted_text = Column(Text)
    created_at = Column(DateTime, default=utc_now)


class Flashcard(Base):
    __tablename__ = "flashcards"
    card_id = Column(String, primary_key=True, default=generate_uuid)
    doc_id = Column(String, ForeignKey("documents.doc_id"))
    front_text = Column(Text)
    back_text = Column(Text)
    created_at = Column(DateTime, default=utc_now)


class Quiz(Base):
    __tablename__ = "quizzes"
    quiz_id = Column(String, primary_key=True, default=generate_uuid)
    doc_id = Column(String, ForeignKey("documents.doc_id"))
    question = Column(Text)
    options = Column(JSON)
    correct_answer = Column(String(255))
    created_at = Column(DateTime, default=utc_now)


class UserProgress(Base):
    __tablename__ = "user_progress"
    progress_id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.user_id"))
    doc_id = Column(String, ForeignKey("documents.doc_id"))
    quiz_id = Column(String, ForeignKey("quizzes.quiz_id"))
    score = Column(Integer)
    completed_at = Column(DateTime, default=utc_now)


def make_database(url: str):
    engine = create_engine(url, connect_args={"check_same_thread": False, "timeout": 15})

    @event.listens_for(engine, "connect")
    def configure_sqlite(connection, _):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=15000")
        cursor.close()

    return engine, sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
