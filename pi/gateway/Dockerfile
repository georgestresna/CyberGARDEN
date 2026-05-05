FROM python:3.10-slim

WORKDIR /app

# Install Linux Bluetooth utilities
RUN apt-get update && apt-get install -y bluez && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY gateway.py .

# Use -u to see print statements live in the logs
CMD ["python", "-u", "gateway.py"]