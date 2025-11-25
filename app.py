import logging
import requests
import subprocess
from flask import Flask, request, Response, stream_with_context
from duckduckgo_search import DDGS

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Danh sách các Cobalt Instance
COBALT_INSTANCES = [
    "[https://cobalt.pub](https://cobalt.pub)",
    "[https://api.cobalt.best](https://api.cobalt.best)",
    "[https://co.wuk.sh](https://co.wuk.sh)",
    "[https://cobalt.tools](https://cobalt.tools)"
]

def search_youtube_video(query):
    """
    Tìm link YouTube thông qua DuckDuckGo (Tránh bị YouTube chặn IP)
    """
    try:
        logging.info(f"Đang tìm kiếm qua DuckDuckGo: {query}")
        # Tìm kiếm video trên youtube thông qua DDG
        with DDGS() as ddgs:
            # Tìm kiếm với từ khóa "site:youtube.com [tên bài hát]"
            results = list(ddgs.videos(f"{query} site:youtube.com", max_results=1))
            
            if results:
                # Kết quả trả về thường có key 'content' là link video
                video_url = results[0].get('content')
                if not video_url:
                     # Fallback nếu cấu trúc khác
                     video_url = results[0].get('href')
                
                title = results[0].get('title', 'Unknown Title')
                
                logging.info(f"Đã tìm thấy: {title} - {video_url}")
                return video_url, title
                
        logging.warning("Không tìm thấy kết quả nào qua DuckDuckGo")
        return None, None
    except Exception as e:
        logging.error(f"Lỗi tìm kiếm DuckDuckGo: {e}")
        return None, None

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
            # logging.info(f"Thử Cobalt: {instance}")
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
    return "Xiaozhi Music Server (Final DuckDuckGo Edition) is Live!"

@app.route('/stream')
def stream_music():
    query = request.args.get('q')
    if not query: return "Thiếu tên bài hát (q)", 400
    
    youtube_link = query
    
    # Nếu người dùng nhập tên bài hát (không phải link), thì đi tìm
    if not query.startswith("http"):
         found_link, found_title = search_youtube_video(query)
         if found_link:
             youtube_link = found_link
         else:
             return "Không tìm thấy bài hát này.", 404

    logging.info(f"Xử lý link: {youtube_link}")
    
    audio_url = get_audio_stream_from_cobalt(youtube_link)
    
    if not audio_url:
        return "Server quá tải, không lấy được nhạc.", 404

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
