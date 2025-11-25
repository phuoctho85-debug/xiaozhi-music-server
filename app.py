import logging
import requests
import subprocess
import random
import json
from flask import Flask, request, Response, stream_with_context

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# 1. Danh sách Piped (Dùng để tìm tên bài hát)
PIPED_INSTANCES = [
    "https://pipedapi.kavin.rocks",
    "https://api.piped.gl",
    "https://pipedapi.drgns.space",
    "https://pa.il.ax",
    "https://pipedapi.adminforge.de"
]

# 2. Danh sách Cobalt (Dùng để tải nhạc) - CẬP NHẬT MỚI
COBALT_INSTANCES = [
    "https://cobalt.pub",
    "https://api.cobalt.best",
    "https://co.wuk.sh",
    "https://cobalt.tools",
    "https://cobalt.xy24.eu.org",
    "https://cobalt.kwiatekmiki.pl",
    "https://api.cobalt.kp.fyi" 
]

def search_with_piped(query):
    """
    Tìm link YouTube thông qua Piped API
    """
    instances = PIPED_INSTANCES.copy()
    random.shuffle(instances)

    for instance in instances:
        try:
            logging.info(f"🔍 Đang tìm trên Piped: {instance}")
            url = f"{instance}/search"
            params = {'q': query, 'filter': 'videos'}
            
            resp = requests.get(url, params=params, timeout=5)
            
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    items = data.get('items', [])
                    if len(items) > 0:
                        for video in items:
                            video_url = video.get('url')
                            title = video.get('title')
                            if video_url:
                                full_link = f"https://www.youtube.com{video_url}"
                                logging.info(f"✅ Đã tìm thấy: {title}")
                                return full_link
                except:
                    continue
        except Exception:
            continue
            
    return None

def get_audio_stream_from_cobalt(url):
    """
    Lấy link tải MP3 từ Cobalt (Có chống lỗi JSON)
    """
    payload = {
        "url": url,
        "vCodec": "h264",
        "vQuality": "720",
        "aFormat": "mp3",
        "isAudioOnly": True
    }
    
    # Headers giả lập trình duyệt để tránh bị chặn
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    instances = COBALT_INSTANCES.copy()
    random.shuffle(instances) # Chọn ngẫu nhiên để giảm tải

    for instance in instances:
        try:
            logging.info(f"⬇️ Thử tải từ Cobalt: {instance}")
            response = requests.post(f"{instance}/api/json", json=payload, headers=headers, timeout=10)
            
            if response.status_code == 200:
                try:
                    data = response.json() # <--- Chỗ này hay bị lỗi nếu server trả về HTML
                    
                    # Cobalt trả về link ở nhiều dạng khác nhau
                    if 'url' in data: 
                        return data['url']
                    elif 'picker' in data:
                        for item in data['picker']:
                            if 'url' in item: return item['url']
                    elif 'audio' in data:
                        return data['audio']
                        
                except json.JSONDecodeError:
                    logging.warning(f"⚠️ {instance} trả về dữ liệu rác, thử server khác.")
                    continue
            else:
                logging.warning(f"⚠️ {instance} lỗi code: {response.status_code}")
                
        except Exception as e:
            logging.error(f"❌ Lỗi kết nối {instance}")
            continue
            
    return None

@app.route('/')
def home():
    return "Xiaozhi Music Server (Super Stable Edition) is Running!"

@app.route('/stream')
def stream_music():
    query = request.args.get('q')
    if not query: return "Thiếu tên bài hát", 400
    
    youtube_link = query
    
    # 1. Tìm kiếm (Nếu không phải là link)
    if not query.startswith("http"):
         found_link = search_with_piped(query)
         if found_link: 
             youtube_link = found_link
         else: 
             return "Không tìm thấy bài hát (Piped bận).", 404

    # 2. Lấy link tải
    audio_url = get_audio_stream_from_cobalt(youtube_link)
    
    if not audio_url: 
        return "Tất cả server Cobalt đều đang bận, vui lòng thử lại sau.", 404

    logging.info(f"🎶 Bắt đầu stream từ: {audio_url}")

    # 3. Chuyển đổi sang PCM cho Robot
    ffmpeg_cmd = [
        'ffmpeg', 
        '-re', 
        '-i', audio_url, 
        '-f', 's16le', 
        '-acodec', 'pcm_s16le', 
        '-ar', '16000', 
        '-ac', '1', 
        '-vn', 
        '-'
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
