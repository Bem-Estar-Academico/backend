import asyncio
import random
from datetime import datetime, timedelta, timezone

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

NUM_STUDENTS = 50
NUM_NOTICES = 10
MAX_REGISTRATIONS_PER_NOTICE = 30
MIN_REGISTRATIONS_PER_NOTICE = 15

fake = Faker("pt_BR")


async def clean_database(db: AsyncSession):
    """Deletes existing data from relevant tables before seeding."""
    print("\nLimpando o banco de dados...")
    try:
        await db.execute(
            text("TRUNCATE TABLE student_registrations RESTART IDENTITY CASCADE;")
        )
        print("  - Tabela 'student_registrations' limpa.")

        await db.execute(text("TRUNCATE TABLE notice_teams RESTART IDENTITY CASCADE;"))
        print("  - Tabela 'notice_teams' limpa.")

        await db.execute(
            text("TRUNCATE TABLE notice_documents RESTART IDENTITY CASCADE;")
        )
        print("  - Tabela 'notice_documents' limpa.")

        await db.execute(text("TRUNCATE TABLE notices RESTART IDENTITY CASCADE;"))
        print("  - Tabela 'notices' limpa.")
        await db.execute(text("DELETE FROM users WHERE user_type = 'STUDENT';"))
        print("  - Usuários do tipo 'STUDENT' deletados.")
        await db.commit()
        print("Limpeza concluída com sucesso.")
    except Exception as e:
        print(f"Erro durante a limpeza do banco de dados: {e}")
        await db.rollback()


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
            "registration": user_data.student_registration,
        }
    except ValueError as e:
        # usuário já existe ou outra validação — ignoramos esse registro
        return None
    except Exception as e:
        print(f"Erro criando estudante: {e}")
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
        "notice_number": notice_number,
    }


async def create_random_registration(
    db: AsyncSession, notice_id: int, student_id: int, coordinator: User
) -> tuple[bool, str]:
    """Creates a random registration and randomly updates its status."""
    student = await UserService.get_user_by_id(db, student_id)
    if not student:
        return False, "Student not found"

    registration_data = StudentRegistrationCreate(
        notice_id=notice_id, notes=fake.sentence()
    )
    try:
        registration = await StudentRegistrationService.create_registration(
            db, registration_data, student
        )
        initial_status = registration.status.name

        # simula atualizações de status
        if random.random() < 0.8:
            possible_new_statuses = [
                RegistrationStatus.APPROVED,
                RegistrationStatus.REJECTED,
            ]
            if random.random() < 0.2:
                possible_new_statuses.append(RegistrationStatus.CANCELLED)

            new_status = random.choice(possible_new_statuses)

            updater_user = (
                student
                if new_status == RegistrationStatus.CANCELLED
                else coordinator
            )

            update_data = StudentRegistrationUpdate(status=new_status)
            await StudentRegistrationService.update_registration(
                db,
                registration_id=registration.id,
                registration_data=update_data,
                current_user=updater_user,
            )
            return True, new_status.name

        return True, initial_status

    except Exception as e:
        # log útil para depuração
        # print(f"Falha ao criar/atualizar inscrição (student_id={student_id}, notice_id={notice_id}): {e}")
        return False, "Failed"


async def ensure_min_students(db: AsyncSession, student_ids: list[int], min_needed: int) -> list[int]:
    """Garante que a lista de student_ids tenha pelo menos min_needed elementos.
    Cria estudantes extras se necessário (até conseguir). Retorna a lista atualizada."""
    while len(student_ids) < min_needed:
        created = await create_random_student(db)
        if created:
            student_ids.append(created["id"])
            print(f"  - Estudante extra criado para cumprir mínimo: {created['name']} (ID {created['id']})")
        else:
            # se por algum motivo criar falhar repetidamente, tentamos novamente
            print("  - Tentativa de criar estudante extra falhou; tentando novamente...")
    return student_ids


async def main():
    """Main function to seed the database."""
    print("=" * 60)
    print("INICIANDO SEED DO BANCO DE DADOS")
    print("=" * 60)

    db: AsyncSession = SessionLocal()
    try:
        # await clean_database(db)

        print("\nCriando usuário coordenador...")
        coordinator_data = UserCreate(
            email="coordinator.seed@example.com",
            full_name="Coordenador do Sistema",
            user_type=UserType.COORDINATOR,
            password="password123",
        )
        try:
            coordinator = await UserService.create_user(db, coordinator_data)
            print(
                f"  Coordenador criado: {coordinator.full_name} (ID: {coordinator.id})"
            )
        except ValueError:
            coordinator = await UserService.get_user_by_email(
                db, coordinator_data.email
            )
            print(
                f"Coordenador já existe: {coordinator.full_name} (ID: {coordinator.id})"
            )

        print(f"\nCriando {NUM_STUDENTS} estudantes...")
        students_created_count = 0
        for i in range(NUM_STUDENTS):
            student_info = await create_random_student(db)
            if student_info:
                students_created_count += 1
                print(
                    f"  [{i+1:02d}/{NUM_STUDENTS}] {student_info['name']:<30} | {student_info['registration']}"
                )
        print(f"Total de estudantes criados nesta execução: {students_created_count}")

        students = await UserService.get_users(
            db, limit=NUM_STUDENTS * 5, user_type=UserType.STUDENT
        )
        student_ids = [student.id for student in students]
        print(f"Total de estudantes no banco agora: {len(student_ids)}")

        # Se houver menos estudantes que o mínimo necessário, criamos extras
        if len(student_ids) < MIN_REGISTRATIONS_PER_NOTICE:
            print(
                f"\nMenos estudantes do que o mínimo por edital ({len(student_ids)} < {MIN_REGISTRATIONS_PER_NOTICE}). Criando estudantes extras..."
            )
            student_ids = await ensure_min_students(db, student_ids, MIN_REGISTRATIONS_PER_NOTICE)
            print(f"Agora há {len(student_ids)} estudantes disponíveis.")

        print(f"\nCriando {NUM_NOTICES} editais...")
        notice_ids = []
        for i in range(NUM_NOTICES):
            notice_info = await create_random_notice(db, coordinator.id)
            notice_ids.append(notice_info)
            print(f"  [{i+1:02d}/{NUM_NOTICES}] {notice_info['title']}")

        print("\nCriando inscrições de estudantes com status variados (garantindo mínimo por edital)...")
        total_registrations = 0
        status_counts: dict[str, int] = {}

        for notice_info in notice_ids:
            target_num = random.randint(MIN_REGISTRATIONS_PER_NOTICE, MAX_REGISTRATIONS_PER_NOTICE)

            # garantimos ao menos MIN_REGISTRATIONS_PER_NOTICE inscrições bem-sucedidas
            registered_ids = set()  # evita duplas inscrições no mesmo edital
            registrations_in_notice_count = 0

            # copia embaralhada do pool de estudantes
            pool = student_ids.copy()
            random.shuffle(pool)
            pool_index = 0

            # função auxiliar para obter próximo candidato (cria estudante novo se acabar pool)
            async def next_candidate():
                nonlocal pool, pool_index, student_ids
                if pool_index >= len(pool):
                    # criar estudante extra e adicionar no pool
                    created = await create_random_student(db)
                    if created:
                        student_ids.append(created["id"])
                        pool.append(created["id"])
                        print(f"    + Estudante extra criado para edital {notice_info['notice_number']} (ID {created['id']})")
                    # continue; se criação falhar, a pool pode permanecer vazia -> lida pelo código chamador
                candidate = None
                # avançar até achar um candidato não registrado
                while pool_index < len(pool):
                    cand = pool[pool_index]
                    pool_index += 1
                    if cand not in registered_ids:
                        candidate = cand
                        break
                return candidate

            # Primeiro, garanta o mínimo
            while registrations_in_notice_count < MIN_REGISTRATIONS_PER_NOTICE:
                candidate = await next_candidate()
                if candidate is None:
                    # se não houver candidate (criação falhou repetidamente), tenta criar explicitamente mais estudantes
                    created = await create_random_student(db)
                    if created:
                        student_ids.append(created["id"])
                        pool.append(created["id"])
                        print(f"    + Criado estudante extra (fallback) ID {created['id']}")
                        continue
                    else:
                        # situação improvável: continua tentando, mas prevenimos loop infinito com pequeno sleep
                        print("    ! Não foi possível obter candidato para inscrição no momento; tentando novamente...")
                        await asyncio.sleep(0.1)
                        continue

                success, final_status = await create_random_registration(
                    db, notice_info["id"], candidate, coordinator
                )
                if success:
                    registered_ids.add(candidate)
                    registrations_in_notice_count += 1
                    status_counts[final_status] = status_counts.get(final_status, 0) + 1
                else:
                    # falha: apenas registra e tenta outro candidato
                    print(f"    - Falha ao criar inscrição (student_id={candidate}) para o edital {notice_info['notice_number']} — tentando próximo.")

            # Se quisermos gerar inscrições adicionais até target_num, fazemos agora
            while registrations_in_notice_count < target_num:
                candidate = await next_candidate()
                if candidate is None:
                    # tenta criar mais estudantes
                    created = await create_random_student(db)
                    if created:
                        student_ids.append(created["id"])
                        pool.append(created["id"])
                        continue
                    else:
                        await asyncio.sleep(0.05)
                        continue

                success, final_status = await create_random_registration(
                    db, notice_info["id"], candidate, coordinator
                )
                if success:
                    registered_ids.add(candidate)
                    registrations_in_notice_count += 1
                    status_counts[final_status] = status_counts.get(final_status, 0) + 1
                else:
                    # em caso de falha, seguimos tentando até completar target_num ou até não haver candidatos razoáveis
                    continue

            total_registrations += registrations_in_notice_count
            print(
                f"  Edital {notice_info['notice_number']:<10}: {registrations_in_notice_count} inscrições criadas (mínimo garantido: {MIN_REGISTRATIONS_PER_NOTICE})"
            )

        print(f"\nTotal de inscrições criadas: {total_registrations}")
        print("\nDistribuição de status:")
        for status, count in sorted(status_counts.items()):
            print(f"  - {status:<10}: {count}")

    finally:
        await db.close()

    print("\n" + "=" * 60)
    print("SEED FINALIZADO COM SUCESSO!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
