import wave
import json
import os
import subprocess
import sys
from vosk import Model, KaldiRecognizer

# Paths
MODEL_PATH = "models/vosk-model-small-en-us-0.15"  # Update with your Vosk model path
PROCESSED_FILES_LOG = "processed_videos.txt"

# Check if model exists
if not os.path.exists(MODEL_PATH):
    print("❌ Vosk model not found! Download and extract it into 'models/'")
    exit(1)

# Load previously processed files
if os.path.exists(PROCESSED_FILES_LOG):
    with open(PROCESSED_FILES_LOG, "r") as log_file:
        processed_files = set(log_file.read().splitlines())
else:
    processed_files = set()

# Get input (files or directory)
if len(sys.argv) < 2:
    print("Usage: python transcribe_videos.py <video_file1> <video_file2> ... OR python transcribe_videos.py <directory>")
    exit(1)

input_path = sys.argv[1]
video_files = []

if os.path.isdir(input_path):
    # Get all video files in the directory
    video_files = [os.path.join(input_path, f) for f in os.listdir(input_path) if f.endswith(('.mp4', '.mkv', '.avi', '.mov'))]
else:
    video_files = sys.argv[1:]

# Filter out already processed files
video_files = [f for f in video_files if f not in processed_files]

if not video_files:
    print("✅ No new videos to process.")
    exit(0)

for VIDEO_INPUT in video_files:
    AUDIO_CONVERTED = "audio_temp.wav"  # Extracted audio file
    OUTPUT_SRT = os.path.splitext(VIDEO_INPUT)[0] + ".srt"  # Subtitles file

    print(f"🎬 Processing: {VIDEO_INPUT}")
    
    # Extract audio from video
    print("🎵 Extracting audio from video...")
    subprocess.run(["ffmpeg", "-i", VIDEO_INPUT, "-ac", "1", "-ar", "16000", "-vn", AUDIO_CONVERTED, "-y"], 
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("✅ Audio extracted successfully.")

    # Load Vosk model
    model = Model(MODEL_PATH)
    recognizer = KaldiRecognizer(model, 16000)
    recognizer.SetWords(True)  # Enable word timestamps

    # Process audio and generate subtitles
    print("📝 Transcribing audio...")
    with wave.open(AUDIO_CONVERTED, "rb") as wf:
        with open(OUTPUT_SRT, "w") as srt_file:
            index = 1
            phrase = []
            start_time = None

            while True:
                data = wf.readframes(4000)
                if len(data) == 0:
                    break
                if recognizer.AcceptWaveform(data):
                    result = json.loads(recognizer.Result())
                    if "result" in result:
                        words = result["result"]
                        for word in words:
                            if start_time is None:
                                start_time = word["start"]

                            phrase.append(word["word"])

                            # End phrase after 9 words
                            if len(phrase) >= 9:  
                                end_time = word["end"]

                                # Convert timestamps to SRT format (hh:mm:ss,ms)
                                start_srt = f"{int(start_time // 3600):02}:{int((start_time % 3600) // 60):02}:{int(start_time % 60):02},{int((start_time % 1) * 1000):03}"
                                end_srt = f"{int(end_time // 3600):02}:{int((end_time % 3600) // 60):02}:{int(end_time % 60):02},{int((end_time % 1) * 1000):03}"

                                # Write to SRT file
                                srt_file.write(f"{index}\n{start_srt} --> {end_srt}\n{' '.join(phrase)}\n\n")

                                # Reset for next subtitle
                                index += 1
                                phrase = []
                                start_time = None

            # Handle any remaining words
            if phrase:
                end_time = words[-1]["end"]
                start_srt = f"{int(start_time // 3600):02}:{int((start_time % 3600) // 60):02}:{int(start_time % 60):02},{int((start_time % 1) * 1000):03}"
                end_srt = f"{int(end_time // 3600):02}:{int((end_time % 3600) // 60):02}:{int(end_time % 60):02},{int((end_time % 1) * 1000):03}"

                srt_file.write(f"{index}\n{start_srt} --> {end_srt}\n{' '.join(phrase)}\n\n")

    print(f"✅ Subtitles saved to {OUTPUT_SRT}")

    # Cleanup temporary files
    os.remove(AUDIO_CONVERTED)
    print("🗑️ Temporary audio file deleted.")

    # Mark as processed
    with open(PROCESSED_FILES_LOG, "a") as log_file:
        log_file.write(VIDEO_INPUT + "\n")

print("🎉 All videos processed successfully!")
