# 👫 SyncUs | Gerenciador Financeiro para Casal

> Aplicativo Web completo para organizar finanças a dois, com sincronização em tempo real, sistema seguro de vínculo por tokens e permissões.

## 🛠️ Stack Tecnológica
| Camada | Tecnologia |
|---|---|
| **Back-end** | FastAPI (Python) |
| **Banco de Dados** | PostgreSQL 15 |
| **Orquestração** | Docker + Docker Compose |
| **Front-end** | HTML5 + CSS3 + JavaScript Puro |
| **Autenticação** | JWT |
| **Tempo Real** | WebSockets |
| **Arquitetura** | Em Camadas (Escalável) |

## ✅ Funcionalidades Implementadas
- [x] Cadastro de usuário
- [x] Login com JWT
- [x] Gerador de tokens de vínculo (7 dias de validade)

## 🚧 Próximas Funcionalidades
- [ ] Sistema de convites com aceite/recusa
- [ ] Notificações em tempo real (sininho)
- [ ] Perfil do parceiro visível
- [ ] Lançamentos de Entrada e Saída
- [ ] Histórico completo com filtros
- [ ] Edição de lançamentos
- [ ] Relatórios e gráficos
- [ ] Dashboard compartilhado

## 🚀 Como Rodar o Projeto
### Pré-requisitos
- Docker Desktop instalado e rodando

### Comandos
```bash
# Subir todos os containers (API + Banco + pgAdmin)
docker compose up --build -d

# Ver logs da API
docker compose logs api -f

# Parar tudo
docker compose down