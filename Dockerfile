# Sử dụng Python 3.11 bản nhẹ
FROM python:3.11-slim

# Cập nhật và cài đặt FFmpeg (Quan trọng!)
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# Thiết lập thư mục làm việc
WORKDIR /app

# Copy file requirements và cài đặt thư viện Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ code vào
COPY . .

# Mở port 8080 (Render cần cái này)
EXPOSE 8080

# Lệnh chạy server bằng Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--timeout", "120", "app:app"]
