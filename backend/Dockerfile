FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends libmagic1 && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml ./
RUN pip install --no-cache-dir ".[docling]"
RUN pip install --no-cache-dir "onnxruntime>=1.20,<2"
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 libxcb1 libxext6 libsm6 tesseract-ocr tesseract-ocr-eng && rm -rf /var/lib/apt/lists/*
COPY . .
RUN chmod +x scripts/start-api.sh
RUN useradd --create-home --uid 10001 appuser && mkdir -p /home/appuser/.cache/huggingface && chown -R appuser:appuser /app /home/appuser
USER appuser
EXPOSE 8000
CMD ["/app/scripts/start-api.sh"]
