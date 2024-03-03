import os
import json
from flask import Flask, render_template, request, jsonify
from pytube import YouTube
from youtube_search import YoutubeSearch
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import re
import ssl
import requests

app = Flask(__name__)

def is_valid_email(email):
    # Regular expression pattern for email validation
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email) is not None

def search_videos(singer_name, num_videos):
    print("Searching for videos...")
    videosSearch = YoutubeSearch(singer_name + ' songs', max_results=num_videos).to_json()
    results = json.loads(videosSearch)

    urls = []
    for video in results["videos"]:
        video_id = video["id"]
        url_suffix = video["url_suffix"]
        youtube_url = f"https://www.youtube.com{url_suffix}"
        print("YouTube Video URL:", youtube_url)
        urls.append(youtube_url)

    return urls

def download_audio(url):
    try:
        yt = YouTube(url)
        audio_stream = yt.streams.filter(only_audio=True, file_extension='mp4').first()
        if audio_stream:
            audio_data = audio_stream.stream_to_buffer()
            return audio_data
        else:
            print(f"No audio stream found for {url}")
            return None
    except Exception as e:
        print(f"An error occurred while downloading audio from {url}: {str(e)}")
        return None


def send_email(email, audio_data):
    sender_email = "vbmashup072@gmail.com"  # Update with your email address
    password = "pxjubdrwqtmpefka"
    port = 465  # For SSL

    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = email
    message["Subject"] = "Mashup Result"

    body = "Please find the result audio attached."
    message.attach(MIMEText(body, "plain"))

    part = MIMEBase("application", "octet-stream")
    part.set_payload(audio_data)
    encoders.encode_base64(part)
    part.add_header(
        "Content-Disposition",
        "attachment; filename= mashup.mp3",
    )
    message.attach(part)

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", port, context=context) as server:
        server.login(sender_email, password)
        server.sendmail(sender_email, email, message.as_string())

@app.route('/', methods=['GET'])
def index():
    return render_template('form.html')

@app.route('/submit', methods=['POST'])
def submit():
    singer_name = request.form.get('singer')
    num_videos = request.form.get('num_videos')
    email = request.form.get('email')

    errors = []

    # Check if all fields are provided
    if not (singer_name and num_videos and email):
        errors.append("All fields are required.")

    # Check if num_videos is an integer
    try:
        num_videos = int(num_videos)
    except ValueError:
        errors.append("Number of videos must be an integer.")

    # Check if num_videos is greater than 0
    if num_videos < 20:
        errors.append("Number of videos must be greater than or equal to 20.")

    # Check if email is valid
    if not email or not is_valid_email(email):
        errors.append("Invalid email address.")

    # If there are errors, return them as JSON response
    if errors:
        return jsonify({'errors': errors})

    try:
        urls = search_videos(singer_name, num_videos)
        audio_data = b''
        for url in urls:
            audio_chunk = download_audio(url)
            if audio_chunk:
                audio_data += audio_chunk
        if audio_data:
            send_email(email, audio_data)
            result = f"Mashup audio for {singer_name} has been created successfully and sent to {email}"
            return jsonify({'result': result})
        else:
            return jsonify({'errors': ["Failed to download audio from all videos."]})
    except Exception as e:
        return jsonify({'errors': [f"An error occurred: {str(e)}"]})

if __name__ == '__main__':
    app.run(debug=True)
