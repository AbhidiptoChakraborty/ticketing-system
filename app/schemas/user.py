from pydantic import BaseModel, ConfigDict


class UserCreate(BaseModel):
    name: str
    username: str
    password: str
    role: str = "user"


class UserRegister(BaseModel):
    name: str
    username: str
    password: str


class UserUpdate(BaseModel):
    name: str


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    username: str
    role: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
