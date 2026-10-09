FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg fonts-dejavu-core && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY videobot ./videobot
COPY scripts ./scripts
ENV PYTHONUNBUFFERED=1
CMD ["python", "-m", "videobot", "schedule"]
