import runpod
import os
import subprocess
import json
import uuid
import requests
import sys
import shutil

# --- 1. SMART PATH & ENVIRONMENT CHECKER ---
def get_file_path(filenames):
    """Multiple filenames check karta hai taake crash na ho[cite: 19]"""
    for filename in filenames:
        if os.path.exists(filename):
            return os.path.abspath(filename)
        for root, dirs, files in os.walk('.'):
            if filename in files:
                return os.path.join(root, filename)
    return None

print("--- Environment Debug Start ---")
# FFmpeg Check
try:
    subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, check=True)
    print("✅ FFmpeg Found and Operational") # Simplified log to prevent splitline errors[cite: 19]
except Exception:
    print("❌ FFmpeg NOT FOUND! Check your Dockerfile installation.")

# Workflow JSON Check[cite: 9, 18, 19]
POSSIBLE_WORKFLOWS = ["workflow_api_2.json", "workflow_api.json", "video_ltx2_3_ia2v.json"]
WORKFLOW_PATH = get_file_path(POSSIBLE_WORKFLOWS)

if WORKFLOW_PATH:
    print(f"✅ Workflow Found at: {WORKFLOW_PATH}")
    with open(WORKFLOW_PATH, 'r') as f:
        BASE_WORKFLOW = json.load(f)
else:
    print("❌ CRITICAL: No Workflow JSON found! Check your file structure.")
    BASE_WORKFLOW = None # sys.exit(1) can be added here for a hard stop
print("--- Environment Debug End ---")

# --- 2. UTILITY FUNCTIONS ---

def split_audio(input_path, output_dir):
    """Splits long audio into 30s chunks[cite: 18, 19]"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    output_pattern = os.path.join(output_dir, "chunk_%03d.wav")
    print(f"Splitting audio: {input_path}")
    
    subprocess.run([
        'ffmpeg', '-i', input_path, '-f', 'segment',
        '-segment_time', '30', '-c', 'copy', output_pattern, '-y'
    ], check=True)
    
    return sorted([os.path.join(output_dir, f) for f in os.listdir(output_dir) if f.endswith('.wav')])

def stitch_videos(video_list, output_path):
    """Stitches video segments into one final MP4[cite: 18, 19]"""
    if not video_list:
        return None
        
    list_path = "concat_list.txt"
    with open(list_path, "w") as f:
        for v in video_list:
            f.write(f"file '{os.path.abspath(v)}'\n")
    
    print(f"Stitching {len(video_list)} segments...")
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

    if BASE_WORKFLOW is None:
        return {"error": "Server started without a valid workflow JSON"}

    job_id = str(uuid.uuid4())
    temp_dir = f"/tmp/{job_id}"
    os.makedirs(temp_dir, exist_ok=True)

    try:
        # Step 1: Download Full Audio[cite: 18, 19]
        full_audio_path = os.path.join(temp_dir, "main_speech.wav")
        print(f"Downloading audio...")
        response = requests.get(speech_url, timeout=120)
        with open(full_audio_path, 'wb') as f:
            f.write(response.content)

        # Step 2: Split into 30s Chunks[cite: 18, 19]
        audio_chunks = split_audio(full_audio_path, os.path.join(temp_dir, "chunks"))
        
        # Step 3: Simulation for Chunks[cite: 19]
        # Actual LTX processing logic will go here
        print(f"Identified {len(audio_chunks)} chunks for processing.")

        return {
            "status": "debug_complete", 
            "chunks_processed": len(audio_chunks),
            "workflow_used": os.path.basename(WORKFLOW_PATH)
        }

    except Exception as e:
        print(f"Handler Error: {str(e)}")
        return {"status": "error", "message": str(e)}
    
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

# --- 4. START RUNPOD ---
runpod.serverless.start({"handler": handler})