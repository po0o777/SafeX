# Используем Python 3.13 slim
FROM python:3.13-slim

# Рабочая директория
WORKDIR /app

# Устанавливаем зависимости для Selenium и Chrome
RUN apt-get update && apt-get install -y \
    wget unzip curl gnupg2 xvfb libnss3 libgconf-2-4 libxi6 libxss1 libglib2.0-0 libfontconfig1 libx11-6 \
    && rm -rf /var/lib/apt/lists/*

# Установка Google Chrome
RUN wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && dpkg -i google-chrome-stable_current_amd64.deb || apt-get -f install -y \
    && rm google-chrome-stable_current_amd64.deb

# Установка ChromeDriver (берём версию Chrome)
RUN CHROME_VERSION=$(google-chrome --version | grep -oP '\d+\.\d+\.\d+') \
    && wget -q "https://chromedriver.storage.googleapis.com/${CHROME_VERSION}/chromedriver_linux64.zip" \
    && unzip chromedriver_linux64.zip \
    && mv chromedriver /usr/local/bin/ \
    && rm chromedriver_linux64.zip

# Копируем requirements и код
COPY requirements.txt .
COPY bot.py .

# Устанавливаем зависимости Python
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Переменные окружения (можно передавать через docker run -e)
ENV TELEGRAM_TOKEN=${TELEGRAM_TOKEN}
ENV OPENAI_API_KEY=${OPENAI_API_KEY}

# Запуск бота
CMD ["python", "bot.py"]
