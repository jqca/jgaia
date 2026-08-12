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


def _days_all(start='10:00', end='17:00', span=120):
    """今日から span 日ぶん、毎日その時間帯で講義できる、という登録内容。

    予定は日付ごとの枠だけが正（2026-08-11〜）。曜日の決まりは持たない。
    """
    d0 = date.today()
    return {(d0 + timedelta(days=i)).isoformat(): [{'開始': start, '終了': end}]
            for i in range(span)}


def _weekly_all_days():
    """旧形式（曜日の決まり）。移行の読み取り互換を確かめるためだけに残す。"""
    return [{'曜日': i, '開始': '10:00', '終了': '17:00'} for i in range(7)]


def _far_day(offset=30):
    return (date.today() + timedelta(days=offset)).isoformat()


class Test講師の登録(unittest.TestCase):
    def setUp(self):
        _clear()

    def test_登録した時点では必ず申請中(self):
        r, token = booking.register_instructor('山田 太郎', 'y@example.com', '',
                                              ['SP-A'], '', _days_all())
        self.assertEqual(r['状態'], '申請中')

    def test_本人用の鍵が推測できない長さである(self):
        r, token = booking.register_instructor('山田', 'y@example.com', '', ['SP-A'],
                                              '', _days_all())
        # この鍵だけで予定を書き換えられるので、短いと総当たりされる
        self.assertGreaterEqual(len(r['鍵']), 16)
        self.assertEqual(r['鍵'], token)

    def test_鍵は講師ごとに違う(self):
        a, _ = booking.register_instructor('A', 'a@example.com', '', ['SP-A'], '',
                                          _days_all())
        b, _ = booking.register_instructor('B', 'b@example.com', '', ['SP-A'], '',
                                          _days_all())
        self.assertNotEqual(a['鍵'], b['鍵'])

    def test_担当できる講座を選んでいない登録は受け取らない(self):
        with self.assertRaises(ValueError):
            booking.register_instructor('山田', 'y@example.com', '', [], '',
                                        _days_all())


class Test承認するまで公開しない(unittest.TestCase):
    def setUp(self):
        _clear()
        self.inst, _ = booking.register_instructor(
            '山田 太郎', 'y@example.com', '', ['SP-A'], '', _days_all())

    def test_申請中の講師の日は予約可にならない(self):
        days = {d['日付']: d['状態'] for d in booking.open_days('SP-A')}
        self.assertNotIn('予約可', set(days.values()))

    def test_承認したら予約可の日が出る(self):
        booking.verify_email(self.inst['鍵'])
        booking.set_state(self.inst['id'], '承認')
        days = [d for d in booking.open_days('SP-A') if d['状態'] == '予約可']
        self.assertTrue(days)

    def test_見送りに戻すと公開が止まる(self):
        booking.verify_email(self.inst['鍵'])
        booking.set_state(self.inst['id'], '承認')
        booking.set_state(self.inst['id'], '見送り')
        days = {d['状態'] for d in booking.open_days('SP-A')}
        self.assertNotIn('予約可', days)

    def test_存在しないIDの承認は成功にしない(self):
        # ⛔ ここが True を返すと、運営が押しても何も変わらないのに成功に見える
        self.assertFalse(booking.set_state('存在しないID', '承認'))

    def test_担当できない講座には出てこない(self):
        booking.verify_email(self.inst['鍵'])
        booking.set_state(self.inst['id'], '承認')
        days = {d['状態'] for d in booking.open_days('SP-C')}
        self.assertNotIn('予約可', days)


class Test日数の下限(unittest.TestCase):
    def setUp(self):
        _clear()
        i, _ = booking.register_instructor('山田', 'y@example.com', '', ['SP-A'],
                                          '', _days_all())
        booking.verify_email(i['鍵'])
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
            '山田', 'y@example.com', '', ['SP-A'], '', _days_all())
        booking.verify_email(self.inst['鍵'])
        booking.set_state(self.inst['id'], '承認')

    def _without(self, *isos):
        """その日だけ外した予定を作る（日を閉じる＝その日付を持たないこと）"""
        days = _days_all()
        for iso in isos:
            days.pop(iso, None)
        return days

    def test_外した日は予約締切になる(self):
        d = _far_day()
        booking.update_availability(self.inst['鍵'], self._without(d))
        info = {x['日付']: x for x in booking.open_days('SP-A')}[d]
        self.assertEqual(info['状態'], '予約締切')

    def test_外した日は申込も断る(self):
        d = _far_day()
        booking.update_availability(self.inst['鍵'], self._without(d))
        with self.assertRaises(ValueError):
            booking.add_booking('SP-A', d, '鈴木', 's@example.com', '', 1, '')

    def test_他人の鍵では書き換えられない(self):
        self.assertIsNone(booking.update_availability('でたらめな鍵', _days_all()))

    def test_予約が入った日は講師が閉じられない(self):
        d = _far_day()
        booking.add_booking('SP-A', d, '鈴木', 's@example.com', '', 1, '')
        booking.update_availability(self.inst['鍵'], self._without(d))
        # 受講者と約束した日を、あとから一方的に消せてはいけない
        self.assertIn(d, booking.booked_days_for_instructor(self.inst['id']))
        self.assertIn(d, booking.instructors()[0]['講義できる日時'])
        # 定員までは追加の申込を受ける（最少催行に人を集める必要がある）
        info = {x['日付']: x for x in booking.open_days('SP-A')}[d]
        self.assertEqual(info['状態'], '予約可')

    def test_予約済みの日は予定を空にしても申込を受けられる(self):
        # ⛔ 1人目が入った日を講師が外した瞬間に2人目が申し込めなくなると、
        #    最少催行に届かず開催できない（申込は残っているのに）
        d = _far_day()
        booking.add_booking('SP-A', d, 'A', 'a@example.com', '', 1, '')
        booking.update_availability(self.inst['鍵'], {})
        r, _ = booking.add_booking('SP-A', d, 'B', 'b@example.com', '', 1, '')
        self.assertEqual(r['_合計人数'], 2)

    def test_定員に達した日は予約締切として出す(self):
        d = _far_day()
        cap = booking.COURSE_BY_CODE['SP-A']['capacity']
        booking.add_booking('SP-A', d, 'A', 'a@example.com', '', cap, '')
        info = {x['日付']: x for x in booking.open_days('SP-A')}[d]
        self.assertEqual(info['状態'], '予約締切')
        self.assertEqual(info['残り'], 0)

    def test_日を1つも選ばなければ公開されない(self):
        booking.update_availability(self.inst['鍵'], {})
        states = {d['状態'] for d in booking.open_days('SP-A')}
        self.assertNotIn('予約可', states)


class Test申込(unittest.TestCase):
    def setUp(self):
        _clear()
        i, _ = booking.register_instructor('山田', 'y@example.com', '', ['SP-A'],
                                          '', _days_all())
        booking.verify_email(i['鍵'])
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
            '山田 太郎', 'y@example.com', '', ['SP-A'], '', _days_all())

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
        booking.verify_email(self.inst['鍵'])
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
                                          '', _days_all())
        booking.verify_email(i['鍵'])
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
            '山田', 'y@example.com', '', list(courses), '', _days_all())
        booking.verify_email(i['鍵'])
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
            '山田', 'y@example.com', '', ['SP-A'], '', _days_all())

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


class Test講義できる日時(unittest.TestCase):
    """予定は「日付ごとの枠」だけが正（2026-08-11 社長ご指摘）。

    ご指摘は2段階だった:
      ・曜日×1つの時間帯では、週ごとの変動も1日2枠も表せない
      ・そもそも曜日で登録させるのが面倒＝日付で選ばせればいい

    固定している事故の型:
      ① 夜間コース（水19:00〜21:30）に、昼しか登録していない講師が割り当たる
         ＝登録させた時間帯を判定に1か所も使っていなかった
      ② 予定の正が2つ（曜日の決まり／日付の例外）になり、答えが割れる
      ③ 予約が入った日を、あとから閉じたり時間をずらしたりできてしまう
    """

    def setUp(self):
        _clear()

    def _reg(self, days, courses=('SP-A',)):
        i, t = booking.register_instructor('山田', 'y@example.com', '',
                                           list(courses), '', days)
        booking.verify_email(i['鍵'])
        booking.set_state(i['id'], '承認')
        return booking.find_instructor(t), t

    def _states(self, code):
        return {d['日付']: d['状態'] for d in booking.open_days(code)}

    # ── 開催時間の読み取り
    def test_コースの開催時間は掲載値から解く(self):
        self.assertEqual(booking.course_hours('SP-A'), ('10:00', '17:00'))
        self.assertEqual(booking.course_hours('SP-C'), ('19:00', '21:30'))
        # 「10:00〜17:00 × 3日間」でも先頭の時間帯を読む
        self.assertEqual(booking.course_hours('SP-B'), ('10:00', '17:00'))

    # ── ① 時間帯を実際に使う
    def test_昼しか登録していない講師に夜間コースを割り当てない(self):
        self._reg(_days_all(), ['SP-C'])                 # 10:00〜17:00
        self.assertNotIn('予約可', set(self._states('SP-C').values()))
        # 申込そのものも通さない（画面だけ塞いでAPIが空いている状態にしない）
        with self.assertRaises(ValueError):
            booking.add_booking('SP-C', _far_day(), '鈴木', 's@example.com',
                                '', 1, '')

    def test_夜の枠を足せば夜間コースを受けられる(self):
        days = _days_all()
        for k in days:
            days[k] = days[k] + [{'開始': '19:00', '終了': '22:00'}]
        self._reg(days, ['SP-C'])
        self.assertIn('予約可', set(self._states('SP-C').values()))

    def test_開催時間ぴったりの枠は担当できる(self):
        # 19:00〜21:30 に対し 19:00〜21:30。境界を「含まない」と読まないこと
        self._reg(_days_all('19:00', '21:30'), ['SP-C'])
        self.assertIn('予約可', set(self._states('SP-C').values()))

    # ── 日付ごとに違う時間・1日に複数の枠
    def test_1日に朝と夜の2枠を持てる(self):
        day = _far_day()
        inst, _ = self._reg({day: [{'開始': '10:00', '終了': '13:00'},
                                   {'開始': '18:00', '終了': '21:00'}]})
        self.assertEqual(booking.slots_on(inst, date.fromisoformat(day)),
                         [{'開始': '10:00', '終了': '13:00'},
                          {'開始': '18:00', '終了': '21:00'}])

    def test_同じ曜日でも日によって時間を変えられる(self):
        a, b = _far_day(30), _far_day(37)      # 同じ曜日の別の週
        self.assertEqual(date.fromisoformat(a).weekday(),
                         date.fromisoformat(b).weekday())
        inst, _ = self._reg({a: [{'開始': '10:00', '終了': '17:00'}],
                             b: [{'開始': '19:00', '終了': '22:00'}]},
                            ['SP-A'])
        st = self._states('SP-A')
        self.assertEqual(st[a], '予約可')       # 昼のコースを受けられる
        self.assertEqual(st[b], '予約締切')     # 同じ曜日でも夜だけなので受けない

    def test_選んでいない日は講義しない日になる(self):
        day = _far_day()
        inst, _ = self._reg({day: [{'開始': '10:00', '終了': '17:00'}]})
        st = self._states('SP-A')
        self.assertEqual(st[day], '予約可')
        self.assertEqual(st[_far_day(31)], '予約締切')

    # ── ② 正を2つ持たない
    def test_保存すると曜日の決まりは台帳から消える(self):
        # ⛔ 旧欄を残すと「予定の正がどれか」が2つになる
        i, token = booking.register_instructor('山田', 'y@example.com', '',
                                               ['SP-A'], '')
        rows = booking.instructors()
        rows[0]['毎週の可能時間'] = _weekly_all_days()
        rows[0]['不可の日'] = [_far_day()]
        rows[0]['日別の可能時間'] = {_far_day(40): [{'開始': '19:00', '終了': '22:00'}]}
        del rows[0]['講義できる日時']
        booking._save('instructors.json', rows)
        r = booking.update_availability(token, _days_all())
        for old in ('毎週の可能時間', '不可の日', '日別の可能時間'):
            self.assertNotIn(old, r)
        self.assertTrue(r['講義できる日時'])

    # ── ③ 約束した日は動かせない
    def test_予約が入っている日は時間も変えられない(self):
        inst, token = self._reg(_days_all())
        day = _far_day()
        booking.add_booking('SP-A', day, '鈴木', 's@example.com', '', 1, '')
        days = _days_all()
        days[day] = [{'開始': '19:00', '終了': '22:00'}]
        r = booking.update_availability(token, days)
        # ⛔ 受講者に案内済みの開始時刻を後からずらせないこと
        self.assertEqual(r['講義できる日時'][day],
                         [{'開始': '10:00', '終了': '17:00'}])

    # ── 保存できない値を通さない
    def test_終了が開始より前の枠は保存しない(self):
        inst, token = self._reg(_days_all())
        day = _far_day()
        r = booking.update_availability(token, {
            day: [{'開始': '18:00', '終了': '09:00'},
                  {'開始': '10:00', '終了': '17:00'}]})
        self.assertEqual(r['講義できる日時'][day],
                         [{'開始': '10:00', '終了': '17:00'}])

    def test_まったく同じ枠は1本に畳む(self):
        # ⛔ 講師には「押した回数だけ増える」壊れ方に見える（2026-08-11 実機で発生）
        inst, token = self._reg(_days_all())
        day = _far_day()
        r = booking.update_availability(token, {
            day: [{'開始': '18:00', '終了': '21:00'},
                  {'開始': '18:00', '終了': '21:00'},
                  {'開始': '10:00', '終了': '13:00'}]})
        self.assertEqual(r['講義できる日時'][day],
                         [{'開始': '10:00', '終了': '13:00'},
                          {'開始': '18:00', '終了': '21:00'}])

    def test_空の枠しかない日は保存しない(self):
        # 日を閉じる＝その日付を持たないこと（同じ意味を2通りで書けないように）
        inst, token = self._reg(_days_all())
        r = booking.update_availability(token, {_far_day(): []})
        self.assertEqual(r['講義できる日時'], {})

    def test_日付として読めない鍵は捨てる(self):
        inst, token = self._reg(_days_all())
        r = booking.update_availability(token, {'いつか': [{'開始': '10:00',
                                                           '終了': '17:00'}]})
        self.assertEqual(r['講義できる日時'], {})

    # ── 移行（2026-08-11 より前に登録された講師）
    def test_旧式の曜日登録でもこれまでどおり予約できる(self):
        i, token = booking.register_instructor('山田', 'y@example.com', '',
                                               ['SP-A'], '')
        booking.verify_email(i['鍵'])
        booking.set_state(i['id'], '承認')
        rows = booking.instructors()
        rows[0]['毎週の可能時間'] = _weekly_all_days()
        rows[0]['不可の日'] = []
        del rows[0]['講義できる日時']          # 旧式のレコードを再現する
        booking._save('instructors.json', rows)
        self.assertIn('予約可', set(self._states('SP-A').values()))

    def test_旧式の予定を日付に展開して見せられる(self):
        i, token = booking.register_instructor('山田', 'y@example.com', '',
                                               ['SP-A'], '')
        rows = booking.instructors()
        rows[0]['毎週の可能時間'] = [{'曜日': 5, '開始': '10:00', '終了': '17:00'}]
        rows[0]['不可の日'] = []
        del rows[0]['講義できる日時']
        booking._save('instructors.json', rows)
        inst = booking.find_instructor(token)
        start = date.today()
        got = booking.materialize(inst, start, start + timedelta(days=20))
        self.assertTrue(got)
        self.assertTrue(all(date.fromisoformat(k).weekday() == 5 for k in got))
        # ⛔ 見せるだけ。台帳は書き換わらない（本人が保存したときに移る）
        self.assertIsNone(booking.instructors()[0].get('講義できる日時'))

    def test_登録されている予定の最終日を出せる(self):
        inst, _ = self._reg({_far_day(20): [{'開始': '10:00', '終了': '17:00'}],
                             _far_day(50): [{'開始': '10:00', '終了': '17:00'}]})
        self.assertEqual(booking.availability_end(inst), _far_day(50))


class Test予定の画面(unittest.TestCase):
    def setUp(self):
        _clear()
        app.logger.disabled = True
        self.c = app.test_client()

    def test_登録フォームは予定を聞かない(self):
        # ⛔ 曜日の欄を戻さないこと（日付はカレンダー画面で選ぶ）
        html = self.c.get('/instructor/register').get_data(as_text=True)
        self.assertNotIn('name="wd0"', html)
        self.assertNotIn('毎週、講義できる曜日と時間', html)
        self.assertIn('カレンダー', html)

    def test_予定を出さずに登録できて予定画面に進める(self):
        antispam._RECENT.clear()
        r = self.c.post('/instructor/register', data={
            'name': '佐藤', 'email': 's@example.com', 'courses': ['SP-A'],
            'note': '', antispam.HONEYPOT_FIELD: '',
            'ts': antispam.issue_token(now=time.time() - 6)})
        self.assertEqual(r.status_code, 200)
        rec = booking.instructors()[-1]
        self.assertEqual(rec['講義できる日時'], {})
        self.assertIn('/instructor/schedule/' + rec['鍵'],
                      r.get_data(as_text=True))

    def test_APIで日付ごとの予定を保存できる(self):
        i, token = booking.register_instructor('山田', 'y@example.com', '',
                                               ['SP-A'], '')
        day = _far_day()
        r = self.c.post('/api/instructor/schedule', json={
            'token': token,
            'days': {day: [{'開始': '10:00', '終了': '13:00'},
                           {'開始': '18:00', '終了': '21:00'}]}})
        self.assertEqual(r.status_code, 200)
        # ⛔ 送った内容ではなく保存された内容を返すこと（画面がそれを写す）
        self.assertEqual(r.get_json()['days'][day],
                         [{'開始': '10:00', '終了': '13:00'},
                          {'開始': '18:00', '終了': '21:00'}])

    def test_予定画面にカレンダーとコースの開催時間を出す(self):
        i, token = booking.register_instructor('山田', 'y@example.com', '',
                                               ['SP-C'], '')
        body = self.c.get('/instructor/schedule/' + token).get_data(as_text=True)
        self.assertIn('講義できる日を選ぶ', body)
        self.assertIn('19:00', body)          # 夜間コースの開催時間
        self.assertNotIn('毎週の可能時間', body)


class Test公開されない理由(unittest.TestCase):
    """承認したのに日程が出ない、を画面で説明できるようにする。

    ⛔ 2026-08-12 実害：承認済みの講師が 8/26 に「10:00〜11:00」「13:00〜14:00」
       だけを登録していた。コースは終日（10:00〜17:00）なので担当できず、
       予約カレンダーには1日も出なかった。判定は正しいが、本人にも運営にも
       その理由がどこにも出ていなかった。
    """

    def setUp(self):
        _clear()

    def _reg(self, days, courses=('SP-A',), approve=True):
        i, t = booking.register_instructor('山田', 'y@example.com', '',
                                           list(courses), '', days)
        if approve:
            booking.verify_email(t)
            booking.set_state(i['id'], '承認')
        return booking.find_instructor(t), t

    def test_短い枠しか無ければ担当できる講座は0(self):
        inst, _ = self._reg({_far_day(): [{'開始': '10:00', '終了': '11:00'},
                                          {'開始': '13:00', '終了': '14:00'}]})
        self.assertEqual(booking.teachable_courses(inst), [])
        理由 = booking.publish_blockers(inst)
        self.assertTrue(any('担当できる講座がありません' in b for b in 理由), 理由)
        # 実際に公開もされない（判定と説明が食い違わないこと）
        self.assertNotIn('予約可', {d['状態'] for d in booking.open_days('SP-A')})

    def test_通しの枠があれば理由は出ない(self):
        inst, _ = self._reg({_far_day(): [{'開始': '10:00', '終了': '17:00'}]})
        self.assertEqual(booking.teachable_courses(inst), ['SP-A'])
        self.assertEqual(booking.publish_blockers(inst), [])
        self.assertIn('予約可', {d['状態'] for d in booking.open_days('SP-A')})

    def test_一部の講座だけ担当できないときはそう言う(self):
        # 昼だけ＝SP-A は担当できるが、夜間の SP-C は担当できない
        inst, _ = self._reg({_far_day(): [{'開始': '10:00', '終了': '17:00'}]},
                            ['SP-A', 'SP-C'])
        self.assertEqual(booking.teachable_courses(inst), ['SP-A'])
        理由 = booking.publish_blockers(inst)
        self.assertTrue(any('一部の講座' in b and 'SP-C' in b for b in 理由), 理由)

    def test_日が1日も無ければそう言う(self):
        inst, _ = self._reg({})
        self.assertIn('講義できる日が1日も登録されていません',
                      booking.publish_blockers(inst))

    def test_締切より手前の日しか無ければそう言う(self):
        soon = (date.today() + timedelta(days=3)).isoformat()
        inst, _ = self._reg({soon: [{'開始': '10:00', '終了': '17:00'}]})
        self.assertTrue(any('日以内です' in b
                            for b in booking.publish_blockers(inst)))

    def test_未承認と未確認も理由として出す(self):
        inst, t = self._reg({_far_day(): [{'開始': '10:00', '終了': '17:00'}]},
                            approve=False)
        理由 = booking.publish_blockers(inst)
        self.assertTrue(any('承認されていません' in b for b in 理由), 理由)
        self.assertTrue(any('確認が済んでいません' in b for b in 理由), 理由)

    def test_保存の返事に公開されない理由が入る(self):
        app.logger.disabled = True
        c = app.test_client()
        inst, token = self._reg({})
        j = c.post('/api/instructor/schedule', json={
            'token': token,
            'days': {_far_day(): [{'開始': '10:00', '終了': '11:00'}]}}).get_json()
        # ⛔ 「保存しました」だけを返さないこと（公開されたつもりで待ち続ける）
        self.assertTrue(j['ok'])
        self.assertTrue(any('担当できる講座がありません' in b
                            for b in j['公開されない理由']), j)

    def test_予定画面と承認画面に理由を出す(self):
        app.logger.disabled = True
        c = app.test_client()
        inst, token = self._reg({_far_day(): [{'開始': '10:00', '終了': '11:00'}]})
        body = c.get('/instructor/schedule/' + token).get_data(as_text=True)
        self.assertIn('受講者に日程が公開されません', body)
        admin = c.get('/admin/instructors', headers={'X-Admin-Token': 'test-admin'},
                      query_string={'token': 'test-admin'}).get_data(as_text=True)
        self.assertIn('受講者には公開されていません', admin)


class Test登録からの流れ(unittest.TestCase):
    """登録 → 仮登録メール → 確認リンク → カレンダー → 承認 → 公開。

    ⛔ 2026-08-11 の実測では、この経路にメールが1通も無かった。
       打ち間違いのアドレスでも登録が成立し、画面を閉じたら本人は
       二度と日程を入れられず、運営も新規申請に気づけなかった。
    """

    def setUp(self):
        _clear()
        app.logger.disabled = True
        self.c = app.test_client()

    def _register(self, email='y@example.com'):
        antispam._RECENT.clear()
        r = self.c.post('/instructor/register', data={
            'name': '山田', 'email': email, 'courses': ['SP-A'], 'note': '',
            antispam.HONEYPOT_FIELD: '',
            'ts': antispam.issue_token(now=time.time() - 6)})
        return r, booking.instructors()[-1]

    def test_登録した時点ではメール未確認(self):
        _, rec = self._register()
        self.assertIsNone(rec['メール確認済み'])

    def test_確認リンクを踏むまで承認しても公開されない(self):
        _, rec = self._register()
        booking.update_availability(rec['鍵'], _days_all())
        booking.set_state(rec['id'], '承認')
        # ⛔ 届かないアドレスの講師を公開しない（当日に誰も来ない事故になる）
        self.assertNotIn('予約可', {d['状態'] for d in booking.open_days('SP-A')})
        self.assertEqual(booking.approved_instructors(), [])

    def test_確認リンクを踏むと公開されカレンダーに送られる(self):
        _, rec = self._register()
        booking.update_availability(rec['鍵'], _days_all())
        booking.set_state(rec['id'], '承認')
        r = self.c.get('/instructor/verify/' + rec['鍵'])
        self.assertEqual(r.status_code, 302)
        self.assertIn('/instructor/schedule/' + rec['鍵'], r.headers['Location'])
        self.assertIn('verified=1', r.headers['Location'])
        self.assertTrue(booking.instructors()[-1]['メール確認済み'])
        self.assertIn('予約可', {d['状態'] for d in booking.open_days('SP-A')})

    def test_確認は何度踏んでも最初の日時を残す(self):
        _, rec = self._register()
        first = booking.verify_email(rec['鍵'])['メール確認済み']
        self.assertEqual(booking.verify_email(rec['鍵'])['メール確認済み'], first)

    def test_でたらめな鍵の確認リンクは404(self):
        self._register()
        self.assertEqual(self.c.get('/instructor/verify/でたらめ').status_code, 404)

    def test_未確認の講師には予定画面で知らせる(self):
        _, rec = self._register()
        body = self.c.get('/instructor/schedule/' + rec['鍵']).get_data(as_text=True)
        self.assertIn('メールアドレスの確認がまだ済んでいません', body)
        booking.verify_email(rec['鍵'])
        body = self.c.get('/instructor/schedule/' + rec['鍵']).get_data(as_text=True)
        self.assertNotIn('メールアドレスの確認がまだ済んでいません', body)

    def test_メールが送れなくても登録は成立し画面にURLを出す(self):
        # ⛔ 送信できない環境（RESEND_API_KEY 未設定）でも登録を失わないこと。
        #    ただし黙らない＝画面に「送れなかった」と出し、専用URLを見せる
        r, rec = self._register()
        body = r.get_data(as_text=True)
        self.assertEqual(r.status_code, 200)
        self.assertIn('確認メールをお送りできませんでした', body)
        self.assertIn('/instructor/schedule/' + rec['鍵'], body)

    def test_承認の結果は本人に伝える口がある(self):
        _, rec = self._register()
        r = self.c.post('/api/instructor/decide',
                        json={'id': rec['id'], 'state': '承認'},
                        headers={'X-Admin-Token': 'test-admin'})
        j = r.get_json()
        self.assertTrue(j['ok'])
        # 送信手段が無いので False。⛔ 送れたかを黙らないこと
        self.assertIs(j['通知'], False)
        # ⛔ 承認したのに公開されない理由を、押した運営にその場で伝える
        self.assertIn('メールの確認', j['警告'])

    def test_確認済みなら承認時に警告を出さない(self):
        _, rec = self._register()
        booking.verify_email(rec['鍵'])
        j = self.c.post('/api/instructor/decide',
                        json={'id': rec['id'], 'state': '承認'},
                        headers={'X-Admin-Token': 'test-admin'}).get_json()
        self.assertNotIn('警告', j)

    def test_再送は運営の合言葉が要る(self):
        _, rec = self._register()
        self.assertEqual(
            self.c.post('/api/instructor/resend', json={'id': rec['id']}).status_code,
            403)

    def test_再送は送れなければ失敗として返す(self):
        # ⛔ 送れていないのに「再送しました」と出さないこと
        _, rec = self._register()
        r = self.c.post('/api/instructor/resend', json={'id': rec['id']},
                        headers={'X-Admin-Token': 'test-admin'})
        self.assertEqual(r.status_code, 502)

    def test_運営の承認画面にメール確認の状態が出る(self):
        _, rec = self._register()
        body = self.c.get('/admin/instructors',
                          headers={'X-Admin-Token': 'test-admin'},
                          query_string={'token': 'test-admin'}).get_data(as_text=True)
        self.assertIn('メール未確認', body)
        self.assertIn('確認メールを再送する', body)


if __name__ == '__main__':
    unittest.main(verbosity=2)
