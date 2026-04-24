import os
import json
import requests
import subprocess
import time
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
        """
        Main Orchestrator: Handles everything from audio to final MP4.
        """
        try:
            print("🚀 [PIPELINE STARTED]")

            # 1. Audio Segmentation (Chunking)
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
                else:
                    print(f"⚠️ Warning: Clip {i} failed to generate.")

            if not generated_clips:
                raise Exception("❌ All clips failed to generate. Check ComfyUI logs.")

            # 4. Stitching (Joining all clips)
            base_video = "base_joined_video.mp4"
            self._stitch_clips(generated_clips, base_video)

            # 5. Post-Processing (Subtitles & Upscaling)
            final_output = "final_video_ready.mp4"
            self._apply_final_touch(base_video, user_input['requirements'], final_output)

            print(f"✅ [SUCCESS] Pipeline Finished! Final Video: {final_output}")
            return final_output

        except Exception as e:
            print(f"❌ [CRITICAL ERROR]: {str(e)}")
            return None

    def _split_audio(self, audio_path):
        print(f"✂️ [STEP 1] Splitting Audio: {audio_path}")
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
            # ⚠️ UPDATED NODE IDs BASED ON YOUR JSON ⚠️
            # Load Audio Node ID: 276
            # Load Image Node ID: 269
            
            workflow['276']['inputs']['audio'] = audio_chunk 
            workflow['269']['inputs']['image'] = avatar       
            
            # Send to ComfyUI API
            payload = {"prompt": workflow}
            response = requests.post(f"{self.comfy_url}/prompt", json=payload)
            
            if response.status_code == 200:
                print(f"   ✅ Clip {index} prompt accepted. Waiting for generation...")
                # NOTE: In a production environment, you should use WebSockets 
                # to poll the status instead of a hard sleep.
                time.sleep(30) 
                # Assuming ComfyUI saves clips in an 'output' folder
                clip_path = f"output/clip_{index}.mp4" 
                return clip_path
            else:
                print(f"   ❌ ComfyUI Error: {response.text}")
                return None
        except KeyError as e:
            print(f"❌ [KEY ERROR]: Node ID {e} not found in JSON. Check your workflow IDs!")
            return None

    def _stitch_clips(self, clips, output_name):
        print("🔗 [STEP 4] Stitching all clips together...")
        list_file = "list.txt"
        with open(list_file, "w") as f:
            for clip in clips:
                if os.path.exists(clip):
                    f.write(f"file '{clip}'\n")
                else:
                    print(f"⚠️ Warning: Clip {clip} missing, skipping.")
        
        subprocess.run(f"ffmpeg -f concat -safe 0 -i {list_file} -c copy {output_name}", shell=True)

    def _apply_final_touch(self, input_video, req, output_name):
        print(f"✨ [STEP 5] Final Touch: Quality={req['quality']}, Subtitles={req['subtitles']}")
        
        # Base Command
        cmd = f"ffmpeg -y -i {input_video}"
        
        # 1. Add Subtitles (Requires .ass file from Whisper)
        if req.get('subtitles'):
            # Note: This assumes your Whisper node generates 'subtitles.ass'
            cmd += " -vf \"subtitles=subtitles.ass\""
        
        # 2. Add Scaling (Quality)
        if req.get('quality') == '4K':
            cmd += " -vf scale=3840:2160"
        elif req.get('quality') == '1080p':
            cmd += " -vf scale=1920:1080"
        elif req.get('quality') == '720p':
            cmd += " -vf scale=1280:720"
        
        cmd += f" -c:v libx264 -preset fast {output_name}"
        subprocess.run(cmd, shell=True)

# ================= TESTING THE AGENT =================
if __name__ == "__main__":
    # Replace these with your actual file names on RunPod
    user_request = {
        "audio_file": "ltx_23_audio.mp3", 
        "avatar_image": "cactus_man.png",
        "requirements": {
            "subtitles": True,
            "subtitle_style": "yellow",
            "quality": "1080p"
        }
    }

    # ⚠️ REPLACE 'YOUR_RUNPOD_IP' with your actual RunPod IP and Port
    agent = AI_Video_Automator(comfy_url="http://YOUR_RUNPOD_IP:8188", 
                               workflow_json="video_ltx2_3_ia2v.json")
    
    agent.run_pipeline(user_request)