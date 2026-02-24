# 1. Используем базовый образ Python (slim версия легче)
FROM python:3.11-slim

# 2. Указываем рабочую папку внутри контейнера
WORKDIR /app

# 3. Копируем файл зависимостей внутрь контейнера
COPY requirements.txt .

# 4. Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# 5. Копируем остальной код проекта в контейнер
COPY . .

# 6. Команда для запуска бота (замени main.py на имя твоего файла)
CMD ["python", "run_esco.py"]