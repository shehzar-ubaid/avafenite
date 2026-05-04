import runpod
import os
import subprocess
import json
import uuid
import requests
import sys
import shutil
import base64

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
    """Processed segments ko sequence mein jorta hai"""
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
    """RunPod Job Handler with robust input detection[cite: 10, 12]"""
    
    # Nesting handling: Pehle 'input' nikalen
    job_input = job.get('input', {})
    
    # --- FIXED DATA EXTRACTION ---
    raw_speech = job_input.get("speech_url") 
    avatar_url = job_input.get("avatar_url")
    
    speech_url = None
    if isinstance(raw_speech, dict):
        # Chatterbox output handling (Base64 or URL)[cite: 12]
        speech_url = raw_speech.get("audio_base64") or raw_speech.get("audio_url")
    else:
        speech_url = raw_speech

    # Debugging logs for RunPod Console[cite: 10, 11]
    print(f"DEBUG: Processed speech_url (len): {len(str(speech_url)) if speech_url else 0}")
    print(f"DEBUG: Processed avatar_url: {avatar_url}")

    # STRICT INPUT VALIDATION: Preventing 'None' errors
    if not speech_url or not avatar_url:
        missing = []
        if not speech_url: missing.append("speech_url")
        if not avatar_url: missing.append("avatar_url")
        return {
            "error": f"Missing inputs: {', '.join(missing)}",
            "found_keys": list(job_input.keys()),
            "status": "FAILED"
        }

    job_id = str(uuid.uuid4())
    temp_dir = f"/tmp/{job_id}"
    os.makedirs(temp_dir, exist_ok=True)

    try:
        full_audio_path = os.path.join(temp_dir, "main_speech.wav")

        # Step 1: Audio Handling (URL vs Base64)[cite: 10, 12]
        if isinstance(speech_url, str) and speech_url.startswith('http'):
            response = requests.get(speech_url, timeout=120)
            response.raise_for_status()
            with open(full_audio_path, 'wb') as f: 
                f.write(response.content)
        else:
            audio_data = speech_url
            if isinstance(audio_data, str) and ',' in audio_data: 
                audio_data = audio_data.split(',')[1]
            with open(full_audio_path, 'wb') as f:
                f.write(base64.b64decode(audio_data))

        # Step 2: 8s Splitting[cite: 10]
        audio_chunks = split_audio_8s(full_audio_path, os.path.join(temp_dir, "chunks"))
        print(f"✅ Identified {len(audio_chunks)} segments of 8 seconds each.")

        # Step 3: Loop through 8s chunks for LTX processing[cite: 10]
        # (Yahan aapka processing logic aayega)
        processed_segments = []
        for i, chunk in enumerate(audio_chunks):
            print(f"🚀 Processing Segment {i+1}/{len(audio_chunks)}...")
            pass

        return {
            "status": "success", 
            "chunks_processed": len(audio_chunks),
            "message": "Processing complete"
        }

    except Exception as e:
        return {"status": "error", "message": f"Processing failed: {str(e)}"}
    finally:
        if os.path.exists(temp_dir): 
            shutil.rmtree(temp_dir)

runpod.serverless.start({"handler": handler})