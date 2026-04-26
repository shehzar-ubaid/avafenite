# Base Image for AI Apps
FROM python:3.10-slim

# Working directory set karein
WORKDIR /app

# Code copy karein
COPY . /app

# Packages install karein
RUN pip install --no-cache-dir requests runpod                   

# App ko start karne ki command
CMD ["python", "agent.py"]
