# -*- coding: utf-8 -*-
"""カード決済（Stripe Checkout）。

なぜこの形か（2026-08-14 社長ご判断）:
    ・申込＝その場で決済にする。請求書払いは1件ごとに発行・入金確認・督促が
      発生し、全部が人手になる（当社の第一基準「人間が介在しないこと」に反する）
    ・法人は購買部が請求書でないと通らないので、請求書払いは併存させる

⛔ Stripe のライブラリを入れないこと。ここは form-encode した POST と
   HMAC-SHA256 の検証だけで足りる。依存を増やすと、バージョンが動いた日に
   本番が止まる（領収書アプリで httpx を固定していなくて実際に止まった）。

⛔ 加盟店は ZebraQuantum。教材もシステムも Zebra が開発・提供し、協会の看板で
   販売する商流なので、Zebra が受講契約の相手方になる。
   ⛔「協会が売主で、代金だけ Zebra が受け取る」形にしないこと。それは
   Stripe の禁止事項（第三者の代理での売上受取＝決済ファシリテーション）に
   正面から当たる。

⛔ 金額は必ず COURSES の price から作ること。画面から来た金額を信じない
   （利用者が書き換えられる）。

環境変数:
    STRIPE_SECRET_KEY       sk_live_... / sk_test_...（無ければ請求書払いのみ）
    STRIPE_WEBHOOK_SECRET   whsec_...（無ければ webhook を受け付けない）
"""
import hashlib
import hmac
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

API = 'https://api.stripe.com/v1'
# 署名の時刻ずれの許容。⛔ 大きくしないこと（再送攻撃の窓が広がる）
TOLERANCE_SEC = 300
# 決済画面を開いたまま放置されたときに、席を解放するまでの時間
SESSION_TTL_MIN = 60


def secret_key():
    return (os.environ.get('STRIPE_SECRET_KEY') or '').strip()


def webhook_secret():
    return (os.environ.get('STRIPE_WEBHOOK_SECRET') or '').strip()


def enabled():
    """カード決済が使えるか。

    ⛔ 鍵が無いときに落ちないこと。未設定なら請求書払いだけで今までどおり
       動く（＝鍵を入れた瞬間にカードが有効になる）。
    """
    return bool(secret_key())


def _post(path, fields):
    """Stripe API を叩く。戻り値: (dict, エラー文 or None)"""
    key = secret_key()
    if not key:
        return None, 'カード決済は未設定です'
    body = urllib.parse.urlencode(fields).encode('utf-8')
    req = urllib.request.Request(
        f'{API}{path}', data=body,
        headers={'Authorization': f'Bearer {key}',
                 'Content-Type': 'application/x-www-form-urlencoded',
                 'Stripe-Version': '2024-06-20'})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode('utf-8')), None
    except urllib.error.HTTPError as e:
        # ⛔ Stripe のエラー本文をそのまま利用者に見せないこと（鍵の一部や
        #    内部の事情が混ざる）。ログには残し、画面には短い日本語を返す
        try:
            detail = json.loads(e.read().decode('utf-8')).get('error', {})
        except Exception:
            detail = {}
        return None, (detail.get('message') or f'決済の準備に失敗しました（{e.code}）')
    except Exception as e:
        return None, f'決済の準備に失敗しました（{type(e).__name__}）'


def _flatten(prefix, value, out):
    """Stripe は入れ子を line_items[0][price_data][...] の形で受け取る。"""
    if isinstance(value, dict):
        for k, v in value.items():
            _flatten(f'{prefix}[{k}]', v, out)
    elif isinstance(value, list):
        for i, v in enumerate(value):
            _flatten(f'{prefix}[{i}]', v, out)
    else:
        out[prefix] = value
    return out


def create_checkout(course, people, email, booking_id, success_url, cancel_url,
                    day_label=''):
    """決済ページを1つ作る。戻り値: (URL, session_id, エラー文 or None)

    ⛔ 金額は course['price'] から作ること（画面の値を使わない）。
    ⛔ 円は「最小単位＝円」なので100倍しないこと。100倍すると請求が100倍になる。
    """
    price = int(course['price'])
    qty = max(1, int(people or 1))
    name = f"{course['code']} {course['name']}"
    if day_label:
        name += f'（{day_label}）'
    fields = {
        'mode': 'payment',
        'locale': 'ja',
        'success_url': success_url,
        'cancel_url': cancel_url,
        'client_reference_id': str(booking_id),
        'expires_at': int(time.time()) + SESSION_TTL_MIN * 60,
    }
    if email:
        fields['customer_email'] = email
    _flatten('line_items', [{
        'quantity': qty,
        'price_data': {
            'currency': 'jpy',
            'unit_amount': price,          # ⛔ 円は0桁通貨。×100しない
            'product_data': {'name': name},
        },
    }], fields)
    _flatten('metadata', {'booking_id': str(booking_id),
                          'course': course['code']}, fields)
    data, err = _post('/checkout/sessions', fields)
    if err:
        return None, None, err
    return data.get('url'), data.get('id'), None


def verify_webhook(raw_body, sig_header):
    """Stripe からの通知が本物かを確かめる。戻り値: (イベント, エラー文 or None)

    ⛔ 署名を検証せずに本文を信じないこと。誰でも「決済が終わった」と
       送れてしまい、無料で受講できる口になる。
    ⛔ 検証は生のバイト列に対して行うこと。json を読み直して文字列化すると
       1バイトでも変わって必ず不一致になる。
    """
    whsec = webhook_secret()
    if not whsec:
        return None, '受信設定がありません'
    if isinstance(raw_body, str):
        raw_body = raw_body.encode('utf-8')
    parts = dict(p.split('=', 1) for p in (sig_header or '').split(',')
                 if '=' in p)
    ts, got = parts.get('t'), parts.get('v1')
    if not ts or not got:
        return None, '署名がありません'
    try:
        if abs(time.time() - int(ts)) > TOLERANCE_SEC:
            return None, '署名の時刻が古すぎます'
    except ValueError:
        return None, '署名の時刻が読めません'
    want = hmac.new(whsec.encode('utf-8'),
                    ts.encode('utf-8') + b'.' + raw_body,
                    hashlib.sha256).hexdigest()
    # ⛔ == で比べないこと（応答時間から鍵が推測できる）
    if not hmac.compare_digest(want, got):
        return None, '署名が一致しません'
    try:
        return json.loads(raw_body.decode('utf-8')), None
    except Exception:
        return None, '本文が読めません'
