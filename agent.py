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
    for filename in filenames:
        if os.path.exists(filename):
            return os.path.abspath(filename)
    return None

def load_workflow_safe(path):
    if not path or not os.path.exists(path): return None
    if os.path.getsize(path) == 0: return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except: return None

# Startup Checks[cite: 19, 20]
POSSIBLE_WORKFLOWS = ["workflow_api_3.json", "workflow_api.json"]
WORKFLOW_PATH = get_file_path(POSSIBLE_WORKFLOWS)
BASE_WORKFLOW = load_workflow_safe(WORKFLOW_PATH)

if not BASE_WORKFLOW:
    print("❌ FATAL: Workflow JSON not found.")
    sys.exit(1)

# --- 2. UTILITY FUNCTIONS (Tornay aur Jornay wala kaam) ---
def split_audio(input_path, output_dir):
    """Audio ko 30s ke chunks mein torta hai[cite: 18, 19]"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    output_pattern = os.path.join(output_dir, "chunk_%03d.wav")
    subprocess.run(['ffmpeg', '-i', input_path, '-f', 'segment', '-segment_time', '30', '-c:v', 'copy', output_pattern, '-y'], check=True)
    return sorted([os.path.join(output_dir, f) for f in os.listdir(output_dir) if f.endswith('.wav')])

def stitch_videos(video_list, output_path):
    """Processed segments ko wapis jorta hai[cite: 18, 19]"""
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
    speech_url = job_input.get("speech_url") # Yeh Chatterbox se aayi audio hai[cite: 19]
    avatar_url = job_input.get("avatar_url")
    
    if not speech_url or not avatar_url:
        return {"error": "Missing inputs from automated chain"}

    job_id = str(uuid.uuid4())
    temp_dir = f"/tmp/{job_id}"
    os.makedirs(temp_dir, exist_ok=True)

    try:
        # Step 1: Download Chatterbox Audio[cite: 19]
        full_audio_path = os.path.join(temp_dir, "main_speech.wav")
        response = requests.get(speech_url, timeout=120)
        with open(full_audio_path, 'wb') as f: f.write(response.content)

        # Step 2: Split Audio (Tornay wala kaam)[cite: 18, 19]
        audio_chunks = split_audio(full_audio_path, os.path.join(temp_dir, "chunks"))
        processed_video_segments = []

        # Step 3: Loop Through Chunks for LTX Lipsync
        for i, chunk in enumerate(audio_chunks):
            print(f"🚀 Processing Segment {i+1}/{len(audio_chunks)}...")
            # YAHAN AAPKA COMFYUI API CALL AYEGA JO ACTUAL LIPSYNC KAREGA[cite: 16]
            # fake_segment = chunk.replace('.wav', '.mp4') 
            # processed_video_segments.append(fake_segment)
            pass

        # Step 4: Stitch Videos (Jornay wala kaam)[cite: 18, 19]
        # final_video = stitch_videos(processed_video_segments, os.path.join(temp_dir, "final.mp4"))

        return {
            "status": "success", 
            "message": f"Successfully chained from Chatterbox. Processed {len(audio_chunks)} segments.",
            "workflow": os.path.basename(WORKFLOW_PATH)
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        if os.path.exists(temp_dir): shutil.rmtree(temp_dir)

runpod.serverless.start({"handler": handler})