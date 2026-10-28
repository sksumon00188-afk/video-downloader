import os
import re
import requests
from flask import Flask, render_template, request, jsonify, send_file, after_this_request
import yt_dlp

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_FOLDER = os.path.join(BASE_DIR, 'downloads')
COOKIE_FILE = os.path.join(BASE_DIR, 'cookies.txt')
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# ফেসবুকের শেয়ার লিংকগুলোকে আসল ভিডিও লিংকে রূপান্তর করার ফাংশন
def resolve_url(url):
    try:
        if 'facebook.com/share' in url or 'fb.watch' in url:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
            }
            res = requests.head(url, allow_redirects=True, headers=headers, timeout=10)
            clean_url = res.url.replace('m.facebook.com', 'www.facebook.com')
            return clean_url
    except Exception:
        pass
    return url

def get_base_opts():
    opts = {
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        }
    }
    if os.path.exists(COOKIE_FILE) and os.path.getsize(COOKIE_FILE) > 0:
        opts['cookiefile'] = COOKIE_FILE
        
    return opts

@app.route('/')
def home():
    return render_template('index.html')

# ১. ভিডিও
