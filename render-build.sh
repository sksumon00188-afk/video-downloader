import os
import re
from flask import Flask, render_template, request, send_file, jsonify, after_this_request
import yt_dlp

app = Flask(__name__)

# সাময়িকভাবে ভিডিও রাখার ফোল্ডার
DOWNLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'downloads')
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/download', methods=['POST'])
def download_video():
    data = request.json
    url = data.get('url')

    if not url:
        return jsonify({'error': 'অনুগ্রহ করে একটি সঠিক ভিডিও লিংক দিন।'}), 400

    outtmpl = os.path.join(DOWNLOAD_FOLDER, '%(id)s.%(ext)s')

    ydl_opts = {
        'format': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best',
        'outtmpl': outtmpl,
        'merge_output_format': 'mp4',
        'quiet': True,
        'no_warnings': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_id = info.get('id')
            raw_title = info.get('title', 'video')
            safe_title = re.sub(r'[\\/*?:"<>|]', "", raw_title)[:60]
            download_filename = f"{safe_title}.mp4"

            final_filepath = os.path.join(DOWNLOAD_FOLDER, f"{video_id}.mp4")

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
                download_name=download_filename,
                mimetype='video/mp4'
            )

    except Exception as e:
        return jsonify({'error': f'ডাউনলোড ব্যর্থ হয়েছে: {str(e)}'}), 500

if __name__ == '__main__':
    print("সার্ভার চালু হচ্ছে...")
    app.run(host='0.0.0.0', port=5000, debug=False)