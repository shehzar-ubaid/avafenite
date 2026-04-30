import runpod
import os
import subprocess
import json
import uuid
import requests
import sys
import shutil

# --- 1. SMART PATH & ENVIRONMENT CHECKER ---
def get_file_path(filename):
    """Scan current directory and subdirectories for the file"""
    if os.path.exists(filename):
        return os.path.abspath(filename)
    for root, dirs, files in os.walk('.'):
        if filename in files:
            return os.path.join(root, filename)
    return None

print("--- Environment Debug Start ---")
# FFmpeg Check for audio splitting/stitching[cite: 16]
try:
    ffmpeg_check = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
    print(f"✅ FFmpeg Found: {ffmpeg_check.stdout.splitlines()[0]}")
except Exception:
    print("❌ FFmpeg NOT FOUND! Check your Dockerfile installation.")

# Workflow JSON Check (Flexible Path)[cite: 16]
# Aapke JSON ka naam yahan confirm karein
WORKFLOW_NAME = "workflow_api.json" 
WORKFLOW_PATH = get_file_path(WORKFLOW_NAME)

if WORKFLOW_PATH:
    print(f"✅ {WORKFLOW_NAME} Found at: {WORKFLOW_PATH}")
    with open(WORKFLOW_PATH, 'r') as f:
        BASE_WORKFLOW = json.load(f)
else:
    print(f"❌ {WORKFLOW_NAME} MISSING! Please check your file structure.")
    BASE_WORKFLOW = {}
print("--- Environment Debug End ---")

# --- 2. UTILITY FUNCTIONS ---

def split_audio(input_path, output_dir):
    """Splits long audio into 30s chunks for stable processing[cite: 16]"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    output_pattern = os.path.join(output_dir, "chunk_%03d.wav")
    print(f"Splitting audio: {input_path}")
    
    subprocess.run([
        'ffmpeg', '-i', input_path, '-f', 'segment',
        '-segment_time', '30', '-c', 'copy', output_pattern, '-y'
    ], check=True)
    
    chunks = sorted([os.path.join(output_dir, f) for f in os.listdir(output_dir) if f.endswith('.wav')])
    print(f"Generated {len(chunks)} chunks.")
    return chunks

def stitch_videos(video_list, output_path):
    """Joins all processed video chunks into one final MP4[cite: 16]"""
    if not video_list:
        return None
        
    list_path = "concat_list.txt"
    with open(list_path, "w") as f:
        for v in video_list:
            f.write(f"file '{os.path.abspath(v)}'\n")
    
    print(f"Stitching {len(video_list)} segments into final video...")
    subprocess.run([
        'ffmpeg', '-f', 'concat', '-safe', '0', '-i', list_path,
        '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-y', output_path
    ], check=True)
    
    if os.path.exists(list_path):
        os.remove(list_path)
    return output_path

# --- 3. CORE HANDLER ---

def handler(job):
    job_input = job['input']
    
    speech_url = job_input.get("speech_url") 
    avatar_url = job_input.get("avatar_url")
    
    if not speech_url or not avatar_url:
        return {"error": "Missing speech_url or avatar_url in input"}

    job_id = str(uuid.uuid4())
    temp_dir = f"/tmp/{job_id}"
    os.makedirs(temp_dir, exist_ok=True)

    try:
        # Step 1: Download Full Audio[cite: 16]
        full_audio_path = os.path.join(temp_dir, "main_speech.wav")
        print(f"Downloading audio from: {speech_url}")
        response = requests.get(speech_url, timeout=60)
        with open(full_audio_path, 'wb') as f:
            f.write(response.content)

        # Step 2: Chunking[cite: 16]
        audio_chunks = split_audio(full_audio_path, os.path.join(temp_dir, "chunks"))
        video_chunks = []

        # Step 3: Loop through chunks for LTX 2.3 processing[cite: 16]
        for i, chunk in enumerate(audio_chunks):
            print(f"🚀 Processing Chunk {i+1}/{len(audio_chunks)}...")
            # Note: Yahan aapka ComfyUI request ka code aayega
            # dummy_video = process_ltx_chunk(chunk, avatar_url, BASE_WORKFLOW)
            # video_chunks.append(dummy_video)

        # Step 4: Final Stitching[cite: 16]
        if video_chunks:
            final_mp4 = os.path.join(temp_dir, "final_result.mp4")
            stitch_videos(video_chunks, final_mp4)
            return {"status": "success", "video_url": "UPLOAD_TO_STORAGE_LINK"}
        
        return {
            "status": "debug_complete", 
            "message": f"FFmpeg checked and {len(audio_chunks)} chunks identified.",
            "workflow_status": "Loaded" if BASE_WORKFLOW else "Missing"
        }

    except Exception as e:
        print(f"Handler Error: {str(e)}")
        return {"status": "error", "message": str(e)}
    
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

# --- 4. START RUNPOD ---
runpod.serverless.start({"handler": handler})