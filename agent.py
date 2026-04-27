import runpod
import os
import subprocess
import json
import uuid
import requests
import time            

# --- 1. COLD START OPTIMIZATION ---
# Workflow JSON ko load karke memory mein rakhein
WORKFLOW_PATH = "workflow_api.json"
with open(WORKFLOW_PATH, 'r') as f:
    BASE_WORKFLOW = json.load(f)

print("Cold Start: Model & Workflow initialized.")

def update_workflow(audio_path, image_url, workflow):
    """
    Workflow JSON mein audio aur image nodes ko update karne ke liye.
    Note: Aapko apne JSON ke mutabiq ID numbers (e.g., '3', '10') check karne honge.
    """
    new_workflow = workflow.copy()
    
    # Example logic: IDs aapke JSON ke mutabiq honi chahiye
    # node_id '3' for LoadImage, '10' for LoadAudio wagera
    for node_id in new_workflow:
        node = new_workflow[node_id]
        if node.get('class_type') == 'LoadAudio':
            node['inputs']['audio'] = audio_path
        if node.get('class_type') == 'LoadImage':
            node['inputs']['image'] = image_url
            
    return new_workflow

def split_audio(input_path, output_dir):
    """FFmpeg use karke audio ko segments mein torta hai"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    output_pattern = os.path.join(output_dir, "chunk_%03d.wav")
    # 30-second chunks for stability
    subprocess.run([
        'ffmpeg', '-i', input_path, '-f', 'segment',
        '-segment_time', '30', '-c', 'copy', output_pattern
    ], check=True)
    
    return sorted([os.path.join(output_dir, f) for f in os.listdir(output_dir) if f.endswith('.wav')])

def stitch_videos(video_list, output_path):
    """Sari choti clips ko join karta hai"""
    list_path = "concat_list.txt"
    with open(list_path, "w") as f:
        for v in video_list:
            f.write(f"file '{os.path.abspath(v)}'\n")
    
    subprocess.run([
        'ffmpeg', '-f', 'concat', '-safe', '0', '-i', list_path,
        '-c', 'copy', output_path
    ], check=True)
    os.remove(list_path)

# --- 2. HANDLER LOGIC ---
def handler(job):
    job_input = job['input']
    
    # Frontend inputs
    user_speech = job_input.get("speech") # Raw text or audio URL
    avatar_url = job_input.get("avatar_url")
    
    job_id = str(uuid.uuid4())
    temp_dir = f"/tmp/{job_id}"
    os.makedirs(temp_dir, exist_ok=True)

    try:
        # STEP A: Voice Cloner Call (Pahlay voice banayen)
        # Maan len ke cloner ne 'generated_speech.wav' di hai
        full_audio = f"{temp_dir}/main_speech.wav"
        # [Aapka Voice Cloner Logic Yahan Aye Ga]

        # STEP B: Chunking
        audio_chunks = split_audio(full_audio, f"{temp_dir}/chunks")
        video_chunks = []

        # STEP C: Loop through chunks
        for i, chunk in enumerate(audio_chunks):
            print(f"Generating Video Chunk {i+1}/{len(audio_chunks)}...")
            
            # Workflow update karein is chunk ke liye
            current_workflow = update_workflow(chunk, avatar_url, BASE_WORKFLOW)
            
            # ComfyUI API call (assuming Comfy is running on port 8181)
            # Yahan aapko actual API request karni hogi jo video return kare
            # output_video = call_comfy_api(current_workflow)
            # video_chunks.append(output_video)
            
            # Debug/Testing ke liye placeholder
            # video_chunks.append(f"{temp_dir}/v_chunk_{i}.mp4")

        # STEP D: Stitching
        final_mp4 = f"{temp_dir}/final_result.mp4"
        stitch_videos(video_chunks, final_mp4)

        # STEP E: Result
        # Yahan video file ko S3 ya cloud storage par upload karein
        return {"status": "completed", "video_url": "UPLOADED_S3_LINK"}

    except Exception as e:
        return {"status": "error", "message": str(e)}

# --- 3. START SERVERLESS ---
runpod.serverless.start({"handler": handler})