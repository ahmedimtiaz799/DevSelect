from pydantic import BaseModel, HttpUrl, field_validator


class ResumeRequest(BaseModel):
    thread_id: str
    selected_profile: HttpUrl | None = None

    @field_validator("selected_profile", mode="before")
    @classmethod
    def empty_string_to_none(cls, v):
        if v == "" or v == "null":
            return None
        return v