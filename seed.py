"""Main FastAPI application."""
from dotenv import load_dotenv

from app.models.period import Period
from app.schemas.period import PeriodCreate
from app.services.period_service import PeriodService
load_dotenv()

import asyncio
import logging
import random
from datetime import datetime, timedelta, timezone
from typing import List

from faker import Faker
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import AsyncSessionLocal as SessionLocal
from app.models.notice import Notice
from app.models.registration import StudentRegistration
from app.models.review import RegistrationStatus, ReviewRegistrationModel
from app.models.user import User, UserType
from app.schemas.notice import NoticeCreate
from app.schemas.review_registration import (
    ReviewRegistrationCreate,
    ReviewRegistrationUpdate,
)
from app.schemas.student_registration import (
    StudentRegistrationCreate,
)
from app.schemas.student_registration import StudentRegistrationCreate
from app.schemas.user import UserCreate
from app.services.notice_service import NoticeService
from app.services.review_registration_service import ReviewRegistrationService
from app.services.user_service import UserService

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

NUM_STUDENTS = 50
NUM_NOTICES = 10
MAX_REGISTRATIONS_PER_NOTICE = 50
MIN_REGISTRATIONS_PER_NOTICE = 15
NUM_SOCIAL_WORKERS = 10
NUM_COORDINATORS = 10


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
        registration_end_date = datetime.now(timezone.utc) + timedelta(
            days=random.randint(45, 75)
        )
        registration_start_date = datetime.now(timezone.utc) - timedelta(
            days=random.randint(45, 75)
        )
        appeal_start_date = registration_end_date + timedelta(days=random.randint(1, 5))
        appeal_end_date = appeal_start_date + timedelta(days=random.randint(5, 10))
        preliminary_result_date = appeal_end_date + timedelta(days=random.randint(1, 3))
        final_result_date = preliminary_result_date + timedelta(
            days=random.randint(5, 10)
        )

        return NoticeCreate(
            title=f"Edital de Cadastramento Socioeconômico {self.fake.year()}",
            registration_start_date=registration_start_date,
            registration_end_date=registration_end_date,
            description=self.fake.paragraph(nb_sentences=5),
            food_allowance=random.choice([True, False]),
            housing_allowance=random.choice([True, False]),
            daycare_allowance=random.choice([True, False]),
            appeal_start_date=appeal_start_date,
            appeal_end_date=appeal_end_date,
            preliminary_result_date=preliminary_result_date,
            final_result_date=final_result_date,
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

    # def get_review(self) -> ReviewRegistrationCreate:
    #     return ReviewRegistrationCreate(
    #         review={"notes": self.fake.paragraph()},
    #         ivs=round(random.uniform(65, 175), 2),
    #         status=RegistrationStatus.PENDING,
    #         approved_food_allowance=random.choice([True, False]),
    #         approved_housing_allowance=random.choice([True, False]),
    #         approved_daycare_allowance=random.choice([True, False]),
    #         approved_graduation_scholarship=random.choice([True, False]),
    #     )


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
                text(
                    "DELETE FROM users WHERE user_type IN ('STUDENT', 'SOCIAL_WORKER', 'COORDINATOR');"
                )
            )
            logging.info(
                "  - Usuários dos tipos 'STUDENT', 'SOCIAL_WORKER' e 'COORDINATOR' deletados."
            )

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
                        f"  [{i + 1:02d}/{num_social_workers}] {user.full_name} criado."
                    )
                else:
                    logging.info(
                        f"  [{i + 1:02d}/{num_social_workers}] {user.full_name} já existe."
                    )
                self.social_workers.append(user)
            except Exception as e:
                logging.error(f"Erro ao criar assistente social {user_data.email}: {e}")
        if not self.social_workers:
            raise Exception(
                "Nenhum assistente social disponível para semear avaliações."
            )

    async def seed_coordinators(self, num_coordinators: int):
        logging.info(f"Criando {num_coordinators} coordenadores aleatórios...")
        created_count = 0
        for i in range(num_coordinators):
            user_data = self.provider.get_user(UserType.COORDINATOR)
            try:
                user = await UserService.create_user(self.db, user_data)
                created_count += 1
                logging.info(
                    f"  [{i + 1:02d}/{num_coordinators}] Coordenador aleatório criado: {user.full_name}"
                )
            except ValueError:
                logging.warning(
                    f"E-mail/CPF/Matrícula duplicado para: {user_data.email}. Ignorando."
                )
            except Exception as e:
                logging.error(
                    f"Erro ao criar coordenador aleatório {user_data.email}: {e}"
                )
        logging.info(f"Total de coordenadores aleatórios criados: {created_count}")

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
                    f"  [{i + 1:02d}/{num_students}] {user.full_name:<30} | {user_data.registration_number}"
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

                num_social_workers_per_notice = random.randint(
                    2, min(5, len(self.social_workers))
                )
                selected_social_workers = random.sample(
                    self.social_workers, num_social_workers_per_notice
                )

                for social_worker in selected_social_workers:
                    try:
                        await NoticeService.add_team_member_to_notice(
                            self.db, notice.id, social_worker.id
                        )
                    except Exception as e:
                        logging.error(
                            f"Erro ao adicionar assistente social {social_worker.id} ao edital {notice.id}: {e}"
                        )

                logging.info(
                    f"  [{i + 1:02d}/{num_notices}] {notice.title} - {num_social_workers_per_notice} assistentes sociais adicionados à equipe"
                )
            except Exception as e:
                logging.error(f"Erro ao criar edital: {e}")
        return notices

    async def seed_registrations(self, notices: list[Notice]):
        if not self.coordinator:
            raise ValueError("Coordenador não foi definido.")

        logging.info("Criando inscrições de estudantes para editais passados...")
        total_registrations = 0

        for notice in notices:
            num_regs = random.randint(
                MIN_REGISTRATIONS_PER_NOTICE,
                MAX_REGISTRATIONS_PER_NOTICE,
            )
            registered_students = random.sample(
                self.student_ids, min(num_regs, len(self.student_ids) // 2)
            )

            for student_id in registered_students:
                try:
                    existing_reg = await self.db.execute(
                        select(StudentRegistration).where(
                            StudentRegistration.student_id == student_id,
                            StudentRegistration.notice_id == notice.id,
                        )
                    )
                    if existing_reg.scalar_one_or_none():
                        continue

                    reg_data = self.provider.get_registration()
                    student = await UserService.get_user_by_id(self.db, student_id)
                    if not student:
                        continue

                    registration = StudentRegistration(
                        **reg_data.model_dump(),
                        student_id=student.id,
                        notice_id=notice.id,
                    )
                    self.db.add(registration)
                    await self.db.flush()
                    await self.db.refresh(registration)

                    total_registrations += 1
                except Exception as e:
                    logging.error(
                        f"Falha ao criar inscrição (student_id={student_id}, notice_id={notice.id}): {e}"
                    )

            logging.info(
                f"  - Edital '{notice.title}': {len(registered_students)} inscrições criadas."
            )

        logging.info(f"\nTotal de inscrições criadas: {total_registrations}")

    async def _randomly_update_status(self, review: ReviewRegistrationModel) -> str:
        if not self.coordinator:
            raise ValueError("Coordenador não foi definido.")

        if random.random() < 0.8:
            possible_statuses = [
                RegistrationStatus.APPROVED,
                RegistrationStatus.REJECTED,
            ]
            # if random.random() < 0.2:
            #     possible_statuses.append(RegistrationStatus.CANCELLED)

            new_status = random.choice(possible_statuses)
            # student = await UserService.get_user_by_id(
            #     self.db, registration.student_id
            # )
            # if not student:
            #     return registration.status.name
            # updater = (
            #     student
            #     if new_status == RegistrationStatus.CANCELLED
            #     else self.coordinator
            # )

            await ReviewRegistrationService.update_review(
                self.db,
                review_id=review.id,
                review_data=ReviewRegistrationUpdate(status=new_status),
                current_user=self.coordinator,
                seed=True
            )
            return new_status.name
        return review.status.name

    async def seed_reviews(self):
        logging.info("Criando avaliações para as inscrições...")
        result = await self.db.execute(select(StudentRegistration))
        registrations = result.scalars().all()
        review_count = 0
        status_counts: dict[str, int] = {}

        for reg in registrations:
            try:
                existing_review = await ReviewRegistrationService.get_review_by_student_registration_id(
                    self.db, reg.id
                )

                if existing_review:
                    continue

                from app.models.notice import NoticeTeam

                social_workers_in_team_result = await self.db.execute(
                    select(User)
                    .join(NoticeTeam, NoticeTeam.user_id == User.id)
                    .where(NoticeTeam.notice_id == reg.notice_id)
                    .where(User.user_type == UserType.SOCIAL_WORKER)
                )
                social_workers_in_team = list(
                    social_workers_in_team_result.scalars().all()
                )

                if not social_workers_in_team:
                    logging.warning(
                        f"Nenhum assistente social encontrado na equipe do edital {reg.notice_id} para inscrição {reg.id}"
                    )
                    continue

                default_review_data = ReviewRegistrationCreate(
                    review={"initial_notes": "Avaliação auto-criada pelo sistema."},
                    ivs=0.0,
                    ocr_analisys={"initial_ocr": "OCR auto-criada pelo sistema."},
                    status=RegistrationStatus.PENDING,
                )

                social_worker = random.choice(social_workers_in_team)

                review = await ReviewRegistrationService.create_review(
                    db=self.db,
                    social_worker=social_worker,
                    student_registration_id=reg.id,
                    review_data=default_review_data
                )
                final_status = await self._randomly_update_status(review)
                status_counts[final_status] = status_counts.get(final_status, 0) + 1
                review_count += 1
            except Exception as e:
                logging.error(
                    f"Falha ao criar avaliação para inscrição (id={reg.id}): {e}"
                )
        logging.info(f"Total de avaliações criadas: {review_count}")
        logging.info("Distribuição de status:")
        for status, count in sorted(status_counts.items()):
            logging.info(f"  - {status:<10}: {count}")

    async def run(self):
        logging.info("=" * 60)
        logging.info("INICIANDO SEED DO BANCO DE DADOS")
        logging.info("=" * 60)

        try:
            await self.clean_database()
            self.coordinator = await self._get_or_create_coordinator()
            await self.seed_coordinators(NUM_COORDINATORS)
            await self.seed_students(NUM_STUDENTS)
            await self._get_or_create_social_workers(NUM_SOCIAL_WORKERS)

            if len(self.student_ids) < MIN_REGISTRATIONS_PER_NOTICE:
                logging.warning(
                    f"Número de estudantes ({len(self.student_ids)}) é menor que o mínimo por edital ({MIN_REGISTRATIONS_PER_NOTICE})."
                )
                
            await self.seed_periods() 

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
    
    async def seed_periods(self, num_years_past=2, num_years_future=1):
        """
        Cria períodos (semestres) de forma independente.
        """
        logging.info("Populando Períodos (Semestres)...")
        current_year = datetime.now().year
        total_created = 0
        
        result = await self.db.execute(select(Period))
        self.created_periods = {p.nome: p for p in result.scalars().all()}
        logging.info(f"  - Encontrados {len(self.created_periods)} períodos existentes.")

        start_year = current_year - num_years_past
        end_year = current_year + num_years_future

        for year in range(start_year, end_year + 1):
            for semester in [1, 2]:
                period_name = f"{year}.{semester}"
                
                if period_name not in self.created_periods:
                    logging.info(f"  - Criando novo período: '{period_name}'...")
                    
                    if semester == 1:
                        start_date = datetime(year, 1, 1, tzinfo=timezone.utc)
                        end_date = datetime(year, 6, 30, 23, 59, 59, tzinfo=timezone.utc)
                    else:
                        start_date = datetime(year, 7, 1, tzinfo=timezone.utc)
                        end_date = datetime(year, 12, 31, 23, 59, 59, tzinfo=timezone.utc)

                    period_data = PeriodCreate(
                        name=period_name,
                        init_date=start_date,
                        end_date=end_date
                    )
                    
                    try:
                        new_period = await PeriodService.create_period(self.db, period=period_data)
                        self.created_periods[period_name] = new_period
                        total_created += 1
                    except Exception as e:
                        logging.error(f"Erro ao criar período {period_name}: {e}")

        logging.info(f"Total de períodos criados nesta execução: {total_created}")
        if not self.created_periods:
            raise Exception("Nenhum período disponível. O seed de editais falhará.")


async def main():
    async with SessionLocal() as db:
        seeder = Seeder(db)
        await seeder.run()


if __name__ == "__main__":
    asyncio.run(main())
