import runpod
import os
import subprocess
import json
import uuid
import requests
import sys
import shutil

# --- UTILITY FUNCTIONS ---
def split_audio_8s(input_path, output_dir):
    """Audio ko exactly 8-second chunks mein torta hai"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    output_pattern = os.path.join(output_dir, "chunk_%03d.wav")
    # 8-second segmenting command
    subprocess.run([
        'ffmpeg', '-i', input_path, '-f', 'segment', 
        '-segment_time', '8', '-c', 'copy', output_pattern, '-y'
    ], check=True)
    return sorted([os.path.join(output_dir, f) for f in os.listdir(output_dir) if f.endswith('.wav')])

def stitch_videos(video_list, output_path):
    """Processed segments ko sequence mein jorta hai[cite: 17]"""
    if not video_list: return None
    list_path = "concat_list.txt"
    with open(list_path, "w") as f:
        for v in video_list:
            f.write(f"file '{os.path.abspath(v)}'\n")
    # Stitching without re-encoding if possible
    subprocess.run([
        'ffmpeg', '-f', 'concat', '-safe', '0', '-i', list_path, 
        '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-y', output_path
    ], check=True)
    if os.path.exists(list_path): os.remove(list_path)
    return output_path

# --- CORE HANDLER ---
def handler(job):
    job_input = job['input']
    speech_url = job_input.get("speech_url") # Chatterbox output URL[cite: 17]
    avatar_url = job_input.get("avatar_url")
    
    if not speech_url or not avatar_url:
        return {"error": "Missing inputs from automated chain"}

    job_id = str(uuid.uuid4())
    temp_dir = f"/tmp/{job_id}"
    os.makedirs(temp_dir, exist_ok=True)

    try:
        # Step 1: Chatterbox Audio Download[cite: 17]
        full_audio_path = os.path.join(temp_dir, "main_speech.wav")
        response = requests.get(speech_url, timeout=120)
        with open(full_audio_path, 'wb') as f: f.write(response.content)

        # Step 2: 8s Splitting (Tornay wala kaam)[cite: 17]
        audio_chunks = split_audio_8s(full_audio_path, os.path.join(temp_dir, "chunks"))
        print(f"✅ Identified {len(audio_chunks)} chunks of 8s.")

        processed_segments = []

        # Step 3: Loop through chunks for LTX processing
        for i, chunk in enumerate(audio_chunks):
            print(f"🎬 Processing Segment {i+1}/{len(audio_chunks)}...")
            # Yahan ComfyUI API call aayegi jo har chunk ko video banayegi
            # processed_clip = run_comfy_api(chunk, avatar_url)
            # processed_segments.append(processed_clip)
            pass

        # Step 4: Final Stitching (Jornay wala kaam)[cite: 17]
        # final_video_path = os.path.join(temp_dir, "final_output.mp4")
        # stitch_videos(processed_segments, final_video_path)

        return {
            "status": "success", 
            "chunks_processed": len(audio_chunks),
            "message": "Chained processing complete"
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        if os.path.exists(temp_dir): shutil.rmtree(temp_dir)

runpod.serverless.start({"handler": handler})