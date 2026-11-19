from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20000)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class OCRResult(StrictModel):
    # Empty text is permitted in the provider schema, then handled as a 422.
    extracted_text: str = Field(max_length=200000)


class FlashcardInput(StrictModel):
    front_text: Text
    back_text: Text


class QuizInput(StrictModel):
    question: Text
    options: list[Text] = Field(min_length=4, max_length=4)
    correct_answer: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]

    @model_validator(mode="after")
    def validate_answer(self):
        if len({option.casefold() for option in self.options}) != 4:
            raise ValueError("Quiz options must be distinct")
        if self.correct_answer not in self.options:
            raise ValueError("correct_answer must exactly match one option")
        return self


class StudyContent(StrictModel):
    flashcards: list[FlashcardInput] = Field(min_length=1, max_length=20)
    quizzes: list[QuizInput] = Field(min_length=1, max_length=20)


class UnifiedStudyOutput(StrictModel):
    # Empty text/lists are permitted in provider schema, then validated as 422 NO_TEXT_DETECTED or 502 AI_COUNT_MISMATCH.
    extracted_text: str = Field(max_length=200000)
    flashcards: list[FlashcardInput] = Field(max_length=20)
    quizzes: list[QuizInput] = Field(max_length=20)


class FlashcardOutput(BaseModel):
    card_id: UUID
    front_text: str
    back_text: str


class QuizOutput(BaseModel):
    quiz_id: UUID
    question: str
    options: list[str]
    correct_answer: str


class DocumentOutput(BaseModel):
    doc_id: UUID
    user_id: UUID
    file_name: str
    extracted_text: str
    flashcards: list[FlashcardOutput]
    quizzes: list[QuizOutput]


class UploadResponse(BaseModel):
    status: Literal["success"] = "success"
    data: DocumentOutput


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    status: Literal["error"] = "error"
    error: ErrorDetail
