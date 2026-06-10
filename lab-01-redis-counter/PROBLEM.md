# Lab 01: Redisでアクセス回数を保存するWeb API

## 1. 問題名

**Redisでアクセス回数を保存するWeb APIをDocker Composeで構築せよ**

## 2. 問題詳細

あなたは、小規模なWebサービスの開発環境をDockerで構築することになりました。

Web APIにアクセスすると、これまでにアクセスされた回数をJSON形式で返します。アクセス回数はRedisに保存してください。

アプリケーションとRedisは、それぞれ異なるコンテナとして起動します。
`docker compose up` を実行するだけで、必要な環境がまとめて起動する構成を作成してください。

---

## 作成する構成

以下の2つのコンテナを起動してください。

| コンテナ    | 役割                     |
| ------- | ---------------------- |
| `app`   | HTTPリクエストを受け付けるWeb API |
| `redis` | アクセス回数を保存するデータストア      |

構成イメージ:

```text
ブラウザ・curl
      |
      | HTTPリクエスト
      v
 appコンテナ
      |
      | Redisへの接続
      v
redisコンテナ
      |
      v
 Docker Volume
```

---

## 使用する技術

Web APIは **Python + Flask** で実装してください。

必要なファイルは以下のとおりです。

```text
lab-01-redis-counter/
├── app.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

---

## API仕様

### `GET /`

以下の形式でレスポンスを返してください。

```json
{
  "message": "Hello from Docker",
  "count": 1
}
```

同じエンドポイントに再度アクセスすると、`count` が増加します。

```json
{
  "message": "Hello from Docker",
  "count": 2
}
```

### `GET /health`

アプリケーションが起動している場合は、以下のレスポンスを返してください。

```json
{
  "status": "ok"
}
```

---

## 必須要件

### 1. アプリケーション用のDockerfileを作成する

`app` コンテナは、自作のDockerfileからビルドしてください。

Dockerfileでは、最低限以下の処理を行ってください。

* Pythonのベースイメージを使用する
* 依存ライブラリをインストールする
* アプリケーションコードをコンテナ内へコピーする
* Flaskアプリケーションを起動する
* コンテナの外部からHTTPリクエストを受け付けられるようにする

---

### 2. `docker-compose.yml` で2つのサービスを定義する

以下のサービスを定義してください。

#### `app`

* 自作のDockerfileを使用してイメージをビルドする
* ホストPCの `8080` 番ポートからアクセスできるようにする
* Redisの接続先を環境変数で受け取る
* Redisが利用可能になってから起動する

#### `redis`

* Redisの公式イメージを使用する
* アクセス回数を永続化する
* Redisが利用可能か確認するヘルスチェックを設定する

---

### 3. 環境変数を使用する

アプリケーションコードにRedisの接続先を直接書かないでください。

以下の環境変数を使用してください。

| 環境変数名        | 用途          |
| ------------ | ----------- |
| `REDIS_HOST` | Redisのホスト名  |
| `REDIS_PORT` | Redisのポート番号 |

`REDIS_HOST` には、Docker Composeで定義したRedisのサービス名を指定してください。

---

### 4. Docker Volumeを使用する

Redisのデータは、Docker Volumeに保存してください。

以下の操作を行っても、アクセス回数が維持されることを確認してください。

```bash
docker compose down
docker compose up -d
```

一方で、Volumeも含めて削除した場合は、アクセス回数がリセットされることを確認してください。

```bash
docker compose down -v
docker compose up -d
```

---

### 5. ヘルスチェックを設定する

Redisコンテナには、Redisが利用可能か確認するヘルスチェックを設定してください。

`app` コンテナは、Redisコンテナのプロセスが開始しただけではなく、ヘルスチェックが成功した後に起動するようにしてください。

---

## 動作確認

### 起動

```bash
docker compose up -d --build
```

### 起動状態の確認

```bash
docker compose ps
```

### APIへのアクセス

```bash
curl http://localhost:8080/
```

複数回実行し、`count` が増加することを確認してください。

### ヘルスチェック用APIへのアクセス

```bash
curl http://localhost:8080/health
```

### ログの確認

```bash
docker compose logs
```

### Redisに保存された値の確認

```bash
docker compose exec redis redis-cli GET count
```

### 終了

```bash
docker compose down
```

---

## 完了条件

以下をすべて満たしたら完了です。

* `docker compose up -d --build` で環境を起動できる
* `http://localhost:8080/` にアクセスできる
* アクセスするたびに `count` が増加する
* `app` と `redis` が別々のコンテナで動いている
* アプリケーションからRedisへ接続できる
* Redisの接続先が環境変数で設定されている
* RedisのデータがDocker Volumeに保存されている
* Redisにヘルスチェックが設定されている
* Redisが利用可能になった後に `app` が起動する
* `docker compose down` 後に再起動してもアクセス回数が維持される
* `docker compose down -v` 後に再起動するとアクセス回数がリセットされる

---

## 制約

* RedisをホストPCに直接インストールしないこと
* `app.py` に `localhost` や `127.0.0.1` をRedisの接続先として記述しないこと
* 最初はインターネット上の完成済み `docker-compose.yml` をコピーしないこと
* エラーが発生した場合は、まず `docker compose ps` と `docker compose logs` を確認すること

---

## 発展課題

時間が余った場合のみ取り組んでください。

### 発展課題1: `.env` ファイルを使用する

Redisのポート番号や、ホストPC側で公開するポート番号を `.env` ファイルへ切り出してください。

### 発展課題2: `app` にもヘルスチェックを設定する

`GET /health` を利用して、`app` コンテナにもヘルスチェックを追加してください。

### 発展課題3: RedisをホストPCから直接操作できない構成にする

RedisのポートをホストPCに公開せず、`app` コンテナからのみ接続できることを確認してください。
