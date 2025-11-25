import logging
import requests
import subprocess
import random
from flask import Flask, request, Response, stream_with_context

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Danh sách các Invidious Instances (Server tìm kiếm YouTube ẩn danh)
# Nếu một cái chết, code sẽ tự nhảy sang cái khác
INVIDIOUS_INSTANCES = [
    "https://inv.tux.pizza",
    "https://vid.puffyan.us",
    "https://yt.artemislena.eu",
    "https://invidious.flokinet.to",
    "https://invidious.projectsegfau.lt"
]

# Danh sách Cobalt để tải nhạc
COBALT_INSTANCES = [
    "https://cobalt.pub",
    "https://api.cobalt.best",
    "https://co.wuk.sh",
    "https://cobalt.tools"
]

def search_with_invidious(query):
    """
    Tìm link YouTube thông qua Invidious API
    """
    # Xáo trộn danh sách để giảm tải cho một server
    instances = INVIDIOUS_INSTANCES.copy()
    random.shuffle(instances)

    for instance in instances:
        try:
            logging.info(f"Đang tìm kiếm trên: {instance}")
            # Gọi API tìm kiếm
            url = f"{instance}/api/v1/search"
            params = {'q': query, 'type': 'video', 'sort_by': 'relevance'}
            
            resp = requests.get(url, params=params, timeout=10)
            
            if resp.status_code == 200:
                results = resp.json()
                if len(results) > 0:
                    video = results[0]
                    video_id = video.get('videoId')
                    title = video.get('title')
                    
                    if video_id:
                        youtube_link = f"https://www.youtube.com/watch?v={video_id}"
                        logging.info(f"Đã tìm thấy: {title} ({youtube_link})")
                        return youtube_link
            else:
                logging.warning(f"Instance {instance} lỗi: {resp.status_code}")
        except Exception as e:
            logging.error(f"Lỗi kết nối {instance}: {e}")
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

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    for instance in COBALT_INSTANCES:
        try:
            response = requests.post(f"{instance}/api/json", json=payload, headers=headers, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                if 'url' in data:
                    return data['url']
                elif 'picker' in data:
                    for item in data['picker']:
                        if 'url' in item:
                            return item['url']
        except Exception:
            continue
    
    return None

@app.route('/')
def home():
    return "Xiaozhi Music Server (Invidious Edition) is Running!"

@app.route('/stream')
def stream_music():
    query = request.args.get('q')
    if not query: return "Thiếu tên bài hát (q)", 400
    
    youtube_link = query
    
    # Nếu không phải link, dùng Invidious để tìm
    if not query.startswith("http"):
         found_link = search_with_invidious(query)
         if found_link:
             youtube_link = found_link
         else:
             return "Xin lỗi, server quá tải không tìm được bài hát này.", 404

    logging.info(f"Xử lý link: {youtube_link}")
    
    audio_url = get_audio_stream_from_cobalt(youtube_link)
    
    if not audio_url:
        return "Không lấy được link nhạc từ Cobalt.", 404

    # Convert sang PCM để Robot hát
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
