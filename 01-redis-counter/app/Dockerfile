FROM python:3.14

# 1. 必要最低限のシステムアップデート
RUN apt-get update && apt-get upgrade -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get install -y curl

# 2. コンテナ内の作業ディレクトリを設定
WORKDIR /app

# 3. 依存パッケージリストをコピーしてインストール   
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. アプリケーションのソースコードを/app/配下にコピー
COPY . .

# 5. Flaskアプリケーションの実行
CMD ["python", "app.py"]