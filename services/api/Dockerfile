# Not: build context repo köküdür (bkz. infra/docker-compose.dev.yml) —
# integrations/quant-adapter'ı da imaja dahil edebilmek için.
FROM python:3.11-slim
WORKDIR /app
COPY services/api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY services/api/app ./app
COPY integrations/quant-adapter ./integrations/quant-adapter
ENV PYTHONPATH=/app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
