FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY templates/ templates/

ENV FLAG=exploiitm{d4Mn_Y0u_4r3_f457}

EXPOSE 5001

CMD ["python", "app.py"]
