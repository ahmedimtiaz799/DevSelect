from datetime import datetime
from pydantic import BaseModel

class ChatResponse(BaseModel):
    id:str
    title:str
    thread_id:str|None
    created_at:datetime

class MessageResponse(BaseModel):
    id:str
    chat_id:str
    role:str
    content:str
    created_at:datetime
