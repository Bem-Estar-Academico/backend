import asyncio
import random
from datetime import datetime, timedelta, timezone

from faker import Faker
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import AsyncSessionLocal as SessionLocal
from app.models.user import UserType
from app.schemas.notice import NoticeCreate
from app.schemas.student_registration import StudentRegistrationCreate
from app.schemas.user import UserCreate
from app.services.notice_service import NoticeService
from app.services.student_registration_service import StudentRegistrationService
from app.services.user_service import UserService

NUM_STUDENTS = 50
NUM_NOTICES = 10
MAX_REGISTRATIONS_PER_NOTICE = 30

fake = Faker("pt_BR")
async def create_random_student(db: AsyncSession) -> dict | None:
    """Creates a random student and returns their info."""
    gender = random.choice(["M", "F"])
    full_name = fake.name_male() if gender == "M" else fake.name_female()
    
    user_data = UserCreate(
        email=fake.unique.email(),
        full_name=full_name,
        user_type=UserType.STUDENT,
        password="password123",
        student_registration=fake.unique.numerify(text="202#####"),
        cpf=fake.unique.cpf(),
    )
    try:
        user = await UserService.create_user(db, user_data)
        return {
            "id": user.id,
            "name": user.full_name,
            "email": user.email,
            "registration": user.student_registration
        }
    except ValueError as e:
        print(f"Erro ao criar estudante {user_data.email}: {e}")
        return None


async def create_random_notice(db: AsyncSession, coordinator_id: int) -> dict:
    """Creates a random notice and returns its info."""
    start_date = datetime.now(timezone.utc) + timedelta(days=random.randint(-10, 10))
    notice_number = f"{random.randint(1, 100)}/{start_date.year}"
    
    notice_data = NoticeCreate(
        title=f"Edital de Cadastramento Socioeconômico {random.randint(2010, 2060)}.{random.randint(1, 2)}",
        notice_number=notice_number,
        year=start_date.year,
        registration_start_date=start_date,
        registration_end_date=start_date + timedelta(days=random.randint(15, 45)),
        responsible_agency="Universidade Federal de Exemplo",
        description=fake.paragraph(nb_sentences=5),
        food_allowance=random.choice([True, False]),
        housing_allowance=random.choice([True, False]),
        daycare_allowance=random.choice([True, False]),
        graduation_scholarship=random.choice([True, False]),
    )
    notice = await NoticeService.create_notice(db, notice_data, coordinator_id)
    return {
        "id": notice.id,
        "title": notice.title,
        "notice_number": notice_number
    }


async def create_random_registration(
    db: AsyncSession, notice_id: int, student_id: int
) -> bool:
    """Creates a random registration for a student in a notice."""
    student = await UserService.get_user_by_id(db, student_id)
    if not student:
        return False

    registration_data = StudentRegistrationCreate(
        notice_id=notice_id, notes=fake.sentence()
    )
    try:
        await StudentRegistrationService.create_registration(db, registration_data, student)
        return True
    except Exception:
        return False


async def main():
    """Main function to seed the database."""
    print("=" * 60)
    print("🌱 INICIANDO SEED DO BANCO DE DADOS")
    print("=" * 60)
    
    db: AsyncSession = SessionLocal()

    try:
        print("\nCriando usuário coordenador...")
        coordinator_data = UserCreate(
            email="coordinator.seed@example.com",
            full_name="Coordenador do Sistema",
            user_type=UserType.COORDINATOR,
            password="password123",
        )
        try:
            coordinator = await UserService.create_user(db, coordinator_data)
            print(f"Coordenador criado: {coordinator.full_name} (ID: {coordinator.id})")
        except ValueError:
            coordinator = await UserService.get_user_by_email(
                db, coordinator_data.email
            )
            print(f"Coordenador já existe: {coordinator.full_name} (ID: {coordinator.id})")
        print(f"\nCriando {NUM_STUDENTS} estudantes...")
        students_created = []
        for i in range(NUM_STUDENTS):
            student_info = await create_random_student(db)
            if student_info:
                students_created.append(student_info)
                print(f"[{i+1:02d}/{NUM_STUDENTS}] {student_info['name']:<30} | {student_info['registration']}")
        students = await UserService.get_users(db, limit=NUM_STUDENTS * 2, user_type=UserType.STUDENT)
        student_ids = [student.id for student in students]
        print(f"\nTotal de estudantes no banco: {len(student_ids)}")

        print(f"\nCriando {NUM_NOTICES} editais...")
        notice_ids = []
        for i in range(NUM_NOTICES):
            notice_info = await create_random_notice(db, coordinator.id)
            notice_ids.append(notice_info)
            print(f"[{i+1:02d}/{NUM_NOTICES}] {notice_info['title']}")

        print("\nCriando inscrições de estudantes...")
        total_registrations = 0
        for notice_info in notice_ids:
            num_registrations = random.randint(1, MAX_REGISTRATIONS_PER_NOTICE)
            selected_student_ids = random.sample(student_ids, min(num_registrations, len(student_ids)))

            registrations_count = 0
            for student_id in selected_student_ids:
                if await create_random_registration(db, notice_info["id"], student_id):
                    registrations_count += 1
            
            total_registrations += registrations_count
            print(f"Edital {notice_info['notice_number']}: {registrations_count} inscrições")
        
        print(f"\nTotal de inscrições criadas: {total_registrations}")

    finally:
        await db.close()

    print("\n" + "=" * 60)
    print("SEED FINALIZADO COM SUCESSO!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())