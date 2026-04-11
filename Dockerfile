FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir uvicorn fastapi

COPY requirements.txt .
RUN pip install --no-cache-dir \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    -r requirements.txt

COPY . .

EXPOSE 7860

CMD ["sh", "-c", "python -m uvicorn mindmap_api:app --host 0.0.0.0 --port 8000 & python -m streamlit run app.py --server.port 7860 --server.address 0.0.0.0"]