ARG PYTHON_VERSION=3.11.9
FROM python:${PYTHON_VERSION}-slim AS base

# Отключаем кеширование pyc-файлов и буферизацию вывода
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Копируем зависимости и устанавливаем их
COPY requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt

# Создаём пользователя без прав суперпользователя
ARG UID=10001
RUN adduser --disabled-password --gecos "" --home "/nonexistent" \
    --shell "/sbin/nologin" --no-create-home --uid "${UID}" appuser

USER appuser

# Копируем весь проект
COPY . .

EXPOSE 8000

CMD ["gunicorn", "SurGu_Calendar.wsgi:application", "--bind", "0.0.0.0:8000"]
