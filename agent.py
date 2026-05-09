import runpod
import os
import subprocess
import json
import uuid
import requests
import sys
import shutil
import base64

# --- 1. UTILITY FUNCTIONS ---

def split_audio_8s(input_path, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    output_pattern = os.path.join(output_dir, "chunk_%03d.wav")
    subprocess.run([
        'ffmpeg', '-i', input_path, '-f', 'segment', 
        '-segment_time', '8', '-c', 'copy', output_pattern, '-y'
    ], check=True)
    return sorted([os.path.join(output_dir, f) for f in os.listdir(output_dir) if f.endswith('.wav')])

def stitch_videos(video_list, output_path):
    if not video_list: return None
    list_path = "concat_list.txt"
    with open(list_path, "w") as f:
        for v in video_list:
            f.write(f"file '{os.path.abspath(v)}'\n")
    subprocess.run([
        'ffmpeg', '-f', 'concat', '-safe', '0', '-i', list_path, 
        '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-y', output_path
    ], check=True)
    if os.path.exists(list_path): os.remove(list_path)
    return output_path

# --- 2. CORE HANDLER ---

def handler(job):
    job_input = job.get('input', {})
    raw_speech = job_input.get("speech_url") 
    avatar_url = job_input.get("avatar_url")
    
    speech_url = None
    if isinstance(raw_speech, dict):
        speech_url = raw_speech.get("audio_base64") or raw_speech.get("audio_url")
    else:
        speech_url = raw_speech

    if not speech_url or not avatar_url:
        return {"status": "FAILED", "message": "Missing inputs: speech or avatar"}

    job_id = str(uuid.uuid4())
    temp_dir = f"/tmp/{job_id}"
    os.makedirs(temp_dir, exist_ok=True)

    try:
        full_audio_path = os.path.join(temp_dir, "main_speech.wav")

        # Step 1: Download/Decode Audio
        if isinstance(speech_url, str) and speech_url.startswith('http'):
            response = requests.get(speech_url, timeout=120)
            with open(full_audio_path, 'wb') as f: f.write(response.content)
        else:
            audio_data = speech_url.split(',')[1] if ',' in speech_url else speech_url
            with open(full_audio_path, 'wb') as f: f.write(base64.b64decode(audio_data))

        # Step 2: Split Audio
        audio_chunks = split_audio_8s(full_audio_path, os.path.join(temp_dir, "chunks"))
        processed_segments = []

        # --- STEP 3: ACTUAL LTX/COMFYUI PROCESSING ---
        for i, chunk in enumerate(audio_chunks):
            print(f"🚀 Processing Segment {i+1}/{len(audio_chunks)}...")
            
            # Segment ke liye output path
            seg_output = os.path.join(temp_dir, f"seg_{i}.mp4")

            # YAHAN APNA ASLI COMMAND LIKHEIN
            # Example (Agar aap koi script chalate hain):
            # subprocess.run(["python", "inference.py", "--audio", chunk, "--image", avatar_url, "--output", seg_output], check=True)
            
            # CHECK: Agar aapka worker sirf dummy hai, toh hum temporary file banate hain testing ke liye
            # LAKIN aapko yahan apna model output append karna hoga:
            if os.path.exists(seg_output):
                processed_segments.append(seg_output)

        # --- STEP 4: STITCHING ---
        if not processed_segments:
            return {
                "status": "FAILED", 
                "message": "Step 3 logic check karein: processed_segments list khali hai. Model ne koi file generate nahi ki."
            }

        final_video_path = os.path.join(temp_dir, "final_output.mp4")
        stitch_videos(processed_segments, final_video_path)
        
        with open(final_video_path, "rb") as f:
            encoded_video = base64.b64encode(f.read()).decode('utf-8')
            
        return {
            "status": "success", 
            "video_base64": encoded_video
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

runpod.serverless.start({"handler": handler})