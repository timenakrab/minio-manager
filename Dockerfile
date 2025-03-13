# ใช้ Python 3.11 เป็น base image
FROM python:3.10

# ตั้ง working directory
WORKDIR /app

# คัดลอกไฟล์ requirements.txt และติดตั้ง dependencies
COPY requirements.txt .

RUN pip install --upgrade pip

RUN pip install --no-cache-dir -r requirements.txt

# คัดลอกโค้ดโปรเจกต์ทั้งหมด
COPY . .

# กำหนดคำสั่งเริ่มต้นเมื่อ container รัน
CMD ["python", "app.py"]
