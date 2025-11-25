import logging
import requests
import subprocess
import random
from flask import Flask, request, Response, stream_with_context
from ytmusicapi import YTMusic

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Khởi tạo YouTube Music API
ytmusic = YTMusic()

# Danh sách Cobalt để tải nhạc
COBALT_INSTANCES = [
    "https://cobalt.pub",
    "https://api.cobalt.best",
    "https://co.wuk.sh",
    "https://cobalt.tools"
]

def search_with_ytmusic(query):
    """
    Tìm link bài hát thông qua YouTube Music API
    """
    try:
        logging.info(f"🔍 Đang tìm trên YouTube Music: {query}")
        # Tìm kiếm bài hát (filter=songs để ra kết quả chính xác nhất)
        results = ytmusic.search(query, filter='songs')
        
        if results and len(results) > 0:
            # Lấy kết quả đầu tiên
            song = results[0]
            video_id = song.get('videoId')
            title = song.get('title')
            
            if video_id:
                full_link = f"https://www.youtube.com/watch?v={video_id}"
                logging.info(f"✅ Đã tìm thấy: {title} ({full_link})")
                return full_link
        
        # Nếu không tìm thấy bài hát, thử tìm video thường
        results = ytmusic.search(query, filter='videos')
        if results and len(results) > 0:
            video = results[0]
            video_id = video.get('videoId')
            if video_id:
                return f"https://www.youtube.com/watch?v={video_id}"

    except Exception as e:
        logging.error(f"❌ Lỗi tìm kiếm YT Music: {e}")
        return None
            
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
    return "Xiaozhi Music Server (YouTube Music Edition) is Running!"

@app.route('/stream')
def stream_music():
    query = request.args.get('q')
    if not query: return "Thiếu tên bài hát", 400
    
    youtube_link = query
    
    # Nếu không phải link, dùng YT Music để tìm
    if not query.startswith("http"):
         found_link = search_with_ytmusic(query)
         if found_link: 
             youtube_link = found_link
         else: 
             return "Xin lỗi, không tìm thấy bài hát này.", 404

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
