FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# system deps
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# copy requirements and install
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install --no-cache-dir -r /app/requirements.txt

# copy application
COPY backend /app

EXPOSE 8000

# default command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
