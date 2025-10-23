"""Router for managing student registrations for notices."""

"""
This module defines the API endpoints for creating, retrieving, updating, and deleting
student registrations for various notices. It includes functionalities for students
to manage their own registrations and for staff members (coordinators, social workers)
to view and manage registrations.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.notice import RegistrationStatus
from app.models.user import User
from app.routers.auth import get_current_user
from app.schemas.student_registration import (
    StudentRegistrationBase,
    StudentRegistrationList,
    StudentRegistrationResponse,
    StudentRegistrationUpdate,
    StudentRegistrationWithDetails,
)
from app.schemas.user import UserType
from app.services.student_registration_service import StudentRegistrationService

router = APIRouter(prefix="/student-registrations", tags=["student-registrations"])


@router.post(
    "/{notice_id}",
    response_model=StudentRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create student registration",
    description="Create a new registration for a student in a notice",
)
async def create_student_registration(
    notice_id: int,
    registration_data: StudentRegistrationBase,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StudentRegistrationResponse:
    """
    Creates a new registration for the current student in a specified notice.

    Args:
        notice_id (int): The ID of the notice to register for.
        registration_data (StudentRegistrationBase): The registration data, including answers to notice-specific questions.
        current_user (User): The authenticated student user.
        db (AsyncSession): The database session.

    Returns:
        StudentRegistrationResponse: The newly created student registration.
    """
    registration = await StudentRegistrationService.create_registration(
        notice_id, db, registration_data, current_user
    )
    return StudentRegistrationResponse.model_validate(registration)


@router.get(
    "/{registration_id}",
    response_model=StudentRegistrationWithDetails,
    summary="Get student registration",
    description="Get a specific student registration by ID with details",
)
async def get_student_registration(
    registration_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StudentRegistrationWithDetails:
    """
    Retrieves a specific student registration by its ID, including detailed information.

    Students can only view their own registrations. Staff members can view any registration.

    Args:
        registration_id (int): The ID of the registration to retrieve.
        current_user (User): The authenticated user.
        db (AsyncSession): The database session.

    Raises:
        HTTPException: If the registration is not found or the user is not authorized.

    Returns:
        StudentRegistrationWithDetails: The student registration with details.
    """
    registration = await StudentRegistrationService.get_registration_by_id(
        db, registration_id
    )

    if not registration:
        raise HTTPException(status_code=404, detail="Inscrição não encontrada")

    if (
        current_user.user_type.value == UserType.STUDENT.value
        and registration.student_id != current_user.id
        and not current_user.is_staff
    ):
        raise HTTPException(
            status_code=403, detail="Sem permissão para ver esta inscrição"
        )

    return StudentRegistrationWithDetails.from_model(registration)


@router.get(
    "/notice/{notice_id}",
    response_model=StudentRegistrationList,
    summary="Get registrations by notice",
    description="Get all registrations for a specific notice",
)
async def get_registrations_by_notice(
    notice_id: int,
    status_filter: Optional[RegistrationStatus] = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StudentRegistrationList:
    """
    Retrieves all student registrations for a specific notice.

    This endpoint is restricted to staff members.

    Args:
        notice_id (int): The ID of the notice to retrieve registrations for.
        status_filter (Optional[RegistrationStatus]): Optional. Filter registrations by their status.
        current_user (User): The authenticated staff user.
        db (AsyncSession): The database session.

    Raises:
        HTTPException: If the user is not authorized.

    Returns:
        StudentRegistrationList: A list of student registrations for the notice.
    """
    if not current_user.is_staff:
        raise HTTPException(
            status_code=403, detail="Sem permissão para ver inscrições de editais"
        )
    registrations, total = await StudentRegistrationService.get_registrations_by_notice(
        db, notice_id, status_filter
    )

    registration_details = [
        StudentRegistrationWithDetails.from_model(reg) for reg in registrations
    ]

    return StudentRegistrationList(
        registrations=registration_details,
        total=total,
    )


@router.get(
    "/student/{student_id}",
    response_model=StudentRegistrationList,
    summary="Get registrations by student",
    description="Get all registrations for a specific student",
)
async def get_registrations_by_student(
    student_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StudentRegistrationList:
    """
    Retrieves all registrations for a specific student.

    Students can only view their own registrations. Staff members can view any student's registrations.

    Args:
        student_id (int): The ID of the student to retrieve registrations for.
        current_user (User): The authenticated user.
        db (AsyncSession): The database session.

    Raises:
        HTTPException: If the user is not authorized to view the registrations.

    Returns:
        StudentRegistrationList: A list of student registrations for the specified student.
    """
    if (
        current_user.user_type.value == UserType.STUDENT.value
        and current_user.id != student_id
        and not current_user.is_staff
    ):
        raise HTTPException(
            status_code=403, detail="Sem permissão para ver inscrições de outros alunos"
        )

    registrations, total = (
        await StudentRegistrationService.get_registrations_by_student(db, student_id)
    )

    registration_details = [
        StudentRegistrationWithDetails.from_model(reg) for reg in registrations
    ]

    return StudentRegistrationList(
        registrations=registration_details,
        total=total,
    )


@router.put(
    "/{registration_id}",
    response_model=StudentRegistrationWithDetails,
    summary="Update student registration",
    description="Update a student registration (status, answer, etc.)",
)
async def update_student_registration(
    registration_id: int,
    registration_data: StudentRegistrationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StudentRegistrationWithDetails:
    """
    Updates an existing student registration.

    Students can only update their own registrations. Staff members can update any registration.

    Args:
        registration_id (int): The ID of the registration to update.
        registration_data (StudentRegistrationUpdate): The updated data for the registration.
        current_user (User): The authenticated user.
        db (AsyncSession): The database session.

    Raises:
        HTTPException: If the registration is not found or the user is not authorized.

    Returns:
        StudentRegistrationWithDetails: The updated student registration with details.
    """
    registration = await StudentRegistrationService.update_registration(
        db, registration_id, registration_data, current_user
    )
    return StudentRegistrationWithDetails.from_model(registration)


@router.delete(
    "/{registration_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete student registration",
    description="Delete a student registration",
)
async def delete_student_registration(
    registration_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Deletes a student registration by its ID.

    Students can only delete their own registrations. Staff members can delete any registration.

    Args:
        registration_id (int): The ID of the registration to delete.
        current_user (User): The authenticated user.
        db (AsyncSession): The database session.

    Raises:
        HTTPException: If the registration is not found or the user is not authorized.

    Returns:
        None
    """
    await StudentRegistrationService.delete_registration(db, registration_id, current_user)
