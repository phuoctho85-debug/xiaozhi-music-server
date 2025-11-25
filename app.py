import logging
import requests
import subprocess
from flask import Flask, request, jsonify, Response, stream_with_context
from youtubesearchpython import VideosSearch

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Danh sách các instance Cobalt công khai
COBALT_INSTANCES = [
    "[https://cobalt.pub](https://cobalt.pub)",
    "[https://api.cobalt.best](https://api.cobalt.best)",
    "[https://co.wuk.sh](https://co.wuk.sh)",
    "[https://cobalt.tools](https://cobalt.tools)"
]

def search_youtube_video(query):
    """
    Tìm kiếm video đầu tiên trên YouTube dựa vào từ khóa
    """
    try:
        logging.info(f"Đang tìm kiếm YouTube với từ khóa: {query}")
        videos_search = VideosSearch(query, limit=1)
        results = videos_search.result()
        
        if results['result']:
            video_info = results['result'][0]
            title = video_info['title']
            link = video_info['link']
            logging.info(f"Đã tìm thấy video: {title} ({link})")
            return link, title
        return None, None
    except Exception as e:
        logging.error(f"Lỗi tìm kiếm YouTube: {e}")
        return None, None

def get_audio_stream_from_cobalt(url):
    """
    Gửi link YouTube sang Cobalt để lấy link tải MP3
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
            logging.info(f"Đang thử lấy link từ Cobalt instance: {instance}")
            response = requests.post(f"{instance}/api/json", json=payload, headers=headers, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                if 'url' in data:
                    return data['url']
                elif 'picker' in data:
                    for item in data['picker']:
                        if 'url' in item:
                            return item['url']
            else:
                logging.warning(f"Instance {instance} trả về lỗi: {response.status_code}")
        except Exception as e:
            logging.error(f"Lỗi kết nối đến {instance}: {e}")
            continue
    
    return None

@app.route('/')
def home():
    return "Xiaozhi Music Server (Cobalt + Search Edition) is Running!"

@app.route('/stream')
def stream_music():
    query = request.args.get('q')
    if not query:
        return "Thiếu tham số q", 400
    
    youtube_link = query
    video_title = "Unknown"

    # Nếu query không phải là link, thực hiện tìm kiếm
    if not query.startswith("http"):
         youtube_link, video_title = search_youtube_video(query)
         if not youtube_link:
             return "Không tìm thấy video nào trên YouTube với từ khóa này", 404

    logging.info(f"Đang xử lý link: {youtube_link}")
    
    audio_url = get_audio_stream_from_cobalt(youtube_link)
    
    if not audio_url:
        return "Không lấy được link stream từ Cobalt (Server quá tải hoặc video bị chặn)", 404

    logging.info(f"Đã lấy được link stream MP3: {audio_url}")
    
    # Stream và chuyển đổi MP3 sang PCM bằng FFmpeg
    ffmpeg_cmd = [
        'ffmpeg',
        '-re',
        '-i', audio_url,      # Input là link MP3 từ Cobalt
        '-f', 's16le',        # Output PCM
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
