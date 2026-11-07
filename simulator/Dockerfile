FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Usuario sin privilegios para aislamiento de red
RUN useradd -m -u 10002 swarm_actor
USER swarm_actor

CMD ["python", "agent_emu.py"]