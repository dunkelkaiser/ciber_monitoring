FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    curl \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Install Google Chrome Stable
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
    && apt-get update && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Copy consolidated requirements
COPY agents/scrapers/requirements.txt scrape_reqs.txt
COPY data_engineering/requirements.txt etl_reqs.txt
COPY api_gateway/requirements.txt api_reqs.txt
COPY rag_system/requirements.txt rag_reqs.txt
COPY gradio_assistant/requirements.txt gradio_reqs.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r scrape_reqs.txt
RUN pip install --no-cache-dir -r etl_reqs.txt
RUN pip install --no-cache-dir -r api_reqs.txt
RUN pip install --no-cache-dir -r rag_reqs.txt
RUN pip install --no-cache-dir -r gradio_reqs.txt

# Playwright browsers are pre-installed in this image

# Copy Python code
COPY . /app

# Set env vars
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose API port
EXPOSE 8000

# Start API by default
CMD ["uvicorn", "api_gateway.main:app", "--host", "0.0.0.0", "--port", "8000"]
