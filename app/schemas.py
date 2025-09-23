from pydantic import BaseModel, EmailStr, field_validator, model_validator
from typing import Optional, Literal


class PaymentInfo(BaseModel):
    method: Literal["visa", "mobile_money"]
    card_number: Optional[str] = None
    phone_number: Optional[str] = None

    @field_validator("card_number", mode="before")
    @classmethod
    def strip_card(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        return value.replace(" ", "")

    @field_validator("phone_number", mode="before")
    @classmethod
    def strip_phone(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        return value.strip()

    @model_validator(mode="after")
    def validate_details(self) -> "PaymentInfo":
        if self.method == "visa":
            if not self.card_number or len(self.card_number) < 4 or not self.card_number.isdigit():
                raise ValueError("visa payments require a numeric card number")
        elif self.method == "mobile_money":
            if not self.phone_number or len(self.phone_number) < 6:
                raise ValueError("mobile money payments require a phone number")
        return self

# Auth
class RegisterIn(BaseModel):
    name: str
    email: EmailStr
    password: str
    payment: PaymentInfo

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    is_active: bool

# Users
class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: str
    is_active: bool
    class Config:
        from_attributes = True


class PaymentMethodOut(BaseModel):
    id: int
    method_type: str
    details_json: dict
    class Config:
        from_attributes = True


class PaymentCheckoutIn(BaseModel):
    provider: Literal["stripe", "mobile"]

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


class VisualizationCreate(BaseModel):
    chart_type: str
    config_json: dict


class VisualizationOut(BaseModel):
    id: int
    project_id: int
    chart_type: str
    config_json: dict

    class Config:
        from_attributes = True


class ReportRequest(BaseModel):
    format: Literal["pdf"] = "pdf"
    deliver_to: dict


class ReportOut(BaseModel):
    id: int
    project_id: int
    format: str
    deliver_to_json: dict
    status: str

    class Config:
        from_attributes = True


class SocialLinkCreate(BaseModel):
    platform: str
    handle: str


class SocialLinkOut(BaseModel):
    id: int
    platform: str
    handle: str

    class Config:
        from_attributes = True


class NotificationCreate(BaseModel):
    title: str
    message: str
    delivery_channel: str = "push"
    schedule_json: Optional[dict] = None


class NotificationOut(BaseModel):
    id: int
    title: str
    message: str
    delivery_channel: str
    status: str
    schedule_json: Optional[dict]

    class Config:
        from_attributes = True


class DashboardCreate(BaseModel):
    name: str
    preference: str
    layout_json: dict


class DashboardOut(BaseModel):
    id: int
    name: str
    preference: str
    layout_json: dict

    class Config:
        from_attributes = True
