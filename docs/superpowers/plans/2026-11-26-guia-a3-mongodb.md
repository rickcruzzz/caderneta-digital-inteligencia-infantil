# Guia A3 MongoDB Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publicar o guia de apresentação MongoDB, compatibilizar o ambiente local e corrigir o atalho do projeto.

**Architecture:** A API resolve a URI em uma função pequena e testável, sem expor seu valor. A documentação descreve o sistema atual em seis blocos. O atalho local apenas abre a raiz do repositório MongoDB no code-server já existente.

**Tech Stack:** Python 3.12, FastAPI, PyMongo, pytest, Next.js 16, TypeScript, MongoDB Atlas, GitHub.

**Spec:** `docs/superpowers/specs/2026-11-26-guia-a3-mongodb-design.md`

## Global Constraints

- Não imprimir nem versionar credenciais.
- Usar somente `caderneta_digital`; não escrever em `sample_mflix` ou outros bancos.
- Preservar o projeto SQL Server anterior.
- Não ampliar a lista de acesso do Atlas durante esta mudança.
- Publicar somente após testes, typecheck e build.

## Review Focus

- Ausência das duas variáveis de URI deve falhar sem revelar valores.
- `MONGO_URI` deve prevalecer quando ambas estiverem definidas.
- `MONGODB_URI` deve funcionar no ambiente local atual.
- O guia não pode descrever coleções MongoDB como tabelas relacionais.
- Atalho deve abrir a subpasta MongoDB, não a raiz SQL.

---

### Task 1: Compatibilidade segura da configuração MongoDB

**Files:**
- Modify: `api/database.py`
- Modify: `tests/test_vercel_api.py`

**Interfaces:**
- Produces: `get_mongo_uri() -> str`
- Consumes: `MONGO_URI` oficial ou `MONGODB_URI` legado/local

- [ ] **Step 1: Escrever testes para precedência, fallback e ausência de URI**
- [ ] **Step 2: Executar testes e confirmar falha pela função ausente**
- [ ] **Step 3: Implementar `get_mongo_uri()` e usá-la em `get_client()`**
- [ ] **Step 4: Executar `python -m pytest -q` e confirmar sucesso**
- [ ] **Step 5: Commit**

### Task 2: Guia atualizado da apresentação

**Files:**
- Create: `docs/09-entrega-e-ensaio.md`
- Modify: `README.md`

**Interfaces:**
- Produces: roteiro de seis partes e link direto no README
- Consumes: rotas, coleções, regras e testes já implementados

- [ ] **Step 1: Escrever o roteiro fiel ao código atual**
- [ ] **Step 2: Revisar terminologia MongoDB, segurança e limites clínicos**
- [ ] **Step 3: Adicionar link destacado no README**
- [ ] **Step 4: Commit**

### Task 3: Atalho, validação e publicação

**Files:**
- Modify local: `~/.local/share/applications/projeto-a3.desktop`
- Modify local: `~/Área de trabalho/Projeto A3.desktop`

**Interfaces:**
- Produces: atalho para `plataforma_saude_infantil` na porta 8080 e repositório remoto atualizado
- Consumes: build e testes verdes

- [ ] **Step 1: Criar backups recuperáveis dos dois atalhos**
- [ ] **Step 2: Atualizar nome, comentário e URL dos atalhos**
- [ ] **Step 3: Validar arquivos `.desktop` e abrir o projeto correto**
- [ ] **Step 4: Executar suite Python, typecheck, build e varredura de segredos**
- [ ] **Step 5: Revisar diff, commit final e push para `origin/main`**

