"""JGAIA コーポレートサイト + バイブコーディング講座

提供ルート:
- /                              トップページ
- /vibe-coding                   講座概要（汎用5コース GA/GB/GC/GD/GE）
- /vibe-coding/course-ga..ge     各コース詳細＋申込フォーム
- /vibe-coding/kids              子ども向けコース（GK1/GK2/GK3）
- /vibe-coding/manufacturing     製造業特化（GM-A/B/C）
- /vibe-coding/healthcare        医療・ヘルスケア特化（GH-A/B/C）
- /vibe-coding/finance           金融特化（GF-A/B/C）
- /vibe-coding/logistics         物流特化（GL-A/B/C）
- /vibe-coding/construction      建設特化（GN-A/B/C）
- /api/course-inquiry            コース問い合わせ受信（SendGrid）
- /api/kids-inquiry              子ども向け問い合わせ受信
- /api/industry-inquiry          業種特化型問い合わせ受信
- /healthz                       ヘルスチェック
"""
import os

from flask import Flask, send_file, send_from_directory

from vibe_coding import register_vibe_coding_routes
from vibe_coding_courses import register_vibe_coding_course_routes
from vibe_coding_kids import register_vibe_coding_kids_routes
from vibe_coding_industry import register_vibe_coding_industry_routes

app = Flask(__name__, static_folder="static", static_url_path="/static")

register_vibe_coding_routes(app)
register_vibe_coding_course_routes(app)
register_vibe_coding_kids_routes(app)
register_vibe_coding_industry_routes(app)


@app.route("/")
def index():
    return send_file("index.html")


@app.route("/healthz")
def healthz():
    return "ok"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("FLASK_DEBUG") == "1")
