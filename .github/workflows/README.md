# GitHub Actions Workflows

Este diretório contém os workflows do GitHub Actions para o projeto BEA Backend.

## Workflows Configurados

### 🧪 Tests (`test.yml`)

**Objetivo**: Executar apenas os testes automatizados sem lint ou deploy.

**Trigger**:

- Push para branches `main` e `develop`
- Pull requests para branches `main` e `develop`

**O que faz**:

1. ✅ **Setup do ambiente**: Python 3.12 + Poetry
2. ✅ **Banco de dados**: PostgreSQL 14 para testes
3. ✅ **Dependências**: Cache inteligente do Poetry
4. ✅ **Migrações**: Aplica migrações no banco de teste
5. ✅ **Testes**: Executa pytest com relatório detalhado
6. ✅ **Artefatos**: Salva resultados dos testes

**Variáveis de ambiente**:

- Configuração completa para testes (banco, AWS mock, etc.)
- Usa PostgreSQL em container Docker
- PYTHONPATH configurado automaticamente

**Cache**:

- Cache do ambiente virtual do Poetry baseado no `poetry.lock`
- Acelera execuções subsequentes

**Relatórios**:

- Upload automático dos resultados de teste
- Retenção de 30 dias para artefatos
- Logs detalhados com `--tb=short`

## 🚀 **Características da Configuração**

### **Focado em Testes**

- ❌ **Sem linting**: Não executa formatação ou análise de código
- ❌ **Sem deploy**: Não faz deploy automático  
- ✅ **Apenas testes**: Foco total na validação funcional

### **Ambiente Completo**

- 🐘 **PostgreSQL**: Banco real para testes de integração
- 🐍 **Python 3.12**: Versão mais recente
- 📦 **Poetry**: Gerenciamento moderno de dependências
- 🔄 **Migrações**: Banco preparado automaticamente

### **Performance Otimizada**

- ⚡ **Cache**: Dependências cacheadas por hash do `poetry.lock`
- 🏃 **Paralelo**: Testes executam de forma otimizada
- 📊 **Relatórios**: Resultados preservados para análise

## 📋 **Como Usar**

### **Desenvolvimento Local**

```bash
# Rodar os mesmos testes que o CI
poetry run pytest -v --tb=short

# Com coverage
poetry run pytest -v --tb=short --cov=app
```

### **Debugging CI**

- Logs disponíveis na aba "Actions" do GitHub
- Artefatos baixáveis com resultados detalhados
- Falhas mostram output completo com `--tb=short`

### **Configuração de Secrets**

Atualmente usa valores mock para AWS. Se precisar de integração real:

```yaml
# Adicionar secrets no GitHub:
# AWS_ACCESS_KEY_ID
# AWS_SECRET_ACCESS_KEY
# S3_BUCKET_NAME
```

## 🔧 **Personalização**

### **Adicionar Novos Testes**

- Criar arquivos em `/tests/`
- Seguir padrão `test_*.py`
- Usar markers: `@pytest.mark.unit`, `@pytest.mark.integration`

### **Modificar Configuração**

- Editar `test.yml` para mudanças no workflow
- Atualizar `pyproject.toml` para configurações do pytest
- Adicionar services no workflow se precisar de Redis, etc.

---

**Status**: ✅ Configurado e funcional
**Manutenção**: Verificar periodicamente atualizações das actions
