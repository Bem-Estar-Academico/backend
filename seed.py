import asyncio
import random
from datetime import datetime, timedelta, timezone
import logging

from faker import Faker
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import AsyncSessionLocal as SessionLocal
from app.models.notice import RegistrationStatus
from app.models.user import User, UserType
from app.schemas.notice import NoticeCreate
from app.schemas.student_registration import (
    StudentRegistrationCreate,
    StudentRegistrationUpdate,
)
from app.schemas.user import UserCreate
from app.services.notice_service import NoticeService
from app.services.student_registration_service import StudentRegistrationService
from app.services.user_service import UserService

# Configuração de Logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# --- Constantes ---
NUM_STUDENTS = 50
NUM_NOTICES = 10
MAX_REGISTRATIONS_PER_NOTICE = 30
MIN_REGISTRATIONS_PER_NOTICE = 15


class DataProvider:
    """Fornece dados de teste gerados pelo Faker."""

    def __init__(self):
        self.fake = Faker("pt_BR")

    def get_user(self, user_type: UserType) -> UserCreate:
        """Gera um novo usuário com dados aleatórios."""
        email = (
            f"coordinator.seed.{self.fake.unique.user_name()}@example.com"
            if user_type == UserType.COORDINATOR
            else self.fake.unique.email()
        )
        full_name = self.fake.name()
        return UserCreate(
            email=email,
            full_name=full_name,
            user_type=user_type,
            password="password123",
            student_registration=(
                self.fake.unique.numerify(text="202#####")
                if user_type == UserType.STUDENT
                else None
            ),
            cpf=self.fake.unique.cpf() if user_type == UserType.STUDENT else None,
        )

    def get_notice(self) -> NoticeCreate:
        """Gera um novo edital com dados aleatórios."""
        start_date = datetime.now() + timedelta(
            days=random.randint(-10, 10)
        )
        return NoticeCreate(
            title=f"Edital de Cadastramento Socioeconômico {self.fake.year()}",
            notice_number=f"{random.randint(1, 100)}/{start_date.year}",
            year=start_date.year,
            registration_start_date=start_date,
            registration_end_date=start_date + timedelta(days=random.randint(15, 45)),
            responsible_agency="Universidade Federal de Exemplo",
            description=self.fake.paragraph(nb_sentences=5),
            food_allowance=random.choice([True, False]),
            housing_allowance=random.choice([True, False]),
            daycare_allowance=random.choice([True, False]),
            graduation_scholarship=random.choice([True, False]),
        )

    def get_registration(self, notice_id: int) -> StudentRegistrationCreate:
        """Gera uma nova inscrição em edital."""
        return StudentRegistrationCreate(notice_id=notice_id, answer=self.fake.sentence())


class Seeder:
    """Orquestra o processo de popular o banco de dados."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.provider = DataProvider()
        self.coordinator: User | None = None
        self.student_ids: list[int] = []

    async def clean_database(self):
        """Limpa as tabelas relevantes do banco de dados."""
        logging.info("Limpando o banco de dados...")
        tables_to_truncate = [
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

            await self.db.execute(text("DELETE FROM users WHERE user_type = 'STUDENT';"))
            logging.info("  - Usuários do tipo 'STUDENT' deletados.")

            await self.db.commit()
            logging.info("Limpeza do banco de dados concluída com sucesso.")
        except Exception as e:
            logging.error(f"Erro durante a limpeza do banco de dados: {e}")
            await self.db.rollback()
            raise

    async def _get_or_create_coordinator(self) -> User:
        """Obtém ou cria o usuário coordenador."""
        logging.info("Verificando/criando usuário coordenador...")
        coordinator_email = "coordinator.seed@example.com"
        user = await UserService.get_user_by_email(self.db, coordinator_email)
        if user:
            logging.info(f"Coordenador já existe: {user.full_name} (ID: {user.id})")
            return user

        user_data = self.provider.get_user(UserType.COORDINATOR)
        user_data.email = coordinator_email # Garante o e-mail padrão
        user = await UserService.create_user(self.db, user_data)
        logging.info(f"Coordenador criado: {user.full_name} (ID: {user.id})")
        return user

    async def seed_students(self, num_students: int):
        """Cria um número especificado de estudantes."""
        logging.info(f"Criando {num_students} estudantes...")
        created_count = 0
        for i in range(num_students):
            user_data = self.provider.get_user(UserType.STUDENT)
            try:
                user = await UserService.create_user(self.db, user_data)
                self.student_ids.append(user.id)
                created_count += 1
                logging.info(
                    f"  [{i+1:02d}/{num_students}] {user.full_name:<30} | {user_data.student_registration}"
                )
            except ValueError:
                logging.warning(f"E-mail/CPF/Matrícula duplicado para: {user_data.email}. Ignorando.")
            except Exception as e:
                logging.error(f"Erro ao criar estudante {user_data.email}: {e}")
        logging.info(f"Total de estudantes criados nesta execução: {created_count}")


    async def seed_notices(self, num_notices: int) -> list[User]:
        """Cria um número especificado de editais."""
        if not self.coordinator:
            raise ValueError("Coordenador não foi definido.")

        logging.info(f"Criando {num_notices} editais...")
        notices = []
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

    async def seed_registrations(self, notices: list[User]):
        """Cria inscrições para os editais fornecidos."""
        if not self.coordinator:
            raise ValueError("Coordenador não foi definido.")

        logging.info("Criando inscrições de estudantes com status variados...")
        total_registrations = 0
        status_counts: dict[str, int] = {}

        for notice in notices:
            num_regs = random.randint(MIN_REGISTRATIONS_PER_NOTICE, MAX_REGISTRATIONS_PER_NOTICE)
            registered_students = random.sample(self.student_ids, min(num_regs, len(self.student_ids)))

            for student_id in registered_students:
                try:
                    reg_data = self.provider.get_registration(notice.id)
                    registration = await StudentRegistrationService.create_registration(
                        self.db, reg_data, await UserService.get_user_by_id(self.db, student_id)
                    )
                    final_status = await self._randomly_update_status(registration)
                    status_counts[final_status] = status_counts.get(final_status, 0) + 1
                    total_registrations += 1
                except Exception as e:
                    logging.error(f"Falha ao criar inscrição (student_id={student_id}, notice_id={notice.id}): {e}")

            logging.info(f"  - Edital {notice.notice_number:<10}: {len(registered_students)} inscrições criadas.")

        logging.info(f"\nTotal de inscrições criadas: {total_registrations}")
        logging.info("Distribuição de status:")
        for status, count in sorted(status_counts.items()):
            logging.info(f"  - {status:<10}: {count}")


    async def _randomly_update_status(self, registration) -> str:
        """Decide aleatoriamente se atualiza o status de uma inscrição."""
        if not self.coordinator:
            raise ValueError("Coordenador não foi definido.")

        if random.random() < 0.8:  # 80% de chance de atualizar
            possible_statuses = [RegistrationStatus.APPROVED, RegistrationStatus.REJECTED]
            if random.random() < 0.2: # 20% de chance de ser cancelado (dentro dos 80%)
                possible_statuses.append(RegistrationStatus.CANCELLED)

            new_status = random.choice(possible_statuses)
            student = await UserService.get_user_by_id(self.db, registration.student_id)
            updater = student if new_status == RegistrationStatus.CANCELLED else self.coordinator

            await StudentRegistrationService.update_registration(
                self.db,
                registration_id=registration.id,
                registration_data=StudentRegistrationUpdate(status=new_status),
                current_user=updater,
            )
            return new_status.name
        return registration.status.name


    async def run(self):
        """Executa todo o processo de seeding."""
        logging.info("=" * 60)
        logging.info("INICIANDO SEED DO BANCO DE DADOS")
        logging.info("=" * 60)

        try:
            await self.clean_database()
            self.coordinator = await self._get_or_create_coordinator()
            await self.seed_students(NUM_STUDENTS)

            if len(self.student_ids) < MIN_REGISTRATIONS_PER_NOTICE:
                logging.warning(f"Número de estudantes ({len(self.student_ids)}) é menor que o mínimo por edital ({MIN_REGISTRATIONS_PER_NOTICE}).")
                # Poderia criar mais estudantes aqui se a regra de negócio exigisse

            notices = await self.seed_notices(NUM_NOTICES)
            if notices:
                await self.seed_registrations(notices)

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
    """Ponto de entrada principal para o script de seed."""
    async with SessionLocal() as db:
        seeder = Seeder(db)
        await seeder.run()


if __name__ == "__main__":
    asyncio.run(main())