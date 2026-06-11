# Lab 04: Dockerストレージの種類とライフサイクルを比較する

## 1. 問題名

**Named Volume、Bind Mount、tmpfs、コンテナの書き込み可能レイヤーの違いを観察せよ**

---

## 2. 問題詳細

Dockerコンテナ内で作成したファイルは、保存場所によってライフサイクルが異なります。

今回は、以下の4種類の保存場所を用意してください。

| 保存場所            | 用途                    |
| --------------- | --------------------- |
| コンテナの書き込み可能レイヤー | コンテナ固有の一時データ          |
| Named Volume    | Dockerが管理する永続データ      |
| Bind Mount      | ホストPC上のディレクトリと共有するデータ |
| tmpfs           | メモリ上だけに保持する一時データ      |

さらに、同じNamed Volumeを2つのコンテナで共有してください。

```text
ホストPC
│
├── host-data/
│      ↑
│      │ Bind Mount
│      ↓
│
├── writerコンテナ
│   ├── /container-data   コンテナ固有領域
│   ├── /volume-data      Named Volume
│   ├── /bind-data        Bind Mount
│   ├── /config           読み取り専用Bind Mount
│   └── /tmp-data         tmpfs
│
└── readerコンテナ
    └── /shared-data      writerと同じNamed Volume
```

`writer` コンテナでは各領域へファイルを書き込みます。

`reader` コンテナでは、`writer` がNamed Volumeへ保存したファイルを読み取れることを確認します。

その後、コンテナの再起動、再作成、Volume削除を行い、どのファイルが残るか観察してください。

---

## 3. 学習目的

この課題では、以下の内容を学習します。

* コンテナのファイルシステムがコンテナ削除時に失われることを確認する
* Named Volumeによるデータ永続化を確認する
* Bind MountによるホストPCとのファイル共有を確認する
* 読み取り専用Bind Mountを設定する
* tmpfsに保存したデータが永続化されないことを確認する
* 1つのNamed Volumeを複数コンテナから共有する
* `docker volume inspect` と `docker inspect` で内部構造を観察する
* ECSやKubernetesにおけるストレージ設計の前提を理解する

---

## 4. 作成する構成

以下の2つのコンテナを起動してください。

| サービス     | 役割                          |
| -------- | --------------------------- |
| `writer` | 各ストレージへファイルを書き込む            |
| `reader` | Named Volumeに保存されたファイルを読み取る |

両方のコンテナには、Alpine Linuxを使用してください。

```text
alpine:3.22
```

---

## 5. ディレクトリ構成

以下の構成を作成してください。

```text
docker-usecase-labs/
└── lab-04-docker-storage/
    ├── docker-compose.yml
    ├── host-data/
    └── config/
        └── app.conf
```

ディレクトリとファイルを作成します。

```bash
cd docker-usecase-labs

mkdir -p lab-04-docker-storage/host-data
mkdir -p lab-04-docker-storage/config

cd lab-04-docker-storage

echo "APP_MODE=production" > config/app.conf
touch docker-compose.yml
```

---

## 6. `docker-compose.yml` を実装する

以下の要件を満たす `docker-compose.yml` を自分で作成してください。

---

### `writer` サービス

| 設定                | 値                           |
| ----------------- | --------------------------- |
| サービス名             | `writer`                    |
| イメージ              | `alpine:3.22`               |
| 起動コマンド            | `sleep infinity`            |
| Named Volume      | `storage-data:/volume-data` |
| 書き込み可能なBind Mount | `./host-data:/bind-data`    |
| 読み取り専用Bind Mount  | `./config:/config:ro`       |
| tmpfs             | `/tmp-data`                 |

---

### `reader` サービス

| 設定           | 値                              |
| ------------ | ------------------------------ |
| サービス名        | `reader`                       |
| イメージ         | `alpine:3.22`                  |
| 起動コマンド       | `sleep infinity`               |
| Named Volume | `storage-data:/shared-data:ro` |

`reader` からNamed Volumeへ書き込めないようにしてください。

---

### Named Volume

以下のNamed Volumeを宣言してください。

```text
storage-data
```

---

## 7. `docker-compose.yml` の骨組み

以下を出発点にしてください。

```yaml
services:
  writer:
    image: alpine:3.22

    # TODO: コンテナを起動し続けるコマンドを設定する

    volumes:
      # TODO: storage-dataを /volume-data にマウントする

      # TODO: ./host-dataを /bind-data にマウントする

      # TODO: ./configを /config に読み取り専用でマウントする

    # TODO: /tmp-dataをtmpfsとしてマウントする

  reader:
    image: alpine:3.22

    # TODO: コンテナを起動し続けるコマンドを設定する

    volumes:
      # TODO: storage-dataを /shared-data に読み取り専用でマウントする

volumes:
  # TODO: storage-dataを宣言する
```

---

## 8. Composeファイルの構文を確認する

```bash
docker compose config
```

エラーが表示されないことを確認してください。

---

## 9. コンテナを起動する

```bash
docker compose up -d
```

状態を確認してください。

```bash
docker compose ps
```

`writer` と `reader` が起動していれば成功です。

---

## 10. マウント情報を確認する

`writer` コンテナの詳細を確認してください。

```bash
docker inspect "$(docker compose ps -q writer)"
```

出力が多いため、マウント情報だけを確認する場合は以下を実行してください。

```bash
docker inspect "$(docker compose ps -q writer)" \
  --format '{{json .Mounts}}'
```

整形して表示する場合は、Pythonを使用できます。

```bash
docker inspect "$(docker compose ps -q writer)" \
  --format '{{json .Mounts}}' \
  | python -m json.tool
```

以下のマウントが存在することを確認してください。

| Type     | Destination    |
| -------- | -------------- |
| `volume` | `/volume-data` |
| `bind`   | `/bind-data`   |
| `bind`   | `/config`      |
| `tmpfs`  | `/tmp-data`    |

環境によっては、tmpfsが `.Mounts` とは別の項目に表示される場合があります。

tmpfsの設定を個別に確認する場合は、以下を実行してください。

```bash
docker inspect "$(docker compose ps -q writer)" \
  --format '{{json .HostConfig.Tmpfs}}'
```

---

## 11. Named Volumeを確認する

Volumeの一覧を確認してください。

```bash
docker volume ls
```

今回作成したVolumeの名前を確認します。

```bash
docker volume ls | grep storage
```

Composeでは、実際のVolume名にプロジェクト名が付与されます。

例:

```text
lab-04-docker-storage_storage-data
```

詳細を確認してください。

```bash
docker volume inspect lab-04-docker-storage_storage-data
```

実際のVolume名が異なる場合は、表示された名前を使用してください。

---

## 12. 各領域へファイルを書き込む

`writer` コンテナ内でシェルを起動します。

```bash
docker compose exec writer sh
```

コンテナ内で以下を実行してください。

```sh
echo "container-layer" > /container-data.txt
echo "named-volume" > /volume-data/volume.txt
echo "bind-mount" > /bind-data/bind.txt
echo "tmpfs" > /tmp-data/tmpfs.txt
```

ファイルが存在することを確認します。

```sh
cat /container-data.txt
cat /volume-data/volume.txt
cat /bind-data/bind.txt
cat /tmp-data/tmpfs.txt
```

---

## 13. 読み取り専用Bind Mountを確認する

`writer` コンテナ内で以下を実行してください。

```sh
cat /config/app.conf
```

想定される結果:

```text
APP_MODE=production
```

次に、設定ファイルを変更してください。

```sh
echo "APP_MODE=development" > /config/app.conf
```

書き込みに失敗すれば成功です。

想定されるエラー:

```text
Read-only file system
```

コンテナ内のシェルを終了します。

```sh
exit
```

---

## 14. Bind MountをホストPC側から確認する

ホストPC上で以下を実行してください。

```bash
cat host-data/bind.txt
```

想定される結果:

```text
bind-mount
```

`writer` コンテナ内で作成したファイルが、ホストPC上にも存在します。

次に、ホストPC上でファイルの内容を変更してください。

```bash
echo "updated-from-host" > host-data/bind.txt
```

コンテナ内から確認します。

```bash
docker compose exec writer cat /bind-data/bind.txt
```

想定される結果:

```text
updated-from-host
```

Bind Mountでは、ホストPCとコンテナが同じファイルを参照しています。

---

## 15. Named Volumeを複数コンテナで共有する

`writer` コンテナで作成したファイルを、`reader` コンテナから読み取ってください。

```bash
docker compose exec reader cat /shared-data/volume.txt
```

想定される結果:

```text
named-volume
```

次に、`reader` コンテナから書き込みを試してください。

```bash
docker compose exec reader sh -c \
  'echo "updated-from-reader" > /shared-data/volume.txt'
```

書き込みに失敗すれば成功です。

`reader` では、Named Volumeを読み取り専用でマウントしています。

---

## 16. コンテナを再起動する

以下を実行してください。

```bash
docker compose restart writer
```

それぞれのファイルを確認します。

```bash
docker compose exec writer cat /container-data.txt
docker compose exec writer cat /volume-data/volume.txt
docker compose exec writer cat /bind-data/bind.txt
docker compose exec writer cat /tmp-data/tmpfs.txt
```

結果を記録してください。

### 予想する

コマンドを実行する前に、各ファイルが残るか予想してください。

| 保存場所            | 再起動後に残るか |
| --------------- | -------- |
| コンテナの書き込み可能レイヤー | 予想を書く    |
| Named Volume    | 予想を書く    |
| Bind Mount      | 予想を書く    |
| tmpfs           | 予想を書く    |

---

## 17. コンテナを削除して再作成する

以下を実行してください。

```bash
docker compose down
docker compose up -d
```

再び、それぞれのファイルを確認します。

```bash
docker compose exec writer sh -c \
  'test -f /container-data.txt && cat /container-data.txt || echo "NOT FOUND"'

docker compose exec writer sh -c \
  'test -f /volume-data/volume.txt && cat /volume-data/volume.txt || echo "NOT FOUND"'

docker compose exec writer sh -c \
  'test -f /bind-data/bind.txt && cat /bind-data/bind.txt || echo "NOT FOUND"'

docker compose exec writer sh -c \
  'test -f /tmp-data/tmpfs.txt && cat /tmp-data/tmpfs.txt || echo "NOT FOUND"'
```

結果を記録してください。

### 予想する

コマンドを実行する前に、各ファイルが残るか予想してください。

| 保存場所            | コンテナ再作成後に残るか |
| --------------- | ------------ |
| コンテナの書き込み可能レイヤー | 予想を書く        |
| Named Volume    | 予想を書く        |
| Bind Mount      | 予想を書く        |
| tmpfs           | 予想を書く        |

---

## 18. Volumeも削除して再作成する

以下を実行してください。

```bash
docker compose down -v
docker compose up -d
```

各ファイルを確認します。

```bash
docker compose exec writer sh -c \
  'test -f /container-data.txt && cat /container-data.txt || echo "NOT FOUND"'

docker compose exec writer sh -c \
  'test -f /volume-data/volume.txt && cat /volume-data/volume.txt || echo "NOT FOUND"'

docker compose exec writer sh -c \
  'test -f /bind-data/bind.txt && cat /bind-data/bind.txt || echo "NOT FOUND"'

docker compose exec writer sh -c \
  'test -f /tmp-data/tmpfs.txt && cat /tmp-data/tmpfs.txt || echo "NOT FOUND"'
```

結果を記録してください。

### 予想する

コマンドを実行する前に、各ファイルが残るか予想してください。

| 保存場所            | Volume削除後に残るか |
| --------------- | ------------- |
| コンテナの書き込み可能レイヤー | 予想を書く         |
| Named Volume    | 予想を書く         |
| Bind Mount      | 予想を書く         |
| tmpfs           | 予想を書く         |

---

## 19. 期待される結果

観察結果は、以下のようになるはずです。

| 保存場所            | `restart` | `down` → `up` | `down -v` → `up` |
| --------------- | --------- | ------------- | ---------------- |
| コンテナの書き込み可能レイヤー | 残る        | 消える           | 消える              |
| Named Volume    | 残る        | 残る            | 消える              |
| Bind Mount      | 残る        | 残る            | 残る               |
| tmpfs           | 消える       | 消える           | 消える              |

---

## 20. 結果の理由

### コンテナの書き込み可能レイヤー

コンテナ自身に紐づいている領域です。

```text
コンテナを再起動する
    ↓
同じコンテナなので残る

コンテナを削除する
    ↓
コンテナ固有領域も消える
```

---

### Named Volume

Dockerが管理する永続領域です。

```text
コンテナを削除する
    ↓
Volumeは独立して残る

docker compose down -v
    ↓
Volumeも削除される
```

---

### Bind Mount

ホストPC上のファイルやディレクトリを、コンテナから参照しています。

```text
コンテナを削除する
    ↓
ホストPC上のファイルは残る
```

---

### tmpfs

メモリ上の一時領域です。

```text
コンテナを停止する
    ↓
データは消える
```

パスワード、トークン、一時ファイルなど、ディスクへ永続保存したくないデータを扱う用途があります。

---

## 21. ストレージを使い分ける

| 状況                    | 選択肢              |
| --------------------- | ---------------- |
| DBなど、コンテナ削除後も保持するデータ  | Named Volume     |
| 開発中のソースコードをホストPCと共有する | Bind Mount       |
| 設定ファイルをコンテナから読み取るだけ   | 読み取り専用Bind Mount |
| コンテナ停止時に消えてよい一時データ    | tmpfs            |
| コンテナ固有の一時ファイル         | コンテナの書き込み可能レイヤー  |

---

## 22. 考察課題

以下の問いに、自分の言葉で回答してください。

### 問1

`docker compose restart writer` では `/container-data.txt` が残るのに、`docker compose down` 後には消えるのはなぜか。

### 問2

Named VolumeとBind Mountは、どちらもコンテナ削除後にデータが残る。両者の違いは何か。

### 問3

なぜ本番環境のアプリケーションコンテナから、ホストPC上の任意のディレクトリをBind Mountする構成には注意が必要なのか。

### 問4

設定ファイルを読み取り専用でマウントする利点は何か。

### 問5

tmpfsへ保存するのが適切なデータと、不適切なデータを1つずつ挙げよ。

### 問6

複数コンテナで同じNamed Volumeを共有するとき、同時書き込みによって問題が発生する可能性はあるか。

---

## 23. 発展課題

余裕がある場合のみ取り組んでください。

### 発展課題1: 匿名Volumeを作る

以下のコマンドを実行してください。

```bash
docker run --rm \
  -v /anonymous-data \
  alpine:3.22 \
  sh -c 'echo "anonymous-volume" > /anonymous-data/test.txt'
```

Volume一覧を確認します。

```bash
docker volume ls
```

自動生成された名前のVolumeが作成されていることを確認してください。

Named Volumeとの違いを考察してください。

---

### 発展課題2: Bind Mount元のファイルを削除する

ホストPC側で以下を実行してください。

```bash
rm host-data/bind.txt
```

コンテナ側から確認します。

```bash
docker compose exec writer ls -la /bind-data
```

ファイルが消えていることを確認してください。

---

### 発展課題3: tmpfsのサイズを制限する

`writer` のtmpfsへサイズ制限を追加してください。

```yaml
tmpfs:
  - /tmp-data:size=10m
```

再作成します。

```bash
docker compose down
docker compose up -d
```

設定を確認します。

```bash
docker inspect "$(docker compose ps -q writer)" \
  --format '{{json .HostConfig.Tmpfs}}'
```

---

## 24. 完了条件

以下をすべて満たしたら完了です。

* `writer` と `reader` の2コンテナを起動できる
* Named Volumeを作成できる
* Named Volumeを2コンテナで共有できる
* `reader` ではNamed Volumeへ書き込めない
* Bind MountでホストPCとコンテナのファイルを共有できる
* 読み取り専用Bind Mountへ書き込めない
* tmpfsへファイルを書き込める
* tmpfsのファイルがコンテナ再起動後に消える
* コンテナの書き込み可能レイヤーがコンテナ削除後に消える
* Named Volumeが `docker compose down` 後も残る
* Named Volumeが `docker compose down -v` 後に消える
* Bind Mountのファイルがコンテナ削除後もホストPC上に残る
* `docker volume inspect` でVolumeの情報を確認できる
* `docker inspect` で各マウントの種類を確認できる

---

## 25. ECS・Kubernetesとの接続

| Docker            | ECS・AWSで考える対象 | Kubernetesで近い概念                        |
| ----------------- | ------------- | -------------------------------------- |
| コンテナの書き込み可能レイヤー   | Task固有の一時領域   | Pod・コンテナ固有の一時領域                        |
| Named Volume      | 永続ストレージの設計    | PersistentVolume、PersistentVolumeClaim |
| Bind Mount        | ホスト依存のマウント    | `hostPath` Volume                      |
| tmpfs             | メモリ上の一時領域     | `emptyDir.medium: Memory`              |
| 読み取り専用マウント        | 設定・機密情報の保護    | Read-only Volume、ConfigMap、Secret      |
| 複数コンテナで共有するVolume | 共有ストレージ       | Volumeの共有、アクセスモード                      |

Docker、ECS、Kubernetesでは具体的な設定方法が異なります。

ただし、最初に考えるべき問いは共通しています。

```text
そのデータは一時的か、永続的か
誰が読み取るのか
誰が書き込むのか
複数の実行単位で共有するのか
ホスト環境へ依存してよいのか
```

---

## 26. 提出する内容

課題が完了したら、以下を提出してください。

```text
docker-compose.yml
```

あわせて、以下のコマンドの実行結果も提出してください。

```bash
docker compose ps
```

```bash
docker inspect "$(docker compose ps -q writer)" \
  --format '{{json .Mounts}}'
```

```bash
docker inspect "$(docker compose ps -q writer)" \
  --format '{{json .HostConfig.Tmpfs}}'
```

最後に、以下の表へ実際の観察結果を記入してください。

| 保存場所            | `restart` | `down` → `up` | `down -v` → `up` |
| --------------- | --------- | ------------- | ---------------- |
| コンテナの書き込み可能レイヤー |    残る       |     消える           |          消える         |
| Named Volume    |    残る       |     残る          |           消える        |
| Bind Mount      |    残る       |      残る         |        残る          |
| tmpfs           |    消える       |       消える         |    消える               |
