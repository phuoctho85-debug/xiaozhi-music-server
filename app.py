import subprocess
import logging
import os
from flask import Flask, request, Response, stream_with_context
import yt_dlp

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Nạp Cookies từ biến môi trường
if os.environ.get('YOUTUBE_COOKIES'):
    with open('cookies.txt', 'w') as f:
        f.write(os.environ.get('YOUTUBE_COOKIES'))

def get_youtube_url(query):
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'noplaylist': True,
        'default_search': 'ytsearch1',
        'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None,
        # --- THÊM CÁC DÒNG NÀY ĐỂ GIẢ LẬP TRÌNH DUYỆT ---
        'nocheckcertificate': True,
        'ignoreerrors': True,
        'logtostderr': False,
        'quiet': True,
        'no_warnings': True,
        'source_address': '0.0.0.0',
        # Giả danh iPhone để ít bị chặn hơn
        'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=False)
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
    return "Xiaozhi Music Server is Running!"

@app.route('/stream')
def stream_music():
    query = request.args.get('q')
    if not query: return "Thiếu tham số q", 400
    
    video_url, title = get_youtube_url(query)
    if not video_url: return "Không tìm thấy bài hát (YouTube Blocked?)", 404
    
    logging.info(f"Streaming: {title}")

    ffmpeg_cmd = [
        'ffmpeg', '-re', '-i', video_url,
        '-f', 's16le', '-acodec', 'pcm_s16le',
        '-ar', '16000', '-ac', '1', '-vn', '-'
    ]

    def generate():
        process = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        try:
            while True:
                data = process.stdout.read(4096)
                if not data: break
                yield data
        finally:
            process.kill()

    return Response(stream_with_context(generate()), mimetype='audio/pcm')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
