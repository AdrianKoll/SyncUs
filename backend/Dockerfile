FROM python:3.11-slim

WORKDIR /app

# Instalar dependências do sistema para PostgreSQL
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Instalar Poetry
RUN pip install --no-cache-dir poetry==1.8.0

# Configurar Poetry: não criar ambiente virtual dentro do container
RUN poetry config virtualenvs.create false

# Copiar apenas arquivos de dependência primeiro (cache do Docker)
COPY pyproject.toml poetry.lock* ./

# A imagem de produção instala apenas o grupo principal. O grupo dev
# continua disponível para desenvolvimento local e CI com `poetry install`.
RUN poetry install --only main --no-root --no-interaction --no-ansi

# Copiar TODO o código do back-end
COPY . .

# Expor porta da API
EXPOSE 8000

# Comando para iniciar o app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]