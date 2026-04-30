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

def load_workflow_safe(path):
    """File size aur JSON format check karke load karta hai[cite: 19, 20]"""
    if not path or not os.path.exists(path):
        return None
    if os.path.getsize(path) == 0:
        print(f"❌ CRITICAL ERROR: {path} is EMPTY (0 bytes)!")
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ JSON FORMAT ERROR in {path}: {str(e)}")
        return None

print("--- Environment Debug Start ---")
# FFmpeg Check
try:
    subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, check=True)
    print("✅ FFmpeg Found and Operational")
except Exception:
    print("❌ FFmpeg NOT FOUND!")

# Workflow JSON Check[cite: 9, 13, 19]
POSSIBLE_WORKFLOWS = ["workflow_api_3.json", "workflow_api_2.json", "workflow_api.json", "video_ltx2_3_ia2v_2.json"]
WORKFLOW_PATH = get_file_path(POSSIBLE_WORKFLOWS)
BASE_WORKFLOW = load_workflow_safe(WORKFLOW_PATH)

if BASE_WORKFLOW:
    print(f"✅ Workflow Successfully Loaded from: {WORKFLOW_PATH}")
else:
    print("❌ FATAL: Valid Workflow JSON NOT found. Worker will exit.")
    sys.exit(1)
print("--- Environment Debug End ---")

# --- 2. UTILITY FUNCTIONS ---
def split_audio(input_path, output_dir):
    """30s segments mein audio torta hai[cite: 18, 19]"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    output_pattern = os.path.join(output_dir, "chunk_%03d.wav")
    subprocess.run(['ffmpeg', '-i', input_path, '-f', 'segment', '-segment_time', '30', '-c', 'copy', output_pattern, '-y'], check=True)
    return sorted([os.path.join(output_dir, f) for f in os.listdir(output_dir) if f.endswith('.wav')])

def stitch_videos(video_list, output_path):
    """Processed chunks ko merge karta hai[cite: 18, 19]"""
    if not video_list: return None
    list_path = "concat_list.txt"
    with open(list_path, "w") as f:
        for v in video_list: f.write(f"file '{os.path.abspath(v)}'\n")
    subprocess.run(['ffmpeg', '-f', 'concat', '-safe', '0', '-i', list_path, '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-y', output_path], check=True)
    if os.path.exists(list_path): os.remove(list_path)
    return output_path

# --- 3. CORE HANDLER ---
def handler(job):
    job_input = job['input']
    speech_url = job_input.get("speech_url") 
    avatar_url = job_input.get("avatar_url")
    
    if not speech_url or not avatar_url:
        return {"error": "Missing inputs"}

    job_id = str(uuid.uuid4())
    temp_dir = f"/tmp/{job_id}"
    os.makedirs(temp_dir, exist_ok=True)

    try:
        full_audio_path = os.path.join(temp_dir, "main_speech.wav")
        response = requests.get(speech_url, timeout=120)
        with open(full_audio_path, 'wb') as f: f.write(response.content)

        audio_chunks = split_audio(full_audio_path, os.path.join(temp_dir, "chunks"))
        print(f"Identified {len(audio_chunks)} chunks.")

        return {
            "status": "success", 
            "chunks_ready": len(audio_chunks),
            "workflow_file": os.path.basename(WORKFLOW_PATH)
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        if os.path.exists(temp_dir): shutil.rmtree(temp_dir)

runpod.serverless.start({"handler": handler})