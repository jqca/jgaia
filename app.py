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
- /api/inquiry         問い合わせ受信（Resend）
- /healthz             ヘルスチェック
"""
import os

from flask import Flask, send_file, render_template, request

from vibe_coding import register_vibe_coding_routes

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
FROM_EMAIL = "info@jgaia.org"
NOTIFY_EMAIL = "takano.hidetaka@gmail.com"

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
        name = (request.form.get("name") or "").strip()
        email = (request.form.get("email") or "").strip()
        company = (request.form.get("company") or "").strip()
        message = (request.form.get("message") or "").strip()

        if name and email and RESEND_API_KEY:
            try:
                import resend
                resend.api_key = RESEND_API_KEY

                body_lines = [
                    f"氏名: {name}",
                    f"メール: {email}",
                ]
                if company:
                    body_lines.append(f"会社名: {company}")
                if message:
                    body_lines.append(f"お問い合わせ内容:\n{message}")
                body_html = "<br>".join(
                    line.replace("\n", "<br>") for line in body_lines
                )

                resend.Emails.send({
                    "from": f"JGAIA <{FROM_EMAIL}>",
                    "to": [NOTIFY_EMAIL],
                    "subject": f"【JGAIA】お問い合わせ: {name}様",
                    "html": (
                        '<html><head><meta charset="utf-8"></head><body>'
                        f"{body_html}</body></html>"
                    ),
                })

                resend.Emails.send({
                    "from": f"JGAIA <{FROM_EMAIL}>",
                    "to": [email],
                    "subject": "【JGAIA】お問い合わせありがとうございます",
                    "html": (
                        '<html><head><meta charset="utf-8"></head><body>'
                        f"<p>{name} 様</p>"
                        "<p>一般社団法人日本生成AI協会（JGAIA）へお問い合わせいただき"
                        "ありがとうございます。</p>"
                        "<p>内容を確認の上、担当者より2営業日以内にご連絡いたします。</p>"
                        "<hr>"
                        "<p>一般社団法人日本生成AI協会（JGAIA）<br>"
                        "〒104-0061 東京都中央区銀座1-22-11 銀座大竹ビジデンス2階<br>"
                        "info@jgaia.org<br>"
                        "https://www.jgaia.org/</p>"
                        "</body></html>"
                    ),
                })
            except Exception:
                pass

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
