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
    """Poori directory scan karta hai agar file root mein na milti ho"""
    if os.path.exists(filename):
        return os.path.abspath(filename)
    for root, dirs, files in os.walk('.'):
        if filename in files:
            return os.path.join(root, filename)
    return None

print("--- Environment Debug Start ---")
# FFmpeg Check (For Chunking & Stitching)
try:
    ffmpeg_check = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
    print(f"✅ FFmpeg Found: {ffmpeg_check.stdout.splitlines()}")
except Exception:
    print("❌ FFmpeg NOT FOUND! Please check Dockerfile installation.")

# Workflow JSON Check
WORKFLOW_PATH = get_file_path("workflow_api.json")
if WORKFLOW_PATH:
    print(f"✅ workflow_api.json Found at: {WORKFLOW_PATH}")
    with open(WORKFLOW_PATH, 'r') as f:
        BASE_WORKFLOW = json.load(f)
else:
    print("❌ workflow_api.json MISSING! Check your file structure.")
    BASE_WORKFLOW = {}
print("--- Environment Debug End ---")

# --- 2. UTILITY FUNCTIONS ---

def split_audio(input_path, output_dir):
    """Audio ko 30s chunks mein torta hai taake timeout na ho"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    output_pattern = os.path.join(output_dir, "chunk_%03d.wav")
    print(f"Splitting audio into chunks: {input_path}")
    
    subprocess.run([
        'ffmpeg', '-i', input_path, '-f', 'segment',
        '-segment_time', '30', '-c', 'copy', output_pattern
    ], check=True)
    
    return sorted([os.path.join(output_dir, f) for f in os.listdir(output_dir) if f.endswith('.wav')])

def stitch_videos(video_list, output_path):
    """Sab video chunks ko join karke final MP4 banata hai"""
    if not video_list:
        return None
        
    list_path = "concat_list.txt"
    with open(list_path, "w") as f:
        for v in video_list:
            f.write(f"file '{os.path.abspath(v)}'\n")
    
    print(f"Stitching {len(video_list)} videos...")
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
    
    # Inputs from Frontend
    speech_url = job_input.get("speech_url")  # Voice cloner output link
    avatar_url = job_input.get("avatar_url")
    
    if not speech_url or not avatar_url:
        return {"error": "Missing speech_url or avatar_url"}

    job_id = str(uuid.uuid4())
    temp_dir = f"/tmp/{job_id}"
    os.makedirs(temp_dir, exist_ok=True)

    try:
        # Step 1: Download Full Audio
        print("Downloading audio...")
        full_audio_path = os.path.join(temp_dir, "main_speech.wav")
        response = requests.get(speech_url, timeout=30)
        with open(full_audio_path, 'wb') as f:
            f.write(response.content)

        # Step 2: Split into 30s Chunks
        audio_chunks = split_audio(full_audio_path, os.path.join(temp_dir, "chunks"))
        video_chunks = []

        # Step 3: Process Chunks (Loop)
        # Note: Yahan aapka ComfyUI / LTX2.3 call logic aye ga
        for i, chunk in enumerate(audio_chunks):
            print(f"Processing Chunk {i+1}/{len(audio_chunks)}...")
            # Placeholder for your LTX generation:
            # video_output = run_ltx_workflow(chunk, avatar_url, BASE_WORKFLOW)
            # video_chunks.append(video_output)

        # Step 4: Stitching
        # (Sirf tab chalega jab chunks generate honge)
        if video_chunks:
            final_mp4 = os.path.join(temp_dir, "final_result.mp4")
            stitch_videos(video_chunks, final_mp4)
            # Yahan aap video ko S3 par upload karke link return karenge
            return {"status": "success", "video_url": "YOUR_S3_LINK"}
        
        return {"status": "completed_debug", "chunks_processed": len(audio_chunks)}

    except Exception as e:
        print(f"Error occurred: {str(e)}")
        return {"status": "error", "message": str(e)}
    
    finally:
        # Cleanup temporary files
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

# --- 4. START SERVERLESS ---
runpod.serverless.start({"handler": handler})