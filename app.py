"""JGAIA コーポレートサイト + バイブコーディング講座

提供ルート:
- /                    トップページ
- /company-info        協会情報
- /team-members        協会メンバー紹介
- /course              資格・認定講座
- /member              協会員一覧
- /join-us             協会員募集
- /contact             お問い合わせ
- /tokutei             特定商取引法に基づく表記
- /vibe-coding         バイブコーディング講座LP（1ページ完結）
- /api/inquiry         問い合わせ受信（SendGrid）
- /healthz             ヘルスチェック
"""
import os

from flask import Flask, send_file, render_template, request

from vibe_coding import register_vibe_coding_routes

app = Flask(__name__, static_folder="static", static_url_path="/static")

register_vibe_coding_routes(app)


@app.route("/")
def index():
    return send_file("index.html")


@app.route("/company-info")
def company_info():
    return render_template("company_info.html")


@app.route("/team-members")
def team_members():
    return render_template("team_members.html")


@app.route("/course")
def course():
    return render_template("course.html")


@app.route("/member")
def member():
    return render_template("member.html")


@app.route("/join-us")
def join_us():
    return render_template("join_us.html")


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        return render_template("contact.html", sent=True)
    return render_template("contact.html", sent=False)


@app.route("/tokutei")
def tokutei():
    return render_template("tokutei.html")


@app.route("/healthz")
def healthz():
    return "ok"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("FLASK_DEBUG") == "1")
