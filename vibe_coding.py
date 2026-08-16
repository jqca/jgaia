"""JGAIA バイブコーディング講座 — 1ページ完結型LP

4コース体系:
  A: AIアプリ開発 入門（3h / ¥19,800）
  B: AIアプリ開発 実践（6h / ¥49,800）
  C: AIセキュリティ＆ガバナンス（6h / ¥49,800）
  D: AIエンジニアリング マスター（3日間 / ¥128,000）
  + 法人カスタマイズ研修

問い合わせAPI:
  POST /api/inquiry — Resend経由でinfo@jgaia.orgへ通知＋自動返信
"""
import json
import os

from flask import render_template, request


RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
FROM_EMAIL = "info@jgaia.org"
NOTIFY_EMAIL = "takano.hidetaka@gmail.com"


def register_vibe_coding_routes(app):
    @app.route("/vibe-coding")
    def vibe_coding():
        return render_template("vibe_coding_lp.html")

    @app.route("/api/inquiry", methods=["POST"])
    def inquiry():
        try:
            data = request.get_json(force=True)
        except Exception:
            return {"error": "invalid JSON"}, 400

        name = (data.get("name") or "").strip()
        email = (data.get("email") or "").strip()
        company = (data.get("company") or "").strip()
        course = (data.get("course") or "").strip()
        message = (data.get("message") or "").strip()

        # スパム判定。⛔ 弾いたことをボットに教えない（成功と同じ形で返す）。
        import antispam
        spam = antispam.check(request, data)
        if spam:
            return {"ok": True}

        # ⛔ メールより先に保存する（枠切れ・障害で問い合わせを失わない）
        if name and email:
            try:
                from inquiry_store import save_inquiry
                save_inquiry('vibe-coding', {'name': name, 'email': email,
                                             'company': company, 'course': course,
                                             'message': message})
            except Exception:
                app.logger.exception('[inquiry] 保存に失敗しました')

        if not name or not email:
            return {"error": "name and email are required"}, 400

        if not RESEND_API_KEY:
            return {"ok": True, "note": "Resend未設定のためメール送信をスキップしました"}

        try:
            import resend
            resend.api_key = RESEND_API_KEY

            body_lines = [
                f"氏名: {name}",
                f"メール: {email}",
                f"会社名: {company}" if company else None,
                f"希望コース: {course}" if course else None,
                f"お問い合わせ内容:\n{message}" if message else None,
            ]
            body_text = "\n".join(line for line in body_lines if line)

            from mail_targets import notify_payload
            resend.Emails.send(notify_payload(
                f"【JGAIA講座】お問い合わせ: {name}様",
                reply_to=email, text=body_text))

            resend.Emails.send({
                "from": FROM_EMAIL,
                "to": [email],
                "subject": "【JGAIA】お問い合わせありがとうございます",
                "text": (
                    f"{name} 様\n\n"
                    "一般社団法人日本生成AI協会（JGAIA）のバイブコーディング講座に"
                    "ご関心をお寄せいただきありがとうございます。\n\n"
                    "担当者より2営業日以内にご連絡いたします。\n\n"
                    "---\n"
                    "一般社団法人日本生成AI協会（JGAIA）\n"
                    "〒104-0061 東京都中央区銀座1-22-11 銀座大竹ビジデンス2階\n"
                    "info@jgaia.org\n"
                    "https://www.jgaia.org/"
                ),
            })

            return {"ok": True}
        except Exception as e:
            return {"error": str(e)}, 500


# ⛔ ここにあった LP_HTML（557行）は 2026-08-15 に削除した。
#    どこからも参照されておらず（/vibe-coding は templates/vibe_coding_lp.html を
#    描画する）、中身は現存しない講座（A/B/C/D・¥19,800）と、廃止した
#    事業外スキルアップ助成金の金額（実質¥24,800）だった。
#    ⛔ 死んだ画面のコードを残さないこと。検索に引っかかり、直すべき箇所と
#       区別が付かないうえ、いつか復活させる者が出る。履歴は git にある。
