# Stage 1: apt-stage - System dependencies and Chrome
FROM python:3.11-slim as apt-stage
RUN apt-get update && apt-get install -y \
    wget gnupg curl unzip \
    libglib2.0-0 libnss3 libatk-bridge2.0-0 libdrm2 \
    libxkbcommon0 libxcomposite1 libxdamage1 libxrandr2 \
    libgbm1 libxss1 libasound2 libgtk-3-0 libx11-xcb1 \
    libxcb-dri3-0 libxcb-shm0 libxcb1 \
    && wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Stage 2: pip-stage - Python dependencies
FROM python:3.11-slim as pip-stage
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 3: runtime - Final application image
FROM python:3.11-slim

# Copy Chrome and system libs from apt-stage
COPY --from=apt-stage /usr/bin/google-chrome-stable /usr/bin/google-chrome-stable
COPY --from=apt-stage /usr/lib /usr/lib
COPY --from=apt-stage /usr/share /usr/share
COPY --from=apt-stage /etc /etc

# Create Chrome symlink for compatibility
RUN ln -sf /usr/bin/google-chrome-stable /usr/bin/chrome && \
    chmod +x /usr/bin/google-chrome-stable && \
    /usr/bin/google-chrome-stable --version || echo "Chrome installed but may need additional setup"

# Copy Python packages from pip-stage
COPY --from=pip-stage /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=pip-stage /usr/local/bin /usr/local/bin

# Application setup
WORKDIR /app
COPY . .
RUN useradd --create-home --shell /bin/bash app && chown -R app:app /app

# Switch to root to handle mounted volume permissions
USER root
RUN mkdir -p /host && chown app:app /host

# Switch back to app user
USER app

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

CMD ["python", "main.py", "sources.json"]
