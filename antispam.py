# -*- coding: utf-8 -*-
"""問い合わせフォームのスパム対策。

背景（2026-08-06 外注先からの報告）:
    スパムが大量に届き、Resendの日次上限（100通/日）に到達して
    **正規の問い合わせが送れない日がある**。つまり被害は迷惑メールの
    受信ではなく「本物の申込が届かなくなること」。

方針:
    1. まず登録不要の防御を重ねる。ここで大半のボットは落ちる
       ・蜜壺（人には見えない入力欄。埋めたらボット）
       ・早すぎる送信（ページを開いてから数秒未満）
       ・同一IPからの連投
       ・本文中のURLが多すぎる
    2. hCaptcha は鍵（HCAPTCHA_SITEKEY / HCAPTCHA_SECRET）が入っていれば
       自動で有効になる。入っていなければ何も要求しない
       ⛔ 鍵が無いことを理由に他の防御まで止めないこと

⛔ 判定に引っかかったリクエストは「成功」と返す（ボットに学習させない）。
   ただしメールは送らず、記録だけ残す。誤判定で本物を落としたときに
   数えられるようにするため、理由つきで instance/spam.log に残す。

⛔ 人間を落とす方向に強くしないこと。ここでの誤判定は売上の機会損失に直結する。
   閾値は「ボットが必ず引っかかり、人間はまず引っかからない」線で置く。
"""
import hashlib
import hmac
import json
import logging
import os
import re
import threading
import time
import urllib.parse
import urllib.request

log = logging.getLogger(__name__)

# 蜜壺の入力欄の名前。
# ⛔ 'website' や 'url' のような一般的な名前にしないこと。ブラウザや
#    パスワード管理ソフトの自動入力が埋めてしまい、**正規の利用者が弾かれる**。
#    ボットは空の入力欄を機械的に全部埋めるので、無名の名前でも十分に効く。
HONEYPOT_FIELD = 'jgaia_hp'

# ページを開いてから送信までの最短秒数。人間が全項目を埋めるには足りない時間。
MIN_SECONDS = 4
# 署名付きトークンの有効期限（長時間開いたまま送る人もいるので長めに）
MAX_SECONDS = 60 * 60 * 12

# 同一IPからの受付上限（時間あたり）。
# ⛔ 少なくしないこと。ここは「人を妨げる側」にしか効いていない。
#    実測（2026-08-06 遮断86件の内訳）: 発行時刻の署名なし84件／蜜壺2件／
#    **連投 0件**。ボットはフォームを開かず直POSTしてくるので署名で落ちる。
#    一方で人は、書き間違いに気づいて2回・3回送り直す。5件は現実的に届く。
#    社長ご指摘（2026-08-06）「二度目の問い合わせができないのか」の原因。
#    ここは連続投稿の暴走を止める最後の砦としてだけ置き、
#    人が普通に使って当たらない数にする。
RATE_LIMIT_PER_HOUR = 30

# 本文に含まれるURLの上限。営業スパムはリンクを並べる。
MAX_LINKS = 2

_LOCK = threading.Lock()
_RECENT = {}          # ip -> [受付時刻, ...]


def _secret():
    return (os.environ.get('SECRET_KEY') or 'jgaia-antispam-fallback').encode()


def issue_token(now=None):
    """フォームに埋める署名付きの発行時刻。

    署名するのは、ボットが「4秒前」を自分で書けないようにするため。
    """
    ts = int(now or time.time())
    sig = hmac.new(_secret(), str(ts).encode(), hashlib.sha256).hexdigest()[:16]
    return f'{ts}.{sig}'


def _token_age(token):
    """トークンの経過秒数。壊れている・署名が合わない場合は None。"""
    try:
        ts_s, sig = (token or '').split('.', 1)
        ts = int(ts_s)
    except Exception:
        return None
    expect = hmac.new(_secret(), str(ts).encode(), hashlib.sha256).hexdigest()[:16]
    if not hmac.compare_digest(sig, expect):
        return None
    return int(time.time()) - ts


def client_ip(request):
    """Railwayの前段プロキシ越しの実IP。"""
    fwd = request.headers.get('X-Forwarded-For', '')
    if fwd:
        return fwd.split(',')[0].strip()
    return request.remote_addr or '?'


def _rate_ok(ip):
    now = time.time()
    with _LOCK:
        hits = [t for t in _RECENT.get(ip, []) if now - t < 3600]
        if len(hits) >= RATE_LIMIT_PER_HOUR:
            _RECENT[ip] = hits
            return False
        hits.append(now)
        _RECENT[ip] = hits
        # 溜め込み防止（プロセスが長生きするので定期的に掃除）
        if len(_RECENT) > 5000:
            for k in [k for k, v in _RECENT.items() if not any(now - t < 3600 for t in v)]:
                _RECENT.pop(k, None)
    return True


def _hcaptcha_ok(token, ip):
    """hCaptchaの検証。鍵が無ければ検証そのものを行わない（Trueを返す）。"""
    secret = (os.environ.get('HCAPTCHA_SECRET') or '').strip()
    if not secret:
        return True, 'hcaptcha未設定'
    if not token:
        return False, 'hcaptcha未回答'
    data = urllib.parse.urlencode({
        'secret': secret, 'response': token, 'remoteip': ip}).encode()
    try:
        req = urllib.request.Request('https://api.hcaptcha.com/siteverify', data=data)
        with urllib.request.urlopen(req, timeout=10) as r:
            body = json.loads(r.read().decode())
    except Exception as e:
        # ⛔ 検証サービスに繋がらないことを理由に本物を落とさない。
        #    他の防御は既に通っているので、ここは通す（可用性を優先）。
        log.warning('hcaptchaの検証に失敗しました（通します）: %s', e)
        return True, 'hcaptcha検証不能'
    if body.get('success'):
        return True, 'hcaptcha合格'
    return False, 'hcaptcha不合格:' + ','.join(body.get('error-codes') or [])


def _log(reason, ip, payload):
    """判定を記録する。誤判定を後から数えられないと閾値を直せない。"""
    d = os.environ.get('INQUIRY_LOG_DIR') or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'data')
    try:
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, 'spam.log'), 'a', encoding='utf-8') as f:
            f.write(json.dumps({
                'at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'reason': reason, 'ip': ip,
                'name': (payload.get('name') or '')[:40],
                'email': (payload.get('email') or '')[:60],
                'message': (payload.get('message') or '')[:200],
            }, ensure_ascii=False) + '\n')
    except Exception as e:
        log.warning('スパム判定の記録に失敗: %s', e)


def check(request, payload):
    """スパムらしければ理由の文字列を返す。問題なければ None。

    payload は {'name','email','message',...} と、
    フォームの隠しフィールド 'website'（蜜壺）'ts'（発行時刻）
    'h-captcha-response' を含む dict。
    """
    ip = client_ip(request)

    if (payload.get(HONEYPOT_FIELD) or '').strip():
        _log('蜜壺に入力あり', ip, payload)
        return '蜜壺に入力あり'

    age = _token_age(payload.get('ts'))
    if age is None:
        # 署名が無い＝フォームを経由せず直接POSTしている
        _log('発行時刻の署名なし', ip, payload)
        return '発行時刻の署名なし'
    if age < MIN_SECONDS:
        _log(f'送信が早すぎる({age}秒)', ip, payload)
        return f'送信が早すぎる({age}秒)'
    if age > MAX_SECONDS:
        _log('発行時刻が古すぎる', ip, payload)
        return '発行時刻が古すぎる'

    links = len(re.findall(r'https?://', payload.get('message') or ''))
    if links > MAX_LINKS:
        _log(f'本文のURLが多い({links})', ip, payload)
        return f'本文のURLが多い({links})'

    ok, detail = _hcaptcha_ok(payload.get('h-captcha-response'), ip)
    if not ok:
        _log(detail, ip, payload)
        return detail

    if not _rate_ok(ip):
        _log('同一IPからの連投', ip, payload)
        return '同一IPからの連投'

    return None


def sitekey():
    """テンプレートに渡す。空ならウィジェットを出さない。"""
    return (os.environ.get('HCAPTCHA_SITEKEY') or '').strip()


def counts():
    """/healthz から見えるように、遮断した件数を返す。"""
    d = os.environ.get('INQUIRY_LOG_DIR') or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'data')
    p = os.path.join(d, 'spam.log')
    if not os.path.exists(p):
        return 0
    try:
        with open(p, encoding='utf-8') as f:
            return sum(1 for line in f if line.strip())
    except Exception:
        return None
