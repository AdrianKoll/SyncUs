# SyncUs — Gestão Financeira para Casais

O **SyncUs** é uma plataforma moderna de gestão financeira compartilhada, desenvolvida especificamente para casais que buscam transparência e organização em tempo real. O projeto utiliza uma arquitetura robusta de microsserviços e tecnologias de ponta no ecossistema Python para garantir segurança, escalabilidade e uma experiência de usuário fluida.

> **Nota de Desenvolvimento:** Este projeto está em fase de desenvolvimento ativo. O backend está funcional e testado, incluindo autenticação, sistema de vínculos e notificações em tempo real. A integração completa com o frontend e o dashboard de lançamentos são as próximas etapas do roadmap.

---

##  Stack Tecnológica

O projeto foi construído utilizando as melhores práticas de desenvolvimento backend, focando em performance e segurança.

| Camada | Tecnologia | Descrição |
| :--- | :--- | :--- |
| **Backend** | **FastAPI (Python 3.12)** | Framework de alta performance com tipagem estática e validação automática. |
| **Banco de Dados** | **PostgreSQL 15** | Banco de dados relacional robusto para persistência de dados complexos. |
| **ORM / Validação** | **SQLAlchemy & Pydantic** | Gerenciamento de banco de dados e validação rigorosa de esquemas de dados. |
| **Segurança** | **OAuth 2.0 + JWT** | Autenticação baseada em tokens com criptografia bcrypt para senhas. |
| **Tempo Real** | **WebSockets** | Comunicação bidirecional para notificações instantâneas sem necessidade de refresh. |
| **Infraestrutura** | **Docker & Docker Compose** | Containerização completa do ambiente para desenvolvimento e deploy consistente. |

---

## Funcionalidades Concluídas (Backend)

O núcleo do sistema já está operacional, com as seguintes funcionalidades implementadas e testadas:

- **Autenticação Segura:** Fluxo completo de cadastro e login utilizando tokens JWT e proteção contra ataques de força bruta.
- **Gestão de Vínculos:** Sistema de convites via tokens únicos com validade de 7 dias, permitindo a conexão segura entre duas contas.
- **Notificações em Tempo Real:** Implementação de WebSockets para alertar usuários sobre novos convites, aceites ou recusas instantaneamente.
- **Segurança de Conta:** Proteção para alteração de dados sensíveis (e-mail e senha) exigindo a validação da senha atual.
- **Arquitetura em Camadas:** Organização profissional do código seguindo os padrões de `api`, `services`, `models`, `repositories` e `schemas`.

---

## Como Rodar o Projeto

Para executar o ambiente completo de desenvolvimento, siga os passos abaixo:

### Pré-requisitos
- **Docker** e **Docker Compose** instalados.
- **Git** para clonagem do repositório.

### Instalação e Execução
1. **Clonar o Repositório:**
   ```bash
   git clone https://github.com/AdrianKoll/SyncUs.git
   cd SyncUs
   ```

2. **Configurar Ambiente:**
   Copie o arquivo de exemplo e preencha suas chaves:
   ```bash
   cp .env.example .env
   ```

3. **Subir Containers:**
   ```bash
   docker-compose up --build -d
   ```

4. **Acessar a Documentação:**
   A documentação interativa da API (Swagger UI) estará disponível em:
   `http://localhost:8000/docs`

---

## Roadmap de Desenvolvimento

- [ ] **Integração Frontend:** Conexão total das telas de Dashboard com as APIs de lançamentos.
- [ ] **Gestão de Lançamentos:** CRUD completo de entradas e saídas com categorias customizadas.
- [ ] **Relatórios Dinâmicos:** Geração de gráficos de desempenho financeiro mensal.
- [ ] **Exportação de Dados:** Suporte para relatórios em formato PDF e CSV.
- [ ] **CI/CD:** Implementação de testes automatizados com Pytest e pipeline de deploy.

---

**Desenvolvido por [Adrian Kauã](https://www.linkedin.com/in/adrian-kaua)** — *Focado em construir soluções backend sólidas e escaláveis.*
