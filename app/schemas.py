from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, Any

# Auth
class RegisterIn(BaseModel):
    name: str
    email: EmailStr
    password: str

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"

# Users
class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: str
    is_active: bool
    class Config:
        from_attributes = True

# Projects
class ProjectCreate(BaseModel):
    name: str
    site_location_json: Optional[dict] = None
    currency: str = "USD"

class ProjectOut(BaseModel):
    id: int
    name: str
    site_location_json: Optional[dict] = None
    currency: str
    status: str
    class Config:
        from_attributes = True

class InputsCreate(BaseModel):
    payload_json: dict

class InputsOut(BaseModel):
    id: int
    project_id: int
    version: int
    payload_json: dict
    class Config:
        from_attributes = True

class CalcResultOut(BaseModel):
    id: int
    project_id: int
    version: int
    results_json: dict
    class Config:
        from_attributes = True
