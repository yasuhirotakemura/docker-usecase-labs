FROM python:3.14-slim

# 1. 必要最低限のシステムアップデート
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# 2. コンテナ内の作業ディレクトリを設定
WORKDIR /app

# 3. 依存パッケージリストをコピーしてインストール   
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. アプリケーションのソースコードを/app/配下にコピー
COPY . .

EXPOSE 8000

# 5. Flaskアプリケーションの実行
CMD ["python", "app.py"]