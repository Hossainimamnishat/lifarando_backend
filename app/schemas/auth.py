from pydantic import BaseModel, EmailStr, field_validator

class SignupIn(BaseModel):
    email: EmailStr | None = None
    phone: str | None = None
    password: str
    first_name: str
    last_name: str
    date_of_birth: str | None = None  # ISO date

    @field_validator("email", "phone")
    @classmethod
    def at_least_one_contact(cls, v, values):
        email = v or values.data.get("email")
        phone = values.data.get("phone")
        if not email and not phone:
            raise ValueError("Provide email or phone")
        return v


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshIn(BaseModel):
    refresh_token: str
