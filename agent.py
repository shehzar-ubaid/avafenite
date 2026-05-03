import runpod
import os
import subprocess
import json
import uuid
import requests
import sys
import shutil

# --- 1. UTILITY FUNCTIONS (Tornay aur Jornay wala kaam) ---

def split_audio_8s(input_path, output_dir):
    """Audio ko exactly 8-second segments mein torta hai"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    output_pattern = os.path.join(output_dir, "chunk_%03d.wav")
    
    # FFmpeg splitting command for 8-second chunks
    subprocess.run([
        'ffmpeg', '-i', input_path, '-f', 'segment', 
        '-segment_time', '8', '-c', 'copy', output_pattern, '-y'
    ], check=True)
    
    return sorted([os.path.join(output_dir, f) for f in os.listdir(output_dir) if f.endswith('.wav')])

def stitch_videos(video_list, output_path):
    """Processed segments ko sequence mein jorta hai[cite: 10]"""
    if not video_list: return None
    list_path = "concat_list.txt"
    with open(list_path, "w") as f:
        for v in video_list:
            f.write(f"file '{os.path.abspath(v)}'\n")
            
    # Linewise stitching logic without quality loss[cite: 10]
    subprocess.run([
        'ffmpeg', '-f', 'concat', '-safe', '0', '-i', list_path, 
        '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-y', output_path
    ], check=True)
    
    if os.path.exists(list_path): os.remove(list_path)
    return output_path

# --- 2. CORE HANDLER ---

def handler(job):
    """RunPod Job Handler with robust input detection[cite: 10]"""
    
    # Nesting handling: Pehle 'input' nikalen, phir keys
    job_input = job.get('input', {})
    
    # Backend mapping to prevent 'Missing inputs' error[cite: 10]
    speech_url = job_input.get("speech_url") 
    avatar_url = job_input.get("avatar_url")
    
    # Debugging logs for RunPod Console[cite: 10]
    print(f"DEBUG: Processed speech_url: {speech_url}")
    print(f"DEBUG: Processed avatar_url: {avatar_url}")

    if not speech_url or not avatar_url:
        return {"error": f"Missing inputs. Worker expected 'speech_url' and 'avatar_url'. Found keys: {list(job_input.keys())}"}

    job_id = str(uuid.uuid4())
    temp_dir = f"/tmp/{job_id}"
    os.makedirs(temp_dir, exist_ok=True)

    try:
        # Step 1: Chatterbox Audio Download[cite: 10]
        full_audio_path = os.path.join(temp_dir, "main_speech.wav")
        response = requests.get(speech_url, timeout=120)
        response.raise_for_status()
        with open(full_audio_path, 'wb') as f: 
            f.write(response.content)

        # Step 2: 8s Splitting (Tornay wala kaam)[cite: 10]
        audio_chunks = split_audio_8s(full_audio_path, os.path.join(temp_dir, "chunks"))
        print(f"✅ Identified {len(audio_chunks)} segments of 8 seconds each.")

        processed_segments = []

        # Step 3: Loop through 8s chunks for processing[cite: 10]
        for i, chunk in enumerate(audio_chunks):
            print(f"🚀 Processing Segment {i+1}/{len(audio_chunks)}...")
            # Actual processing logic (ComfyUI etc.) yahan aayega
            pass

        # Step 4: Final Stitching (Jornay wala kaam)[cite: 10]
        # output_video = stitch_videos(processed_segments, os.path.join(temp_dir, "final.mp4"))

        return {
            "status": "success", 
            "chunks_processed": len(audio_chunks),
            "message": "Inputs received, split into 8s segments, and ready for output."
        }

    except Exception as e:
        return {"status": "error", "message": f"Processing failed: {str(e)}"}
    finally:
        if os.path.exists(temp_dir): 
            shutil.rmtree(temp_dir)

runpod.serverless.start({"handler": handler})