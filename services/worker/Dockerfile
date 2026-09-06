FROM python:3.11-slim
WORKDIR /app
COPY services/worker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY services/worker/app ./app
COPY integrations/quant-adapter ./integrations/quant-adapter
ENV PYTHONPATH=/app
CMD ["python", "-m", "app.main"]
