"""
Authentication router for user login, registration, and token management.
"""

from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.user import User
from app.schemas.user import Token
from app.schemas.user import User as UserSchema
from app.schemas.user import UserCreate
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
) -> User:
    """
    Dependency to get the current authenticated user from the OAuth2 token.

    Raises:
        HTTPException: If credentials are invalid or the user is not found.

    Returns:
        User: The authenticated user object.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    user = await AuthService.get_current_user_from_token(db, token)
    if user is None:
        raise credentials_exception
    return user


@router.post(
    "/register", response_model=UserSchema, status_code=status.HTTP_201_CREATED
)
async def register_user(
    user_data: UserCreate, db: AsyncSession = Depends(get_db)
) -> UserSchema:
    """
    Registers a new user in the system.

    Args:
        user_data (UserCreate): The user data for registration.
        db (AsyncSession): The database session.

    Raises:
        HTTPException: If a user with the provided email already exists or other validation errors occur.

    Returns:
        UserSchema: The newly created user's information.
    """
    try:
        user = await AuthService.register_user(db, user_data)
        return user
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/login", response_model=Token)
async def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)
) -> Token:
    """
    Authenticates a user and returns an access token.

    Args:
        form_data (OAuth2PasswordRequestForm): The login credentials (username and password).
        db (AsyncSession): The database session.

    Raises:
        HTTPException: If authentication fails due to incorrect credentials.

    Returns:
        Token: An access token and token type.
    """
    user = await AuthService.authenticate_user(
        db, form_data.username, form_data.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = AuthService.create_access_token_for_user(user)
    return Token(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=UserSchema)
async def get_current_user_info(current_user: User = Depends(get_current_user)) -> UserSchema:
    """
    Retrieves information about the currently authenticated user.

    Args:
        current_user (User): The authenticated user object, obtained from the dependency.

    Returns:
        UserSchema: The current user's information.
    """
    return current_user


@router.get("/verify-token")
async def verify_token(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Verifies the validity of the provided authentication token.

    Args:
        current_user (User): The authenticated user object, obtained from the dependency.

    Returns:
        Dict[str, Any]: A dictionary indicating the token is valid and the user's ID.
    """
    return {"message": "Token is valid", "user_id": current_user.id}
