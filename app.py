import logging
import requests
from flask import Flask, request, jsonify, Response, stream_with_context

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Danh sách các instance Cobalt công khai
# Nếu một cái bị lỗi, code sẽ tự thử cái tiếp theo
COBALT_INSTANCES = [
    "[https://cobalt.pub](https://cobalt.pub)",
    "[https://api.cobalt.best](https://api.cobalt.best)",
    "[https://co.wuk.sh](https://co.wuk.sh)",
    "[https://cobalt.tools](https://cobalt.tools)"
]

def get_audio_stream_from_cobalt(query):
    # Cấu hình request gửi đến Cobalt để lấy MP3
    payload = {
        "url": query,
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
            logging.info(f"Đang thử lấy link từ: {instance}")
            response = requests.post(f"{instance}/api/json", json=payload, headers=headers, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                # Cobalt trả về link trong trường 'url' hoặc 'picker'
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
    return "Xiaozhi Music Server (Cobalt Edition) is Running!"

@app.route('/stream')
def stream_music():
    query = request.args.get('q')
    if not query:
        return "Thiếu tham số q", 400
    
    # Cobalt yêu cầu link đầy đủ, không hỗ trợ từ khóa
    # Tạm thời yêu cầu người dùng nhập link youtube
    if not query.startswith("http"):
         return "Vui lòng nhập link YouTube đầy đủ (ví dụ: [https://www.youtube.com/watch?v=](https://www.youtube.com/watch?v=)...)", 400

    logging.info(f"Đang xử lý link: {query}")
    
    audio_url = get_audio_stream_from_cobalt(query)
    
    if not audio_url:
        return "Không lấy được link stream từ Cobalt (Tất cả instance đều bận)", 404

    logging.info(f"Đã lấy được link stream: {audio_url}")
    
    # Stream dữ liệu từ link Cobalt về cho client
    # Lưu ý: Cobalt trả về MP3, không phải PCM. 
    # Robot cần hỗ trợ giải mã MP3 hoặc server này phải convert lại.
    # Để đơn giản và tương thích với code robot hiện tại (đang chờ PCM),
    # ta sẽ dùng FFmpeg để convert MP3 từ Cobalt sang PCM trước khi gửi đi.
    
    import subprocess
    
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
