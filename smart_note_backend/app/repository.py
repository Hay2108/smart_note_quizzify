from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert

from app.database import Document, Flashcard, Quiz, User, generate_uuid, utc_now
from app.errors import APIError
from app.schemas import DocumentOutput, FlashcardOutput, QuizOutput, StudyContent, UploadResponse

# Stable local profile: supports the no-login local MVP without nullable ownership.
LOCAL_USER_ID = "00000000-0000-4000-8000-000000000001"


def check_user(session_factory, user_id: UUID | None):
    if user_id is not None:
        with session_factory() as session:
            if session.scalar(select(1).where(User.user_id == str(user_id))) is None:
                raise APIError(404, "USER_NOT_FOUND", "Không tìm thấy người dùng đã chỉ định.")


def save_study_material(session_factory, filename: str, text: str, content: StudyContent,
                        user_id: UUID | None) -> UploadResponse:
    """One transaction: user (if local), document, flashcards, quizzes or nothing."""
    owner = str(user_id) if user_id is not None else LOCAL_USER_ID
    doc_id = generate_uuid()
    cards = [
        FlashcardOutput(card_id=generate_uuid(), front_text=card.front_text, back_text=card.back_text)
        for card in content.flashcards
    ]
    quizzes = [
        QuizOutput(
            quiz_id=generate_uuid(),
            question=quiz.question,
            options=quiz.options,
            correct_answer=quiz.correct_answer,
        )
        for quiz in content.quizzes
    ]
    # Validate/construct the public response before commit, preventing post-commit schema errors.
    response = UploadResponse(data=DocumentOutput(
        doc_id=doc_id, user_id=owner, file_name=filename, extracted_text=text,
        flashcards=cards, quizzes=quizzes,
    ))
    now = utc_now()
    with session_factory.begin() as session:
        if user_id is None:
            session.execute(
                insert(User)
                .values(user_id=owner, username="local_student", created_at=now)
                .on_conflict_do_nothing(index_elements=["user_id"])
            )
        elif session.scalar(select(1).where(User.user_id == owner)) is None:
            raise APIError(404, "USER_NOT_FOUND", "Không tìm thấy người dùng đã chỉ định.")
        # Insert parent document first so foreign key constraints hold for child rows.
        session.execute(
            insert(Document),
            {
                "doc_id": doc_id,
                "user_id": owner,
                "file_name": filename,
                "extracted_text": text,
                "created_at": now,
            },
        )
        if cards:
            session.execute(
                insert(Flashcard),
                [
                    {
                        "card_id": str(card.card_id),
                        "doc_id": doc_id,
                        "front_text": card.front_text,
                        "back_text": card.back_text,
                        "created_at": now,
                    }
                    for card in cards
                ],
            )
        if quizzes:
            session.execute(
                insert(Quiz),
                [
                    {
                        "quiz_id": str(quiz.quiz_id),
                        "doc_id": doc_id,
                        "question": quiz.question,
                        "options": quiz.options,
                        "correct_answer": quiz.correct_answer,
                        "created_at": now,
                    }
                    for quiz in quizzes
                ],
            )
    return response
