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
from booking_routes import register_booking_routes

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
FROM_EMAIL = "info@jgaia.org"
NOTIFY_EMAIL = "takano.hidetaka@gmail.com"

app = Flask(__name__, static_folder="static", static_url_path="/static")

# Railway のプロキシ配下で動くので、外向きURL（url_for(_external=True)）の
# スキームを X-Forwarded-Proto から判定させる。
# ⛔ これを外すと講師にお送りするURLが http:// になる（2026-08-09 実測）。
#    リダイレクトはされるが、コピーして配るURLとしては使えない。
from werkzeug.middleware.proxy_fix import ProxyFix  # noqa: E402
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

# アイコン（Lucide）。テンプレートから {{ icon('clock', 16) }} で呼べるようにする。
# ⛔ |safe を書かせないこと＝書き忘れると <svg> がそのまま文字として出る。
#    Markup を返して、常にそのまま描かれるようにしておく。
import icons  # noqa: E402
from markupsafe import Markup  # noqa: E402
app.jinja_env.globals['icon'] = lambda *a, **k: Markup(icons.icon(*a, **k))

register_vibe_coding_routes(app)
register_vibe_coding_course_routes(app)
register_vibe_coding_kids_routes(app)
register_booking_routes(app)
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


@app.context_processor
def _subsidy_globals():
    """助成金の金額を、どのテンプレートからも1か所から引けるようにする。

    ⛔ 各テンプレートに金額を直書きしないこと（2026-08-15 実害）。廃止した
       事業外スキルアップ助成金の実質負担額が4ファイルに散っており、制度を
       切り替えてもそこだけ古いまま残っていた。テストは module 側しか
       見ておらず、テンプレートの直書きを1件も捕まえられなかった。
    """
    import booking
    s = booking.subsidy_for("GA")          # 個人向けの代表値
    # ⛔ 助成額を「代表値」で全講座に使い回さないこと（2026-08-15 実害）。
    #    GB を値上げした後も表の GB 行が GA の金額（¥49,800／実質¥15,846）の
    #    ままになっていた。講座ごとの値を引けるようにする。
    return {"prices": {c["code"]: c["price"] for c in booking.COURSES},
            "subsidy_of": {c["code"]: booking.subsidy_for(c["code"])
                           for c in booking.COURSES},
            # ⛔ 単位（/名）と「1研修あたり」を各画面に手打ちしないこと。
            #    出どころは booking.PRICE_UNIT / unit_price_note() の1か所
            "price_unit": booking.PRICE_UNIT,
            "price_suffix": booking.PRICE_SUFFIX,
            "unit_notes": {c["code"]: booking.unit_price_note(c["code"])
                           for c in booking.COURSES},
            "subsidy_net_typical": s["net"],
            "subsidy_grant_typical": s["grant"],
            "subsidy_cap_person": booking.SUBSIDY["cap_per_person"],
            "subsidy_cap_company": booking.SUBSIDY["cap_per_company"]}


@app.route("/subsidy")
def subsidy():
    """法人のお客様向け 助成金のご案内。

    ⛔ 金額・要件をこのページに直書きしないこと。判定と金額は
       booking.subsidy_for() の1か所から作る（制度が変わった日に、
       直し忘れた画面が古い金額を出し続ける＝法人はその額で申請して落ちる）。
    """
    import booking
    rows = []
    for c in booking.COURSES:
        s = booking.subsidy_for(c["code"])
        rows.append(dict(code=c["code"], name=c["name"], price=c["price"],
                         hours=s["hours"], grant=s["grant"], net=s["net"],
                         eligible=s["eligible"], reason=s["reason"],
                         # ⛔ 試験名を画面に手打ちしないこと（講座ごとに違う）
                         exam=(booking.exam_for(c["code"]) or {}).get("name", ""),
                         dx=booking.dx_skills(c["code"])))
    corp = booking.CORPORATE
    # ⛔ 「カード払いは助成の対象外」を、カードを提供していない日にも出さないこと。
    #    選べない支払方法の注意書きは読み手を迷わせる（2026-08-17）。
    #    ⛔ 渡し忘れるとJinjaが未定義を偽として扱い、Stripeを入れた日に
    #       「カードは対象外」の注意が消えたままになる＝必ず明示的に渡す。
    import payments as _pay
    return render_template(
        "subsidy.html", s=booking.subsidy_for("SP-A"), corp=corp,
        card_enabled=_pay.enabled(),
        q1=booking.corporate_quote(1, corp["included"])[0],
        q2=booking.corporate_quote(1, 20)[0],
        q3=booking.corporate_quote(3, corp["included"])[0],
        cap_person=booking.SUBSIDY["cap_per_person"],
        cap_company=booking.SUBSIDY["cap_per_company"],
        eligible=[r for r in rows if r["eligible"]],
        # ⛔ 「時間で外れたもの」だけを出す。子ども向けは受講者の立場の
        #    問題なので、時間の説明文に混ぜると誤解される
        not_eligible=[r for r in rows if not r["eligible"]
                      and r["code"] not in booking._SUBSIDY_NEVER])


@app.route("/tokutei")
def tokutei():
    # ⛔ 売主と返金の条件をテンプレートに直書きしないこと。講座の売主は
    #    ZebraQuantum で、条件は booking.py が唯一の出どころ（画面・メール・
    #    法定表示が別々の答えを出すのを防ぐ）
    import booking
    # ⛔ 価格帯も直書きしないこと（2026-08-17 に ¥228,000 が残っていた）。実価格から出す。
    _p = [c['price'] for c in booking.COURSES]
    price_range = '¥{:,}〜¥{:,}'.format(min(_p), max(_p))
    # ⛔ 決済手段を直書きしないこと（2026-08-17 実害）。カードの鍵が入っていないのに
    #    法定表示だけが「クレジットカード決済（VISA…）」と掲げていた＝提供していない
    #    支払方法を表示していた。実際の設定（payments.enabled）から出す。
    import payments
    return render_template("tokutei.html", seller=booking.SELLER,
                           cancel_policy=booking.CANCEL_POLICY,
                           extra_cost_note=booking.EXTRA_COST_NOTE,
                           price_range=price_range,
                           card_enabled=payments.enabled(),
                           delivery_note=booking.DELIVERY_NOTE)


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
