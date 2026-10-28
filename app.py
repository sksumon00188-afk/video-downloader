import os
import re
from flask import Flask, render_template, request, jsonify, send_file, after_this_request
import yt_dlp

app = Flask(__name__)
DOWNLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'downloads')
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# ইউটিউব বট বাইপাস করার ক্লায়েন্ট কনফিগারেশন
YTDL_BASE_OPTS = {
    'quiet': True,
    'no_warnings': True,
    'extractor_args': {
        'youtube': {
            'player_client': ['ios', 'android']
        }
    },
    'http_headers': {
        'User-Agent': 'com.google.ios.youtube/19.29.1 (iPhone14,5; U; CPU iOS 17_5_1 like Mac OS X; en_US)'
    }
}

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/download-video', methods=['POST'])
def download_video():
    data = request.get_json() or {}
    url = data.get('url', '').strip()
    
    if not url:
        return jsonify({'error': 'দয়া করে একটি সঠিক ভিডিও লিংক দিন!'}), 400

    ydl_opts = {
        **YTDL_BASE_OPTS,
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
            
            # এক্সটেনশন ভিন্ন হলে খুঁজে নেওয়া
            if not os.path.exists(final_filepath):
                for f in os.listdir(DOWNLOAD_FOLDER):
                    if f.startswith(video_id):
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
        return jsonify({'error': 'দয়া করে একটি সঠিক ভিডিও লিংক দিন!'}), 400

    ydl_opts = {
        **YTDL_BASE_OPTS,
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
            return jsonify({'error': 'এই ভিডিওতে কোনো সাবটাইটেল পাওয়া যায়নি!'}), 404

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
