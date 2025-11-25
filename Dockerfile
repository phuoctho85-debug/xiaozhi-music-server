# Dùng bản Python 3.10 đầy đủ (không phải slim) để cài thư viện dễ hơn
FROM python:3.10

# Cập nhật và cài đặt FFmpeg
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# Thiết lập thư mục làm việc
WORKDIR /app

# Copy file requirements và cài đặt thư viện
COPY requirements.txt .
# Nâng cấp pip trước để tránh lỗi cài đặt
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ code vào
COPY . .

# Mở port 8080
EXPOSE 8080

# Chạy server
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--timeout", "120", "app:app"]
