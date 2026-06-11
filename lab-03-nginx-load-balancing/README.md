# Lab 03: 複数のappコンテナへリクエストを分散する

## 1. 問題名

**Flaskアプリケーションを3コンテナへスケールし、Nginxでロードバランシングせよ**

---

## 2. 問題詳細

前回は、Nginx、Flaskアプリケーション、Redisを分離しました。

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

今回は、Flaskアプリケーションを3コンテナへ増やしてください。

```text
                         +----------+
                      +->|  app-1   |--+
                      |  |  :8000   |  |
                      |  +----------+  |
                      |                |
ホストPC ---> nginx --+->+----------+  +--> redis
             :8080       |  app-2   |--+     :6379
                         |  :8000   |  |
                         +----------+  |
                      |                |
                      |  +----------+  |
                      +->|  app-3   |--+
                         |  :8000   |
                         +----------+
```

Nginxは、受け取ったHTTPリクエストを3つのFlaskコンテナへ分散します。

Redisは1コンテナのままにしてください。

各Flaskコンテナは同じRedisを利用するため、どのFlaskコンテナがリクエストを処理しても、アクセス回数は共通です。

---

## 3. 学習目的

この課題では、以下の内容を学習します。

* 1つのComposeサービスから同一構成のコンテナを複数起動する
* `docker compose up --scale` を使用する
* Nginxの `upstream` を使用する
* ラウンドロビン方式でHTTPリクエストを分散する
* ステートレスなアプリケーションの考え方を理解する
* 複数のアプリケーションコンテナからRedisを共有する
* 1つのアプリケーションコンテナが停止してもサービスを継続できることを確認する
* KubernetesのDeployment、Replica、Serviceへつながる構造を理解する

---

## 4. 作成する構成

ネットワーク構成は、Lab 02と同じです。

```text
                  frontend network
        +---------------------------------------+
        |                                       |
        |                  +----------+         |
        |               +->|  app-1   |         |
        |               |  +----------+         |
外部 ---> nginx --------+->|  app-2   |         |
        |               |  +----------+         |
        |               +->|  app-3   |         |
        |                  +-----+----+         |
        +------------------------|--------------+
                                 |
                                 |
                  backend network
        +------------------------|--------------+
        |                        v              |
        |                    +-------+          |
        |                    | redis |          |
        |                    +-------+          |
        +---------------------------------------+
```

各サービスが参加するネットワークは以下のとおりです。

| サービス    | コンテナ数 | `frontend` | `backend` |
| ------- | ----: | ---------- | --------- |
| `nginx` |     1 | 接続する       | 接続しない     |
| `app`   |     3 | 接続する       | 接続する      |
| `redis` |     1 | 接続しない      | 接続する      |

---

## 5. Lab 02をコピーする

```bash
cd docker-usecase-labs

cp -r lab-02-nginx-reverse-proxy lab-03-nginx-load-balancing
cd lab-03-nginx-load-balancing
```

最終的なディレクトリ構成は以下です。

```text
lab-03-nginx-load-balancing/
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

---

## 6. Flaskアプリケーションを変更する

どのFlaskコンテナがリクエストを処理したか確認できるように、レスポンスへコンテナのホスト名を追加します。

`app/app.py` を以下の内容へ置き換えてください。

```python
import os
import socket

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
            "message": "Hello from a scaled app container",
            "instance": socket.gethostname(),
            "count": count,
        }
    )


@app.get("/health")
def health():
    return jsonify(
        {
            "status": "ok",
            "instance": socket.gethostname(),
        }
    )


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=8000,
    )
```

`socket.gethostname()` で、処理を実行したコンテナのホスト名を取得できます。

レスポンスは以下のような形式になります。

```json
{
  "message": "Hello from a scaled app container",
  "instance": "a1b2c3d4e5f6",
  "count": 1
}
```

`instance` はコンテナごとに異なります。

---

## 7. Flask用Dockerfileを確認する

`app/Dockerfile` はLab 02で作成したものをそのまま使用してください。

以下の要件を満たしていることを確認してください。

* `python:3.14-slim` を使用している
* `curl` をインストールしている
* 作業ディレクトリが `/app` である
* `requirements.txt` を先にコピーしている
* `pip install --no-cache-dir -r requirements.txt` を実行している
* アプリケーションコードをコピーしている
* `EXPOSE 8000` を記述している
* `CMD ["python", "app.py"]` を記述している

---

## 8. Nginx用Dockerfileを確認する

`nginx/Dockerfile` もLab 02で作成したものをそのまま使用してください。

以下の要件を満たしていることを確認してください。

* `nginx:alpine` を使用している
* `curl` をインストールしている
* `default.conf` を `/etc/nginx/conf.d/default.conf` へコピーしている
* `EXPOSE 80` を記述している

---

## 9. Nginxの設定を変更する

Lab 02では、Nginxから1つのFlaskアプリケーションへ直接リクエストを転送していました。

```nginx
proxy_pass http://app:8000;
```

今回は、複数のFlaskコンテナを転送先として扱えるように、`upstream` を定義してください。

`nginx/default.conf` を自分で変更してください。

### 必須要件

以下の要件を満たしてください。

1. `upstream` の名前を `app_servers` にする
2. 転送先として `app:8000` を指定する
3. `location /` では `http://app_servers` へ転送する
4. `Host` ヘッダーを引き継ぐ
5. `X-Real-IP` ヘッダーを引き継ぐ

### 使用する構文

```nginx
upstream 名前 {
    server 転送先;
}

server {
    listen 80;

    location / {
        proxy_pass http://upstreamの名前;
    }
}
```

### ポイント

Composeで `app` サービスを3コンテナへスケールすると、`app` というサービス名は複数のIPアドレスへ名前解決されます。

Nginxは、起動時に取得した複数のIPアドレスを転送先として扱います。

---

## 10. `docker-compose.yml` を確認する

Lab 02で作成した `docker-compose.yml` を基本的にそのまま使用できます。

ただし、以下を確認してください。

### `container_name` を書かない

`app` サービスには、以下のような固定コンテナ名を設定しないでください。

```yaml
container_name: flask-app
```

同じ名前のコンテナを複数作成できないためです。

Composeにコンテナ名の割り当てを任せてください。

---

### `app` に `ports` を書かない

`app` サービスは、ホストPCへ直接公開しません。

```yaml
app:
  # portsは設定しない
```

外部からのHTTPリクエストは、必ずNginxを経由させてください。

---

### `redis` は1コンテナのままにする

Redisをスケールしないでください。

今回は、3つのFlaskコンテナから1つのRedisコンテナを共有します。

---

### `docker-compose.yml` の骨組み

以下の構造になっていることを確認してください。

```yaml
services:
  nginx:
    build: ./nginx
    ports:
      - "${NGINX_PORT}:80"
    depends_on:
      app:
        condition: service_healthy
    healthcheck:
      # TODO: Nginx自身のヘルスチェック
    networks:
      - frontend

  app:
    build: ./app
    environment:
      # TODO: Redisの接続情報
    depends_on:
      redis:
        condition: service_healthy
    healthcheck:
      # TODO: Flaskアプリケーションのヘルスチェック
    networks:
      - frontend
      - backend

  redis:
    image: redis:8.6.4-alpine
    healthcheck:
      # TODO: redis-cli ping
    volumes:
      - redis-data:/data
    networks:
      - backend

volumes:
  redis-data:

networks:
  frontend:
  backend:
```

Lab 02で実装済みの設定は、そのまま残してください。

---

## 11. Composeファイルの構文を確認する

```bash
docker compose config
```

エラーが表示されないことを確認してください。

---

## 12. 既存のコンテナを削除する

Nginxが3つのFlaskコンテナを起動時に認識できるように、一度既存のコンテナを削除します。

Redisのカウンターを残したい場合は、Volumeを削除しないでください。

```bash
docker compose down
```

カウンターもリセットしたい場合は、Volumeを含めて削除してください。

```bash
docker compose down -v
```

---

## 13. `app` を3コンテナへスケールして起動する

以下のコマンドを実行してください。

```bash
docker compose up -d --build --scale app=3 --wait
```

`--scale app=3` によって、`app` サービスのコンテナを3つ起動します。

`--wait` によって、サービスが起動済みまたはhealthyになるまで待機します。

---

## 14. 起動状態を確認する

```bash
docker compose ps
```

以下のように、`app` コンテナが3つ表示されることを確認してください。

```text
NAME                                      SERVICE   STATUS
lab-03-nginx-load-balancing-nginx-1       nginx     Up (healthy)
lab-03-nginx-load-balancing-app-1         app       Up (healthy)
lab-03-nginx-load-balancing-app-2         app       Up (healthy)
lab-03-nginx-load-balancing-app-3         app       Up (healthy)
lab-03-nginx-load-balancing-redis-1       redis     Up (healthy)
```

実際のコンテナ名は、Composeのプロジェクト名によって異なります。

---

## 15. Nginxの設定を確認する

Nginxコンテナ内で、実際に読み込まれている設定を表示してください。

```bash
docker compose exec nginx nginx -T
```

出力内に以下が含まれていることを確認してください。

```nginx
upstream app_servers {
    server app:8000;
}
```

---

## 16. ロードバランシングを確認する

以下を実行してください。

```bash
for i in {1..12}; do
  curl -s http://localhost:8080/
  echo
done
```

PowerShellを使用する場合は、以下を実行してください。

```powershell
1..12 | ForEach-Object {
    curl.exe -s http://localhost:8080/
    Write-Output ""
}
```

レスポンス例:

```json
{"count":1,"instance":"f4a92c6381e7","message":"Hello from a scaled app container"}
{"count":2,"instance":"0c35e1315df1","message":"Hello from a scaled app container"}
{"count":3,"instance":"9836e4f315da","message":"Hello from a scaled app container"}
{"count":4,"instance":"f4a92c6381e7","message":"Hello from a scaled app container"}
```

確認するポイントは2つあります。

### `instance` が切り替わる

複数の異なる `instance` が表示されれば、Nginxが複数のFlaskコンテナへリクエストを分散しています。

完全に同じ順序で交互に表示されるとは限りません。

複数のコンテナが処理に使われていることを確認してください。

### `count` は共通で増加する

処理を担当するFlaskコンテナが切り替わっても、`count` は連続して増加します。

3つのFlaskコンテナが、同じRedisを共有しているためです。

---

## 17. Redisの値を直接確認する

```bash
docker compose exec redis redis-cli GET count
```

APIへアクセスした回数に応じて、値が増加していることを確認してください。

---

## 18. appコンテナが3つ存在することを確認する

```bash
docker compose ps app
```

Docker Engine側から確認する場合は、以下も実行してください。

```bash
docker ps
```

`app` サービスに対応するコンテナが3つ存在することを確認してください。

---

## 19. 1つのappコンテナを停止する

起動中の `app` コンテナ名を確認してください。

```bash
docker compose ps app
```

表示されたコンテナのうち、1つを停止してください。

```bash
docker stop <停止するappコンテナ名>
```

例:

```bash
docker stop lab-03-nginx-load-balancing-app-2
```

---

## 20. 一部停止後もAPIが利用できることを確認する

再度、複数回アクセスしてください。

```bash
for i in {1..10}; do
  curl -s http://localhost:8080/
  echo
done
```

PowerShellの場合:

```powershell
1..10 | ForEach-Object {
    curl.exe -s http://localhost:8080/
    Write-Output ""
}
```

停止していないFlaskコンテナからレスポンスが返れば成功です。

```text
app-1   稼働中
app-2   停止
app-3   稼働中
```

```text
nginx
  |
  +--> app-1
  |
  +--> app-3
```

1つのFlaskコンテナが停止しても、サービス全体は継続できます。

---

## 21. appコンテナを3つに戻す

以下を実行してください。

```bash
docker compose up -d --scale app=3
```

appコンテナが再作成された場合は、Nginxに転送先を再認識させるため、Nginxも再起動してください。

```bash
docker compose restart nginx
```

状態を確認してください。

```bash
docker compose ps
```

---

## 22. スケールダウンを確認する

appコンテナを1つに減らしてください。

```bash
docker compose up -d --scale app=1
docker compose restart nginx
```

状態を確認します。

```bash
docker compose ps
```

`app` コンテナが1つだけになっていることを確認してください。

APIへ複数回アクセスしてください。

```bash
curl http://localhost:8080/
curl http://localhost:8080/
curl http://localhost:8080/
```

すべてのレスポンスで同じ `instance` が表示されれば成功です。

---

## 23. 再び3コンテナへ増やす

```bash
docker compose up -d --scale app=3
docker compose restart nginx
```

ロードバランシングが再び機能することを確認してください。

---

## 24. 考察課題

以下の問いに、自分の言葉で回答してください。

### 問1

なぜ `app` サービスには `container_name` を指定しない方がよいのか。

### 問2

なぜ `app` サービスには `ports` を設定しなくても、Nginxからアクセスできるのか。

### 問3

3つのFlaskコンテナが別々に動作しているのに、なぜ `count` は共通で増加するのか。

### 問4

Flaskコンテナ内のメモリだけにアクセス回数を保存した場合、どのような問題が起きるか。

### 問5

`app` コンテナを3つから4つへ増やした後、Nginxを再起動する理由は何か。

### 問6

Kubernetesで同様の構成を作る場合、Flaskコンテナの個数はどのリソースで指定するか。

---

## 25. 発展課題

余裕がある場合のみ取り組んでください。

### 発展課題1: appコンテナを5つへ増やす

```bash
docker compose up -d --scale app=5
docker compose restart nginx
```

APIへ複数回アクセスし、5種類の `instance` が表示されることを確認してください。

---

### 発展課題2: `least_conn` を使用する

Nginxの `upstream` に以下を追加してください。

```nginx
least_conn;
```

```nginx
upstream app_servers {
    least_conn;

    server app:8000;
}
```

ラウンドロビン方式との違いを調べてください。

---

### 発展課題3: Composeファイルへデフォルトのレプリカ数を書く

CLIの `--scale app=3` を毎回指定する代わりに、`app` サービスへ以下を追加してください。

```yaml
scale: 3
```

その後、以下で3コンテナが起動することを確認してください。

```bash
docker compose down
docker compose up -d --build --wait
```

---

## 26. 完了条件

以下をすべて満たしたら完了です。

* Lab 02の3サービス構成を維持できている
* `app` サービスに `container_name` を指定していない
* `app` サービスを3コンテナへスケールできる
* `nginx` と `redis` は1コンテナのままである
* Nginxの `upstream` を設定できる
* Nginxから複数のFlaskコンテナへリクエストを分散できる
* レスポンスの `instance` が複数の値に切り替わる
* レスポンスを処理するコンテナが変わっても `count` が連続して増加する
* 1つのFlaskコンテナを停止してもAPIを利用できる
* appコンテナをスケールダウンできる
* appコンテナを再びスケールアップできる
* RedisのデータがVolumeに保存される
* `frontend` と `backend` のネットワーク分離を維持できている

---

## 27. Kubernetesとの対応関係

| Docker Compose    | Kubernetesで近い概念       |
| ----------------- | --------------------- |
| `app` サービス        | Deployment            |
| `--scale app=3`   | `spec.replicas: 3`    |
| 3つのappコンテナ        | 3つのPod                |
| Nginxの `upstream` | Serviceによる負荷分散        |
| `app` というサービス名    | Kubernetes Service名   |
| Redisの共有          | 外部状態を共有するデータストア       |
| コンテナ停止後も処理を継続     | 複数Replicaによる可用性向上     |
| Redis用Volume      | PersistentVolumeClaim |

Docker ComposeとKubernetesは、完全に同じ仕組みではありません。

ただし、今回の課題では以下の構造を意識してください。

```text
同じアプリケーションを複数起動する
        ↓
入口でリクエストを分散する
        ↓
状態はアプリケーションコンテナの外部へ保存する
```

この考え方が、KubernetesのDeployment、Replica、Serviceを理解する基礎になります。

---

## 28. 提出する内容

課題が完了したら、以下を提出してください。

```text
app/app.py
nginx/default.conf
docker-compose.yml
```

あわせて、以下のコマンドの実行結果も提出してください。

```bash
docker compose ps
```

```bash
for i in {1..6}; do
  curl -s http://localhost:8080/
  echo
done
```

Windows PowerShellの場合:

```powershell
1..6 | ForEach-Object {
    curl.exe -s http://localhost:8080/
    Write-Output ""
}
```
