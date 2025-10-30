"""Router for managing student registrations for notices."""

"""
This module defines the API endpoints for creating, retrieving, updating, and deleting
student registrations for various notices. It includes functionalities for students
to manage their own registrations and for staff members (coordinators, social workers)
to view and manage registrations.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.db.database import get_db
from app.routers.auth import get_current_user
from app.models.review import RegistrationStatus
from app.schemas.review_registration import (ReviewRegistrationCreate, ReviewRegistrationResponse, ReviewRegistrationResponseWithDetails, ReviewRegistrationUpdate)
from app.schemas.student_registration import (
    StudentRegistrationList,
    StudentRegistrationResponse,
    StudentRegistrationUpdate,
    StudentRegistrationWithDetails,
    StudentRegistrationCreate,
    StudentRegistrationWithReviewResponse,
    RegistrationListResponse,
)
from app.schemas.user import UserType
from app.services.review_registration_service import ReviewRegistrationService
from app.services.student_registration_service import StudentRegistrationService
from app.services.user_service import UserService

router = APIRouter(prefix="/student-registrations", tags=["student-registrations"])

@router.post(
    "/{notice_id}",
    response_model=StudentRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create student registration",
    description="""Cria uma nova inscrição para o estudante no edital.
    Isto também irá criar automaticamente uma avaliação (review) pendente
    e atribuí-la a um assistente social aleatório.""",
)
async def create_student_registration(
    notice_id: int,
    registration_data: StudentRegistrationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StudentRegistrationResponse:
    """
    Cria uma nova inscrição para o estudante atual em um edital específico.
    
    Este processo automaticamente dispara a criação de uma 'ReviewRegistration'
    e a atribui a um assistente social aleatório disponível.
    """
    print("Creating student registration...")
    registration = await StudentRegistrationService.create_registration(
        notice_id, db, registration_data, current_user
    )
    print("Student registration created:", registration.id)
    random_social_worker = await UserService.get_random_social_worker(db)
    print("Random social worker selected:", random_social_worker.id if random_social_worker else "None")
    if not random_social_worker:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Nenhum assistente social disponível no sistema para atribuir a avaliação."
        )

    print("Creating review registration...")
    default_review_data = ReviewRegistrationCreate(
        review={"initial_notes": "Avaliação auto-criada pelo sistema."},
        ivs=0.0,
        ocr_analisys={"initial_ocr": "OCR auto-criada pelo sistema."},
        status=RegistrationStatus.PENDING,
    )

    try:
        await ReviewRegistrationService.create_review(
            db=db,
            social_worker=random_social_worker,
            student_registration_id=registration.id,
            review_data=default_review_data
        )
        print("Review registration created for registration:", registration.id)
    except Exception as e:
        print(f"Alerta: A inscrição {registration.id} foi criada, mas a 'review' falhou: {e}")

    return StudentRegistrationResponse.model_validate(registration)


@router.get(
    "/me",
    response_model=List[StudentRegistrationWithReviewResponse],
    summary="Get my registrations with review results",
    description="Retrieves all registrations for the currently authenticated student, including the final review result for each.",
)
async def get_my_registrations_with_reviews(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[StudentRegistrationWithReviewResponse]:
    """
    Retrieves all registrations for the currently authenticated student, including details
    about the notice and the final review result.

    Args:
        current_user (User): The authenticated student user, injected by dependency.
        db (AsyncSession): The database session.

    Returns:
        List[StudentRegistrationWithReviewResponse]: A list of the student's registrations with review details.
    """
    if current_user.user_type != UserType.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only available for students.",
        )

    registrations = (
        await StudentRegistrationService.get_student_registrations_with_reviews(
            db=db, student_id=current_user.id
        )
    )
    return registrations


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
    response_model=RegistrationListResponse,
    summary="Get registrations by notice with aggregated counts",
    description="Get all registrations for a specific notice with the new JSON structure",
)
async def get_registrations_by_notice(
    notice_id: int,
    status: Optional[RegistrationStatus] = Query(None, description="Filter registrations by status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RegistrationListResponse:
    """
    Retrieves all student registrations for a specific notice, formatted
    with aggregated status counts.

    This endpoint is restricted to staff members.

    Args:
        notice_id (int): The ID of the notice to retrieve registrations for.
        status (Optional[RegistrationStatus]): Optional status to filter registrations.
        current_user (User): The authenticated staff user.
        db (AsyncSession): The database session.

    Raises:
        HTTPException: If the user is not authorized.

    Returns:
        RegistrationListResponse: A list of student registrations and status counts.
    """
    if not current_user.is_staff:
        raise HTTPException(
            status_code=403, detail="Sem permissão para ver inscrições de editais"
        )
    
    response = await StudentRegistrationService.get_registrations_for_notice_list(
        db, notice_id, status=status
    )

    return response


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