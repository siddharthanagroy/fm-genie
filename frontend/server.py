import os
import requests
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__)

API_BASE = "https://fm-genie-ffp75lvgda-el.a.run.app"

@app.route("/")
def index():
    return send_from_directory(".", "index.html")

@app.route("/api/<path:path>", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
def proxy(path):
    url = f"{API_BASE}/{path}"

    try:
        response = requests.request(
            method=request.method,
            url=url,
            headers={
                "Content-Type": request.headers.get("Content-Type", "application/json")
            },
            data=request.get_data(),
            timeout=120,
        )

        return (
            response.content,
            response.status_code,
            {"Content-Type": response.headers.get("Content-Type", "application/json")}
        )

    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 502


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
