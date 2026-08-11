# -*- coding: utf-8 -*-
"""講座の予約（講師の登録・承認・空き日・申込）の回帰テスト。

ここで固定しているのは「事故の型」であって、機能の説明ではない。
2026-08-09 に実際に起きた4つを落とせるようにしてある:
  ① 承認していない講師の日程が受講者に公開される
  ② 存在しないIDでも承認が成功したことになる（押しても何も変わらない）
  ③ 予約が入った日を講師があとから閉じられてしまう
  ④ 選べる日が0件のページでスクリプトが落ちる／テンプレートが500になる
"""
import os
import sys
import tempfile
import time
import unittest
from datetime import date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

# ⛔ import より前に置く。booking はここを見て保存先を決める。
_TMP = tempfile.mkdtemp(prefix='jgaia-booking-test-')
os.environ['INQUIRY_LOG_DIR'] = _TMP
os.environ['SECRET_KEY'] = 'test-secret'
os.environ['INQUIRY_ADMIN_TOKEN'] = 'test-admin'
for _k in ('RESEND_API_KEY', 'HCAPTCHA_SECRET', 'SMTP_PASSWORD'):
    os.environ.pop(_k, None)

import booking  # noqa: E402
import antispam  # noqa: E402
from app import app  # noqa: E402
from solo_ceo import booking_summary as solo_ceo_summary  # noqa: E402


def _clear():
    for f in ('instructors.json', 'bookings.json'):
        p = os.path.join(_TMP, f)
        if os.path.exists(p):
            os.remove(p)


def _weekly_all_days():
    """毎日いつでも講義できる、という登録内容。"""
    return [{'曜日': i, '開始': '10:00', '終了': '17:00'} for i in range(7)]


def _far_day(offset=30):
    return (date.today() + timedelta(days=offset)).isoformat()


class Test講師の登録(unittest.TestCase):
    def setUp(self):
        _clear()

    def test_登録した時点では必ず申請中(self):
        r, token = booking.register_instructor('山田 太郎', 'y@example.com', '',
                                              ['SP-A'], '', _weekly_all_days())
        self.assertEqual(r['状態'], '申請中')

    def test_本人用の鍵が推測できない長さである(self):
        r, token = booking.register_instructor('山田', 'y@example.com', '', ['SP-A'],
                                              '', _weekly_all_days())
        # この鍵だけで予定を書き換えられるので、短いと総当たりされる
        self.assertGreaterEqual(len(r['鍵']), 16)
        self.assertEqual(r['鍵'], token)

    def test_鍵は講師ごとに違う(self):
        a, _ = booking.register_instructor('A', 'a@example.com', '', ['SP-A'], '',
                                          _weekly_all_days())
        b, _ = booking.register_instructor('B', 'b@example.com', '', ['SP-A'], '',
                                          _weekly_all_days())
        self.assertNotEqual(a['鍵'], b['鍵'])

    def test_担当できる講座を選んでいない登録は受け取らない(self):
        with self.assertRaises(ValueError):
            booking.register_instructor('山田', 'y@example.com', '', [], '',
                                        _weekly_all_days())


class Test承認するまで公開しない(unittest.TestCase):
    def setUp(self):
        _clear()
        self.inst, _ = booking.register_instructor(
            '山田 太郎', 'y@example.com', '', ['SP-A'], '', _weekly_all_days())

    def test_申請中の講師の日は予約可にならない(self):
        days = {d['日付']: d['状態'] for d in booking.open_days('SP-A')}
        self.assertNotIn('予約可', set(days.values()))

    def test_承認したら予約可の日が出る(self):
        booking.set_state(self.inst['id'], '承認')
        days = [d for d in booking.open_days('SP-A') if d['状態'] == '予約可']
        self.assertTrue(days)

    def test_見送りに戻すと公開が止まる(self):
        booking.set_state(self.inst['id'], '承認')
        booking.set_state(self.inst['id'], '見送り')
        days = {d['状態'] for d in booking.open_days('SP-A')}
        self.assertNotIn('予約可', days)

    def test_存在しないIDの承認は成功にしない(self):
        # ⛔ ここが True を返すと、運営が押しても何も変わらないのに成功に見える
        self.assertFalse(booking.set_state('存在しないID', '承認'))

    def test_担当できない講座には出てこない(self):
        booking.set_state(self.inst['id'], '承認')
        days = {d['状態'] for d in booking.open_days('SP-C')}
        self.assertNotIn('予約可', days)


class Test日数の下限(unittest.TestCase):
    def setUp(self):
        _clear()
        i, _ = booking.register_instructor('山田', 'y@example.com', '', ['SP-A'],
                                          '', _weekly_all_days())
        booking.set_state(i['id'], '承認')
        self.inst = i

    def test_直近は準備期間として受け付けない(self):
        soon = (date.today() + timedelta(days=booking.LEAD_DAYS - 1)).isoformat()
        info = {d['日付']: d for d in booking.open_days('SP-A')}.get(soon)
        self.assertIsNotNone(info, '当月のカレンダーに日が無い')
        self.assertEqual(info['状態'], '準備期間')

    def test_準備期間の日は申込を断る(self):
        soon = (date.today() + timedelta(days=1)).isoformat()
        with self.assertRaises(ValueError):
            booking.add_booking('SP-A', soon, '鈴木', 's@example.com', '', 1, '')

    def test_締切より先の日は受け付ける(self):
        ok, inst = booking.add_booking('SP-A', _far_day(), '鈴木', 's@example.com',
                                      '', 1, '')
        self.assertEqual(ok['担当講師'], '山田')
        self.assertEqual(inst['氏名'], '山田')

    def test_カレンダーは空き日だけでなく全日を状態つきで返す(self):
        # ⛔ 空き日だけ返すと、画面が「予約締切」を出せなくなる
        states = {d['状態'] for d in booking.open_days('SP-A')}
        self.assertIn('予約可', states)
        self.assertIn('準備期間', states)


class Test講師の都合(unittest.TestCase):
    def setUp(self):
        _clear()
        self.inst, _ = booking.register_instructor(
            '山田', 'y@example.com', '', ['SP-A'], '', _weekly_all_days())
        booking.set_state(self.inst['id'], '承認')

    def test_不可にした日は予約締切になる(self):
        d = _far_day()
        booking.update_availability(self.inst['鍵'], _weekly_all_days(), [d])
        info = {x['日付']: x for x in booking.open_days('SP-A')}[d]
        self.assertEqual(info['状態'], '予約締切')

    def test_不可にした日は申込も断る(self):
        d = _far_day()
        booking.update_availability(self.inst['鍵'], _weekly_all_days(), [d])
        with self.assertRaises(ValueError):
            booking.add_booking('SP-A', d, '鈴木', 's@example.com', '', 1, '')

    def test_他人の鍵では書き換えられない(self):
        self.assertIsNone(booking.update_availability('でたらめな鍵',
                                                      _weekly_all_days(), []))

    def test_予約が入った日は講師が閉じられない(self):
        d = _far_day()
        booking.add_booking('SP-A', d, '鈴木', 's@example.com', '', 1, '')
        booking.update_availability(self.inst['鍵'], _weekly_all_days(), [d])
        # 受講者と約束した日を、あとから一方的に消せてはいけない
        self.assertIn(d, booking.booked_days_for_instructor(self.inst['id']))
        self.assertNotIn(d, booking.instructors()[0]['不可の日'])
        # 定員までは追加の申込を受ける（最少催行に人を集める必要がある）
        info = {x['日付']: x for x in booking.open_days('SP-A')}[d]
        self.assertEqual(info['状態'], '予約可')

    def test_予約済みの日は週の設定から外しても申込を受けられる(self):
        # ⛔ 1人目が入った日を講師が土曜から外した瞬間に2人目が申し込めなくなると、
        #    最少催行に届かず開催できない（申込は残っているのに）
        d = _far_day()
        booking.add_booking('SP-A', d, 'A', 'a@example.com', '', 1, '')
        booking.update_availability(self.inst['鍵'], [], [])
        r, _ = booking.add_booking('SP-A', d, 'B', 'b@example.com', '', 1, '')
        self.assertEqual(r['_合計人数'], 2)

    def test_定員に達した日は予約締切として出す(self):
        d = _far_day()
        cap = booking.COURSE_BY_CODE['SP-A']['capacity']
        booking.add_booking('SP-A', d, 'A', 'a@example.com', '', cap, '')
        info = {x['日付']: x for x in booking.open_days('SP-A')}[d]
        self.assertEqual(info['状態'], '予約締切')
        self.assertEqual(info['残り'], 0)

    def test_曜日を1つも選ばなければ公開されない(self):
        booking.update_availability(self.inst['鍵'], [], [])
        states = {d['状態'] for d in booking.open_days('SP-A')}
        self.assertNotIn('予約可', states)


class Test申込(unittest.TestCase):
    def setUp(self):
        _clear()
        i, _ = booking.register_instructor('山田', 'y@example.com', '', ['SP-A'],
                                          '', _weekly_all_days())
        booking.set_state(i['id'], '承認')
        self.inst = i

    def test_最少催行に届かない申込は確定にしない(self):
        r, _ = booking.add_booking('SP-A', _far_day(), '鈴木', 's@example.com', '', 1, '')
        self.assertFalse(r['_開催確定'])
        self.assertEqual(r['_最少催行'], booking.COURSE_BY_CODE['SP-A']['min_people'])

    def test_人数が集まれば確定になる(self):
        d = _far_day()
        need = booking.COURSE_BY_CODE['SP-A']['min_people']
        r, _ = booking.add_booking('SP-A', d, 'A', 'a@example.com', '', need, '')
        self.assertTrue(r['_開催確定'], r)

    def test_合計人数は同じ日の申込を足す(self):
        d = _far_day()
        booking.add_booking('SP-A', d, 'A', 'a@example.com', '', 2, '')
        r, _ = booking.add_booking('SP-A', d, 'B', 'b@example.com', '', 1, '')
        self.assertEqual(r['_合計人数'], 3)

    def test_定員を超える申込は断る(self):
        d = _far_day()
        cap = booking.COURSE_BY_CODE['SP-A']['capacity']
        with self.assertRaises(ValueError):
            booking.add_booking('SP-A', d, 'A', 'a@example.com', '', cap + 1, '')

    def test_担当講師が決まらない申込は作らない(self):
        # ⛔「講師未定」で受け付けないこと（当日に人がいない事故になる）
        booking.set_state(self.inst['id'], '見送り')
        with self.assertRaises(ValueError):
            booking.add_booking('SP-A', _far_day(), '鈴木', 's@example.com', '', 1, '')

    def test_受講料は台帳の金額を使う(self):
        r, _ = booking.add_booking('SP-A', _far_day(), '鈴木', 's@example.com', '', 1, '')
        self.assertEqual(r['受講料_円'], booking.COURSE_BY_CODE['SP-A']['price'])

    def test_名前とメールがなければ断る(self):
        with self.assertRaises(ValueError):
            booking.add_booking('SP-A', _far_day(), '', 's@example.com', '', 1, '')
        with self.assertRaises(ValueError):
            booking.add_booking('SP-A', _far_day(), '鈴木', '', '', 1, '')


class Test画面(unittest.TestCase):
    """テンプレートが実際に描けること。⛔ 500は「撮れた」では気づけない。"""

    def setUp(self):
        _clear()
        app.logger.disabled = True
        self.c = app.test_client()
        self.inst, _ = booking.register_instructor(
            '山田 太郎', 'y@example.com', '', ['SP-A'], '', _weekly_all_days())

    def test_講師の登録画面が開く(self):
        r = self.c.get('/instructor/register')
        self.assertEqual(r.status_code, 200)

    def test_登録画面に謝礼の希望額の入力欄を出さない(self):
        # ⛔ 2026-08-11 社長ご指示で削除した項目。戻すとここが落ちる
        html = self.c.get('/instructor/register').get_data(as_text=True)
        self.assertNotIn('name="fee"', html)
        self.assertNotIn('ご希望額', html)

    def test_謝礼の項目なしで登録できる(self):
        antispam._RECENT.clear()
        before = len(booking.instructors())
        r = self.c.post('/instructor/register', data={
            'name': '佐藤 次郎', 'email': 'j@example.com', 'org': '',
            'courses': ['SP-A'], 'wd5': '1', 'from5': '10:00', 'to5': '17:00',
            'note': 'よろしくお願いします',
            antispam.HONEYPOT_FIELD: '',
            'ts': antispam.issue_token(now=time.time() - 6)})
        self.assertEqual(r.status_code, 200)
        rows = booking.instructors()
        self.assertEqual(len(rows), before + 1)
        # 謝礼の希望額は受け取らないので、台帳にも入らない
        self.assertNotIn('希望謝礼_円_日', rows[-1])
        self.assertEqual(rows[-1]['状態'], '申請中')

    def test_予約できる日が0件でも予約画面が開く(self):
        # 承認前＝0件。ここで500やJSエラーになると、日程調整中に穴が空く
        r = self.c.get('/book/SP-A')
        self.assertEqual(r.status_code, 200)
        self.assertIn('いまお選びいただける日程がありません', r.get_data(as_text=True))

    def test_全コースの予約画面が開く(self):
        booking.set_state(self.inst['id'], '承認')
        for c in booking.COURSES:
            with self.subTest(course=c['code']):
                r = self.c.get('/book/' + c['code'])
                self.assertEqual(r.status_code, 200)
                body = r.get_data(as_text=True)
                self.assertNotIn('Internal Server Error', body)

    def test_知らないコースは404(self):
        self.assertEqual(self.c.get('/book/そんなコース').status_code, 404)

    def test_講師の予定画面は正しい鍵でしか開かない(self):
        self.assertEqual(
            self.c.get('/instructor/schedule/' + self.inst['鍵']).status_code, 200)
        self.assertEqual(self.c.get('/instructor/schedule/でたらめ').status_code, 404)

    def test_承認画面は合言葉がなければ開かない(self):
        self.assertIn(self.c.get('/admin/instructors').status_code, (403, 503))

    def test_承認画面は合言葉があれば開く(self):
        r = self.c.get('/admin/instructors?token=test-admin')
        self.assertEqual(r.status_code, 200)
        self.assertIn('山田 太郎', r.get_data(as_text=True))

    def test_承認のAPIは合言葉がなければ動かない(self):
        r = self.c.post('/api/instructor/decide',
                        json={'id': self.inst['id'], 'state': '承認'})
        self.assertEqual(r.status_code, 403)
        self.assertEqual(booking.instructors()[0]['状態'], '申請中')

    def test_存在しないIDの承認は404で断る(self):
        r = self.c.post('/api/instructor/decide',
                        json={'id': 'でたらめ', 'state': '承認'},
                        headers={'X-Admin-Token': 'test-admin'})
        self.assertEqual(r.status_code, 404)

    def test_知らない状態には変えられない(self):
        r = self.c.post('/api/instructor/decide',
                        json={'id': self.inst['id'], 'state': '勝手な状態'},
                        headers={'X-Admin-Token': 'test-admin'})
        self.assertEqual(r.status_code, 400)


class Test申込のAPI(unittest.TestCase):
    def setUp(self):
        _clear()
        app.logger.disabled = True
        self.c = app.test_client()
        i, _ = booking.register_instructor('山田', 'y@example.com', '', ['SP-A'],
                                          '', _weekly_all_days())
        booking.set_state(i['id'], '承認')
        antispam._RECENT.clear()

    def _payload(self, **kw):
        d = {'course': 'SP-A', 'day': _far_day(), 'name': '鈴木 花子',
             'email': 's@example.com', 'company': '', 'people': 2, 'message': '',
             antispam.HONEYPOT_FIELD: '',
             'ts': antispam.issue_token(now=__import__('time').time() - 6)}
        d.update(kw)
        return d

    def test_申し込める(self):
        r = self.c.post('/api/book', json=self._payload())
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True))
        self.assertTrue(r.get_json().get('ok'))
        self.assertEqual(len(booking.bookings()), 1)

    def test_スパム対策で弾かれた申込は台帳に入れない(self):
        antispam._RECENT.clear()
        r = self.c.post('/api/book',
                        json=self._payload(**{antispam.HONEYPOT_FIELD: 'http://spam'}))
        # ボットに弾いたと教えないので画面は成功と同じでよいが、台帳は汚さない
        self.assertEqual(len(booking.bookings()), 0, r.get_data(as_text=True))

    def test_締切内の日はエラーを返す(self):
        antispam._RECENT.clear()
        soon = (date.today() + timedelta(days=1)).isoformat()
        r = self.c.post('/api/book', json=self._payload(day=soon))
        self.assertEqual(r.status_code, 400)
        self.assertEqual(len(booking.bookings()), 0)

    def test_メールが飛ばなくても申込は残る(self):
        # ⛔ メール送信が唯一の記録手段だと、障害のとき申込が痕跡ごと消える
        antispam._RECENT.clear()
        self.assertFalse(os.environ.get('RESEND_API_KEY'))
        r = self.c.post('/api/book', json=self._payload())
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(booking.bookings()), 1)


class Test台帳の整合(unittest.TestCase):
    def test_全コースに最少催行と定員と金額がある(self):
        for c in booking.COURSES:
            with self.subTest(course=c['code']):
                self.assertGreater(c['price'], 0)
                self.assertGreaterEqual(c['capacity'], c['min_people'])
                self.assertGreater(c['min_people'], 0)

    def test_コードが重複していない(self):
        codes = [c['code'] for c in booking.COURSES]
        self.assertEqual(len(codes), len(set(codes)))

    def test_支払いとキャンセルの条件が空でない(self):
        # 有料講座で、画面に必ず出す約束（空欄で世に出さない）
        self.assertTrue(booking.PAY_NOTE.strip())
        self.assertTrue(booking.CANCEL_POLICY.strip())


class Test予約への導線(unittest.TestCase):
    """/solo-ceo から予約ページに辿り着けるか。

    ⛔ 日程が0件のときに予約へ誘導しないこと（押した先が行き止まりになる）。
    ⛔ 開催日を手打ちの文字列で持たないこと（講師のカレンダーだけが出どころ）。
    """

    def setUp(self):
        _clear()
        app.logger.disabled = True
        self.c = app.test_client()

    def _approve(self, courses=('SP-A',)):
        i, _ = booking.register_instructor(
            '山田', 'y@example.com', '', list(courses), '', _weekly_all_days())
        booking.set_state(i['id'], '承認')
        return i

    def test_日程がないときは予約へ誘導しない(self):
        top = self.c.get('/solo-ceo').get_data(as_text=True)
        self.assertNotIn('開催日を見て申し込む', top)
        self.assertIn('無料で相談する', top)
        detail = self.c.get('/solo-ceo/course-spa').get_data(as_text=True)
        self.assertNotIn('開催日を見て申し込む', detail)

    def test_日程があればトップとカードと詳細の3か所から行ける(self):
        self._approve()
        top = self.c.get('/solo-ceo').get_data(as_text=True)
        self.assertIn('開催日を見て申し込む', top)
        self.assertIn('/book/SP-A', top)
        detail = self.c.get('/solo-ceo/course-spa').get_data(as_text=True)
        self.assertIn('/book/SP-A', detail)

    def test_担当していないコースには予約ボタンを出さない(self):
        self._approve(['SP-A'])
        body = self.c.get('/solo-ceo/course-spc').get_data(as_text=True)
        self.assertNotIn('開催日を見て申し込む', body)

    def test_開催日は手打ちではなくカレンダーから出す(self):
        # ⛔ next_date のような手打ちの欄を復活させないこと
        import solo_ceo
        for c in solo_ceo.COURSES.values():
            self.assertNotIn('next_date', c, c['code'])

    def test_開催日の表示がカレンダーと一致する(self):
        self._approve()
        s = solo_ceo_summary('SP-A')
        days = [d for d in booking.open_days('SP-A') if d['状態'] == '予約可']
        self.assertEqual(s['件数'], len(days))
        self.assertEqual(s['最短'], days[0]['日付'])
        body = self.c.get('/solo-ceo').get_data(as_text=True)
        self.assertIn(s['表示'], body)

    def test_日程がなければ調整中と出す(self):
        # ⛔ 空欄にしないこと（日程が見つからないと問い合わせ前に離脱する）
        self.assertEqual(solo_ceo_summary('SP-A')['表示'], '調整中')
        self.assertIn('調整中', self.c.get('/solo-ceo').get_data(as_text=True))

    def test_カレンダーが壊れていてもコース紹介は開く(self):
        # 紹介ページは予約より上位の役目。ここが落ちると集客が止まる
        import solo_ceo
        orig = booking.open_days
        booking.open_days = lambda *a, **k: (_ for _ in ()).throw(RuntimeError('故障'))
        try:
            self.assertEqual(self.c.get('/solo-ceo').status_code, 200)
            self.assertEqual(self.c.get('/solo-ceo/course-spa').status_code, 200)
            self.assertEqual(solo_ceo.booking_summary('SP-A')['表示'], '調整中')
        finally:
            booking.open_days = orig


class Test外向きURL(unittest.TestCase):
    """講師にお送りするURLが https になること。

    ⛔ Railway のプロキシ配下では素の Flask が http と判断する。
       講師に配るURLが http:// だとコピーして使えない（2026-08-09 実測）。
    """

    def setUp(self):
        _clear()
        app.logger.disabled = True
        self.c = app.test_client()
        self.inst, _ = booking.register_instructor(
            '山田', 'y@example.com', '', ['SP-A'], '', _weekly_all_days())

    def _hdr(self):
        return {'X-Admin-Token': 'test-admin',
                'X-Forwarded-Proto': 'https',
                'X-Forwarded-Host': 'www.jgaia.org'}

    def test_一覧APIのURLがhttpsになる(self):
        d = self.c.get('/api/instructors', headers=self._hdr()).get_json()
        self.assertTrue(d['登録URL'].startswith('https://'), d['登録URL'])
        self.assertTrue(d['rows'][0]['予定URL'].startswith('https://'),
                        d['rows'][0]['予定URL'])

    def test_登録完了画面のURLもhttpsになる(self):
        body = self.c.get('/admin/instructors', headers=self._hdr(),
                          query_string={'token': 'test-admin'}).get_data(as_text=True)
        self.assertIn('https://www.jgaia.org/instructor/', body)
        self.assertNotIn('http://www.jgaia.org/instructor/', body)


if __name__ == '__main__':
    unittest.main(verbosity=2)
