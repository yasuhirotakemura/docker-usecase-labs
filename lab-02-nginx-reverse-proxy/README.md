# Lab 02: Nginxを入口にした3コンテナ構成

## 1. 問題名

**Nginxをリバースプロキシとして使用し、外部公開するコンテナと内部専用コンテナを分離せよ**

---

## 2. 問題詳細

前回は、ホストPCからFlaskアプリケーションへ直接アクセスする構成を作成しました。

```text
ホストPC
   |
   | localhost:8080
   v
 app
   |
   v
 redis
```

今回は、Webアプリケーションの前段にNginxを追加してください。

```text
ホストPC
   |
   | localhost:8080
   v
 nginx
   |
   | http://app:8000
   v
 app
   |
   | redis:6379
   v
 redis
```

Nginxは、外部から受け取ったHTTPリクエストをFlaskアプリケーションへ転送する**リバースプロキシ**として動作させます。

ホストPCへポートを公開するのはNginxだけにしてください。

FlaskアプリケーションとRedisは、Docker内部のネットワークからのみアクセスできる構成にしてください。

---

## 3. 学習目的

この課題では、以下の内容を学習します。

* 複数のDockerfileを作成する
* Nginxをリバースプロキシとして使用する
* Composeのサービス名を利用してコンテナ間通信を行う
* ホストPCへ公開するポートを必要最低限にする
* Docker Networkを利用して通信経路を分離する
* ヘルスチェックと依存関係を設定する
* Docker Volumeを利用してRedisのデータを永続化する

---

## 4. 作成する構成

今回は、3つのコンテナを起動してください。

| コンテナ    | 役割                             |
| ------- | ------------------------------ |
| `nginx` | 外部からHTTPリクエストを受け取り、`app` へ転送する |
| `app`   | Flaskで動作するWeb API              |
| `redis` | アクセス回数を保存するデータストア              |

また、ネットワークを2つに分けてください。

```text
                  frontend network
        +-----------------------------------+
        |                                   |
        |   +---------+       +---------+   |
外部 --->|   nginx    | ----> |   app   |   |
        |   :80       |       |  :8000  |   |
        |   公開      |       | 非公開  |   |
        |   +---------+       +----+----+   |
        |                          |        |
        +--------------------------|--------+
                                   |
                                   |
                  backend network  |
        +--------------------------|--------+
        |                          v        |
        |                     +---------+   |
        |                     |  redis  |   |
        |                     |  :6379  |   |
        |                     | 非公開  |   |
        |                     +---------+   |
        +-----------------------------------+
```

各サービスが参加するネットワークは以下のとおりです。

| サービス    | `frontend` | `backend` |
| ------- | ---------- | --------- |
| `nginx` | 接続する       | 接続しない     |
| `app`   | 接続する       | 接続する      |
| `redis` | 接続しない      | 接続する      |

`app` は以下の2つの役割を持つため、両方のネットワークへ接続してください。

* NginxからHTTPリクエストを受け取る
* Redisへアクセス回数を保存する

---

## 5. ディレクトリ構成

以下のディレクトリ構成を作成してください。

```text
lab-02-nginx-reverse-proxy/
├── .env
├── docker-compose.yml
├── app/
│   ├── app.py
│   ├── requirements.txt
│   └── Dockerfile
└── nginx/
    ├── default.conf
    └── Dockerfile
```

前回の課題をコピーして使用して構いません。

```bash
cd docker-usecase-labs

cp -r lab-01-redis-counter lab-02-nginx-reverse-proxy
cd lab-02-nginx-reverse-proxy

mkdir -p app nginx
touch nginx/default.conf
touch nginx/Dockerfile
```

---

## 6. Flaskアプリケーション

`app/app.py` は以下の内容をそのまま使用してください。

```python
import os

from flask import Flask, jsonify
from redis import Redis

app = Flask(__name__)

redis_client = Redis(
    host=os.environ["REDIS_HOST"],
    port=int(os.environ["REDIS_PORT"]),
    decode_responses=True,
)


@app.get("/")
def index():
    count = redis_client.incr("count")

    return jsonify(
        {
            "message": "Hello through Nginx",
            "count": count,
        }
    )


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=8000,
    )
```

`app/requirements.txt` は以下の内容を使用してください。

```text
Flask
redis
```

---

## 7. Nginxの設定ファイル

`nginx/default.conf` は以下の内容をそのまま使用してください。

```nginx
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://app:8000;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

重要なのは以下の設定です。

```nginx
proxy_pass http://app:8000;
```

転送先には、IPアドレスや `localhost` ではなく、Composeのサービス名である `app` を指定しています。

---

## 8. 環境変数

`.env` を作成し、以下の内容を記述してください。

```dotenv
NGINX_PORT=8080
```

今回は、FlaskアプリケーションではなくNginxのポートをホストPCへ公開します。

---

## 9. `app/Dockerfile` を実装する

Flaskアプリケーション用のDockerfileを自分で記述してください。

### 必須要件

以下の処理を順番に記述してください。

1. Pythonの軽量イメージを使用する
2. `curl` をインストールする
3. コンテナ内の作業ディレクトリを `/app` に設定する
4. `requirements.txt` をコピーする
5. Pythonライブラリをインストールする
6. アプリケーションコードをコピーする
7. アプリケーションが `8000` 番ポートを使用することを明示する
8. コンテナ起動時に `python app.py` を実行する

### 使用するベースイメージ

```text
python:3.14-slim
```

### 使用するDockerfile命令

```text
FROM
RUN
WORKDIR
COPY
EXPOSE
CMD
```

### ヒント

`curl` は、`app` コンテナのヘルスチェックで使用します。

Debian系のベースイメージでは、以下のようにパッケージをインストールできます。

```dockerfile
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*
```

---

## 10. `nginx/Dockerfile` を実装する

Nginx用のDockerfileを自分で記述してください。

### 必須要件

以下の処理を記述してください。

1. NginxのAlpine Linux版イメージを使用する
2. `curl` をインストールする
3. `default.conf` をNginxの設定ディレクトリへコピーする
4. Nginxが `80` 番ポートを使用することを明示する

### 使用するベースイメージ

```text
nginx:alpine
```

### 設定ファイルのコピー先

```text
/etc/nginx/conf.d/default.conf
```

### 使用するDockerfile命令

```text
FROM
RUN
COPY
EXPOSE
```

### ヒント

Alpine Linuxでは、`apt-get` ではなく `apk` を使用します。

```dockerfile
RUN apk add --no-cache curl
```

---

## 11. `docker-compose.yml` を実装する

以下の要件を満たす `docker-compose.yml` を自分で記述してください。

---

### `nginx` サービス

| 設定            | 値                                 |
| ------------- | --------------------------------- |
| サービス名         | `nginx`                           |
| Dockerfileの場所 | `./nginx`                         |
| ホストPC側のポート    | `${NGINX_PORT:-8080}`             |
| コンテナ側のポート     | `80`                              |
| 接続するネットワーク    | `frontend`                        |
| 起動条件          | `app` がhealthyになった後               |
| ヘルスチェック       | `curl -f http://localhost/health` |
| チェック間隔        | `5s`                              |
| タイムアウト        | `3s`                              |
| リトライ回数        | `5`                               |
| 起動猶予時間        | `5s`                              |

---

### `app` サービス

| 設定            | 値                                      |
| ------------- | -------------------------------------- |
| サービス名         | `app`                                  |
| Dockerfileの場所 | `./app`                                |
| ホストPCへのポート公開  | 設定しない                                  |
| Redisのホスト名    | `redis`                                |
| Redisのポート番号   | `6379`                                 |
| 接続するネットワーク    | `frontend`、`backend`                   |
| 起動条件          | `redis` がhealthyになった後                  |
| ヘルスチェック       | `curl -f http://localhost:8000/health` |
| チェック間隔        | `5s`                                   |
| タイムアウト        | `3s`                                   |
| リトライ回数        | `5`                                    |
| 起動猶予時間        | `5s`                                   |

---

### `redis` サービス

| 設定           | 値                    |
| ------------ | -------------------- |
| サービス名        | `redis`              |
| 使用するイメージ     | `redis:8.6.4-alpine` |
| ホストPCへのポート公開 | 設定しない                |
| 接続するネットワーク   | `backend`            |
| Volume       | `redis-data:/data`   |
| ヘルスチェック      | `redis-cli ping`     |
| チェック間隔       | `5s`                 |
| タイムアウト       | `3s`                 |
| リトライ回数       | `5`                  |
| 起動猶予時間       | `5s`                 |

---

### 名前付きVolume

以下のVolumeを宣言してください。

```text
redis-data
```

---

### 名前付きNetwork

以下のNetworkを宣言してください。

```text
frontend
backend
```

---

## 12. `docker-compose.yml` の骨組み

以下を出発点にしてください。

```yaml
services:
  nginx:
    # TODO: ./nginx のDockerfileからビルドする

    # TODO: ホストPCの8080番ポートを
    #       nginxコンテナの80番ポートへ接続する

    # TODO: appがhealthyになった後に起動する

    # TODO: ヘルスチェックを追加する

    # TODO: frontendネットワークへ接続する

  app:
    # TODO: ./app のDockerfileからビルドする

    # TODO: Redisの接続情報を環境変数で渡す

    # TODO: redisがhealthyになった後に起動する

    # TODO: ヘルスチェックを追加する

    # TODO: frontendとbackendへ接続する

  redis:
    # TODO: Redis公式イメージを使用する

    # TODO: RedisのデータをVolumeへ保存する

    # TODO: ヘルスチェックを追加する

    # TODO: backendネットワークへ接続する

volumes:
  # TODO: redis-dataを定義する

networks:
  # TODO: frontendを定義する

  # TODO: backendを定義する
```

---

## 13. 動作確認

### Composeファイルの構文を確認する

```bash
docker compose config
```

### コンテナを起動する

```bash
docker compose up -d --build
```

### コンテナの状態を確認する

```bash
docker compose ps
```

最終的に、すべてのサービスがhealthyになれば成功です。

```text
nginx    healthy
app      healthy
redis    healthy
```

---

## 14. Nginx経由でAPIへアクセスする

以下を複数回実行してください。

```bash
curl http://localhost:8080/
curl http://localhost:8080/
```

想定されるレスポンスは以下です。

```json
{"count":1,"message":"Hello through Nginx"}
{"count":2,"message":"Hello through Nginx"}
```

通信経路は以下のとおりです。

```text
curl
  ↓
localhost:8080
  ↓
nginx:80
  ↓
app:8000
  ↓
redis:6379
```

ヘルスチェック用APIも確認してください。

```bash
curl http://localhost:8080/health
```

想定されるレスポンスは以下です。

```json
{"status":"ok"}
```

---

## 15. 外部公開が制限されていることを確認する

Flaskアプリケーションへ直接アクセスしてください。

```bash
curl http://localhost:8000/
```

接続に失敗すれば正解です。

Flaskアプリケーションは起動していますが、ホストPCへポートを公開していないため、直接アクセスできません。

ホストPCに `redis-cli` がインストールされている場合は、Redisにも直接アクセスしてください。

```bash
redis-cli -h localhost -p 6379 ping
```

接続に失敗すれば正解です。

Redisについても、ホストPCへポートを公開していません。

---

## 16. コンテナ間通信を確認する

NginxコンテナからFlaskアプリケーションへアクセスしてください。

```bash
docker compose exec nginx curl -f http://app:8000/health
```

成功すれば、`nginx` と `app` が同じ `frontend` ネットワーク上で通信できています。

次に、FlaskアプリケーションからRedisへ接続してください。

```bash
docker compose exec app python -c "from redis import Redis; print(Redis(host='redis', port=6379).ping())"
```

以下が表示されれば成功です。

```text
True
```

---

## 17. ネットワーク分離を確認する

NginxコンテナからRedisへの接続を試してください。

```bash
docker compose exec nginx curl --connect-timeout 3 redis:6379
```

接続に失敗すれば正解です。

`nginx` と `redis` は共通のネットワークに参加していないため、直接通信できません。

ネットワーク一覧も確認してください。

```bash
docker network ls
```

作成されたネットワークの詳細を確認してください。

```bash
docker network inspect lab-02-nginx-reverse-proxy_frontend
docker network inspect lab-02-nginx-reverse-proxy_backend
```

実際のネットワーク名は、Composeのプロジェクト名によって異なる場合があります。

---

## 18. Volumeによる永続化を確認する

### Volumeを残してコンテナを削除する

```bash
docker compose down
docker compose up -d
curl http://localhost:8080/
```

以前の値からカウンターが増えていれば成功です。

### Volumeも含めて削除する

```bash
docker compose down -v
docker compose up -d
curl http://localhost:8080/
```

カウンターが `1` に戻れば成功です。

---

## 19. エラーが発生した場合の確認手順

コンテナの状態を確認してください。

```bash
docker compose ps
```

すべてのログを確認してください。

```bash
docker compose logs
```

サービスごとのログも確認できます。

```bash
docker compose logs nginx
docker compose logs app
docker compose logs redis
```

Composeが解釈した設定内容を確認してください。

```bash
docker compose config
```

---

## 20. 完了条件

以下をすべて満たしたら完了です。

* `nginx`、`app`、`redis` の3コンテナを起動できる
* Nginx用とFlask用のDockerfileを作成できる
* ホストPCからはNginxにのみアクセスできる
* Nginxから `app:8000` へ接続できる
* Flaskアプリケーションから `redis:6379` へ接続できる
* ホストPCからFlaskアプリケーションへ直接アクセスできない
* ホストPCからRedisへ直接アクセスできない
* `nginx` と `redis` が異なるネットワークに分離されている
* Redisがhealthyになった後にFlaskアプリケーションが起動する
* Flaskアプリケーションがhealthyになった後にNginxが起動する
* RedisのデータがDocker Volumeに保存される
* `docker compose down` 後もカウンターが維持される
* `docker compose down -v` 後はカウンターがリセットされる

---

## 21. Kubernetesとの対応関係

| Docker Compose               | Kubernetesで近い概念                        |
| ---------------------------- | -------------------------------------- |
| `nginx` コンテナ                 | Ingress Controller、リバースプロキシ            |
| `app` コンテナ                   | アプリケーションPod                            |
| `redis` コンテナ                 | Redis Pod                              |
| `localhost:8080 → nginx:80`  | 外部公開用Service、Ingress                   |
| `proxy_pass http://app:8000` | Service名によるバックエンド転送                    |
| サービス名による名前解決                 | Kubernetes Service DNS                 |
| `frontend`、`backend`         | NetworkPolicyで制御する通信経路                 |
| Redis用Volume                 | PersistentVolumeClaim、PersistentVolume |

Docker ComposeのNetworkとKubernetesのNetworkPolicyは、厳密には異なる仕組みです。

ただし、この課題では以下の観点を意識してください。

```text
どのサービスを外部へ公開するのか
どのサービス同士を通信させるのか
どのサービス同士を直接通信させないのか
```

---

## 22. 提出するファイル

課題が完了したら、以下の3ファイルを提出してください。

```text
app/Dockerfile
nginx/Dockerfile
docker-compose.yml
```
