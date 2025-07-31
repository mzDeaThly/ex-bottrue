# ใช้ Image พื้นฐานของ Playwright ที่มีเบราว์เซอร์และทุกอย่างติดตั้งมาพร้อมแล้ว
FROM mcr.microsoft.com/playwright/python:v1.44.0

# กำหนดโฟลเดอร์ทำงานภายใน Container
WORKDIR /app

# คัดลอกไฟล์ requirements.txt เข้าไปก่อน แล้วติดตั้งไลบรารี
COPY requirements.txt .
RUN pip install -r requirements.txt

# คัดลอกโค้ดส่วนที่เหลือทั้งหมดเข้าไป
COPY . .

# คำสั่งสำหรับรันบอท (ตรวจสอบให้แน่ใจว่าไฟล์หลักของคุณชื่อ app.py)
CMD ["python", "app.py"]
