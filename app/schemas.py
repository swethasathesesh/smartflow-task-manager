from pydantic import BaseModel, EmailStr

# This is the blueprint for the data coming FROM the Sign-Up form
class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: str

# This is the blueprint for the data we send BACK (hiding the password)
class UserResponse(BaseModel):
    full_name: str
    email: EmailStr