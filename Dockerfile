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

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:9688/mcp')" || exit 1

EXPOSE 9688

# Run the server in HTTP mode
CMD ["python", "mcpserver.py", "http"]
