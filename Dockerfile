# 1. LTX 2.3 aur GPU support ke liye CUDA base image use karein
FROM runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel

# 2. System Level dependencies (FFmpeg lazmi hai audio splitting ke liye)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 3. Working directory set karein
WORKDIR /app

# 4. Pehlay requirements install karein (Fast builds ke liye)
# Note: pydub ko audio handling ke liye add kiya gaya hai
RUN pip install --no-cache-dir \
    runpod \
    requests \
    pydub \
    numpy

# 5. Apna poora code aur workflow JSON copy karein
COPY . /app

# 6. Environment variables (Taake Python logs foran nazar aayein)
ENV PYTHONUNBUFFERED=1

# 7. Apne handler (agent.py) ko start karein
CMD ["python", "-u", "agent.py"]