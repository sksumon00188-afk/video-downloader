import os
import glob
import re
from flask import Flask, render_template, request, jsonify, send_file, after_this_request
import yt_dlp

app = Flask(__name__)

# টেম্পোরারি ডাউনলোড ফোল্ডার
DOWNLOAD_DIR = os.path.join(os.getcwd(), 'temp_downloads')
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def clean_ansi(text):
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/download', methods=['POST'])
def handle_download():
    data = request.get_json()
    url = data.get('url', '').strip()
    mode = data.get('mode', 'video') # 'video' অথবা 'subtitle'

    if not url:
        return jsonify({"status": "error", "message": "ভিডিও লিংক দিন!"}), 400

    out_template = os.path.join(DOWNLOAD_DIR, '%(id)s.%(ext)s')

    # ১. সাবটাইটেল ডাউনলোডের কনফিগারেশন
    if mode == 'subtitle':
        ydl_opts = {
            'skip_download': True,
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': ['all', 'bn', 'en'],
            'subtitlesformat': 'srt/vtt/best',
            'outtmpl': os.path.join(DOWNLOAD_DIR, '%(id)s'),
            'quiet': True,
            'no_warnings': True
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                video_id = info.get('id', 'sub')

            sub_files = glob.glob(os.path.join(DOWNLOAD_DIR, f"{video_id}*.*"))
            if not sub_files:
                return jsonify({"status": "error", "message": "এই ভিডিওতে কোনো সাবটাইটেল পাওয়া যায়নি!"}), 404

            chosen_file = sub_files[0]

            @after_this_request
            def cleanup(response):
                try:
                    for f in sub_files:
                        if os.path.exists(f): os.remove(f)
                except Exception:
                    pass
                return response

            return send_file(chosen_file, as_attachment=True)

        except Exception as e:
            return jsonify({"status": "error", "message": clean_ansi(str(e))}), 500

    # ২. ভিডিও ডাউনলোডের কনফিগারেশন
    else:
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': out_template,
            'merge_output_format': 'mp4',
            'quiet': True,
            'no_warnings': True
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                if not filename.endswith('.mp4'):
                    filename = os.path.splitext(filename)[0] + '.mp4'

            @after_this_request
            def cleanup(response):
                try:
                    if os.path.exists(filename):
                        os.remove(filename)
                except Exception:
                    pass
                return response

            safe_title = re.sub(r'[^a-zA-Z0-9_\- ]', '_', info.get('title', 'video'))
            return send_file(filename, as_attachment=True, download_name=f"{safe_title}.mp4")

        except Exception as e:
            return jsonify({"status": "error", "message": clean_ansi(str(e))}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)