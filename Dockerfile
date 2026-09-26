# SonicSentinel AI — container image
FROM python:3.13-slim

# FFmpeg is needed for mp3/m4a decoding; libsndfile for soundfile.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Generated artefacts live under this path (override paths.output_root or mount a volume).
ENV SONIC_BG_TRAIN=0 \
    PYTHONUNBUFFERED=1

EXPOSE 5000

# The Flask dev server is fine for the prototype. For production use a WSGI
# server, e.g.:  gunicorn -w 2 -b 0.0.0.0:5000 webapp.app:app  (Linux).
CMD ["python", "webapp/app.py"]
