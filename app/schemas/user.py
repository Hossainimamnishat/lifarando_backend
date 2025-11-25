from pydantic import BaseModel, EmailStr
from app.models.user import UserRole

class UserOut(BaseModel):
    id: int
    email: EmailStr | None = None
    phone: str | None = None
    first_name: str
    last_name: str
    role: UserRole

    class Config:
        from_attributes = True
