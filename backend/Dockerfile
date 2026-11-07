FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Instalar dependencias del sistema mínimas y limpiar caché
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar los módulos del sensor forense
COPY . .

# Crear usuario no-root por seguridad (Hardening de Contenedor)
RUN useradd -m -u 10001 forensic_sensor && \
    mkdir -p /app/vault && \
    chown -R forensic_sensor:forensic_sensor /app

USER forensic_sensor

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--no-server-header"]