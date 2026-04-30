# CUDA base image for LTX 2.3 and GPU support[cite: 17]
FROM runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel

# Install FFmpeg and system GL libraries[cite: 17]
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libgl1-mesa-glx \
    libglib2.0-0 \
<<<<<<< HEAD
    && rm -rf /var/lib/apt/lists/*

# Working directory set karein[cite: 17]
WORKDIR /app

# Python packages install karein[cite: 17]
=======
    && rm -rf /var/lib/apt/lists/*             
                                                                  
WORKDIR /app          
                               
# Install Python dependencies
>>>>>>> 783fb462c5cc60f8142868ecb518e7448c424a5c
RUN pip install --no-cache-dir \
    runpod \
    requests \
    pydub \
    numpy

# Sari files copy karein[cite: 17]
# Note: Ensure workflow_api.json is in the same folder as agent.py
COPY . /app

# Immediate log visibility[cite: 17]
ENV PYTHONUNBUFFERED=1

<<<<<<< HEAD
# Execute the handler[cite: 17]
CMD ["python", "-u", "agent.py"]
=======
# Execute agent.py
CMD ["python", "-u", "agent.py"]
>>>>>>> 783fb462c5cc60f8142868ecb518e7448c424a5c
