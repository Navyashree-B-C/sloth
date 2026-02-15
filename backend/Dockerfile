# Pin Python 3.12 so pydantic-core installs from wheel.
FROM python:3.12-slim

WORKDIR /app

# Install system deps for audio/TTS if needed (ffmpeg for Whisper).
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Railway (and similar platforms) set PORT for web services.
ENV PORT=10000
EXPOSE $PORT
CMD ["/bin/sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port $PORT"]
