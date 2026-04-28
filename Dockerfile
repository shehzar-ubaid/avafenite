# Base image with CUDA support
FROM runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel

# Fix for FFmpeg installation
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*             

WORKDIR /app          

# Install Python dependencies
RUN pip install --no-cache-dir \
    runpod \
    requests \
    pydub \
    numpy

# Copy all files from your repo to the container
COPY . /app

# Ensure logs are visible immediately
ENV PYTHONUNBUFFERED=1

# Execute agent.py
CMD ["python", "-u", "agent.py"]
