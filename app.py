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

def download_videos(urls):
    print("Downloading videos...")
    for url in urls:
        try:
            YouTube(url).streams.filter(progressive=True, file_extension='mp4').first().download()
        except Exception as e:
            print(f"An error occurred while downloading {url}: {str(e)}")

def convert_to_audio():
    print("Converting videos to audio...")
    for file in os.listdir():
        if file.endswith(".mp4"):
            print(f"Processing video file: {file}")
            try:
                video = VideoFileClip(file)
                audio_file = os.path.splitext(file)[0] + ".mp3"
                video.audio.write_audiofile(audio_file)
                video.close()
                os.remove(file)
            except Exception as e:
                print(f"An error occurred while processing {file}: {str(e)}")

def cut_audio(duration):
    print(f"Cutting first {duration} seconds from audio files...")
    for file in os.listdir():
        if file.endswith(".mp3"):
            audio = AudioFileClip(file)
            new_audio = audio.subclip(0, duration)
            new_audio.write_audiofile(f"cut_{file}")
            audio.close()
            new_audio.close()
            os.remove(file)

def merge_audios(output_file):
    print("Merging audio files...")
    audio_files = [file for file in os.listdir() if file.startswith("cut_")]
    if len(audio_files) == 0:
        print("No audio files to merge.")
        return

    audio_clips = [AudioFileClip(file) for file in audio_files]
    final_clip = concatenate_audioclips(audio_clips)

    final_clip.write_audiofile(output_file)
    final_clip.close()

    for file in audio_files:
        os.remove(file)

    print("Merging completed.")

def send_email(email, file_path):
    sender_email = "vbmashup072@gmail.com"  # Update with your email address
    password = "pxjubdrwqtmpefka"
    port = 465  # For SSL

    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = email
    message["Subject"] = "Mashup Result"

    body = "Please find the result file attached."
    message.attach(MIMEText(body, "plain"))

    with open(file_path, "rb") as attachment:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(attachment.read())

    encoders.encode_base64(part)
    part.add_header(
        "Content-Disposition",
        f"attachment; filename= {os.path.basename(file_path)}",
    )

    message.attach(part)

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", port, context=context) as server:
        server.login(sender_email, password)
        server.sendmail(sender_email, email, message.as_string())

@app.route('/', methods=['GET'])
def index():
    return render_template('form.html')

from flask import jsonify

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

    output_file = f"{singer_name}_mashup.mp3"  # Update with your output file name

    try:
        urls = search_videos(singer_name, num_videos)
        download_videos(urls)
        convert_to_audio()
        cut_audio(duration)
        merge_audios(output_file)
        send_email(email, output_file)
        result = f"Mashup file for {singer_name} has been created successfully and sent to {email}"
        return jsonify({'result': result})
    except Exception as e:
        return jsonify({'errors': [f"An error occurred: {str(e)}"]})

if __name__ == '__main__':
    app.run(debug=True)
