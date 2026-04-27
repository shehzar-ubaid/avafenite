import runpod
import os
import subprocess
import json
import uuid
import requests
import time
import sys

# --- 1. PRE-FLIGHT CHECKS (Debugging for Serverless) ---
def debug_environment():
    print("--- Environment Debug Start ---")
    # FFmpeg Check
    try:
        ffmpeg_v = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
        print(f"✅ FFmpeg Found: {ffmpeg_v.stdout.splitlines()}")
    except FileNotFoundError:
        print("❌ FFmpeg NOT FOUND! Check your Dockerfile installation.")
    
    # Workflow File Check
    if os.path.exists("workflow_api.json"):
        print("✅ workflow_api.json Found.")
    else:
        print("❌ workflow_api.json MISSING in current directory.")
        # List files for debugging
        print(f"Current Directory Files: {os.listdir('.')}")
    print("--- Environment Debug End ---")

debug_environment()

# --- 2. COLD START OPTIMIZATION ---
WORKFLOW_PATH = "workflow_api.json"

try:
    with open(WORKFLOW_PATH, 'r') as f:
        BASE_WORKFLOW = json.load(f)
    print("Cold Start: Workflow JSON loaded successfully.")
except Exception as e:
    print(f"CRITICAL ERROR: Could not load workflow JSON: {str(e)}")
    # Worker ko crash hone se bachaane ke liye empty dict ya exit
    BASE_WORKFLOW = {}

def update_workflow(audio_path, image_url, workflow):
    """Workflow nodes update logic"""
    new_workflow = workflow.copy()
    for node_id in new_workflow:
        node = new_workflow[node_id]
        if node.get('class_type') == 'LoadAudio':
            node['inputs']['audio'] = audio_path
        if node.get('class_type') == 'LoadImage':
            node['inputs']['image'] = image_url
    return new_workflow

def split_audio(input_path, output_dir):
    """Audio splitting with FFmpeg"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    output_pattern = os.path.join(output_dir, "chunk_%03d.wav")
    print(f"Splitting audio: {input_path} -> {output_dir}")
    
    subprocess.run([
        'ffmpeg', '-i', input_path, '-f', 'segment',
        '-segment_time', '30', '-c', 'copy', output_pattern
    ], check=True)
    
    chunks = sorted([os.path.join(output_dir, f) for f in os.listdir(output_dir) if f.endswith('.wav')])
    print(f"Generated {len(chunks)} audio chunks.")
    return chunks

def stitch_videos(video_list, output_path):
    """FFmpeg video stitching"""
    if not video_list:
        raise Exception("No video chunks to stitch!")
        
    list_path = "concat_list.txt"
    with open(list_path, "w") as f:
        for v in video_list:
            f.write(f"file '{os.path.abspath(v)}'\n")
    
    print(f"Stitching {len(video_list)} videos into {output_path}")
    subprocess.run([
        'ffmpeg', '-f', 'concat', '-safe', '0', '-i', list_path,
        '-c:v', 'libx264', '-pix_fmt', 'yuv420p', output_path
    ], check=True)
    
    if os.path.exists(list_path):
        os.remove(list_path)

# --- 3. HANDLER LOGIC ---
def handler(job):
    job_input = job['input']
    
    speech_url = job_input.get("speech_url") # URL of pre-generated audio
    avatar_url = job_input.get("avatar_url")
    
    job_id = str(uuid.uuid4())
    temp_dir = f"/tmp/{job_id}"
    os.makedirs(temp_dir, exist_ok=True)

    try:
        # STEP A: Download/Get Full Audio
        full_audio_path = os.path.join(temp_dir, "main_speech.wav")
        # Example: Download from URL if provided
        if speech_url:
            r = requests.get(speech_url)
            with open(full_audio_path, 'wb') as f:
                f.write(r.content)
        else:
            return {"error": "No speech_url provided"}

        # STEP B: Chunking
        audio_chunks = split_audio(full_audio_path, os.path.join(temp_dir, "chunks"))
        video_chunks = []

        # STEP C: Pipeline Loop (Simulated for your logic)
        for i, chunk in enumerate(audio_chunks):
            print(f"Processing Chunk {i+1}/{len(audio_chunks)}...")
            # actual_video = call_your_comfy_logic(chunk, avatar_url)
            # video_chunks.append(actual_video)

        # STEP D: Stitching (Sirf tab chalega jab video_chunks list khali na ho)
        if video_chunks:
            final_mp4 = os.path.join(temp_dir, "final_result.mp4")
            stitch_videos(video_chunks, final_mp4)
            return {"status": "completed", "video_url": "S3_UPLOAD_LINK"}
        else:
            return {"status": "debug", "message": f"Processed {len(audio_chunks)} chunks, but no videos generated."}

    except Exception as e:
        print(f"Handler Error: {str(e)}")
        return {"status": "error", "message": str(e)}

# --- 4. START RUNPOD ---
runpod.serverless.start({"handler": handler})