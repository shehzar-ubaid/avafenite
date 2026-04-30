FROM runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel

# Install System dependencies
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

# Copy all repository files[cite: 17, 18]
COPY . /app

ENV PYTHONUNBUFFERED=1

# Run the handler
CMD ["python", "-u", "agent.py"]