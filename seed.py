import asyncio
import random
from datetime import datetime, timedelta, timezone
import logging
from typing import List

from faker import Faker
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import AsyncSessionLocal as SessionLocal
from app.models.notice import Notice
from app.models.registration import RegistrationStatus, StudentRegistration
from app.models.user import User, UserType
from app.schemas.notice import NoticeCreate
from app.schemas.review_registration import ReviewRegistrationCreate
from app.schemas.student_registration import (
    StudentRegistrationCreate,
    StudentRegistrationUpdate,
)
from app.schemas.user import UserCreate
from app.services.notice_service import NoticeService
from app.services.review_registration_service import ReviewRegistrationService
from app.services.student_registration_service import StudentRegistrationService
from app.services.user_service import UserService

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

NUM_STUDENTS = 50
NUM_NOTICES = 10
MAX_REGISTRATIONS_PER_NOTICE = 30
MIN_REGISTRATIONS_PER_NOTICE = 15
NUM_SOCIAL_WORKERS = 5


class DataProvider:
    def __init__(self):
        self.fake = Faker("pt_BR")

    def get_user(self, user_type: UserType) -> UserCreate:
        if user_type == UserType.COORDINATOR:
            email = f"coordinator.seed.{self.fake.unique.user_name()}@example.com"
        elif user_type == UserType.SOCIAL_WORKER:
            email = f"social.worker.seed.{self.fake.unique.user_name()}@example.com"
        else:
            email = self.fake.unique.email()

        return UserCreate(
            email=email,
            full_name=self.fake.name(),
            user_type=user_type,
            password="password123",
            registration_number=(
                self.fake.unique.numerify(text="202#####")
                if user_type == UserType.STUDENT
                else None
            ),
            cpf=self.fake.unique.cpf() if user_type == UserType.STUDENT else None,
        )

    def get_notice(self) -> NoticeCreate:
        start_date = datetime.now() + timedelta(days=-10)
        return NoticeCreate(
            title=f"Edital de Cadastramento Socioeconômico {self.fake.year()}",
            registration_start_date=start_date,
            registration_end_date=start_date + timedelta(days=random.randint(15, 45)),
            description=self.fake.paragraph(nb_sentences=5),
            food_allowance=random.choice([True, False]),
            housing_allowance=random.choice([True, False]),
            daycare_allowance=random.choice([True, False]),
            appeal_start_date=datetime.now(timezone.utc) + timedelta(days=1),
            appeal_end_date=datetime.now(timezone.utc) + timedelta(days=11),
            preliminary_result_date=datetime.now(timezone.utc) + timedelta(days=12),
            final_result_date=datetime.now(timezone.utc) + timedelta(days=22),
            graduation_scholarship=random.choice([True, False]),
            team_members=[],
        )

    def get_registration(self) -> StudentRegistrationCreate:
        return StudentRegistrationCreate(
            answer={
                "a": [self.fake.sentence() for _ in range(1, 6)],
                "b": self.fake.paragraph(),
            }
        )

    def get_review(self) -> ReviewRegistrationCreate:
        return ReviewRegistrationCreate(
            review={"notes": self.fake.paragraph()},
            ivs=round(random.uniform(65, 175), 2),
        )


class Seeder:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.provider = DataProvider()
        self.coordinator: User | None = None
        self.social_workers: list[User] = []
        self.student_ids: list[int] = []

    async def clean_database(self):
        logging.info("Limpando o banco de dados...")
        tables_to_truncate = [
            "review_registrations",
            "student_registrations",
            "notice_teams",
            "notice_documents",
            "notices",
        ]
        try:
            for table in tables_to_truncate:
                await self.db.execute(
                    text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE;")
                )
                logging.info(f"  - Tabela '{table}' limpa.")

            await self.db.execute(
                text("DELETE FROM users WHERE user_type IN ('STUDENT', 'SOCIAL_WORKER');")
            )
            logging.info("  - Usuários dos tipos 'STUDENT' e 'SOCIAL_WORKER' deletados.")

            await self.db.commit()
            logging.info("Limpeza do banco de dados concluída com sucesso.")
        except Exception as e:
            logging.error(f"Erro durante a limpeza do banco de dados: {e}")
            await self.db.rollback()
            raise

    async def _get_or_create_coordinator(self) -> User:
        logging.info("Verificando/criando usuário coordenador...")
        coordinator_email = "coordinator.seed@example.com"
        user = await UserService.get_user_by_email(self.db, coordinator_email)
        if user:
            logging.info(f"Coordenador já existe: {user.full_name} (ID: {user.id})")
            return user

        user_data = self.provider.get_user(UserType.COORDINATOR)
        user_data.email = coordinator_email
        user = await UserService.create_user(self.db, user_data)
        logging.info(f"Coordenador criado: {user.full_name} (ID: {user.id})")
        return user

    async def _get_or_create_social_workers(self, num_social_workers: int):
        logging.info(f"Criando {num_social_workers} assistentes sociais...")
        for i in range(num_social_workers):
            user_data = self.provider.get_user(UserType.SOCIAL_WORKER)
            try:
                user = await UserService.get_user_by_email(self.db, user_data.email)
                if not user:
                    user = await UserService.create_user(self.db, user_data)
                    logging.info(
                        f"  [{i+1:02d}/{num_social_workers}] {user.full_name} criado."
                    )
                else:
                    logging.info(
                        f"  [{i+1:02d}/{num_social_workers}] {user.full_name} já existe."
                    )
                self.social_workers.append(user)
            except Exception as e:
                logging.error(
                    f"Erro ao criar assistente social {user_data.email}: {e}"
                )
        if not self.social_workers:
            raise Exception(
                "Nenhum assistente social disponível para semear avaliações."
            )

    async def seed_students(self, num_students: int):
        logging.info(f"Criando {num_students} estudantes...")
        created_count = 0
        for i in range(num_students):
            user_data = self.provider.get_user(UserType.STUDENT)
            try:
                user = await UserService.create_user(self.db, user_data)
                self.student_ids.append(user.id)
                created_count += 1
                logging.info(
                    f"  [{i+1:02d}/{num_students}] {user.full_name:<30} | {user_data.registration_number}"
                )
            except ValueError:
                logging.warning(
                    f"E-mail/CPF/Matrícula duplicado para: {user_data.email}. Ignorando."
                )
            except Exception as e:
                logging.error(f"Erro ao criar estudante {user_data.email}: {e}")
        logging.info(f"Total de estudantes criados nesta execução: {created_count}")

    async def seed_notices(self, num_notices: int) -> list[Notice]:
        if not self.coordinator:
            raise ValueError("Coordenador não foi definido.")

        logging.info(f"Criando {num_notices} editais...")
        notices: List[Notice] = []
        for i in range(num_notices):
            notice_data = self.provider.get_notice()
            try:
                notice = await NoticeService.create_notice(
                    self.db, notice_data, self.coordinator.id
                )
                notices.append(notice)
                logging.info(f"  [{i+1:02d}/{num_notices}] {notice.title}")
            except Exception as e:
                logging.error(f"Erro ao criar edital: {e}")
        return notices

    async def seed_registrations(self, notices: list[Notice]):
        if not self.coordinator:
            raise ValueError("Coordenador não foi definido.")

        logging.info("Criando inscrições de estudantes com status variados...")
        total_registrations = 0
        status_counts: dict[str, int] = {}

        for notice in notices:
            num_regs = random.randint(
                MIN_REGISTRATIONS_PER_NOTICE,
                MAX_REGISTRATIONS_PER_NOTICE,
            )
            registered_students = random.sample(
                self.student_ids, min(num_regs, len(self.student_ids))
            )

            for student_id in registered_students:
                try:
                    reg_data = self.provider.get_registration()
                    student = await UserService.get_user_by_id(self.db, student_id)
                    if not student:
                        continue
                    registration = (
                        await StudentRegistrationService.create_registration(
                            notice_id=notice.id,
                            db=self.db,
                            registration_data=reg_data,
                            student=student,
                        )
                    )
                    final_status = await self._randomly_update_status(registration)
                    status_counts[final_status] = (
                        status_counts.get(final_status, 0) + 1
                    )
                    total_registrations += 1
                except Exception as e:
                    logging.error(
                        f"Falha ao criar inscrição (student_id={student_id}, notice_id={notice.id}): {e}"
                    )

            logging.info(f"  - Edital: {len(registered_students)} inscrições criadas.")

        logging.info(f"\nTotal de inscrições criadas: {total_registrations}")
        logging.info("Distribuição de status:")
        for status, count in sorted(status_counts.items()):
            logging.info(f"  - {status:<10}: {count}")

    async def _randomly_update_status(
        self, registration: StudentRegistration
    ) -> str:
        if not self.coordinator:
            raise ValueError("Coordenador não foi definido.")

        if random.random() < 0.8:
            possible_statuses = [
                RegistrationStatus.APPROVED,
                RegistrationStatus.REJECTED,
            ]
            if random.random() < 0.2:
                possible_statuses.append(RegistrationStatus.CANCELLED)

            new_status = random.choice(possible_statuses)
            student = await UserService.get_user_by_id(
                self.db, registration.student_id
            )
            if not student:
                return registration.status.name
            updater = (
                student
                if new_status == RegistrationStatus.CANCELLED
                else self.coordinator
            )

            await StudentRegistrationService.update_registration(
                self.db,
                registration_id=registration.id,
                registration_data=StudentRegistrationUpdate(status=new_status),
                current_user=updater,
            )
            return new_status.name
        return registration.status.name

    async def seed_reviews(self):
        logging.info("Criando avaliações para as inscrições...")
        result = await self.db.execute(select(StudentRegistration))
        registrations = result.scalars().all()
        review_count = 0
        for reg in registrations:
            if reg.status == RegistrationStatus.CANCELLED:
                continue
            try:
                existing_review = (
                    await ReviewRegistrationService.get_review_by_student_registration_id(
                        self.db, reg.id
                    )
                )
                if existing_review:
                    continue

                review_data = self.provider.get_review()
                social_worker = random.choice(self.social_workers)
                await ReviewRegistrationService.create_review(
                    self.db,
                    social_worker=social_worker,
                    student_registration_id=reg.id,
                    review_data=review_data,
                )
                review_count += 1
            except Exception as e:
                logging.error(
                    f"Falha ao criar avaliação para inscrição (id={reg.id}): {e}"
                )
        logging.info(f"Total de avaliações criadas: {review_count}")

    async def run(self):
        logging.info("=" * 60)
        logging.info("INICIANDO SEED DO BANCO DE DADOS")
        logging.info("=" * 60)

        try:
            await self.clean_database()
            self.coordinator = await self._get_or_create_coordinator()
            await self.seed_students(NUM_STUDENTS)
            await self._get_or_create_social_workers(NUM_SOCIAL_WORKERS)

            if len(self.student_ids) < MIN_REGISTRATIONS_PER_NOTICE:
                logging.warning(
                    f"Número de estudantes ({len(self.student_ids)}) é menor que o mínimo por edital ({MIN_REGISTRATIONS_PER_NOTICE})."
                )

            notices = await self.seed_notices(NUM_NOTICES)
            if notices:
                await self.seed_registrations(notices)
                await self.seed_reviews()

            await self.db.commit()
            logging.info("=" * 60)
            logging.info("SEED FINALIZADO COM SUCESSO!")
            logging.info("=" * 60)

        except Exception as e:
            logging.error(f"Ocorreu um erro crítico durante o seeding: {e}")
            await self.db.rollback()
        finally:
            await self.db.close()


async def main():
    async with SessionLocal() as db:
        seeder = Seeder(db)
        await seeder.run()


if __name__ == "__main__":
    asyncio.run(main())
