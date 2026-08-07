# -*- coding: utf-8 -*-
"""問い合わせ通知の宛先を1か所で決める。

なぜ必要か（2026-08-06 外注先の指摘で判明）:
    フォームが6つあり、通知先がバラバラだった。
      /contact /api/inquiry /api/course-inquiry /api/industry-inquiry
      /api/solo-inquiry … 代表者の個人Gmail
      /api/kids-inquiry … info@jgaia.org
    協会の窓口（info@jgaia.org）を見ていた外注先には、申込が
    「届いていない」ように見えていた。実際はほぼ全部が個人Gmailへ
    飛んでいた。

方針:
    ・宛先は **info@jgaia.org**（協会の窓口）。担当者が代わっても届く
    ・控えとして代表者にもCcする。⛔別々に2通送らない
      （Resendの無料枠は1日100通。宛先を増やすほど枠を食う）
    ・環境変数で変えられる。コードを触らずに宛先を移せるようにする

⛔ 各ファイルで宛先を直書きしないこと。増えるたびに散らばり、
   「どこに届くのか」が誰にも分からなくなる。
"""
import os

# 差出人。⛔ドメイン認証済みのアドレス以外にしないこと（送信が弾かれる）
FROM_EMAIL = os.environ.get('MAIL_FROM', 'info@jgaia.org')

# 届け先（協会の窓口）
NOTIFY_TO = [a.strip() for a in
             os.environ.get('NOTIFY_TO', 'info@jgaia.org').split(',') if a.strip()]

# 控え。空にすれば送らない
NOTIFY_CC = [a.strip() for a in
             os.environ.get('NOTIFY_CC', 'takano.hidetaka@gmail.com').split(',')
             if a.strip()]


def notify_payload(subject, reply_to=None, **body):
    """通知メール1通分の中身。ccは同じ1通に載せる（枠を余計に使わない）。

    body には text= か html= を渡す（フォームによって作りが違うため）。
    """
    p = {'from': f'JGAIA <{FROM_EMAIL}>', 'to': list(NOTIFY_TO), 'subject': subject}
    p.update(body)
    if NOTIFY_CC:
        p['cc'] = list(NOTIFY_CC)
    if reply_to:
        # 受け取った側がそのまま申込者へ返信できるようにする
        p['reply_to'] = reply_to
    return p
