import subprocess
import logging
from flask import Flask, request, Response, stream_with_context, jsonify
import yt_dlp

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

def get_youtube_url(query):
    # Cấu hình yt-dlp để lấy link audio tốt nhất
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'noplaylist': True,
        'default_search': 'ytsearch1' # Tự động tìm kiếm nếu không phải link
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Nếu query không phải url, yt-dlp sẽ tự tìm
            info = ydl.extract_info(query, download=False)
            
            # Xử lý kết quả tìm kiếm (playlist hoặc video đơn)
            if 'entries' in info:
                if len(info['entries']) > 0:
                    video = info['entries'][0]
                else:
                    return None, None
            else:
                video = info
                
            return video.get('url'), video.get('title', 'Unknown')
    except Exception as e:
        logging.error(f"Lỗi tìm kiếm YouTube: {e}")
        return None, None

@app.route('/')
def home():
    return "Xiaozhi Music Server is Running with FFmpeg!"

@app.route('/stream')
def stream_music():
    query = request.args.get('q')
    if not query:
        return "Thiếu tham số 'q' (tên bài hát)", 400
    
    logging.info(f"Nhận yêu cầu tìm: {query}")
    video_url, title = get_youtube_url(query)
    
    if not video_url:
        return "Không tìm thấy bài hát", 404
    
    logging.info(f"Bắt đầu stream: {title}")

    # Lệnh FFmpeg để chuyển đổi sang PCM 16kHz, 16bit, Mono (Chuẩn ESP32 I2S)
    ffmpeg_cmd = [
        'ffmpeg',
        '-re',                # Read input at native frame rate
        '-i', video_url,      # Input URL (YouTube)
        '-f', 's16le',        # Format: PCM Signed 16-bit Little Endian
        '-acodec', 'pcm_s16le',
        '-ar', '16000',       # Sample rate: 16000 Hz
        '-ac', '1',           # Channels: 1 (Mono)
        '-vn',                # No video
        '-'                   # Output to pipe (stdout)
    ]

    def generate():
        # Chạy FFmpeg và pipe dữ liệu ra response
        process = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        try:
            while True:
                # Đọc từng chunk 4KB để gửi về ESP32
                data = process.stdout.read(4096)
                if not data:
                    break
                yield data
        except Exception as e:
            logging.error(f"Lỗi stream: {e}")
        finally:
            logging.info("Kết thúc stream")
            process.kill()

    return Response(stream_with_context(generate()), mimetype='audio/pcm')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
