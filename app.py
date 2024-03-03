import os
import json
from flask import Flask, render_template, request, jsonify
from pytube import YouTube
from moviepy.editor import *
from youtube_search import YoutubeSearch
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import re
import ssl

app = Flask(__name__)

def is_valid_email(email):
    # Regular expression pattern for email validation
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email) is not None

def create_youtube_url(url_suffix):
    return f"https://www.youtube.com{url_suffix}"

def search_videos(singer_name, num_videos):
    print("Searching for videos...")
    videosSearch = YoutubeSearch(singer_name + ' songs', max_results=num_videos).to_json()
    results = json.loads(videosSearch)

    urls = []
    for video in results["videos"]:
        video_id = video["id"]
        url_suffix = video["url_suffix"]
        youtube_url = create_youtube_url(url_suffix)
        print("YouTube Video URL:", youtube_url)
        urls.append(youtube_url)

    return urls

def download_video(url):
    try:
        YouTube(url).streams.filter(progressive=True, file_extension='mp4').first().download()
    except Exception as e:
        print(f"An error occurred while downloading {url}: {str(e)}")

def convert_to_audio(video_file):
    print("Converting video to audio...")
    try:
        video = VideoFileClip(video_file)
        audio = video.audio
        return audio
    except Exception as e:
        print(f"An error occurred while processing {video_file}: {str(e)}")

def merge_audios(output_file, audio_files):
    print("Merging audio files...")
    try:
        final_clip = concatenate_audioclips(audio_files)
        final_clip.write_audiofile(output_file)
        final_clip.close()
        print("Merging completed.")
    except Exception as e:
        print(f"An error occurred while merging audio files: {str(e)}")

def send_email(email, audio_data):
    sender_email = "vbmashup072@gmail.com"  # Update with your email address
    password = "pxjubdrwqtmpefka"
    port = 465  # For SSL

    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = email
    message["Subject"] = "Mashup Result"

    body = "Please find the result file attached."
    message.attach(MIMEText(body, "plain"))

    part = MIMEBase("audio", "mp3")
    part.set_payload(audio_data)
    encoders.encode_base64(part)
    part.add_header(
        "Content-Disposition",
        f"attachment; filename= {os.path.basename('mashup.mp3')}",
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
    duration = request.form.get('duration')
    email = request.form.get('email')

    errors = []

    # Check if all fields are provided
    if not (singer_name and num_videos and duration and email):
        errors.append("All fields are required.")

    # Check if num_videos and duration are integers
    try:
        num_videos = int(num_videos)
        duration = int(duration)
    except ValueError:
        errors.append("Number of videos and duration must be integers.")

    # Check if num_videos is greater than 0
    if num_videos < 20:
        errors.append("Number of videos must be greater than or equal to 20.")

    # Check if duration is greater than 0
    if duration < 20:
        errors.append("Duration must be greater than or equal to 20.")

    # Check if email is valid
    if not email or not is_valid_email(email):
        errors.append("Invalid email address.")

    # If there are errors, return them as JSON response
    if errors:
        return jsonify({'errors': errors})

    output_file = "mashup.mp3"  # Hardcoded output file name
    audio_files = []

    try:
        urls = search_videos(singer_name, num_videos)
        for url in urls:
            download_video(url)
            video_file = f"{YouTube(url).title}.mp4"
            audio = convert_to_audio(video_file)
            audio_files.append(audio)
        merge_audios(output_file, audio_files)
        with open(output_file, "rb") as audio_data:
            audio_binary = audio_data.read()
        send_email(email, audio_binary)
        result = f"Mashup file for {singer_name} has been created successfully and sent to {email}"
        return jsonify({'result': result})
    except Exception as e:
        return jsonify({'errors': [f"An error occurred: {str(e)}"]})

if __name__ == '__main__':
    app.run(debug=True)
