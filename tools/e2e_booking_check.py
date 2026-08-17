# -*- coding: utf-8 -*-
"""申込導線を、ダミーの講師・予定・受講者で一気通貫に確かめる。

社長ご指示 2026-08-17「ダミーの講師とかダミーの講座の予定とかダミーの受講者とかで
テストまでやって」。

⛔ 本番の台帳には1行も書かないこと。ここは INQUIRY_LOG_DIR を毎回まっさらな
   一時フォルダに向けてから app を読み込む（import より前に環境変数を置く）。
   本番の /data を指していたら、その場で止める。
⛔ RESEND_API_KEY を持ったまま走らせないこと。ダミーの宛先に実メールが出る。

使い方:  python tools/e2e_booking_check.py
戻り値:  すべて通れば 0、1つでも落ちれば 1
"""
import io
import os
import re
import sys
import json
import time
import tempfile
from datetime import date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

# ── 隔離（⛔ import より前）
_SANDBOX = tempfile.mkdtemp(prefix='jgaia-e2e-')
os.environ['INQUIRY_LOG_DIR'] = _SANDBOX
os.environ['SECRET_KEY'] = 'e2e-secret'
os.environ['INQUIRY_ADMIN_TOKEN'] = 'e2e-admin-token'
# ⛔ 外に出る鍵は全部落とす（ダミー宛にメールを出さない・決済を作らない）
for _k in ('RESEND_API_KEY', 'SMTP_PASSWORD', 'HCAPTCHA_SECRET',
           'STRIPE_SECRET_KEY'):
    os.environ.pop(_k, None)

import antispam            # noqa: E402
import booking             # noqa: E402
from app import app        # noqa: E402

if booking._dir() != _SANDBOX:
    raise SystemExit('保存先が砂場になっていません: %s' % booking._dir())

app.logger.disabled = True
C = app.test_client()

_ok = 0
_ng = []


def check(label, cond, detail=''):
    global _ok
    if cond:
        _ok += 1
        print('  OK   %s%s' % (label, ('  … ' + detail) if detail else ''))
    else:
        _ng.append(label)
        print('  NG   %s%s' % (label, ('  … ' + detail) if detail else ''))


def _spam_fields(d):
    """蜜壺と発行時刻。⛔ 付けないと本物と同じく黙って弾かれる。"""
    d = dict(d)
    d[antispam.HONEYPOT_FIELD] = ''
    d['ts'] = antispam.issue_token(now=time.time() - 6)
    return d


COURSE = 'GM-B'            # 全3研修・1研修 ¥110,000（決裁ラインの検証に使う）
SINGLE = 'GA'              # 1本の講座（比較用）


def main():
    n_all = booking.sessions_of(COURSE)
    unit = booking.unit_price_of(COURSE)
    print('\n== 前提 ==')
    print('  講座 %s ／ 全%d研修 ／ 1研修 %s円（税抜 %s円）'
          % (COURSE, n_all, format(unit, ','), format(int(unit / 1.1), ',')))
    print('  砂場: %s' % _SANDBOX)

    # ───────── 1. ダミー講師の登録
    print('\n== 1. ダミー講師が登録する ==')
    antispam._RECENT.clear()
    r = C.get('/instructor/register')
    check('登録画面が開く', r.status_code == 200)
    r = C.post('/instructor/register', data=_spam_fields({
        'name': 'ダミー 講師', 'email': 'dummy-instructor@example.com',
        'org': 'テスト株式会社', 'courses': [COURSE, SINGLE],
        # ⛔ 同意は「1」ではなく提示した条件の版を送る（サーバーが照合する）
        'note': 'E2Eテスト', 'fee_agree': booking.FEE_TERMS_VERSION}),
        follow_redirects=True)
    check('登録できる', r.status_code == 200
          and 'ご同意が必要' not in r.get_data(as_text=True))
    rows = booking.instructors()
    check('台帳に1名入る', len(rows) == 1, '%d名' % len(rows))
    inst = rows[0]
    token = inst['鍵']

    # ───────── 2. メール確認
    print('\n== 2. 本人がメールの確認リンクを開く ==')
    r = C.get('/instructor/verify/%s' % token, follow_redirects=True)
    inst = booking.instructors()[0]
    check('メール確認済みになる', bool(inst.get('メール確認済み')),
          str(inst.get('メール確認済み')))

    # ───────── 3. 運営が承認
    print('\n== 3. 運営が承認する ==')
    r = C.post('/api/instructor/decide',
               json={'id': inst['id'], 'state': '承認'},
               headers={'X-Admin-Token': 'e2e-admin-token'})
    check('承認APIが通る', r.status_code == 200, str(r.get_json())[:80])
    inst = booking.instructors()[0]
    check('状態が承認になる', inst.get('状態') == '承認', str(inst.get('状態')))
    check('担当できる講座に入る', COURSE in booking.approved_courses(inst),
          str(booking.approved_courses(inst)))

    # ───────── 4. 講師が予定を登録（⛔締切の外側の日を選ぶ）
    print('\n== 4. 講師が開催できる日を登録する ==')
    earliest = booking.today_jst() + timedelta(days=booking.LEAD_DAYS)
    # その講座が開催できる曜日で、全3回ぶん先まで取れる日を探す
    day = None
    d = earliest + timedelta(days=1)
    for _ in range(90):
        if booking.course_open_on(COURSE, d):
            day = d
            break
        d += timedelta(days=1)
    check('開催できる日が見つかる', day is not None, str(day))
    # 全3回ぶん（毎週なので3週）の予定を入れる
    isos = booking.course_dates(COURSE, day.isoformat())
    for iso in isos:
        r = C.post('/instructor/schedule/%s/day/%s' % (token, iso),
                   data={'courses': [COURSE, SINGLE], 'confirm': '1'},
                   follow_redirects=True)
        if r.status_code != 200:
            break
    # ⛔ GA 用の日を別に取ること。GM-B の申込が入るとその3日は講師が埋まり、
    #    GA が「開催日なし」になる（正しい挙動）。同じ日で確かめようとすると
    #    最後の確認が黙って飛ばされる（2026-08-17 に実際にそうなった）。
    dd = date.fromisoformat(isos[-1]) + timedelta(days=1)
    ga_day = None
    for _ in range(60):
        # ⛔ course_open_on だけで選ばないこと。あれは講座の曜日制限しか見ず、
        #    GA は制限が無いので木曜でも True を返す。開催日そのものの決まり
        #    （毎週水＋第2・第4土）は is_session_day が持っている
        if (booking.is_session_day(dd) and booking.course_open_on(SINGLE, dd)
                and dd.isoformat() not in isos):
            ga_day = dd.isoformat()
            break
        dd += timedelta(days=1)
    check('GA用の別の日が見つかる', ga_day is not None, str(ga_day))
    if ga_day:
        C.post('/instructor/schedule/%s/day/%s' % (token, ga_day),
               data={'courses': [SINGLE], 'confirm': '1'},
               follow_redirects=True)
    inst = booking.instructors()[0]
    reg = booking.registered_days(inst)
    check('%d日ぶん登録される' % len(isos), len(reg) >= len(isos),
          '%d日' % len(reg))
    blockers = booking.publish_blockers(inst)
    check('公開されない理由が無くなる', not blockers, ' / '.join(blockers))

    # ───────── 5. 受講者から見えるか
    print('\n== 5. 受講者の画面に開催日が出る ==')
    html = C.get('/book/%s' % COURSE).get_data(as_text=True)
    check('「日程がありません」が消える', '日程がありません' not in html)
    check('研修数の欄が出る', '今回お申し込みになる研修数' in html)
    check('1研修の金額が出る', '{:,}'.format(unit) in html,
          '¥%s' % format(unit, ','))
    opens = [x for x in booking.open_days(COURSE, months=4) if x['講師数'] > 0]
    check('予約できる日がある', bool(opens), '%d日' % len(opens))
    target = opens[0]['日付']

    # ───────── 6. ダミー受講者が「1研修だけ」申し込む
    print('\n== 6. ダミー受講者が1研修だけ申し込む ==')
    antispam._RECENT.clear()
    r = C.post('/api/book', json=_spam_fields({
        'course': COURSE, 'day': target, 'name': 'ダミー 受講者',
        'email': 'dummy-student@example.com', 'company': 'テスト株式会社',
        'people': 1, 'message': 'E2E', 'sessions': '1', 'pay': 'invoice'}))
    check('申込APIが通る', r.status_code == 200, str(r.get_json())[:80])
    bk = booking.bookings()
    check('申込が1件入る', len(bk) == 1, '%d件' % len(bk))
    rec = bk[0]
    check('受講料が1研修ぶん', rec['受講料_円'] == unit,
          '¥%s' % format(rec['受講料_円'], ','))
    check('★20万円未満（決裁権限の内側）', rec['受講料_円'] < 200000,
          '税抜 ¥%s' % format(int(rec['受講料_円'] / 1.1), ','))
    check('開催日が1日だけ', len(rec['開催日']) == 1, str(rec['開催日']))
    check('研修数が残る', rec.get('研修数') == 1 and rec.get('全研修数') == n_all,
          '%s/%s' % (rec.get('研修数'), rec.get('全研修数')))

    # ───────── 7. 受講証明書
    print('\n== 7. 受講証明書（助成金の実績報告に出すもの） ==')
    r = C.get('/admin/booking/%s/certificate?token=e2e-admin-token' % rec['id'])
    check('証明書APIが通る', r.status_code == 200)
    cert = r.get_json() if r.status_code == 200 else {}
    cert = cert.get('rows') or cert
    full = booking.TRAINING_HOURS[COURSE]
    want_h = round(full / n_all, 2)
    check('総研修時間数が1研修ぶん', cert.get('総研修時間数') == want_h,
          '%s時間（講座全体は%s時間）' % (cert.get('総研修時間数'), full))
    check('助成の時間要件に収まる',
          booking.SUBSIDY['min_hours'] <= (cert.get('総研修時間数') or 0)
          < booking.SUBSIDY['max_hours'])
    check('必要出席時間数が8割', cert.get('必要出席時間数') == round(want_h * .8, 1),
          str(cert.get('必要出席時間数')))
    check('出席時間は空のまま', cert.get('出席時間数') is None)
    check('実施日が1日だけ', len(cert.get('実施日') or []) == 1,
          str(cert.get('実施日')))

    # ───────── 8. あとから2研修目を追加
    print('\n== 8. 同じ受講者があとから追加で申し込む ==')
    antispam._RECENT.clear()
    r = C.post('/api/book', json=_spam_fields({
        'course': COURSE, 'day': target, 'name': 'ダミー 受講者',
        'email': 'dummy-student@example.com', 'company': 'テスト株式会社',
        'people': 1, 'message': '追加', 'sessions': '2', 'pay': 'invoice'}))
    check('追加の申込が通る', r.status_code == 200, str(r.get_json())[:80])
    add = booking.bookings()[-1]
    check('2研修ぶんの金額', add['受講料_円'] == unit * 2,
          '¥%s' % format(add['受講料_円'], ','))
    total = sum(b['受講料_円'] for b in booking.bookings())
    check('合計は全研修ぶんと同じ（値引きでない）',
          total == booking.COURSE_BY_CODE[COURSE]['price'],
          '¥%s' % format(total, ','))

    # ───────── 9. ガードが効くか
    print('\n== 9. 値引きされない・締切が効く ==')
    for bad in ('0', '-3', '99', 'abc'):
        antispam._RECENT.clear()
        C.post('/api/book', json=_spam_fields({
            'course': COURSE, 'day': target, 'name': 'ダミー',
            'email': 'x@example.com', 'company': '', 'people': 1,
            'message': '', 'sessions': bad, 'pay': 'invoice'}))
        got = booking.bookings()[-1]['受講料_円']
        want = unit if bad in ('0', '-3') else unit * n_all
        check('sessions=%-4s → ¥%s' % (bad, format(got, ',')), got == want)
    antispam._RECENT.clear()
    soon = (booking.today_jst() + timedelta(days=1)).isoformat()
    r = C.post('/api/book', json=_spam_fields({
        'course': COURSE, 'day': soon, 'name': 'ダミー',
        'email': 'y@example.com', 'company': '', 'people': 1,
        'message': '', 'sessions': '1', 'pay': 'invoice'}))
    check('締切内の日は断られる', r.status_code == 400,
          str(r.get_json())[:60])

    # ───────── 10. 1本の講座は今までどおり
    print('\n== 10. 1本の講座（GA）は今までどおり ==')
    html = C.get('/book/%s' % SINGLE).get_data(as_text=True)
    check('研修数の欄は出ない', '今回お申し込みになる研修数' not in html)
    sopen = [x for x in booking.open_days(SINGLE, months=4) if x['講師数'] > 0]
    # ⛔ 「日が無いので飛ばす」を成功にしないこと。黙って飛ばすと、この確認は
    #    落ちようがない検査になる（2026-08-17 に実際に飛ばしていた）
    check('GAにも予約できる日がある', bool(sopen), '%d日' % len(sopen))
    if sopen:
        antispam._RECENT.clear()
        r = C.post('/api/book', json=_spam_fields({
            'course': SINGLE, 'day': sopen[0]['日付'], 'name': 'ダミー',
            'email': 'z@example.com', 'company': '', 'people': 2,
            'message': '', 'pay': 'invoice'}))
        check('GAの申込が通る', r.status_code == 200, str(r.get_json())[:60])
        g = booking.bookings()[-1]
        check('受講料は講座の価格のまま',
              g['受講料_円'] == booking.COURSE_BY_CODE[SINGLE]['price'],
              '¥%s' % format(g['受講料_円'], ','))
        check('人数ぶん請求される', g['請求額_円'] == g['受講料_円'] * 2,
              '¥%s' % format(g['請求額_円'], ','))
        check('研修数は1のまま', g.get('研修数') == 1, str(g.get('研修数')))

    print('\n' + '=' * 58)
    print('  通った: %d 件 ／ 落ちた: %d 件' % (_ok, len(_ng)))
    for x in _ng:
        print('   NG %s' % x)
    print('  ⛔ ここで作ったダミーは砂場だけ（本番の台帳は無傷）')
    print('=' * 58)
    return 1 if _ng else 0


if __name__ == '__main__':
    sys.exit(main())
