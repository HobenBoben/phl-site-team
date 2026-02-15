FROM python:3.11-slim

# Создаём непривилегированного пользователя с UID/GID 568 (как на хосте)
RUN groupadd -g 568 appuser && useradd -m -u 568 -g appuser appuser

WORKDIR /app

# Копируем только requirements.txt сначала для лучшего кэширования
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем остальной код приложения
COPY . .

# Создаём папки для данных и загрузок и даём права пользователю
RUN mkdir -p /app/data /app/static/uploads && \
    chown -R appuser:appuser /app

# Переключаемся на непривилегированного пользователя
USER appuser

# Команда по умолчанию
CMD ["python", "app.py"]