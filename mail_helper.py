# -*- coding: utf-8 -*-
"""問い合わせ通知メールの送信口。

なぜ自前のSMTPを使うか（2026-08-04）:
    外部の送信APIに依存していたところ、その無料枠（100通/日）を使い切って
    送信が全部落ちた。鍵は設定済みなので設定画面上は正常に見え、
    実際には1通も出ていないという状態になった。
    jgaia.org はさくらのメールサーバーを契約しており、自ドメインのMXでもある。
    送信もそこから出すのが素直で、通数の上限に振り回されない。

方針:
    1. SMTP（さくら）が設定されていればそれを使う ← 既定
    2. 設定が無い場合だけ、旧経路（Resend）にフォールバックする
    3. どちらも無い／失敗したときは、黙って成功にせず必ず呼び出し元へ知らせる
       （呼び出し元は保存済みの申込を残し、画面にも正直に出す）
"""
import os
import smtplib
from email.message import EmailMessage

FROM_EMAIL = "info@jgaia.org"


def smtp_configured():
    return bool(os.environ.get("SMTP_HOST") and os.environ.get("SMTP_USER")
                and os.environ.get("SMTP_PASSWORD"))


def _clean(s):
    """環境変数に紛れ込むBOM・前後の空白を落とす。

    設定の入れ方によっては先頭にBOMが入り、画面では見えないまま
    認証だけが通らなくなる（2026-08-04に合言葉で実際に踏んだ）。
    """
    return (s or "").strip().lstrip("﻿").strip()


def send_via_smtp(to, subject, body, reply_to=None):
    """さくらのSMTPで送る。失敗したら例外を上げる（握り潰さない）。"""
    host = _clean(os.environ.get("SMTP_HOST"))
    port = int(_clean(os.environ.get("SMTP_PORT")) or 587)
    user = _clean(os.environ.get("SMTP_USER"))
    password = _clean(os.environ.get("SMTP_PASSWORD"))
    sender = _clean(os.environ.get("SMTP_FROM")) or FROM_EMAIL

    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = to
    msg["Subject"] = subject
    if reply_to:
        msg["Reply-To"] = reply_to
    msg.set_content(body, charset="utf-8")

    if port == 465:
        with smtplib.SMTP_SSL(host, port, timeout=20) as s:
            s.login(user, password)
            s.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=20) as s:
            s.ehlo()
            s.starttls()
            s.ehlo()
            s.login(user, password)
            s.send_message(msg)
