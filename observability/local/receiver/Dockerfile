FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY receiver.py .
RUN useradd -u 10002 -M receiver && mkdir -p /receipts && chown 10002 /receipts
USER 10002
EXPOSE 9099
CMD ["python", "receiver.py"]
