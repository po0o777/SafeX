# Используем официальный Python образ
FROM python:3.13-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем системные зависимости для Selenium и Chrome
RUN apt-get update && apt-get install -y \
    wget unzip curl gnupg2 xvfb libnss3 libgconf-2-4 libxi6 libxss1 libglib2.0-0 libfontconfig1 libx11-6 \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем Google Chrome
RUN wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && dpkg -i google-chrome-stable_current_amd64.deb || apt-get -f install -y \
    && rm google-chrome-stable_current_amd64.deb

# Устанавливаем ChromeDriver (под версию Chrome)
RUN CHROME_VERSION=$(google-chrome --version | grep -oP '\d+\.\d+\.\d+') \
    && wget -q "https://chromedriver.storage.googleapis.com/${CHROME_VERSION}/chromedriver_linux64.zip" \
    && unzip chromedriver_linux64.zip \
    && mv chromedriver /usr/local/bin/ \
    && rm chromedriver_linux64.zip

# Копируем зависимости и код бота
COPY requirements.txt .
COPY bot.py .

# Обновляем pip и устанавливаем Python-зависимости
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Переменные окружения для бота
ENV TELEGRAM_TOKEN=${TELEGRAM_TOKEN}
ENV OPENAI_API_KEY=${OPENAI_API_KEY}

# Запуск бота
CMD ["python", "bot.py"]
