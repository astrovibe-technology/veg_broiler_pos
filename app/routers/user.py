from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from jose import jwt
from datetime import datetime, timedelta
import bcrypt

from database import get_db
from models.user import User


router = APIRouter(
    prefix="/users",
    tags=["Users"]
)


# =========================================================
# JWT SETTINGS
# =========================================================

SECRET_KEY = "your-secret-key-change-this"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


# =========================================================
# REQUEST SCHEMAS
# =========================================================

class CreateUserRequest(BaseModel):
    name: str
    username: str
    password: str
    email: EmailStr
    phone: str | None = None
    role: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# =========================================================
# CREATE ADMIN / MANAGER
# =========================================================

@router.post(
    "/create",
    status_code=status.HTTP_201_CREATED
)
def create_user(
    request: CreateUserRequest,
    db: Session = Depends(get_db)
):

    # -----------------------------------------------------
    # Validate role
    # -----------------------------------------------------

    if request.role not in ["admin", "manager"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role must be either admin or manager"
        )

    # -----------------------------------------------------
    # Check username
    # -----------------------------------------------------

    existing_username = db.query(User).filter(
        User.username == request.username
    ).first()

    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )

    # -----------------------------------------------------
    # Check email
    # -----------------------------------------------------

    existing_email = db.query(User).filter(
        User.email == request.email
    ).first()

    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists"
        )

    # -----------------------------------------------------
    # Hash password
    # -----------------------------------------------------

    password_hash = bcrypt.hashpw(
        request.password.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")

    # -----------------------------------------------------
    # Create ADMIN / MANAGER
    # -----------------------------------------------------

    user = User(
        name=request.name,
        username=request.username,
        password_hash=password_hash,
        email=request.email,
        phone=request.phone,
        role=request.role,
        shop_id=None,
        is_active=True
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    # -----------------------------------------------------
    # Response
    # -----------------------------------------------------

    return {
        "message": f"{request.role.capitalize()} created successfully",
        "user": {
            "id": user.id,
            "name": user.name,
            "username": user.username,
            "email": user.email,
            "phone": user.phone,
            "role": user.role,
            "shop_id": user.shop_id,
            "is_active": user.is_active
        }
    }


# =========================================================
# LOGIN
# =========================================================

@router.post("/login")
def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):

    # -----------------------------------------------------
    # Find user by email
    # -----------------------------------------------------

    user = db.query(User).filter(
        User.email == request.email
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # -----------------------------------------------------
    # Check active status
    # -----------------------------------------------------

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    # -----------------------------------------------------
    # Verify password
    # -----------------------------------------------------

    password_valid = bcrypt.checkpw(
        request.password.encode("utf-8"),
        user.password_hash.encode("utf-8")
    )

    if not password_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # -----------------------------------------------------
    # JWT expiration
    # -----------------------------------------------------

    expire = datetime.utcnow() + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    # -----------------------------------------------------
    # JWT payload
    # -----------------------------------------------------

    token_data = {
        "user_id": user.id,
        "email": user.email,
        "role": user.role,
        "shop_id": user.shop_id,
        "exp": expire
    }

    # -----------------------------------------------------
    # Generate token
    # -----------------------------------------------------

    access_token = jwt.encode(
        token_data,
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    # -----------------------------------------------------
    # Response
    # -----------------------------------------------------

    return {
        "message": "Login successful",
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "name": user.name,
            "username": user.username,
            "email": user.email,
            "phone": user.phone,
            "role": user.role,
            "shop_id": user.shop_id,
            "is_active": user.is_active
        }
    }

