FROM python:3.13-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

ENV CHROME_BIN=/usr/bin/chromium

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000
ENV FLAG=exploiitm{3asy_p3asy_l3m0n_squ33zy_xss}
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]
