import os
import json
from flask import Flask, render_template, request, jsonify
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import re
import ssl
import youtube_dl

app = Flask(__name__)

def is_valid_email(email):
    # Regular expression pattern for email validation
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email) is not None

def search_videos(singer_name, num_videos):
    print("Searching for videos...")
    # You can add your own logic here to search for videos using the method you prefer
    # This example doesn't include video search functionality
    urls = []  # Placeholder for video URLs
    return urls

def download_audio(url):
    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': '%(title)s.%(ext)s',  # Use title as filename
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }

        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info_dict)
        return filename
    except Exception as e:
        print(f"An error occurred while downloading audio from {url}: {str(e)}")
        return None

def send_email(email, audio_file):
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
    with open(audio_file, "rb") as attachment:
        part.set_payload(attachment.read())
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
        audio_files = []
        for url in urls:
            audio_file = download_audio(url)
            if audio_file:
                audio_files.append(audio_file)
        if audio_files:
            send_email(email, audio_files[0])  # Sending only the first audio file for now
            result = f"Mashup audio for {singer_name} has been created successfully and sent to {email}"
            return jsonify({'result': result})
        else:
            return jsonify({'errors': ["Failed to download audio from all videos."]})
    except Exception as e:
        return jsonify({'errors': [f"An error occurred: {str(e)}"]})

if __name__ == '__main__':
    app.run(debug=True)
