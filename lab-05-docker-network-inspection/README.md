# Lab 05: Docker Networkの通信経路を観察する

## 1. 問題名

**複数のDocker Networkを作成し、名前解決・内部IP・公開ポート・ネットワーク分離を観察せよ**

---

## 2. 問題詳細

Docker Composeを使って、以下の4コンテナを起動してください。

| サービス         | 役割                           |
| ------------ | ---------------------------- |
| `client`     | 通信確認用コンテナ                    |
| `public-web` | ホストPCからアクセス可能なWebサーバー        |
| `app`        | Docker内部からのみアクセス可能なWebサーバー   |
| `redis`      | Docker内部からのみアクセス可能なRedisサーバー |

また、以下の3つのNetworkを作成してください。

| Network    | 用途                           |
| ---------- | ---------------------------- |
| `frontend` | `client` と `public-web` 間の通信 |
| `backend`  | `public-web` と `app` 間の通信    |
| `data`     | `app` と `redis` 間の通信         |

構成は以下のとおりです。

```text
ホストPC
   |
   | localhost:8080
   v
+----------------------+
| frontend network     |
|                      |
| client <-> public-web|
+---------------+------+
                |
                | public-webは両方に参加
                |
+---------------+------+
| backend network      |
|                      |
| public-web <-> app   |
+---------------+------+
                |
                | appは両方に参加
                |
+---------------+------+
| data network         |
|                      |
| app <-> redis        |
+----------------------+
```

各サービスの所属関係は以下です。

| サービス         | `frontend` | `backend` | `data` |
| ------------ | ---------- | --------- | ------ |
| `client`     | 接続する       | 接続しない     | 接続しない  |
| `public-web` | 接続する       | 接続する      | 接続しない  |
| `app`        | 接続しない      | 接続する      | 接続する   |
| `redis`      | 接続しない      | 接続しない     | 接続する   |

---

## 3. 学習目的

この課題では、以下の内容を学習します。

* User-defined bridge networkを作成する
* 同じNetwork上のコンテナ間で通信する
* 異なるNetwork上のコンテナ間では直接通信できないことを確認する
* Composeのサービス名による名前解決を確認する
* Network aliasを設定する
* コンテナの内部IPアドレスを確認する
* コンテナ内のネットワークインターフェースとルーティングテーブルを確認する
* `ports` と `expose` の違いを理解する
* ホストPCから公開されているポートを確認する
* 稼働中のコンテナをNetworkへ接続・切断する
* 外部接続から隔離されたNetworkを作成する
* ECSやKubernetesのネットワーク設計を学ぶための前提を整理する

---

## 4. ディレクトリ構成

以下の構成を作成してください。

```text
docker-usecase-labs/
└── lab-05-docker-network-inspection/
    ├── .env
    ├── docker-compose.yml
    └── tools/
        └── Dockerfile
```

ディレクトリとファイルを作成します。

```bash
cd docker-usecase-labs

mkdir -p lab-05-docker-network-inspection/tools
cd lab-05-docker-network-inspection

touch .env
touch docker-compose.yml
touch tools/Dockerfile
```

---

## 5. `.env` を作成する

`.env` に以下を記述してください。

```dotenv
PUBLIC_WEB_PORT=8080
```

---

## 6. 通信確認用イメージを作成する

今回の中心はNetworkの観察です。

通信確認用コマンドを利用できるように、`tools/Dockerfile` は以下をそのまま使用してください。

```dockerfile
FROM alpine:3.22

RUN apk add --no-cache \
    bind-tools \
    curl \
    iproute2 \
    redis

CMD ["sleep", "infinity"]
```

各ライブラリの用途は以下です。

| パッケージ        | 主に使用するコマンド           | 用途               |
| ------------ | -------------------- | ---------------- |
| `bind-tools` | `nslookup`           | DNSによる名前解決の確認    |
| `curl`       | `curl`               | HTTP通信の確認        |
| `iproute2`   | `ip addr`、`ip route` | IPアドレスとルーティングの確認 |
| `redis`      | `redis-cli`          | Redisへの接続確認      |

---

## 7. `docker-compose.yml` を実装する

以下の要件を満たす `docker-compose.yml` を自分で作成してください。

---

### `client` サービス

| 設定            | 値                |
| ------------- | ---------------- |
| サービス名         | `client`         |
| Dockerfileの場所 | `./tools`        |
| 起動コマンド        | `sleep infinity` |
| 接続するNetwork   | `frontend`       |
| ホストPCへのポート公開  | 設定しない            |

---

### `public-web` サービス

| 設定             | 値                          |
| -------------- | -------------------------- |
| サービス名          | `public-web`               |
| Dockerfileの場所  | `./tools`                  |
| コンテナ側のHTTPポート  | `8000`                     |
| ホストPC側のHTTPポート | `${PUBLIC_WEB_PORT:-8080}` |
| 接続するNetwork    | `frontend`、`backend`       |

コンテナ起動時に、以下の処理を実行してください。

```sh
mkdir -p /www
echo "hello-from-public-web" > /www/index.html
exec httpd -f -p 8000 -h /www
```

`httpd` は、Alpine Linuxに含まれる軽量なHTTPサーバーです。

ホストPCから以下へアクセスすると、`hello-from-public-web` が返る構成にしてください。

```text
http://localhost:8080
```

---

### `app` サービス

| 設定                        | 値                |
| ------------------------- | ---------------- |
| サービス名                     | `app`            |
| Dockerfileの場所             | `./tools`        |
| コンテナ側のHTTPポート             | `8000`           |
| ホストPCへのポート公開              | 設定しない            |
| Docker内部へ通知するポート          | `8000`           |
| 接続するNetwork               | `backend`、`data` |
| `backend` 上のNetwork alias | `internal-api`   |

コンテナ起動時に、以下の処理を実行してください。

```sh
mkdir -p /www
echo "hello-from-app" > /www/index.html
exec httpd -f -p 8000 -h /www
```

`app` は、Docker内部からのみアクセス可能にしてください。

---

### `redis` サービス

| 設定           | 値                    |
| ------------ | -------------------- |
| サービス名        | `redis`              |
| イメージ         | `redis:8.6.4-alpine` |
| ホストPCへのポート公開 | 設定しない                |
| 接続するNetwork  | `data`               |

---

### `frontend` Network

| 設定                      | 値                |
| ----------------------- | ---------------- |
| Compose上のNetwork名       | `frontend`       |
| Docker Engine上のNetwork名 | `lab05-frontend` |
| Driver                  | `bridge`         |

---

### `backend` Network

| 設定                      | 値               |
| ----------------------- | --------------- |
| Compose上のNetwork名       | `backend`       |
| Docker Engine上のNetwork名 | `lab05-backend` |
| Driver                  | `bridge`        |

---

### `data` Network

| 設定                      | 値                |
| ----------------------- | ---------------- |
| Compose上のNetwork名       | `data`           |
| Docker Engine上のNetwork名 | `lab05-data`     |
| Driver                  | `bridge`         |
| 外部接続から隔離する              | `internal: true` |

---

## 8. `docker-compose.yml` の骨組み

以下を出発点にしてください。

```yaml
services:
  client:
    build: ./tools

    # TODO: sleep infinityを実行する

    # TODO: frontendへ接続する

  public-web:
    build: ./tools

    # TODO: HTTPサーバーを起動する
    # mkdir -p /www
    # echo "hello-from-public-web" > /www/index.html
    # exec httpd -f -p 8000 -h /www

    # TODO: ホストPCの8080番ポートを
    #       コンテナの8000番ポートへ接続する

    # TODO: frontendとbackendへ接続する

  app:
    build: ./tools

    # TODO: HTTPサーバーを起動する
    # mkdir -p /www
    # echo "hello-from-app" > /www/index.html
    # exec httpd -f -p 8000 -h /www

    # TODO: Docker内部で8000番ポートを使用することを明示する

    # TODO:
    # backendへ接続し、internal-apiというaliasを追加する
    # dataへ接続する

  redis:
    image: redis:8.6.4-alpine

    # TODO: dataへ接続する

networks:
  frontend:
    # TODO:
    # Docker Engine上のNetwork名をlab05-frontendにする
    # bridge driverを使用する

  backend:
    # TODO:
    # Docker Engine上のNetwork名をlab05-backendにする
    # bridge driverを使用する

  data:
    # TODO:
    # Docker Engine上のNetwork名をlab05-dataにする
    # bridge driverを使用する
    # 外部接続から隔離する
```

### コマンドを複数行で書く場合のヒント

以下のように記述できます。

```yaml
command:
  - sh
  - -c
  - |
      mkdir -p /www
      echo "hello" > /www/index.html
      exec httpd -f -p 8000 -h /www
```

### Network aliasを設定する場合のヒント

以下の形式で記述できます。

```yaml
networks:
  backend:
    aliases:
      - internal-api
  data:
```

### Network名を固定する場合のヒント

以下の形式で記述できます。

```yaml
networks:
  frontend:
    name: lab05-frontend
    driver: bridge
```

---

## 9. Composeファイルの構文を確認する

```bash
docker compose config
```

エラーが表示されないことを確認してください。

---

## 10. コンテナを起動する

```bash
docker compose up -d --build
```

状態を確認してください。

```bash
docker compose ps
```

以下の4サービスが起動していれば成功です。

```text
client
public-web
app
redis
```

---

## 11. Network一覧を確認する

Docker Engineが管理しているNetworkを一覧表示してください。

```bash
docker network ls
```

以下の3つが存在することを確認してください。

```text
lab05-frontend
lab05-backend
lab05-data
```

---

## 12. 各Networkの所属コンテナを確認する

`frontend` の詳細を確認してください。

```bash
docker network inspect lab05-frontend
```

出力が多いため、所属コンテナだけを整形して確認する場合は以下を実行してください。

```bash
docker network inspect lab05-frontend \
  --format '{{json .Containers}}' \
  | python -m json.tool
```

同様に、残りのNetworkも確認してください。

```bash
docker network inspect lab05-backend \
  --format '{{json .Containers}}' \
  | python -m json.tool

docker network inspect lab05-data \
  --format '{{json .Containers}}' \
  | python -m json.tool
```

以下の所属関係になっていることを確認してください。

| Network          | 所属するサービス              |
| ---------------- | --------------------- |
| `lab05-frontend` | `client`、`public-web` |
| `lab05-backend`  | `public-web`、`app`    |
| `lab05-data`     | `app`、`redis`         |

---

## 13. 外部接続から隔離されたNetworkを確認する

`lab05-data` の `Internal` を確認してください。

```bash
docker network inspect lab05-data \
  --format '{{.Internal}}'
```

想定される結果:

```text
true
```

---

## 14. コンテナのIPアドレスを確認する

`app` コンテナは、`backend` と `data` の2つのNetworkに参加しています。

以下を実行してください。

```bash
docker inspect "$(docker compose ps -q app)" \
  --format '{{json .NetworkSettings.Networks}}' \
  | python -m json.tool
```

`app` に2つのIPアドレスが割り当てられていることを確認してください。

概念的には以下の状態です。

```text
app
├── lab05-backend上のIPアドレス
└── lab05-data上のIPアドレス
```

---

## 15. コンテナ内のネットワークインターフェースを確認する

`app` コンテナ内で以下を実行してください。

```bash
docker compose exec app ip addr
```

次に、ルーティングテーブルを確認してください。

```bash
docker compose exec app ip route
```

DNSの設定も確認してください。

```bash
docker compose exec app cat /etc/resolv.conf
```

実行環境によって出力は異なります。

確認するポイントは以下です。

```text
appには複数のネットワークインターフェースがある
各インターフェースにはIPアドレスがある
ルーティングテーブルが存在する
DNSサーバーの設定が存在する
```

---

## 16. ホストPCへ公開されたポートを確認する

ホストPCから `public-web` へアクセスしてください。

```bash
curl http://localhost:8080
```

想定される結果:

```text
hello-from-public-web
```

次に、Compose上で公開されているポートを確認します。

```bash
docker compose port public-web 8000
```

想定される結果の例:

```text
0.0.0.0:8080
```

環境によって、IPv6用の公開情報も表示される場合があります。

---

## 17. `app` と `redis` がホストPCへ公開されていないことを確認する

以下を実行してください。

```bash
docker compose port app 8000
```

```bash
docker compose port redis 6379
```

公開ポートが表示されなければ成功です。

### 注意

以下のコマンドで応答が返っても、Compose上の `redis` に接続しているとは限りません。

```bash
redis-cli -h localhost -p 6379 ping
```

ホストPC上で別のRedisが起動している可能性があります。

Compose上で公開されているポートを調べる場合は、以下を使ってください。

```bash
docker compose port redis 6379
```

---

## 18. `client` から通信可能な範囲を確認する

`client` は `frontend` にだけ接続しています。

まず、`public-web` の名前解決を確認してください。

```bash
docker compose exec client nslookup public-web
```

次に、HTTP通信を確認してください。

```bash
docker compose exec client curl -s http://public-web:8000
```

想定される結果:

```text
hello-from-public-web
```

次に、`app` の名前解決を試してください。

```bash
docker compose exec client nslookup app
```

名前解決に失敗すれば成功です。

同様に、Redisの名前解決も試してください。

```bash
docker compose exec client nslookup redis
```

名前解決に失敗すれば成功です。

`client` は `backend` と `data` に参加していません。

---

## 19. `public-web` から通信可能な範囲を確認する

`public-web` は `frontend` と `backend` に参加しています。

`app` の名前解決を確認してください。

```bash
docker compose exec public-web nslookup app
```

HTTP通信を確認してください。

```bash
docker compose exec public-web curl -s http://app:8000
```

想定される結果:

```text
hello-from-app
```

Network aliasでも接続できることを確認してください。

```bash
docker compose exec public-web nslookup internal-api
```

```bash
docker compose exec public-web curl -s http://internal-api:8000
```

想定される結果:

```text
hello-from-app
```

次に、Redisの名前解決を試してください。

```bash
docker compose exec public-web nslookup redis
```

名前解決に失敗すれば成功です。

`public-web` は `data` に参加していません。

---

## 20. `app` からRedisへ接続する

`app` は `data` に参加しています。

以下を実行してください。

```bash
docker compose exec app redis-cli -h redis ping
```

想定される結果:

```text
PONG
```

`app` から `redis` というサービス名でRedisへ接続できています。

---

## 21. 稼働中のコンテナをNetworkへ追加する

現在、`client` は `backend` に参加していません。

`client` コンテナのIDを取得してください。

```bash
CLIENT_ID="$(docker compose ps -q client)"
```

`client` を動的に `lab05-backend` へ追加してください。

```bash
docker network connect lab05-backend "$CLIENT_ID"
```

所属関係を確認してください。

```bash
docker network inspect lab05-backend \
  --format '{{json .Containers}}' \
  | python -m json.tool
```

`client` が追加されていることを確認してください。

---

## 22. Network追加後の通信を確認する

`client` から `app` へアクセスしてください。

```bash
docker compose exec client curl -s http://app:8000
```

想定される結果:

```text
hello-from-app
```

Network aliasも確認してください。

```bash
docker compose exec client curl -s http://internal-api:8000
```

想定される結果:

```text
hello-from-app
```

`client` を `backend` に接続したことで、`app` と通信できるようになりました。

---

## 23. 稼働中のコンテナをNetworkから切断する

`client` を `lab05-backend` から切断してください。

```bash
docker network disconnect lab05-backend "$CLIENT_ID"
```

再度、`app` の名前解決を試してください。

```bash
docker compose exec client nslookup app
```

名前解決に失敗すれば成功です。

---

## 24. `client` を `data` Networkへ一時的に接続する

`client` を `lab05-data` へ接続してください。

```bash
docker network connect lab05-data "$CLIENT_ID"
```

Redisへ接続してください。

```bash
docker compose exec client redis-cli -h redis ping
```

想定される結果:

```text
PONG
```

`app` というサービス名も名前解決できます。

```bash
docker compose exec client nslookup app
```

一方で、以下の名前解決は失敗するはずです。

```bash
docker compose exec client nslookup internal-api
```

`internal-api` というaliasは、`backend` 上でのみ設定されているためです。

Network aliasは、Networkごとに有効範囲が分かれています。

確認後、`client` を切断してください。

```bash
docker network disconnect lab05-data "$CLIENT_ID"
```

---

## 25. `ports` と `expose` の違いを確認する

現在、`public-web` には `ports` を設定しています。

概念的には以下の意味です。

```text
ホストPCの8080番ポート
        ↓
public-webコンテナの8000番ポート
```

一方、`app` には `expose` を設定しています。

```yaml
expose:
  - "8000"
```

`expose` は、ホストPCへポートを公開する設定ではありません。

同じNetworkに参加したコンテナからは、`app:8000` へ接続できます。

---

## 26. `expose` を削除して挙動を確認する

`docker-compose.yml` の `app` から以下を一時的に削除してください。

```yaml
expose:
  - "8000"
```

`app` を再作成してください。

```bash
docker compose up -d --force-recreate app
```

`public-web` から `app` へアクセスしてください。

```bash
docker compose exec public-web curl -s http://app:8000
```

想定される結果:

```text
hello-from-app
```

`expose` を削除しても、同じNetwork上のコンテナからはアクセスできます。

`expose` は、通信許可を制御するファイアウォール設定ではありません。

確認後、学習用に `expose` の記述を戻してください。

---

## 27. コンテナ再作成時のIPアドレスを観察する

`app` のIPアドレスを記録してください。

```bash
docker inspect "$(docker compose ps -q app)" \
  --format '{{json .NetworkSettings.Networks}}' \
  | python -m json.tool
```

`app` を再作成してください。

```bash
docker compose up -d --force-recreate app
```

再びIPアドレスを確認してください。

```bash
docker inspect "$(docker compose ps -q app)" \
  --format '{{json .NetworkSettings.Networks}}' \
  | python -m json.tool
```

IPアドレスが変わる場合もあれば、以前のIPアドレスが再利用される場合もあります。

重要なのは、IPアドレスが固定される保証はないことです。

`public-web` からサービス名でアクセスしてください。

```bash
docker compose exec public-web curl -s http://app:8000
```

想定される結果:

```text
hello-from-app
```

接続側は、個別のIPアドレスではなく、サービス名を使用してください。

---

## 28. Networkを停止・削除する

以下を実行してください。

```bash
docker compose down
```

Network一覧を確認してください。

```bash
docker network ls
```

以下のNetworkが削除されていることを確認してください。

```text
lab05-frontend
lab05-backend
lab05-data
```

Composeが作成したNetworkは、Composeで起動したコンテナとあわせて削除されます。

---

## 29. 考察課題

以下の問いに、自分の言葉で回答してください。

### 問1

`client` から `public-web` へ接続できるのに、`app` へ接続できないのはなぜか。

### 問2

`public-web` は、なぜ `client` と `app` の両方へ接続できるのか。

### 問3

`app` へ `ports` を設定していないのに、`public-web` から `app:8000` へ接続できるのはなぜか。

### 問4

`ports` と `expose` の違いは何か。

### 問5

IPアドレスを直接指定せず、サービス名を使用する利点は何か。

### 問6

`internal-api` というaliasが、`backend` では利用できるのに `data` では利用できないのはなぜか。

### 問7

`data` Networkへ `internal: true` を設定する意図は何か。

### 問8

`public-web` は `frontend` と `backend` の両方へ参加している。これだけで、`client` から `app` への通信を自動的に中継するルーターになるか。

### 問9

本番環境で、Redisの `6379` 番ポートを無条件にホストPCやインターネットへ公開すべきではない理由は何か。

---

## 30. 発展課題

余裕がある場合のみ取り組んでください。

### 発展課題1: `docker network connect` でaliasを追加する

`client` を `lab05-backend` へ接続するとき、aliasも追加してください。

```bash
docker network connect \
  --alias debug-client \
  lab05-backend \
  "$CLIENT_ID"
```

`public-web` から名前解決してください。

```bash
docker compose exec public-web nslookup debug-client
```

確認後、切断してください。

```bash
docker network disconnect lab05-backend "$CLIENT_ID"
```

---

### 発展課題2: NetworkのSubnetを確認する

以下を実行してください。

```bash
docker network inspect lab05-backend \
  --format '{{json .IPAM.Config}}' \
  | python -m json.tool
```

SubnetとGatewayを確認してください。

---

### 発展課題3: NetworkのSubnetを明示的に指定する

`backend` に以下を追加してください。

```yaml
ipam:
  config:
    - subnet: 172.30.0.0/24
```

再作成します。

```bash
docker compose down
docker compose up -d --build
```

Subnetを確認してください。

```bash
docker network inspect lab05-backend \
  --format '{{json .IPAM.Config}}' \
  | python -m json.tool
```

### 注意

既存のNetworkと重複するSubnetは指定しないでください。

---

## 31. 完了条件

以下をすべて満たしたら完了です。

* `frontend`、`backend`、`data` の3つのNetworkを作成できる
* 各サービスを適切なNetworkへ接続できる
* `docker network ls` でNetwork一覧を確認できる
* `docker network inspect` で所属コンテナを確認できる
* `docker inspect` でコンテナの内部IPアドレスを確認できる
* `ip addr` でコンテナ内のネットワークインターフェースを確認できる
* `ip route` でコンテナ内のルーティングテーブルを確認できる
* 同じNetwork上のサービスをサービス名で名前解決できる
* 異なるNetwork上のサービスを直接名前解決できない
* Network aliasを利用できる
* Network aliasの有効範囲がNetworkごとに分かれることを確認できる
* `public-web` のみがホストPCへ公開されている
* `app` と `redis` がホストPCへ公開されていない
* `ports` と `expose` の違いを説明できる
* 稼働中のコンテナをNetworkへ追加できる
* 稼働中のコンテナをNetworkから切断できる
* `internal: true` のNetworkを作成できる
* IPアドレスではなくサービス名を利用する理由を説明できる

---

## 32. ECS・Kubernetesとの接続

Docker、ECS、Kubernetesでは具体的な仕組みが異なります。

ただし、ネットワーク設計で考える観点は共通しています。

| Docker                      | ECS・AWSで考える対象                             | Kubernetesで近い概念               |
| --------------------------- | ----------------------------------------- | ----------------------------- |
| User-defined bridge network | VPC、Subnet、Security Group                 | Pod Network、NetworkPolicy     |
| サービス名による名前解決                | Service Connect、Cloud Mapなど               | Service DNS                   |
| `ports`                     | Load Balancer、Security Group、Port Mapping | Service、NodePort、LoadBalancer |
| Network分離                   | Subnet、Security Group、Network ACL         | Namespace、NetworkPolicy       |
| `internal: true`            | 外部接続を制限したNetwork設計                        | 内部通信専用の構成、NetworkPolicy       |
| Network alias               | サービスディスカバリ上の名前                            | Service名、DNS名                 |
| コンテナの内部IP                   | Task ENIのIPアドレス                           | Pod IP                        |
| 複数Networkへの参加               | 複数の通信経路を持つ設計                              | CNI構成など                       |

完全に1対1で対応するわけではありません。

重要なのは、以下の問いを考えることです。

```text
どのサービスを外部へ公開するのか
どのサービス同士だけ通信できればよいのか
安定した接続先として何を使用するのか
IPアドレスが変わっても動作するか
不要な通信経路を作っていないか
```

---

## 33. 提出する内容

課題が完了したら、以下を提出してください。

```text
docker-compose.yml
```

あわせて、以下のコマンドの実行結果を提出してください。

```bash
docker compose ps
```

```bash
docker network inspect lab05-frontend \
  --format '{{json .Containers}}' \
  | python -m json.tool
```

```bash
docker network inspect lab05-backend \
  --format '{{json .Containers}}' \
  | python -m json.tool
```

```bash
docker network inspect lab05-data \
  --format '{{json .Containers}}' \
  | python -m json.tool
```

```bash
docker inspect "$(docker compose ps -q app)" \
  --format '{{json .NetworkSettings.Networks}}' \
  | python -m json.tool
```

最後に、以下の表へ実際の観察結果を記入してください。

| 実行元                         | 接続先                 | 通信できたか |
| --------------------------- | ------------------- | ------ |
| ホストPC                       | `localhost:8080`    |        |
| `client`                    | `public-web:8000`   |        |
| `client`                    | `app:8000`          |        |
| `client`                    | `redis:6379`        |        |
| `public-web`                | `app:8000`          |        |
| `public-web`                | `internal-api:8000` |        |
| `public-web`                | `redis:6379`        |        |
| `app`                       | `redis:6379`        |        |
| `client` を `backend` へ追加した後 | `app:8000`          |        |
| `client` を `data` へ追加した後    | `redis:6379`        |        |
