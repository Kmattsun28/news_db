FROM nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04

# 依存ライブラリとツールをまとめてインストール
RUN apt update && apt install -y python3 python3-pip git curl wget unzip gnupg libreoffice\
    && pip3 install --upgrade pip

# Chromeの依存関係をインストール
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] https://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends google-chrome-stable \
    && apt-get remove -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]