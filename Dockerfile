FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir uvicorn fastapi

RUN pip install --no-cache-dir \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    -r requirements.txt

COPY . .

EXPOSE 7860

CMD ["python", "-m", "uvicorn", "mindmap_api:app", "--host", "0.0.0.0", "--port", "7860"]