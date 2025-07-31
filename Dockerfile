# Python base image
FROM python:3.10-slim

# ติดตั้ง dependencies พื้นฐาน
RUN apt-get update && apt-get install -y \
    curl \
    unzip \
    wget \
    xvfb \
    libnss3 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    libxss1 \
    libasound2 \
    libdrm2 \
    libgbm1 \
    && rm -rf /var/lib/apt/lists/*

# ติดตั้ง Playwright
RUN pip install --upgrade pip
COPY requirements.txt .
RUN pip install -r requirements.txt
RUN playwright install --with-deps

# Copy โค้ดเข้า container
COPY . /app
WORKDIR /app

# Run Bot
CMD ["python", "app.py"]
