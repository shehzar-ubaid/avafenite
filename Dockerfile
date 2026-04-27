# 1. GPU support aur CUDA ke liye sahi base image
FROM runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel

# 2. System Level dependencies (FFmpeg yahan install ho raha hai)
# 'apt-get update' aur 'install ffmpeg' lazmi hain
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 3. Working directory set karein
WORKDIR /app

# 4. Python ki zaroori libraries install karein
# pydub aur numpy audio handling ke liye zaroori hain
RUN pip install --no-cache-dir \
    runpod \
    requests \
    pydub \
    numpy

# 5. Apna saara code (agent.py, workflow_api.json) copy karein
COPY . /app

# 6. Logs ko real-time dekhne ke liye setting
ENV PYTHONUNBUFFERED=1

# 7. Apne handler ko start karein
CMD ["python", "-u", "agent.py"]