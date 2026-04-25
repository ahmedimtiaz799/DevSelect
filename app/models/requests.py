from pydantic import BaseModel,HttpUrl,field_validator

class ResumeRequest(BaseModel):
    thread_id:str
    selected_profile:HttpUrl|None=None
    @field_validator("selected_profile",mode="before")
    @classmethod
    def empty_string_to_none(cls,v):
        if v=="" or v=="null":
            return None
        return v

class UploadRequest(BaseModel):
    chat_id:str
    @field_validator("chat_id")
    @classmethod
    def chat_id_must_not_be_blank(cls,v:str)->str:
        if not v.strip():
            raise ValueError("chat_id must not be blank")
        return v.strip()
