import logging
import requests
import subprocess
import random
import json
import time
from flask import Flask, request, Response, stream_with_context
from ytmusicapi import YTMusic

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Khởi tạo YouTube Music API
ytmusic = YTMusic()

# DANH SÁCH COBALT SERVERS (Cập nhật mới nhất & Nhiều nhất)
COBALT_INSTANCES = [
    "https://cobalt.pub",
    "https://api.cobalt.best",
    "https://co.wuk.sh",
    "https://cobalt.tools",
    "https://cobalt.xy24.eu.org",
    "https://api.cobalt.kp.fyi",
    "https://cobalt.kwiatekmiki.pl",
    "https://cobalt.lacus.live",
    "https://cobalt.synced.is",
    "https://cobalt.bowring.uk",
    "https://cobalt.repl.co" 
]

def search_with_ytmusic(query):
    """Tìm link bài hát qua YouTube Music"""
    try:
        logging.info(f"🔍 Đang tìm: {query}")
        results = ytmusic.search(query, filter='songs')
        if results:
            video_id = results[0].get('videoId')
            title = results[0].get('title')
            if video_id:
                link = f"https://www.youtube.com/watch?v={video_id}"
                logging.info(f"✅ Tìm thấy: {title} ({link})")
                return link
        
        # Fallback: Tìm video thường nếu không ra bài hát
        results = ytmusic.search(query, filter='videos')
        if results:
            video_id = results[0].get('videoId')
            if video_id: return f"https://www.youtube.com/watch?v={video_id}"
            
    except Exception as e:
        logging.error(f"❌ Lỗi tìm kiếm: {e}")
    return None

def get_audio_stream_from_cobalt(url):
    """Lấy link tải MP3 từ danh sách Cobalt (Thử từng cái một)"""
    
    payload = {
        "url": url,
        "vCodec": "h264",
        "vQuality": "720",
        "aFormat": "mp3",
        "isAudioOnly": True
    }
    
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    # Xáo trộn danh sách để cân bằng tải
    instances = COBALT_INSTANCES.copy()
    random.shuffle(instances)

    for instance in instances:
        try:
            # logging.info(f"➡️ Thử server: {instance}")
            response = requests.post(f"{instance}/api/json", json=payload, headers=headers, timeout=8)
            
            if response.status_code == 200:
                data = response.json()
                
                # Xử lý các kiểu trả về khác nhau của Cobalt
                if 'url' in data: return data['url']
                if 'picker' in data:
                    for item in data['picker']:
                        if 'url' in item: return item['url']
                if 'audio' in data: return data['audio']
                
            # Nếu server này lỗi, thử cái tiếp theo ngay
            continue
            
        except Exception:
            continue
            
    return None

@app.route('/')
def home():
    return "Xiaozhi Music Server (Ultimate Edition) is Running!"

@app.route('/stream')
def stream_music():
    query = request.args.get('q')
    if not query: return "Thiếu tên bài hát", 400
    
    youtube_link = query
    
    # 1. Tìm kiếm
    if not query.startswith("http"):
         found_link = search_with_ytmusic(query)
         if found_link: 
             youtube_link = found_link
         else: 
             return "Không tìm thấy bài hát.", 404

    # 2. Lấy link tải (Thử tối đa 3 lần nếu thất bại)
    audio_url = None
    for _ in range(3):
        audio_url = get_audio_stream_from_cobalt(youtube_link)
        if audio_url: break
        time.sleep(1) # Nghỉ 1 giây rồi thử lại
    
    if not audio_url: 
        return "Server quá tải, không lấy được nhạc.", 404

    logging.info(f"🎶 Stream từ: {audio_url}")

    # 3. Convert sang PCM
    ffmpeg_cmd = [
        'ffmpeg', '-re', '-i', audio_url, 
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
