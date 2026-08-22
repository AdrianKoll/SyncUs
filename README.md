# SyncUs — Gestão Financeira para Casais

O SyncUs é uma aplicação web de gestão financeira compartilhada para casais. O projeto possui um backend em FastAPI, persistência PostgreSQL, autenticação JWT, vínculo entre usuários, notificações e uma SPA leve em HTML, CSS e JavaScript.

## Stack

| Camada | Tecnologia |
|---|---|
| API | FastAPI, Uvicorn e Python 3.11+ |
| Banco | PostgreSQL 15 e SQLAlchemy |
| Validação | Pydantic 2 e e-mail validado |
| Segurança | OAuth2 password flow, JWT, Passlib e bcrypt |
| Tempo real | WebSocket com fallback de polling de notificações |
| Frontend | HTML, CSS, JavaScript, Bootstrap e Chart.js |
| Infraestrutura | Docker Compose com PostgreSQL, pgAdmin, API e Nginx |

## Executar com Docker

Crie o arquivo de ambiente a partir do modelo e preencha os valores reais:

```bash
cp .env.example .env
docker compose up --build -d
```

Após a inicialização, os endereços locais são:

| Serviço | URL |
|---|---|
| Frontend | http://localhost:8080 |
| API | http://localhost:8000 |
| Swagger | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |
| pgAdmin | http://localhost:5050 |

O frontend usa `http://localhost:8000/api` por padrão. Para outro ambiente, pode-se definir `window.SYNCUS_API_URL` antes dos scripts do frontend.

## Funcionalidades integradas

A autenticação possui cadastro, login OAuth2, JWT, armazenamento de sessão conforme a opção “Manter conectado”, consulta de perfil e atualização protegida por senha atual. Novos usuários recebem automaticamente um token de vínculo com validade de sete dias.

O vínculo possui envio, aceite, recusa, consulta de parceiro e desconexão. O aceite cria ou reutiliza a sala financeira compartilhada e garante as categorias padrão. As notificações podem ser listadas, marcadas como lidas, apagadas e respondidas diretamente pelo menu superior. O WebSocket permanece disponível e o frontend utiliza polling como fallback quando a conexão em memória não estiver disponível.

O domínio financeiro possui:

| Recurso | Endpoint principal |
|---|---|
| Listar lançamentos | `GET /api/transactions/` |
| Criar lançamento | `POST /api/transactions/` |
| Atualizar lançamento | `PUT /api/transactions/{id}` |
| Excluir lançamento | `DELETE /api/transactions/{id}` |
| Excluir todos da sala | `DELETE /api/transactions/all` |
| Listar categorias | `GET /api/transactions/categories` |
| Criar categoria | `POST /api/transactions/categories` |
| Excluir categoria | `DELETE /api/transactions/categories/{id}` |
| Dashboard mensal | `GET /api/transactions/dashboard?year=YYYY&month=MM` |

O dashboard mensal calcula saldo, entradas, saídas, gastos por categoria, lançamentos recentes, saldo entre parceiros e séries diárias reais. A tela de lançamentos consome o CRUD completo, a tela de histórico possui filtros e exportação CSV, e a tela de relatórios utiliza os dados reais para cards, gráficos e exportações CSV, TXT e JSON.

## Testes

Os testes de integração ficam em `backend/tests` e cobrem registro, login, vínculo, categorias, criação, listagem, atualização, dashboard, filtros e exclusão de lançamentos.

```bash
cd backend
pytest -q
```

O teste usa SQLite temporário e não substitui a validação final com PostgreSQL em Docker. Para uma execução completa do ambiente:

```bash
docker compose up --build -d
curl http://localhost:8000/
```

## Organização do código

O backend está dividido em `api`, `core`, `models`, `repositories`, `schemas`, `services` e `websockets`. O frontend possui `app.js` para autenticação, API e utilitários; `router.js` para navegação hash-based; `ui.js` para perfil, notificações e dashboard; e views HTML carregadas dinamicamente.

As alterações de manutenção foram implementadas de forma incremental na branch de trabalho, preservando os endpoints existentes e adicionando os novos recursos de forma complementar.
