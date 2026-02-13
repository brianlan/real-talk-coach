# Build stage
FROM python:3.11-slim AS builder

# Install build dependencies for any packages that need compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies directly (no manifest file)
WORKDIR /install
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    fastapi \
    httpx \
    "openai>=1.52.0" \
    pydantic \
    uvicorn[standard] \
    numpy \
    soundfile \
    pydub \
    ffmpeg-python


# Runtime stage
FROM python:3.11-slim

# Install system packages required at runtime
# - ffmpeg: audio conversion (PCM/MP3/WAV)
# - libsndfile1: soundfile library for audio I/O
# - libgcc-s1: runtime support for compiled extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    libgcc-s1 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /usr/local /usr/local

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser
WORKDIR /app
USER appuser

# Copy application code
COPY --chown=appuser:appuser app ./app

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
