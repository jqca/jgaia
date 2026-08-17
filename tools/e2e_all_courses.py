# -*- coding: utf-8 -*-
"""掲載している**全講座**を、1つずつ実際に予約してみる。

社長ご質問 2026-08-17「26講座すべてについてテスト予約して動作確認したの？」
→ していなかった（GM-B・GA・SP-B の3講座だけ）。講座ごとに開催曜日・研修数・
   定員・単位が違うので、通してみるまで分からない。

⛔ 本番の台帳には1行も書かない（tools/e2e_booking_check.py と同じ隔離）。
⛔ 1講座ごとに台帳をまっさらにする。同じ講師が続けて担当すると、前の講座の
   予約でその日が埋まり、次の講座が「日程なし」になって偽の不合格が出る。

使い方:  python tools/e2e_all_courses.py
戻り値:  すべて通れば 0、1つでも落ちれば 1
"""
import io
import os
import re
import sys
import time
import shutil
import tempfile
from datetime import date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

_SANDBOX = tempfile.mkdtemp(prefix='jgaia-e2e-all-')
os.environ['INQUIRY_LOG_DIR'] = _SANDBOX
os.environ['SECRET_KEY'] = 'e2e-secret'
os.environ['INQUIRY_ADMIN_TOKEN'] = 'e2e-admin-token'
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

# 講座コード → その講座を紹介しているページ（予約への導線が出るか見る）
INTRO = {'SP-A': '/solo-ceo/course-spa', 'SP-B': '/solo-ceo/course-spb',
         'SP-C': '/solo-ceo/course-spc',
         'GA': '/vibe-coding/course-ga', 'GA-P': '/vibe-coding/course-gap',
         'GB': '/vibe-coding/course-gb', 'GC': '/vibe-coding/course-gc',
         'GD': '/vibe-coding/course-gd', 'GE': '/vibe-coding/course-ge',
         'GK1': '/vibe-coding/kids', 'GK2': '/vibe-coding/kids',
         'GK3': '/vibe-coding/kids'}
for _s, _slug in (('GM', 'manufacturing'), ('GH', 'healthcare'),
                  ('GF', 'finance'), ('GL', 'logistics'),
                  ('GN', 'construction')):
    for _lv in ('A', 'B', 'C'):
        INTRO['%s-%s' % (_s, _lv)] = '/vibe-coding/' + _slug


def reset():
    """台帳をまっさらにする（⛔講座をまたいで持ち越さない）。"""
    for name in ('instructors.json', 'bookings.json'):
        p = os.path.join(_SANDBOX, name)
        if os.path.exists(p):
            os.remove(p)
    antispam._RECENT.clear()


def prepare(code):
    """その講座だけを担当する講師を1名立て、全日程を登録する。"""
    days = {(date.today() + timedelta(days=i)).isoformat(): [code]
            for i in range(150)}
    booking.register_instructor('担当 太郎', 'i@example.com', '', [code], '',
                                days)
    inst = booking.instructors()[0]
    booking.set_state(inst['id'], '承認')
    booking.verify_email(inst['鍵'])
    return inst


def spam(d):
    d = dict(d)
    d[antispam.HONEYPOT_FIELD] = ''
    d['ts'] = antispam.issue_token(now=time.time() - 6)
    return d


def check_course(code):
    """1講座ぶんを通す。戻り値: (見出し, [失敗の理由...])"""
    ng = []
    c = booking.COURSE_BY_CODE[code]
    n_all = booking.sessions_of(code)
    unit = booking.unit_price_of(code)
    reset()
    prepare(code)

    # ① 公開されるか
    blockers = booking.publish_blockers(booking.instructors()[0])
    if blockers:
        ng.append('公開されない: ' + ' / '.join(blockers))
    opens = [d for d in booking.open_days(code, months=6)
             if d['状態'] == '予約可']
    if not opens:
        ng.append('予約できる日が0件')
        return c, ng
    day = opens[0]['日付']

    # ② 紹介ページに予約への導線が出るか（子ども向けは予約導線を持たない）
    # ⛔ 「助成対象外だから導線も無い」と読み替えないこと（2026-08-17 実際に
    #    そう書いて、子ども向け3講座の欠陥を検査ごと飛ばしていた）。
    #    助成の可否と、予約できるかどうかは別の話。
    intro = INTRO.get(code)
    if intro:
        h = C.get(intro).get_data(as_text=True)
        if ('/book/%s' % code) not in h:
            ng.append('紹介ページ %s に予約への導線が無い' % intro)

    # ③ 申込画面
    h = C.get('/book/%s' % code).get_data(as_text=True)
    if '日程がありません' in h:
        ng.append('申込画面が「日程がありません」')
    if n_all > 1 and '今回お申し込みになる研修数' not in h:
        ng.append('分割掲載なのに研修数の欄が出ない')
    if n_all == 1 and '今回お申し込みになる研修数' in h:
        ng.append('1本の講座なのに研修数の欄が出ている')

    # ④ 申し込む（分割掲載は1研修だけ＝決裁ラインの検証を兼ねる）
    take = 1 if n_all > 1 else None
    r = C.post('/api/book', json=spam({
        'course': code, 'day': day, 'name': 'テスト 太郎',
        'email': 't@example.com', 'company': 'テスト株式会社', 'people': 1,
        'message': 'E2E', 'sessions': take, 'pay': 'invoice'}))
    if r.status_code != 200:
        ng.append('申込APIが %d' % r.status_code)
        return c, ng
    rows = booking.bookings()
    if len(rows) != 1:
        ng.append('台帳に入らなかった（%d件）' % len(rows))
        return c, ng
    rec = rows[0]

    # ⑤ 金額
    want = unit * (take or n_all)
    if rec['受講料_円'] != want:
        ng.append('受講料が ¥%s（期待 ¥%s）'
                  % (format(rec['受講料_円'], ','), format(want, ',')))
    if len(rec['開催日']) != (take or n_all):
        ng.append('開催日が%d件（期待%d件）'
                  % (len(rec['開催日']), take or n_all))

    # ⑥ 受講証明書
    cert = booking.certificate_data(rec['id'])
    if not cert:
        ng.append('受講証明書が出ない')
    else:
        full = booking.TRAINING_HOURS[code]
        want_h = round(full / n_all * (take or n_all), 2)
        if cert['総研修時間数'] != want_h:
            ng.append('証明書の時間が %s（期待 %s）'
                      % (cert['総研修時間数'], want_h))
        if cert['出席時間数'] is not None:
            ng.append('出席時間が埋まっている（当日確認するもの）')
        # 助成の対象／対象外が講座の判定と一致すること
        s = booking.subsidy_for(code) or {}
        if bool(cert['助成対象']) != bool(s.get('eligible')):
            ng.append('証明書の助成対象が判定と違う')

    # ⑦ 1研修あたりが決裁ラインの内側か（社長ご指示の要）
    if unit >= 200000:
        ng.append('1研修 ¥%s が20万円以上' % format(unit, ','))
    return c, ng


def main():
    codes = [c['code'] for c in booking.COURSES]
    print('\n掲載している講座: %d 件' % len(codes))
    print('砂場: %s\n' % _SANDBOX)
    print('%-7s %-30s %8s %5s %9s  %s'
          % ('code', 'name', '受講料', '研修', '1研修', '結果'))
    print('-' * 88)
    bad = {}
    for code in codes:
        c, ng = check_course(code)
        unit = booking.unit_price_of(code)
        n = booking.sessions_of(code)
        print('%-7s %-30s %8s %5s %9s  %s'
              % (code, c['name'][:30], format(c['price'], ','), n,
                 format(unit, ','), 'OK' if not ng else 'NG'))
        for x in ng:
            print('        - %s' % x)
        if ng:
            bad[code] = ng
    print('-' * 88)
    print('通った: %d 件 ／ 落ちた: %d 件' % (len(codes) - len(bad), len(bad)))
    print('⛔ ここで作ったダミーは砂場だけ（本番の台帳は無傷）')
    shutil.rmtree(_SANDBOX, ignore_errors=True)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
