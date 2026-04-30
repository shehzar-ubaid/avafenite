# 1. CUDA base image for LTX 2.3 and GPU support[cite: 17, 20]
FROM runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel

# 2. Install FFmpeg and system GL libraries[cite: 17, 20]
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 3. Working directory set karein[cite: 17, 20]
WORKDIR /app

# 4. Python packages install karein[cite: 17, 20]
RUN pip install --no-cache-dir \
    runpod \
    requests \
    pydub \
    numpy

# 5. Sari files copy karein[cite: 17, 20]
COPY . /app

# 6. Ensure logs are visible immediately[cite: 17, 20]
ENV PYTHONUNBUFFERED=1

# 7. Execute the handler script[cite: 17, 20]
CMD ["python", "-u", "agent.py"]