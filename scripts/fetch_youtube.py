#!/usr/bin/env python3
"""Fetch F1 videos from YouTube and save as JSON for the website."""

import os
import json
import re
from datetime import datetime, timezone
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv('/root/.openclaw/workspace/.env')

API_KEY = os.getenv('GOOGLE_API_KEY')
youtube = build('youtube', 'v3', developerKey=API_KEY)

F1_CHANNEL_ID = 'UCB_qr75-ydFVKSF9Dmo6izg'

def parse_duration(duration_iso):
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration_iso)
    if match:
        h, m, s = match.groups()
        h, m, s = int(h or 0), int(m or 0), int(s or 0)
        return f"{h}:{m:02d}:{s:02d}" if h > 0 else f"{m}:{s:02d}"
    return ""

def fetch_channel_videos(channel_id, query_filter=None, max_results=6):
    channel_response = youtube.channels().list(part='contentDetails', id=channel_id).execute()
    if not channel_response['items']:
        return []
    
    uploads_id = channel_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
    playlist_response = youtube.playlistItems().list(
        part='snippet', playlistId=uploads_id, maxResults=50
    ).execute()
    
    videos = []
    for item in playlist_response.get('items', []):
        snippet = item['snippet']
        title = snippet['title'].lower()
        
        if query_filter and not any(q.lower() in title for q in query_filter):
            continue
        
        videos.append({
            'id': snippet['resourceId']['videoId'],
            'title': snippet['title'],
            'thumbnail': snippet['thumbnails'].get('high', snippet['thumbnails']['default'])['url'],
            'channel': snippet['channelTitle'],
            'published': snippet['publishedAt'],
        })
        if len(videos) >= max_results:
            break
    
    if videos:
        video_ids = [v['id'] for v in videos]
        details = youtube.videos().list(part='contentDetails', id=','.join(video_ids)).execute()
        durations = {i['id']: parse_duration(i['contentDetails']['duration']) for i in details['items']}
        for v in videos:
            v['duration'] = durations.get(v['id'], '')
            v['url'] = f"https://www.youtube.com/watch?v={v['id']}"
    
    return videos

def main():
    os.makedirs('data', exist_ok=True)
    
    # Interviews - broader filter
    print("Fetching F1 interviews...")
    interviews = fetch_channel_videos(F1_CHANNEL_ID, 
        query_filter=['react', 'driver', 'speaks', 'says', 'exclusive', 'wrap-up', 'learned'],
        max_results=6)
    with open('data/interviews.json', 'w') as f:
        json.dump({'videos': interviews, 'updated': datetime.now(timezone.utc).isoformat()}, f, indent=2)
    print(f"Saved {len(interviews)} interviews")
    
    # Highlights
    print("Fetching F1 highlights...")
    highlights = fetch_channel_videos(F1_CHANNEL_ID,
        query_filter=['highlight', 'fastest', 'best', 'day', 'testing'],
        max_results=6)
    with open('data/highlights.json', 'w') as f:
        json.dump({'videos': highlights, 'updated': datetime.now(timezone.utc).isoformat()}, f, indent=2)
    print(f"Saved {len(highlights)} highlights")

if __name__ == '__main__':
    main()
