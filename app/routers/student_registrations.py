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

from app.models.user import User
from app.db.database import get_db
from app.routers.auth import get_current_user
from app.models.registration import RegistrationStatus
from app.schemas.review_registration import (ReviewRegistrationCreate, ReviewRegistrationResponse, ReviewRegistrationResponseWithDetails, ReviewRegistrationUpdate)
from app.schemas.student_registration import (
    StudentRegistrationBase,
    StudentRegistrationList,
    StudentRegistrationResponse,
    StudentRegistrationUpdate,
    StudentRegistrationWithDetails,
)
from app.schemas.user import UserType
from app.services.review_registration_service import ReviewRegistrationService
from app.services.student_registration_service import StudentRegistrationService

router = APIRouter(prefix="/student-registrations", tags=["student-registrations"])

@router.post(
    "/{notice_id}",
    "/{notice_id}",
    response_model=StudentRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create student registration",
    description="Create a new registration for a student in a notice",
)
async def create_student_registration(
    notice_id: int,
    registration_data: StudentRegistrationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StudentRegistrationResponse:
    """
    Creates a new registration for the current student in a specified notice.

    Args:
        notice_id (int): The ID of the notice to register for.
        registration_data (StudentRegistrationCreate): The registration data, including answers to notice-specific questions.
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
    "/{student_registration_id}",
    response_model=StudentRegistrationWithDetails,
    summary="Get student registration",
    description="Get a specific student registration by ID with details",
)
async def get_student_registration(
    student_registration_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StudentRegistrationWithDetails:
    """
    Retrieves a specific student registration by its ID, including detailed information.

    Students can only view their own registrations. Staff members can view any registration.

    Args:
        student_registration_id (int): The ID of the registration to retrieve.
        current_user (User): The authenticated user.
        db (AsyncSession): The database session.

    Raises:
        HTTPException: If the registration is not found or the user is not authorized.

    Returns:
        StudentRegistrationWithDetails: The student registration with details.
    """
    registration = await StudentRegistrationService.get_registration_by_id(
        db, student_registration_id
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
    "/{student_registration_id}",
    response_model=StudentRegistrationWithDetails,
    summary="Update student registration",
    description="Update a student registration (status, answer, etc.)",
)
async def update_student_registration(
    student_registration_id: int,
    registration_data: StudentRegistrationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StudentRegistrationWithDetails:
    """
    Updates an existing student registration.

    Students can only update their own registrations. Staff members can update any registration.

    Args:
        student_registration_id (int): The ID of the registration to update.
        registration_data (StudentRegistrationUpdate): The updated data for the registration.
        current_user (User): The authenticated user.
        db (AsyncSession): The database session.

    Raises:
        HTTPException: If the registration is not found or the user is not authorized.

    Returns:
        StudentRegistrationWithDetails: The updated student registration with details.
    """
    registration = await StudentRegistrationService.update_registration(
        db, student_registration_id, registration_data, current_user
    )
    return StudentRegistrationWithDetails.from_model(registration)


@router.delete(
    "/{student_registration_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete student registration",
    description="Delete a student registration",
)
async def delete_student_registration(
    student_registration_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Deletes a student registration by its ID.

    Students can only delete their own registrations. Staff members can delete any registration.

    Args:
        student_registration_id (int): The ID of the registration to delete.
        current_user (User): The authenticated user.
        db (AsyncSession): The database session.

    Raises:
        HTTPException: If the registration is not found or the user is not authorized.

    Returns:
        None
    """
    await StudentRegistrationService.delete_registration(db, student_registration_id, current_user)
    
    
#------------------- REVIEW REGISTRATION ------------------------

@router.post(
    "/{student_registration_id}/review",
    response_model=ReviewRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create review registration",
    description="Create a new review registration for a student in a notice",
)
async def create_review_registration(
    student_registration_id: int,
    review_data:  ReviewRegistrationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReviewRegistrationResponse:
    """
    Creates a new registration for the current student in a specified notice.

    Args:
        notice_id (int): The ID of the notice to register for.
        registration_data (StudentRegistrationCreate): The registration data, including answers to notice-specific questions.
        current_user (User): The authenticated student user.
        db (AsyncSession): The database session.

    Returns:
        ReviewRegistrationResponse: The newly created student registration.
    """
    registration = await ReviewRegistrationService.create_review(
        db, current_user, student_registration_id, review_data
    )
    return ReviewRegistrationResponse.model_validate(registration)

@router.get(
    "/{student_registration_id}/review",
    response_model=ReviewRegistrationResponseWithDetails,
    status_code=status.HTTP_200_OK,
    summary="Get review for a student registration",
    description="Get the review for a specific student registration by its ID",
)
async def get_review_registration(
    student_registration_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReviewRegistrationResponseWithDetails:
    """
    Retrieves the review for a specific student registration.

    Args:
        student_registration_id (int): The ID of the student registration.
        db (AsyncSession): The database session.
        current_user (User): The authenticated user.

    Returns:
        ReviewRegistrationResponseWithDetails: The review for the student registration.
    """
    registration = await ReviewRegistrationService.get_review_by_student_registration_id(
        db, student_registration_id
    )
    if not registration:
        raise HTTPException(status_code=404, detail="Review not found")

    is_owner = registration.student_registration.student_id == current_user.id
    is_reviewer = registration.social_worker_id == current_user.id
    is_coordinator = current_user.user_type == UserType.COORDINATOR

    if not is_owner and not is_reviewer and not is_coordinator:
        raise HTTPException(
            status_code=403, detail="Not enough permissions to view this review."
        )

    return ReviewRegistrationResponseWithDetails.from_model(registration)


@router.get(
    "/reviews/{review_id}",
    response_model=ReviewRegistrationResponseWithDetails,
    summary="Get a review by ID",
    description="Get a specific review by its ID.",
)
async def get_review_registration_by_id(
    review_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReviewRegistrationResponseWithDetails:
    """
    Retrieves a review by its ID.

    Args:
        review_id (int): The ID of the review to retrieve.
        current_user (User): The authenticated user.
        db (AsyncSession): The database session.

    Returns:
        ReviewRegistrationResponseWithDetails: The review with details.
    """
    review = await ReviewRegistrationService.get_review_by_id(db, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    is_owner = review.student_registration.student_id == current_user.id
    is_reviewer = review.social_worker_id == current_user.id
    is_coordinator = current_user.user_type == UserType.COORDINATOR

    if not is_owner and not is_reviewer and not is_coordinator:
        raise HTTPException(
            status_code=403, detail="Not enough permissions to view this review."
        )

    return ReviewRegistrationResponseWithDetails.from_model(review)


@router.put(
    "/reviews/{review_id}",
    response_model=ReviewRegistrationResponse,
    summary="Update a review",
    description="Update an existing review by its ID.",
)
async def update_review_registration(
    review_id: int,
    review_data: ReviewRegistrationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReviewRegistrationResponse:
    """
    Updates a review by its ID.

    Args:
        review_id (int): The ID of the review to update.
        review_data (ReviewRegistrationUpdate): The data to update the review with.
        current_user (User): The authenticated user.
        db (AsyncSession): The database session.

    Returns:
        ReviewRegistrationResponse: The updated review.
    """
    updated_review = await ReviewRegistrationService.update_review(
        db, review_id, review_data, current_user
    )
    if not updated_review:
        raise HTTPException(status_code=404, detail="Review not found")
    return ReviewRegistrationResponse.model_validate(updated_review)


@router.delete(
    "/reviews/{review_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a review",
    description="Delete an existing review by its ID.",
)
async def delete_review_registration(
    review_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Deletes a review by its ID.

    Args:
        review_id (int): The ID of the review to delete.
        current_user (User): The authenticated user.
        db (AsyncSession): The database session.
    """
    deleted = await ReviewRegistrationService.delete_review(db, review_id, current_user)
    if not deleted:
        raise HTTPException(status_code=404, detail="Review not found")
