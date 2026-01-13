# Optimized version of your current approach
FROM --platform=linux/amd64 python:3.12-bookworm

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/usr/local/bin:${PATH}"

# Set the working directory
WORKDIR /app

# Install system dependencies in a single layer
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl wget xvfb xauth \
    libcairo2 libpango1.0-0 libgdk-pixbuf2.0-0 \
    libffi-dev libjpeg-dev libxml2-dev \
    libfreetype6-dev liblcms2-dev libopenjp2-7 \
    libtiff5-dev libwebp-dev libgtk2.0-0 \
    libxtst6 libxss1 libgconf-2-4 libnss3 libasound2 \
    dos2unix fonts-dejavu-core fonts-liberation \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8080

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl --fail http://localhost:8080/_stcore/health || exit 1

# Start application
ENTRYPOINT ["streamlit", "run", "chat_interface.py", "--server.port=8080", "--server.address=0.0.0.0"]