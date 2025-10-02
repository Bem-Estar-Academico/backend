# BEA Backend - Sistema de Bem-Estar Acadêmico

API backend para o sistema de Bem-Estar Acadêmico (BEA), desenvolvida com FastAPI, SQLAlchemy e PostgreSQL.

## 🚀 Tecnologias

- **FastAPI** - Framework web moderno e rápido para APIs
- **SQLAlchemy 2.0** - ORM async para Python
- **PostgreSQL** - Banco de dados relacional
- **Alembic** - Gerenciamento de migrações de banco
- **Poetry** - Gerenciamento de dependências
- **Pydantic v2** - Validação de dados
- **JWT** - Autenticação via tokens

## 📋 Funcionalidades

- ✅ Sistema de autenticação JWT
- ✅ Gerenciamento de usuários com tipos (COORDINATOR, STUDENT, SOCIAL_WORKER, NTI)
- ✅ CRUD de editais/notices
- ✅ Autorização baseada em roles
- ✅ Documentação automática da API (Swagger/OpenAPI)
- ✅ Migrações automáticas de banco de dados

## 🏗️ Arquitetura

```text
app/
├── models/          # Modelos SQLAlchemy
├── schemas/         # Schemas Pydantic para validação
├── services/        # Camada de lógica de negócio
├── routers/         # Endpoints da API
├── core/           # Configurações e autenticação
├── db/             # Configuração do banco de dados
└── main.py         # Aplicação principal
```

## 🔧 Pré-requisitos

- Python 3.12+
- Poetry
- PostgreSQL (local ou remoto)

## 🚀 Como executar localmente

### 1. Clone o repositório

```bash
git clone <url-do-repositorio>
cd backend
```

### 2. Configure as variáveis de ambiente

```bash
cp .env.example .env
```

Edite o arquivo `.env` com suas configurações:

```env
# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/bea_db

# JWT
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Application
DEBUG=True
```

### 3. Instalar dependências

```bash
poetry install
```

### 4. Configurar banco de dados

Certifique-se de que o PostgreSQL está rodando e crie o banco de dados:

```bash
# Se usando PostgreSQL local
createdb bea_db

# Ou conecte ao PostgreSQL e execute:
# CREATE DATABASE bea_db;
```

### 5. Executar migrações

```bash
poetry run alembic upgrade head
```

### 6. Executar a aplicação

```bash
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 7. Acessar a aplicação

- **API**: <http://localhost:8000>
- **Documentação Swagger**: <http://localhost:8000/docs>
- **Documentação ReDoc**: <http://localhost:8000/redoc>

## 🗄️ Banco de Dados

### Gerenciar migrações

```bash
# Criar nova migração
poetry run alembic revision --autogenerate -m "descrição da migração"

# Aplicar migrações
poetry run alembic upgrade head

# Reverter migração
poetry run alembic downgrade -1

# Ver histórico de migrações
poetry run alembic history

# Ver migração atual
poetry run alembic current
```

### Acessar PostgreSQL

```bash
# Via linha de comando
psql -h localhost -U postgres -d bea_db

# Ou usando a URL de conexão
psql postgresql://postgres:postgres@localhost:5432/bea_db
```

## 🔐 Autenticação

O sistema usa JWT para autenticação. Para acessar endpoints protegidos:

1. Faça login via `a/pi/v1/auth/login` para obter o token
2. Inclua o token no header: `Authorization: Bearer <seu-token>`

### Tipos de usuário

- **COORDINATOR**: Pode gerenciar editais e usuários
- **STUDENT**: Acesso limitado para visualização
- **SOCIAL_WORKER**: Acesso a funcionalidades sociais
- **NTI**: Acesso técnico ao sistema

## 📝 Exemplos de uso

### Criar usuário

```bash
curl -X POST "http://localhost:8000/api/v1/users/" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "full_name": "Administrador",
    "password": "senha123",
    "user_type": "COORDINATOR"
  }'
```

### Login

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@example.com&password=senha123"
```

### Criar edital (requer autenticação)

```bash
curl -X POST "http://localhost:8000/notices/" \
  -H "Authorization: Bearer <seu-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Edital de Bolsas 2024",
    "notice_number": "05/2024", 
    "year": 2024,
    "registration_start_date": "2024-01-15T00:00:00",
    "registration_end_date": "2024-02-15T23:59:59",
    "appeal_start_date": "2024-02-20T00:00:00",
    "appeal_end_date": "2024-02-25T23:59:59",
    "preliminary_result_date": "2024-03-01T00:00:00",
    "final_result_date": "2024-03-15T00:00:00",
    "responsible_agency": "Pró-Reitoria de Assuntos Estudantis",
    "description": "Processo seletivo para bolsas de auxílio estudantil...",
    "food_allowance": true,
    "housing_allowance": true,
    "daycare_allowance": false,
    "graduation_scholarship": true
  }'
```

### Fazer upload de documento para edital

```bash
curl -X POST "http://localhost:8000/api/v1/notices/1/documents" \
  -H "Authorization: Bearer <seu-token>" \
  -F "file=@/caminho/para/documento.pdf"
```

## 🧪 Desenvolvimento

### Executar em modo desenvolvimento

```bash
# Com hot reload
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Linting e formatação

```bash
# Black - formatação (se instalado)
poetry run black .

# isort - ordenação de imports (se instalado)
poetry run isort .

# flake8 - linting (se instalado)
poetry run flake8 .
```

### Estrutura do projeto

```text
backend/
├── app/
│   ├── core/           # Configurações e autenticação
│   ├── db/            # Configuração do banco de dados
│   ├── models/        # Modelos SQLAlchemy
│   ├── routers/       # Endpoints da API
│   ├── schemas/       # Schemas Pydantic
│   ├── services/      # Lógica de negócio
│   └── main.py        # Aplicação principal
├── alembic/           # Migrações do banco
├── pyproject.toml     # Configuração do Poetry
└── README.md          # Este arquivo
```
