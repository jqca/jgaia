# -*- coding: utf-8 -*-
"""運営用「予約できるか（全講座）」の回帰テスト。

固定しているのは事故の型:
  ① 講座を足したのに、この画面／紹介ページの対応表に載せ忘れる
     （＝載っていない講座は目視確認の対象から静かに外れる）
  ② 予約できるかを、受講者に見えている判断と**別のやり方**で数える
     （この画面は緑なのに紹介ページは「調整中」になる）
  ③ 0件なのに理由が出ない（＝何をすれば直るのか誰にも分からない）
  ④ 合言葉なしで開ける（担当講師の氏名が出る画面）
"""
import os
import sys
import tempfile
import unittest
from datetime import date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

# ⛔ import より前に置く。booking はここを見て保存先を決める。
_TMP = tempfile.mkdtemp(prefix='jgaia-bookcheck-test-')
os.environ['INQUIRY_LOG_DIR'] = _TMP
os.environ['SECRET_KEY'] = 'test-secret'
os.environ['INQUIRY_ADMIN_TOKEN'] = 'test-admin'
for _k in ('RESEND_API_KEY', 'HCAPTCHA_SECRET', 'SMTP_PASSWORD'):
    os.environ.pop(_k, None)

import booking          # noqa: E402
import booking_check    # noqa: E402
from app import app     # noqa: E402

ALL = [c['code'] for c in booking.COURSES]


def _rows():
    """course_rows() を呼ぶ。url_for を使うので application context が要る。"""
    with app.test_request_context():
        return booking_check.course_rows()


def _clear():
    for f in ('instructors.json', 'bookings.json'):
        p = os.path.join(_TMP, f)
        if os.path.exists(p):
            os.remove(p)


def _every_day(codes, span=150):
    """今日から span 日ぶん、その講座を担当する、という登録内容。

    開催日でない日・曜日の合わない講座は読み出し側が落とすので、
    ここで絞らない（絞ると「絞り方」を2か所に持つことになる）。
    """
    d0 = date.today()
    return {(d0 + timedelta(days=i)).isoformat(): list(codes)
            for i in range(span)}


def _seed_full_instructor():
    """全講座を担当できる、承認済み・メール確認済みの講師を1人置く。"""
    _clear()
    rec, token = booking.register_instructor(
        '確認 太郎', 'check@example.com', '', ALL, '',
        days=_every_day(ALL), fee_agreed=booking.FEE_TERMS_VERSION)
    booking.verify_email(token)
    booking.set_state(rec['id'], '承認')
    return rec, token


class Test対応表(unittest.TestCase):

    def test_全講座に紹介ページの対応がある(self):
        # ⛔ 講座を足して対応表を忘れると、その講座だけ目視確認から静かに外れる
        missing = [c for c in ALL if not booking_check.INTRO.get(c)]
        self.assertEqual(missing, [], '紹介ページの対応が無い講座: %s' % missing)

    def test_紹介ページはすべて実在する(self):
        c = app.test_client()
        for path in sorted(set(booking_check.INTRO.values())):
            r = c.get(path)
            self.assertEqual(r.status_code, 200, '%s が %s' % (path, r.status_code))


class Test合言葉(unittest.TestCase):

    def test_合言葉なしでは開けない(self):
        r = app.test_client().get('/admin/booking-check')
        self.assertEqual(r.status_code, 403)

    def test_合言葉が違えば開けない(self):
        r = app.test_client().get('/admin/booking-check?token=zzz')
        self.assertEqual(r.status_code, 403)


class Test判定(unittest.TestCase):

    def setUp(self):
        _clear()

    def tearDown(self):
        _clear()

    def test_全講座が並ぶ(self):
        rows = _rows()
        self.assertEqual([r['code'] for r in rows], ALL)

    def test_受講者に見えている判断と一致する(self):
        # ⛔ ここで別に数えないこと。紹介ページの「申し込む」と同じ出どころ
        _seed_full_instructor()
        for r in _rows():
            slot = booking.open_slots(r['code'])
            self.assertEqual(r['件数'], slot['件数'], r['code'])
            self.assertEqual(r['最短'], slot['最短'], r['code'])

    def test_講師を1人置けば全講座が予約できる(self):
        _seed_full_instructor()
        rows = _rows()
        ng = [r['code'] for r in rows if not r['件数']]
        self.assertEqual(ng, [], '予約できない講座が残っています: %s' % ng)

    def test_承認していない講師しかいなければ理由は講師0名(self):
        _clear()
        rec, token = booking.register_instructor(
            '未 承認', 'pending@example.com', '', ALL, '',
            days=_every_day(ALL), fee_agreed=booking.FEE_TERMS_VERSION)
        booking.verify_email(token)
        rows = {r['code']: r for r in _rows()}
        self.assertEqual(rows['GA']['件数'], 0)
        self.assertIn('0名', rows['GA']['理由'])

    def test_日が無ければ理由は日程がないこと(self):
        _clear()
        rec, token = booking.register_instructor(
            '日 なし', 'noday@example.com', '', ALL, '', days={},
            fee_agreed=booking.FEE_TERMS_VERSION)
        booking.verify_email(token)
        booking.set_state(rec['id'], '承認')
        rows = {r['code']: r for r in _rows()}
        self.assertEqual(rows['GA']['件数'], 0)
        # ⛔ 「講師がいません」と出さないこと（居る。足りないのは日程）
        self.assertIn('講師は1名', rows['GA']['理由'])

    def test_日程が無い講師を予約を受けられる講師として出さない(self):
        # ⛔ 承認済み＝受けられる、ではない。日が無ければ1件も受けられないので、
        #    担当者として並べると「誰かが受けてくれる」と読み違える
        _clear()
        rec, token = booking.register_instructor(
            '日 なし', 'noday@example.com', '', ALL, '', days={},
            fee_agreed=booking.FEE_TERMS_VERSION)
        booking.verify_email(token)
        booking.set_state(rec['id'], '承認')
        rows = {r['code']: r for r in _rows()}
        self.assertEqual(rows['GA']['講師'], [])
        self.assertEqual(rows['GA']['日程待ちの講師'], ['日 なし'])

    def test_予約できないときは必ず理由がある(self):
        _clear()
        for r in _rows():
            if not r['件数']:
                self.assertTrue(r['理由'].strip(), r['code'])


class Test画面(unittest.TestCase):

    def setUp(self):
        _seed_full_instructor()

    def tearDown(self):
        _clear()

    def test_画面が出て全講座の予約ページへの導線がある(self):
        r = app.test_client().get('/admin/booking-check?token=test-admin')
        self.assertEqual(r.status_code, 200)
        html = r.get_data(as_text=True)
        for code in ALL:
            self.assertIn('/book/%s"' % code, html, code)

    def test_JSONでも同じ数を返す(self):
        r = app.test_client().get('/admin/booking-check?token=test-admin&format=json')
        self.assertEqual(r.status_code, 200)
        d = r.get_json()
        self.assertEqual(d['講座数'], len(ALL))
        self.assertEqual(d['予約できる講座'], len(ALL))

    def test_予約ページが実際に開く(self):
        c = app.test_client()
        for code in ALL:
            self.assertEqual(c.get('/book/%s' % code).status_code, 200, code)


if __name__ == '__main__':
    unittest.main(verbosity=2)
