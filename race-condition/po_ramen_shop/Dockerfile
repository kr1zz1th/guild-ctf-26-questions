FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY templates/ templates/

ENV FLAG=exploiitm{w3_aR3_nO7_7HA7_57Upid}

EXPOSE 5001

CMD ["python", "app.py"]
