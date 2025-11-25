import logging
import requests
import subprocess
import random
from flask import Flask, request, Response, stream_with_context

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Danh sách các Piped Instances (Thay thế cho Invidious)
# Piped thường ổn định hơn cho việc tìm kiếm
PIPED_INSTANCES = [
    "https://pipedapi.kavin.rocks",
    "https://api.piped.gl",
    "https://pipedapi.adminforge.de",
    "https://api.piped.privacy.com.de",
    "https://pipedapi.drgns.space",
    "https://pa.il.ax"
]

# Danh sách Cobalt để tải nhạc
COBALT_INSTANCES = [
    "https://cobalt.pub",
    "https://api.cobalt.best",
    "https://co.wuk.sh",
    "https://cobalt.tools"
]

def search_with_piped(query):
    """
    Tìm link YouTube thông qua Piped API
    """
    instances = PIPED_INSTANCES.copy()
    random.shuffle(instances)

    for instance in instances:
        try:
            logging.info(f"🔍 Đang tìm kiếm trên Piped: {instance}")
            url = f"{instance}/search"
            params = {'q': query, 'filter': 'videos'}
            
            # Timeout ngắn để chuyển nhanh nếu lỗi
            resp = requests.get(url, params=params, timeout=6)
            
            if resp.status_code == 200:
                data = resp.json()
                items = data.get('items', [])
                if len(items) > 0:
                    # Lấy video đầu tiên không phải là short
                    for video in items:
                        video_url = video.get('url') # Piped trả về đường dẫn /watch?v=...
                        title = video.get('title')
                        if video_url:
                            full_link = f"https://www.youtube.com{video_url}"
                            logging.info(f"✅ Đã tìm thấy: {title} ({full_link})")
                            return full_link
            else:
                logging.warning(f"⚠️ Instance {instance} lỗi: {resp.status_code}")
        except Exception as e:
            logging.error(f"❌ Lỗi kết nối {instance}")
            continue
            
    return None

def get_audio_stream_from_cobalt(url):
    """
    Lấy link tải MP3 từ Cobalt
    """
    payload = {
        "url": url,
        "vCodec": "h264",
        "vQuality": "720",
        "aFormat": "mp3",
        "isAudioOnly": True
    }
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    
    instances = COBALT_INSTANCES.copy()
    random.shuffle(instances)

    for instance in instances:
        try:
            # logging.info(f"Đang tải nhạc từ: {instance}")
            response = requests.post(f"{instance}/api/json", json=payload, headers=headers, timeout=15)
            if response.status_code == 200:
                data = response.json()
                if 'url' in data: return data['url']
                elif 'picker' in data:
                    for item in data['picker']:
                        if 'url' in item: return item['url']
        except Exception:
            continue
    return None

@app.route('/')
def home():
    return "Xiaozhi Music Server (Piped Edition) is Running!"

@app.route('/stream')
def stream_music():
    query = request.args.get('q')
    if not query: return "Thiếu tên bài hát", 400
    
    youtube_link = query
    
    # Nếu không phải link, dùng Piped để tìm
    if not query.startswith("http"):
         found_link = search_with_piped(query)
         if found_link: 
             youtube_link = found_link
         else: 
             return "Xin lỗi, không tìm thấy bài hát (Tất cả server đều bận).", 404

    # Lấy link tải từ Cobalt
    audio_url = get_audio_stream_from_cobalt(youtube_link)
    if not audio_url: return "Lỗi lấy link nhạc từ Cobalt.", 404

    # Convert sang PCM
    ffmpeg_cmd = ['ffmpeg', '-re', '-i', audio_url, '-f', 's16le', '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1', '-vn', '-']
    
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
