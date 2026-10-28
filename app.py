import os
import re
from flask import Flask, render_template, request, jsonify, send_file, after_this_request
import yt_dlp

app = Flask(__name__)
DOWNLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'downloads')
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# ফেসবুক, ইনস্টাগ্রাম, এক্স (টুইটার), ইউটিউব সহ সব ওয়েবসাইটের জন্য সার্বজনীন কনফিগারেশন
BASE_OPTS = {
    'quiet': True,
    'no_warnings': True,
    'nocheckcertificate': True,
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
    }
}

@app.route('/')
def home():
    return render_template('index.html')

# ১. যেকোনো ওয়েবসাইট থেকে ভিডিও ডাউনলোড
@app.route('/download-video', methods=['POST'])
def download_video():
    data = request.get_json() or {}
    url = data.get('url', '').strip()
    if not url:
        return jsonify({'error': 'দয়া করে একটি লিংক দিন!'}), 400

    ydl_opts = {
        **BASE_OPTS,
        'format': 'best[ext=mp4]/bestvideo+bestaudio/best',
        'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(id)s.%(ext)s'),
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_id = info.get('id', 'video')
            raw_title = info.get('title', 'downloaded_video')
            safe_title = re.sub(r'[\\/*?:"<>|]', "", raw_title)[:50]
            
            final_file = None
            for f in os.listdir(DOWNLOAD_FOLDER):
                if f.startswith(video_id):
                    final_file = os.path.join(DOWNLOAD_FOLDER, f)
                    ext = os.path.splitext(f)[1]
                    break

        if not final_file or not os.path.exists(final_file):
            return jsonify({'error': 'ভিডিও ফাইল প্রসেস করা যায়নি!'}), 500

        @after_this_request
        def cleanup(response):
            try:
                if os.path.exists(final_file):
                    os.remove(final_file)
            except Exception:
                pass
            return response

        return send_file(final_file, as_attachment=True, download_name=f"{safe_title}{ext}")

    except Exception as e:
        return jsonify({'error': f'ডাউনলোড ব্যর্থ হয়েছে: {str(e)}'}), 500

# ২. যেকোনো ওয়েবসাইট থেকে সাবটাইটেল ডাউনলোড
@app.route('/download-subtitle', methods=['POST'])
def download_subtitle():
    data = request.get_json() or {}
    url = data.get('url', '').strip()
    if not url:
        return jsonify({'error': 'দয়া করে একটি লিংক দিন!'}), 400

    ydl_opts = {
        **BASE_OPTS,
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
            video_id = info.get('id', 'subtitles')
            raw_title = info.get('title', 'subtitles')
            safe_title = re.sub(r'[\\/*?:"<>|]', "", raw_title)[:50]

        sub_files = [f for f in os.listdir(DOWNLOAD_FOLDER) if f.startswith(video_id) and (f.endswith('.srt') or f.endswith('.vtt'))]
        
        if not sub_files:
            return jsonify({'error': 'এই ভিডিওতে কোনো সাবটাইটেল পাওয়া যায়নি!'}), 404

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
        return jsonify({'error': f'সাবটাইটেল পাওয়া যায়নি: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
