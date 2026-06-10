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
            "message": "Hello from Docker",
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
