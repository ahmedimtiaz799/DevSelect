from pydantic import BaseModel, HttpUrl, field_validator

from app.config import settings


USER_INPUT_TOO_LONG_MESSAGE = f"Message is too long. Please keep it under {settings.MAX_USER_INPUT_CHARS} characters."


class ResumeRequest(BaseModel):
    thread_id: str
    selected_profile: HttpUrl | None = None

    @field_validator("selected_profile", mode="before")
    @classmethod
    def empty_string_to_none(cls, v):
        if v == "" or v == "null":
            return None
        return v


class FollowUpRequest(BaseModel):
    question: str

    @field_validator("question", mode="before")
    @classmethod
    def normalize_question(cls, v):
        value = str(v or "").strip()
        if len(value) > settings.MAX_USER_INPUT_CHARS:
            raise ValueError(USER_INPUT_TOO_LONG_MESSAGE)
        return value
