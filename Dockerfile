FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=Europe/Paris

WORKDIR /app

# tzdata : fuseaux horaires pour ZoneInfo("Europe/Paris") (ping Lounge 9h/16h)
COPY requirements.txt .
RUN pip install -r requirements.txt tzdata

COPY botsq/ ./botsq/

# Le token n'est pas dans l'image : .env est monté par compose.yaml
CMD ["python", "-m", "botsq"]
