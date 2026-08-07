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
from vibe_coding_courses import register_vibe_coding_course_routes
from vibe_coding_kids import register_vibe_coding_kids_routes
from vibe_coding_industry import register_vibe_coding_industry_routes
from solo_ceo import register_solo_ceo_routes

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
FROM_EMAIL = "info@jgaia.org"
NOTIFY_EMAIL = "takano.hidetaka@gmail.com"

app = Flask(__name__, static_folder="static", static_url_path="/static")

register_vibe_coding_routes(app)
register_vibe_coding_course_routes(app)
register_vibe_coding_kids_routes(app)
register_vibe_coding_industry_routes(app)
register_solo_ceo_routes(app)


@app.route("/")
def index():
    return render_template("index.html")


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

        # スパム判定。⛔ 弾いたことをボットに教えないため、画面は成功と同じにする。
        import antispam
        spam = antispam.check(request, {
            'name': name, 'email': email, 'message': message,
            antispam.HONEYPOT_FIELD: request.form.get(antispam.HONEYPOT_FIELD),
            'ts': request.form.get('ts'),
            'h-captcha-response': request.form.get('h-captcha-response'),
        })
        if spam:
            app.logger.info('[contact] スパムとして遮断: %s', spam)
            return render_template("contact.html", sent=True)

        # ⛔ メールより先に保存する。メール送信が唯一の記録手段だと、
        #    枠切れ・障害のときに問い合わせが痕跡ごと消える。
        if name and email:
            try:
                from inquiry_store import save_inquiry
                save_inquiry('contact', {'name': name, 'email': email,
                                         'company': company, 'message': message})
            except Exception:
                app.logger.exception('[contact] 保存に失敗しました')

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

                # 宛先は mail_targets で1か所に決める（協会の窓口＋代表者Cc）
                from mail_targets import notify_payload
                resend.Emails.send(notify_payload(
                    f"【JGAIA】お問い合わせ: {name}様",
                    reply_to=email,
                    html=('<html><head><meta charset="utf-8"></head><body>'
                          f"{body_html}</body></html>"),
                ))

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


@app.route("/gpu-guide")
def gpu_guide():
    return render_template("gpu_guide.html")


@app.route("/tokutei")
def tokutei():
    return render_template("tokutei.html")


@app.route("/sitemap.xml")
def sitemap():
    return send_file("static/sitemap.xml", mimetype="application/xml")


@app.route("/robots.txt")
def robots():
    return send_file("static/robots.txt", mimetype="text/plain")


@app.route("/llms.txt")
def llms_txt():
    """AIの回答に引用されるための要約ファイル（llms.txt）。

    検索の入口がAIの回答に移り、ユーザーはAIが挙げた名前から流入する。
    HTMLを読ませるより、何の団体で・どの講座が・いくらで・何時間かを
    機械が読める1枚にまとめたほうが正確に引用される。
    金額・時間は各ページの掲載値と一致させること（食い違うと誤案内になる）。
    """
    return send_file("static/llms.txt", mimetype="text/plain")


@app.context_processor
def inject_antispam():
    """全テンプレートにスパム対策の材料を渡す。

    ⛔ ここを外すとフォームの隠しフィールドが空になり、
       サーバー側の署名チェックで**正規の送信が全部落ちる**。
    """
    import antispam
    return {'form_ts': antispam.issue_token(),
            'hcaptcha_sitekey': antispam.sitekey(),
            'honeypot_field': antispam.HONEYPOT_FIELD}


@app.route("/healthz")
def healthz():
    """稼働確認に加えて、申込を受け取れる状態かどうかを返す。

    ページが200で開いてもメールの設定が無ければ申込は届かない。
    それを外から検知できるようにする（SoloOSの申込導線カナリアが毎時見る）。
    秘密は出さない。設定の有無と受付件数だけ。
    """
    from flask import jsonify
    from inquiry_store import count_inquiries
    # サイトから送れるのはHTTPのAPI（Resend）だけ。
    # ⛔ SMTPは書かない。Railwayが外向きSMTPを遮断しており必ず失敗する
    #    （2026-08-06実測）。送れなかったぶんは SoloOS が予備で拾う。
    mailer_kind = "resend" if os.environ.get("RESEND_API_KEY") else "missing"
    mailer = mailer_kind != "missing"
    try:
        saved = count_inquiries()
    except Exception:
        saved = None
    # 鍵の有無だけでは足りない。設定済みでも日次上限などで実際には
    # 送れていないことがある（2026-08-04に発生）。直近の失敗も返す。
    try:
        from solo_ceo import LAST_MAIL_ERROR
        mail_error = LAST_MAIL_ERROR.get("kind")
        mail_error_at = LAST_MAIL_ERROR.get("at")
    except Exception:
        mail_error = mail_error_at = None
    return jsonify({
        "status": "ok",
        "mailer": "configured" if mailer else "missing",
        "mailer_kind": mailer_kind,
        "mail_last_error": mail_error,
        "mail_last_error_at": mail_error_at,
        "inquiries_saved": saved,
        # スパムで遮断した累計。0のまま増えないなら対策が効いていない疑い。
        "spam_blocked": (lambda: __import__('antispam').counts())(),
        "captcha": "on" if os.environ.get("HCAPTCHA_SECRET") else "off",
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("FLASK_DEBUG") == "1")
