FROM python:3.12

# Define diretório de trabalho
WORKDIR /app

# Instala dependências do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl && \
    rm -rf /var/lib/apt/lists/*

# Copia dependências Python
COPY requirements.txt .

# Instala dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante do código
COPY app ./app

# Porta padrão do FastAPI/Uvicorn
EXPOSE 8000

# Comando padrão para produção
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
