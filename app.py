import os
import re
from flask import Flask, render_template, request, jsonify, send_file, after_this_request
import yt_dlp

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_FOLDER = os.path.join(BASE_DIR, 'downloads')
COOKIE_FILE = os.path.join(BASE_DIR, 'cookies.txt')
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

def get_ytdl_base_opts():
    opts = {
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        # একাধিক ক্লায়েন্ট ফলব্যাক (অ্যান্ড্রয়েড, আইওএস ও ওয়েব)
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'ios', 'web'],
                'player_skip': ['configs']
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        }
    }
    
    # কুকিজ ফাইল উপস্থিত থাকলে সেটি স্বয়ংক্রিয়ভাবে যুক্ত হবে
    if os.path.exists(COOKIE_FILE):
        opts['cookiefile'] = COOKIE_FILE
        
    return opts

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/download-video', methods=['POST'])
def download_video():
    data = request.get_json() or {}
    url = data.get('url', '').strip()
    
    if not url:
        return jsonify({'error': 'দয়া করে একটি সঠিক ভিডিও লিংক দিন!'}), 400

    ydl_opts = {
        **get_ytdl_base_opts(),
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(id)s.%(ext)s'),
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_id = info.get('id')
            raw_title = info.get('title', 'video')
            safe_title = re.sub(r'[\\/*?:"<>|]', "", raw_title)[:60]
            download_filename = f"{safe_title}.mp4"

            final_filepath = os.path.join(DOWNLOAD_FOLDER, f"{video_id}.mp4")
            
            if not os.path.exists(final_filepath):
                for f in os.listdir(DOWNLOAD_FOLDER):
                    if f.startswith(video_id) and not f.endswith('.temp'):
                        final_filepath = os.path.join(DOWNLOAD_FOLDER, f)
                        download_filename = f"{safe_title}{os.path.splitext(f)[1]}"
                        break

        @after_this_request
        def cleanup(response):
            try:
                if os.path.exists(final_filepath):
                    os.remove(final_filepath)
            except Exception as e:
                print(f"Cleanup error: {e}")
            return response

        return send_file(
            final_filepath,
            as_attachment=True,
            download_name=download_filename
        )

    except Exception as e:
        return jsonify({'error': f'{str(e)}'}), 500

@app.route('/download-subtitle', methods=['POST'])
def download_subtitle():
    data = request.get_json() or {}
    url = data.get('url', '').strip()
    
    if not url:
        return jsonify({'error': 'দয়া করে একটি সঠিক ভিডিও লিংক দিন!'}), 400

    ydl_opts = {
        **get_ytdl_base_opts(),
        'skip_download': True,
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': ['all'],
        'subtitlesformat': 'srt/vtt/best',
        'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(id)s'),
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_id = info.get('id')
            raw_title = info.get('title', 'subtitles')
            safe_title = re.sub(r'[\\/*?:"<>|]', "", raw_title)[:60]

        sub_files = [f for f in os.listdir(DOWNLOAD_FOLDER) if f.startswith(video_id) and (f.endswith('.srt') or f.endswith('.vtt'))]
        
        if not sub_files:
            return jsonify({'error': 'এই ভিডিওতে কোনো সাবটাইটেল পাওয়া যায়নি!'}), 404

        target_file = sub_files[0]
        ext = os.path.splitext(target_file)[1]
        final_filepath = os.path.join(DOWNLOAD_FOLDER, target_file)
        download_filename = f"{safe_title}{ext}"

        @after_this_request
        def cleanup(response):
            try:
                for f in sub_files:
                    path = os.path.join(DOWNLOAD_FOLDER, f)
                    if os.path.exists(path):
                        os.remove(path)
            except Exception as e:
                print(f"Cleanup error: {e}")
            return response

        return send_file(
            final_filepath,
            as_attachment=True,
            download_name=download_filename,
            mimetype='text/plain'
        )

    except Exception as e:
        return jsonify({'error': f'{str(e)}'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
