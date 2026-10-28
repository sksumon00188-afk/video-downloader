import os
import re
from flask import Flask, render_template, request, jsonify, send_file, after_this_request
import yt_dlp

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_FOLDER = os.path.join(BASE_DIR, 'downloads')
COOKIE_FILE = os.path.join(BASE_DIR, 'cookies.txt')
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

def get_base_opts():
    opts = {
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        # PO-Token ছাড়া ক্লাউড আইপি বাইপাস করার জন্য বিশেষ টিভি-এম্বেডেড ও অ্যান্ড্রয়েড ক্লায়েন্ট
        'extractor_args': {
            'youtube': {
                'player_client': ['tv_embedded', 'android', 'ios'],
                'player_skip': ['webpage', 'configs']
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (PlayStation 4 5.05) AppleWebKit/537.78 (KHTML, like Gecko)',
            'Accept-Language': 'en-US,en;q=0.9',
        }
    }
    
    if os.path.exists(COOKIE_FILE) and os.path.getsize(COOKIE_FILE) > 0:
        opts['cookiefile'] = COOKIE_FILE
        
    return opts

@app.route('/')
def home():
    return render_template('index.html')

# ১. ভিডিও ডাউনলোড
@app.route('/download-video', methods=['POST'])
def download_video():
    data = request.get_json() or {}
    url = data.get('url', '').strip()
    if not url:
        return jsonify({'error': 'দয়া করে একটি সঠিক ভিডিও লিংক দিন!'}), 400

    ydl_opts = {
        **get_base_opts(),
        'format': 'best',
        'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(id)s.%(ext)s'),
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_id = info.get('id', 'video')
            raw_title = info.get('title', 'video')
            safe_title = re.sub(r'[\\/*?:"<>|]', "", raw_title)[:50]

            final_filepath = None
            for f in os.listdir(DOWNLOAD_FOLDER):
                if f.startswith(video_id) and not f.endswith('.temp'):
                    final_filepath = os.path.join(DOWNLOAD_FOLDER, f)
                    ext = os.path.splitext(f)[1]
                    break

        if not final_filepath or not os.path.exists(final_filepath):
            return jsonify({'error': 'ভিডিও ফাইল প্রসেস করা সম্ভব হয়নি!'}), 500

        @after_this_request
        def cleanup(response):
            try:
                if os.path.exists(final_filepath):
                    os.remove(final_filepath)
            except Exception:
                pass
            return response

        return send_file(final_filepath, as_attachment=True, download_name=f"{safe_title}{ext}")

    except Exception as e:
        return jsonify({'error': f'ভিডিও ডাউনলোড ব্যর্থ: {str(e)}'}), 500

# ২. সাবটাইটেল ডাউনলোড
@app.route('/download-subtitle', methods=['POST'])
def download_subtitle():
    data = request.get_json() or {}
    url = data.get('url', '').strip()
    if not url:
        return jsonify({'error': 'দয়া করে একটি সঠিক ভিডিও লিংক দিন!'}), 400

    ydl_opts = {
        **get_base_opts(),
        'skip_download': True,
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': ['all'],
        'subtitlesformat': 'srt/vtt/best',
        'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(id)s.%(ext)s'),
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_id = info.get('id', 'subtitles')
            raw_title = info.get('title', 'subtitles')
            safe_title = re.sub(r'[\\/*?:"<>|]', "", raw_title)[:50]

        sub_files = [f for f in os.listdir(DOWNLOAD_FOLDER) if f.startswith(video_id) and (f.endswith('.srt') or f.endswith('.vtt'))]

        if not sub_files:
            return jsonify({'error': 'এই ভিডিওতে কোনো সাবটাইটেল ট্র্যাক পাওয়া যায়নি!'}), 404

        target_file = os.path.join(DOWNLOAD_FOLDER, sub_files[0])
        ext = os.path.splitext(sub_files[0])[1]

        @after_this_request
        def cleanup(response):
            try:
                for f in sub_files:
                    path = os.path.join(DOWNLOAD_FOLDER, f)
                    if os.path.exists(path):
                        os.remove(path)
            except Exception:
                pass
            return response

        return send_file(target_file, as_attachment=True, download_name=f"{safe_title}{ext}")

    except Exception as e:
        return jsonify({'error': f'সাবটাইটেল ডাউনলোড ব্যর্থ: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
