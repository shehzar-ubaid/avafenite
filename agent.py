import runpod
import os
import subprocess
import json
import uuid
import requests
import sys
import shutil
import base64
from pydub import AudioSegment
from faster_whisper import WhisperModel

# ====================== UTILITY FUNCTIONS ======================

def split_audio_8s(input_path, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    # Pydub se better splitting (accurate timestamps)
    audio = AudioSegment.from_file(input_path)
    chunk_len = 8000  # 8 seconds in ms
    chunks = [audio[i:i+chunk_len] for i in range(0, len(audio), chunk_len)]
    
    chunk_files = []
    for idx, chunk in enumerate(chunks):
        path = os.path.join(output_dir, f"chunk_{idx:03d}.wav")
        chunk.export(path, format="wav")
        chunk_files.append(path)
    return chunk_files


def stitch_videos(video_list, output_path):
    if not video_list:
        return None
    list_path = "concat_list.txt"
    with open(list_path, "w") as f:
        for v in video_list:
            f.write(f"file '{os.path.abspath(v)}'\n")
    
    subprocess.run([
        'ffmpeg', '-f', 'concat', '-safe', '0', '-i', list_path,
        '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-y', output_path
    ], check=True)
    
    if os.path.exists(list_path):
        os.remove(list_path)
    return output_path


def generate_subtitles(audio_path, srt_path, model_size="base"):
    """faster-whisper se subtitles generate"""
    model = WhisperModel(model_size, device="cuda" if os.path.exists("/usr/local/cuda") else "cpu", compute_type="float16")
    segments, info = model.transcribe(audio_path, beam_size=5, word_timestamps=True)
    
    with open(srt_path, "w", encoding="utf-8") as f:
        for i, segment in enumerate(segments, start=1):
            f.write(f"{i}\n")
            f.write(f"{segment.start:.2f} --> {segment.end:.2f}\n")
            f.write(f"{segment.text.strip()}\n\n")
    return srt_path


def add_subtitles_to_video(video_path, srt_path, output_path, font_size=24, font_color="FFFFFF", font_name="Arial"):
    """FFmpeg se styled subtitles add"""
    style = f"Fontsize={font_size},PrimaryColour=&H{font_color}&,Fontname={font_name},Alignment=2"
    subprocess.run([
        'ffmpeg', '-i', video_path, '-vf',
        f"subtitles={srt_path}:force_style='{style}'",
        '-c:v', 'libx264', '-crf', '20', '-y', output_path
    ], check=True)
    return output_path


def create_quality_versions(input_video, output_dir, base_name="final"):
    qualities = {
        "1080p": ("1920x1080", 23),
        "4k": ("3840x2160", 20),
        "8k": ("7680x4320", 18)
    }
    outputs = {}
    for name, (res, crf) in qualities.items():
        out_path = os.path.join(output_dir, f"{base_name}_{name}.mp4")
        subprocess.run([
            'ffmpeg', '-i', input_video, '-s', res, '-crf', str(crf),
            '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-y', out_path
        ], check=False)  # check=False kyunke 8K bohot heavy hota hai
        outputs[name] = out_path
    return outputs


# ====================== MAIN HANDLER ======================

def handler(job):
    job_input = job.get('input', {})
    
    speech_url = job_input.get("speech_url") or job_input.get("audio_url") or job_input.get("audio_base64")
    avatar_url = job_input.get("avatar_url") or job_input.get("image_url")
    
    # User preferences
    font_size = job_input.get("font_size", 28)
    font_color = job_input.get("font_color", "FFFFFF")
    font_name = job_input.get("font_name", "Arial")
    quality = job_input.get("quality", "1080p")   # 1080p, 4k, 8k

    if not speech_url or not avatar_url:
        return {"status": "FAILED", "message": "Missing speech or avatar input"}

    job_id = str(uuid.uuid4())
    temp_dir = f"/tmp/{job_id}"
    os.makedirs(temp_dir, exist_ok=True)

    try:
        full_audio_path = os.path.join(temp_dir, "main_speech.wav")

        # Download / Decode Audio
        if isinstance(speech_url, str) and speech_url.startswith('http'):
            response = requests.get(speech_url, timeout=120)
            with open(full_audio_path, 'wb') as f:
                f.write(response.content)
        else:
            # Base64 handling
            audio_data = speech_url.split(',')[1] if isinstance(speech_url, str) and ',' in speech_url else speech_url
            with open(full_audio_path, 'wb') as f:
                f.write(base64.b64decode(audio_data))

        # Step 1: Split Audio
        audio_chunks = split_audio_8s(full_audio_path, os.path.join(temp_dir, "chunks"))
        processed_segments = []

        # Step 2: Lip-Sync per chunk
        for i, chunk in enumerate(audio_chunks):
            print(f"🚀 Processing Segment {i+1}/{len(audio_chunks)}...")
            seg_output = os.path.join(temp_dir, f"seg_{i:03d}.mp4")

            try:
                subprocess.run([
                    "python", "inference.py",
                    "--input_image", avatar_url,
                    "--input_audio", chunk,
                    "--output_video", seg_output
                ], check=True, cwd=os.getcwd())

                if os.path.exists(seg_output):
                    processed_segments.append(seg_output)
            except Exception as e:
                print(f"Segment {i} failed: {e}")

        if not processed_segments:
            return {"status": "FAILED", "message": "No video segments generated. Check inference.py"}

        # Step 3: Stitch
        stitched_path = os.path.join(temp_dir, "stitched.mp4")
        stitch_videos(processed_segments, stitched_path)

        # Step 4: Generate & Add Subtitles
        srt_path = os.path.join(temp_dir, "subtitles.srt")
        generate_subtitles(full_audio_path, srt_path)
        
        subbed_path = os.path.join(temp_dir, "final_with_subtitles.mp4")
        add_subtitles_to_video(stitched_path, srt_path, subbed_path, font_size, font_color, font_name)

        # Step 5: Create Quality Versions
        quality_dir = os.path.join(temp_dir, "qualities")
        os.makedirs(quality_dir, exist_ok=True)
        quality_files = create_quality_versions(subbed_path, quality_dir)

        # Return selected quality (default 1080p)
        final_output_path = quality_files.get(quality, quality_files["1080p"])

        with open(final_output_path, "rb") as f:
            video_base64 = base64.b64encode(f.read()).decode('utf-8')

        return {
            "status": "success",
            "video_base64": video_base64,
            "message": f"Video generated successfully in {quality}"
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


runpod.serverless.start({"handler": handler})