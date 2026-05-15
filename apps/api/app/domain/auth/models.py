from pydantic import BaseModel, Field


class UserOut(BaseModel):
    id: str
    username: str


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)
