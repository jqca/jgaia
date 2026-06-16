"""JGAIA コーポレートサイト + バイブコーディング講座

提供ルート:
- /                    トップページ
- /vibe-coding         バイブコーディング講座LP（1ページ完結）
- /api/inquiry         問い合わせ受信（SendGrid）
- /healthz             ヘルスチェック
"""
import os

from flask import Flask, send_file

from vibe_coding import register_vibe_coding_routes

app = Flask(__name__, static_folder="static", static_url_path="/static")

register_vibe_coding_routes(app)


@app.route("/")
def index():
    return send_file("index.html")


@app.route("/healthz")
def healthz():
    return "ok"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("FLASK_DEBUG") == "1")
