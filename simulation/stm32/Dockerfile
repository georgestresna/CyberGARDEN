FROM python:3.12-slim
WORKDIR /app
RUN pip install requests paho-mqtt
COPY stm.py .
CMD ["python", "-u", "stm.py"]