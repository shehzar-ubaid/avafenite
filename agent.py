import os
import json
import requests
import subprocess
import time
import runpod  # Required for RunPod Serverless
from pydub import AudioSegment

class AI_Video_Automator:
    def __init__(self, comfy_url, workflow_json):
        self.comfy_url = comfy_url
        self.workflow_path = workflow_json
        self.temp_dir = "temp_processing"
        self.clips_dir = "generated_clips"
        
        # Create folders if they don't exist
        for folder in [self.temp_dir, self.clips_dir]:
            if not os.path.exists(folder):
                os.makedirs(folder)

    def run_pipeline(self, user_input):
        try:
            print("🚀 [PIPELINE STARTED]")

            # 1. Audio Segmentation
            audio_chunks = self._split_audio(user_input['audio_file'])

            # 2. Load Workflow Template
            if not os.path.exists(self.workflow_path):
                raise FileNotFoundError(f"Workflow file '{self.workflow_path}' not found!")
                
            with open(self.workflow_path, 'r') as f:
                workflow = json.load(f)

            # 3. Loop: Generate Clips via ComfyUI
            generated_clips = []
            for i, chunk in enumerate(audio_chunks):
                print(f"🎬 [STEP 3] Generating Clip {i+1}/{len(audio_chunks)}...")
                clip_path = self._generate_single_clip(workflow, chunk, user_input['avatar_image'], i)
                if clip_path:
                    generated_clips.append(clip_path)

            if not generated_clips:
                raise Exception("❌ All clips failed to generate.")

            # 4. Stitching
            base_video = "base_joined_video.mp4"
            self._stitch_clips(generated_clips, base_video)

            # 5. Post-Processing
            final_output = "final_video_ready.mp4"
            self._apply_final_touch(base_video, user_input['requirements'], final_output)

            return final_output

        except Exception as e:
            print(f"❌ [CRITICAL ERROR]: {str(e)}")
            return None

    def _split_audio(self, audio_path):
        audio = AudioSegment.from_file(audio_path)
        chunks = []
        for i, start_ms in enumerate(range(0, len(audio), 10000)):
            chunk = audio[start_ms:start_ms + 10000]
            path = f"{self.temp_dir}/chunk_{i}.mp3"
            chunk.export(path, format="mp3")
            chunks.append(path)
        return chunks

    def _generate_single_clip(self, workflow, audio_chunk, avatar, index):
        try:
            # Node IDs mapping
            workflow['276']['inputs']['audio'] = audio_chunk 
            workflow['269']['inputs']['image'] = avatar       
            
            payload = {"prompt": workflow}
            response = requests.post(f"{self.comfy_url}/prompt", json=payload)
            
            if response.status_code == 200:
                # Note: Production mein polling behtar hai, but for now:
                time.sleep(30) 
                clip_path = f"output/clip_{index}.mp4" 
                return clip_path
            return None
        except Exception as e:
            print(f"Error in clip {index}: {e}")
            return None

    def _stitch_clips(self, clips, output_name):
        list_file = "list.txt"
        with open(list_file, "w") as f:
            for clip in clips:
                f.write(f"file '{clip}'\n")
        subprocess.run(f"ffmpeg -y -f concat -safe 0 -i {list_file} -c copy {output_name}", shell=True)

    def _apply_final_touch(self, input_video, req, output_name):
        cmd = f"ffmpeg -y -i {input_video}"
        if req.get('subtitles'):
            cmd += " -vf \"subtitles=subtitles.ass\""
        
        quality_map = {'4K': '3840:2160', '1080p': '1920:1080', '720p': '1280:720'}
        if req.get('quality') in quality_map:
            cmd += f" -vf scale={quality_map[req['quality']]}"
        
        cmd += f" -c:v libx264 -preset fast {output_name}"
        subprocess.run(cmd, shell=True)

# --- RUNPOD INTEGRATION ---

def handler(job):
    """
    This function processes the input from the RunPod API
    """
    job_input = job['input']
    
    # ComfyUI often runs on localhost:8188 inside the container
    comfy_url = job_input.get("comfy_url", "http://127.0.0.1:8188")
    workflow_json = job_input.get("workflow_json", "video_ltx2_3_ia2v.json")

    agent = AI_Video_Automator(comfy_url=comfy_url, workflow_json=workflow_json)
    result = agent.run_pipeline(job_input)

    if result:
        return {"status": "success", "video_path": result}
    else:
        return {"status": "failed", "error": "Check container logs for details"}

# Start the serverless worker
if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})