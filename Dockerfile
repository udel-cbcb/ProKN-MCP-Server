FROM python:3.12-slim

WORKDIR /app

# Install system dependencies if any are needed (none for now)
# RUN apt-get update && apt-get install -y --no-install-recommends ...

# Install Python dependencies
COPY ./requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the server code and queries
COPY ./mcpserver.py .
COPY ./queries.py .
COPY ./arg_normalization.py .

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import socket; s = socket.socket(); s.settimeout(2); s.connect(('localhost', 8000)); s.close()" || exit 1

EXPOSE 8000

# Run the server in HTTP mode
CMD ["python", "mcpserver.py", "streamable-http"]
