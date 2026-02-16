#!/usr/bin/env python3
"""Build the site by fetching YouTube data and updating HTML."""

import os
import json
import re
from datetime import datetime, timezone
from html import escape
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv('/root/.openclaw/workspace/.env')

API_KEY = os.getenv('GOOGLE_API_KEY')
youtube = build('youtube', 'v3', developerKey=API_KEY)
F1_CHANNEL_ID = 'UCB_qr75-ydFVKSF9Dmo6izg'

def parse_duration(duration_iso):
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration_iso)
    if match:
        h, m, s = [int(x or 0) for x in match.groups()]
        return f"{h}:{m:02d}:{s:02d}" if h > 0 else f"{m}:{s:02d}"
    return ""

def fetch_channel_videos(query_filter=None, max_results=6):
    channel = youtube.channels().list(part='contentDetails', id=F1_CHANNEL_ID).execute()
    if not channel['items']:
        return []
    
    uploads_id = channel['items'][0]['contentDetails']['relatedPlaylists']['uploads']
    playlist = youtube.playlistItems().list(part='snippet', playlistId=uploads_id, maxResults=50).execute()
    
    videos = []
    for item in playlist.get('items', []):
        s = item['snippet']
        title = s['title'].lower()
        if query_filter and not any(q.lower() in title for q in query_filter):
            continue
        videos.append({
            'id': s['resourceId']['videoId'],
            'title': s['title'],
            'thumbnail': s['thumbnails'].get('high', s['thumbnails']['default'])['url'],
        })
        if len(videos) >= max_results:
            break
    
    if videos:
        ids = ','.join(v['id'] for v in videos)
        details = youtube.videos().list(part='contentDetails', id=ids).execute()
        durations = {i['id']: parse_duration(i['contentDetails']['duration']) for i in details['items']}
        for v in videos:
            v['duration'] = durations.get(v['id'], '')
            v['url'] = f"https://www.youtube.com/watch?v={v['id']}"
    return videos

def generate_video_html(videos, first_large=True):
    """Generate HTML for video cards."""
    html = []
    for i, v in enumerate(videos):
        card_class = "video-card" if not (first_large and i == 0) else "video-card"
        html.append(f'''      <a href="{v['url']}" target="_blank" class="{card_class}">
        <div class="video-card-thumb">
          <img src="{v['thumbnail']}" alt="">
          <div class="play-btn"><svg viewBox="0 0 16 16"><polygon points="5,3 13,8 5,13"/></svg></div>
          <span class="video-duration">{v['duration']}</span>
        </div>
        <div class="video-card-title">{escape(v['title'])}</div>
      </a>''')
    return '\n'.join(html)

def generate_highlight_html(videos):
    """Generate HTML for highlight cards."""
    html = []
    for v in videos:
        html.append(f'''      <a href="{v['url']}" target="_blank" class="highlight-card">
        <div class="highlight-card-thumb">
          <img src="{v['thumbnail']}" alt="">
          <div class="play-btn"><svg viewBox="0 0 16 16" fill="#fff"><polygon points="5,3 13,8 5,13"/></svg></div>
          <span class="video-duration">{v['duration']}</span>
        </div>
        <div class="highlight-card-title">{escape(v['title'])}</div>
      </a>''')
    return '\n'.join(html)

def main():
    print("Fetching YouTube data...")
    
    # Fetch interviews
    interviews = fetch_channel_videos(
        query_filter=['react', 'driver', 'speaks', 'says', 'exclusive', 'wrap-up', 'learned', 'interview'],
        max_results=6
    )
    print(f"Got {len(interviews)} interviews")
    
    # Fetch highlights
    highlights = fetch_channel_videos(
        query_filter=['highlight', 'fastest', 'best', 'day', 'testing'],
        max_results=6
    )
    print(f"Got {len(highlights)} highlights")
    
    # Read current HTML
    with open('index.html', 'r') as f:
        html = f.read()
    
    # Replace Featured Video section
    interview_html = generate_video_html(interviews)
    pattern = r'(<div class="video-carousel">)\s*<a href.*?</a>\s*</div>\s*(</div>\s*</section>\s*<!-- ========== EDITOR)'
    replacement = r'\1\n' + interview_html + r'\n    </div>\n  \2'
    html = re.sub(pattern, replacement, html, flags=re.DOTALL)
    
    # Replace Highlights section
    highlight_html = generate_highlight_html(highlights)
    pattern = r'(<div class="highlights-carousel">)\s*<a href.*?</a>\s*</div>\s*(</div>\s*</section>\s*<!-- ========== FOOTER)'
    replacement = r'\1\n' + highlight_html + r'\n    </div>\n  \2'
    html = re.sub(pattern, replacement, html, flags=re.DOTALL)
    
    # Write updated HTML
    with open('index.html', 'w') as f:
        f.write(html)
    
    print("HTML updated!")

if __name__ == '__main__':
    main()
