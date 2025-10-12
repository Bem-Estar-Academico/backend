# Relatório de Análise: Fluxo de Registro de Estudante

Este documento detalha as inconsistências, bugs e pontos de melhoria encontrados na funcionalidade de registro de estudantes, juntamente com os testes criados para reproduzi-los.

## Resumo

Foram identificados e confirmados com testes automatizados dois bugs críticos no fluxo de registro de estudantes. O primeiro impede a criação de inscrições, enquanto o segundo impede a visualização dos detalhes de uma inscrição. Adicionalmente, foram observadas oportunidades de melhoria na consistência da API, cobertura de testes e performance de consultas.

---

## Inconsistências Críticas e Achados

### 1. BUG CONFIRMADO: Nomes de Campos de Data Incorretos (`AttributeError`)

- **Onde:** `app/services/student_registration_service.py`, na função `create_registration`.
- **Problema:** O código tenta acessar `notice.start_date` e `notice.end_date`, mas o modelo `Notice` define esses campos como `registration_start_date` e `registration_end_date`.
- **Impacto:** Causa um `AttributeError` fatal que bloqueia completamente a criação de qualquer inscrição de estudante.
- **Prova:** O teste `test_create_student_registration` em `tests/routers/test_student_registrations.py` foi criado e falha exatamente como esperado, confirmando o bug.

### 2. BUG CONFIRMADO: Falha de Validação no Schema de Resposta (`ValidationError`)

- **Onde:** Endpoints em `app/routers/student_registrations.py` que usam o schema `StudentRegistrationWithDetails` (ex: `GET /{registration_id}`).
- **Problema:** O schema `StudentRegistrationWithDetails` exige um campo `notice_title`, que não é populado pelo `service` ao buscar uma `StudentRegistration` do banco de dados.
- **Impacto:** Causa um `ResponseValidationError` do FastAPI, resultando em um erro `500 Internal Server Error` ao tentar ver os detalhes de uma inscrição.
- **Prova:** O teste `test_get_student_registration_fails_due_to_schema_bug` em `tests/routers/test_student_registrations.py` foi corrigido e agora falha como esperado, confirmando que a resposta da API não inclui o campo `notice_title` obrigatório.

### 3. ACHADO: Prefixo de URL Inconsistente

- **Onde:** `app/main.py`.
- **Observação:** O roteador `student_registrations_router` é incluído na aplicação com o prefixo `/api/v1/registrations`. Isso é inconsistente com o nome do arquivo do roteador (`student_registrations.py`), o que pode gerar confusão para desenvolvedores e levou à falha inicial dos testes com erro `404 Not Found`.

---

## Pontos de Melhoria

### 1. Cobertura de Testes

- **Problema:** A funcionalidade de registro de estudantes foi adicionada sem testes automatizados para os fluxos de listagem, atualização e remoção.
- **Impacto:** Aumenta o risco de regressões e dificulta a validação de que a funcionalidade opera como esperado.

### 2. Performance da Contagem de Registros

- **Onde:** `app/services/student_registration_service.py`, nas funções `get_registrations_by_notice` e `get_registrations_by_student`.
- **Problema:** A contagem do total de registros é feita carregando todos os objetos do banco em memória (`len(result.scalars().all())`).
- **Impacto:** Causa performance degradada e alto consumo de memória com um grande volume de dados. A forma correta seria usar uma consulta de contagem (`SELECT COUNT(*)`).

---

## Recomendações

1.  **Corrigir os dois bugs confirmados** como prioridade máxima.
2.  Avaliar os pontos de melhoria sobre a cobertura de testes e a performance das consultas.
3.  Considerar renomear o prefixo da rota em `main.py` para `/api/v1/student-registrations` para maior consistência, ou documentar a escolha atual.