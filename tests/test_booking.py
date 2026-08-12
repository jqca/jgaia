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
import re
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


def _days_all(courses=('SP-A',), span=120):
    """今日から span 日ぶん、毎日そのコースを担当する、という登録内容。

    予定は「日付 → その日に担当する講座」だけが正（2026-08-12〜）。
    時間はコースが持っているので、講師が時刻を組むことはない。
    """
    d0 = date.today()
    return {(d0 + timedelta(days=i)).isoformat(): list(courses)
            for i in range(span)}


def _weekly_all_days():
    """旧形式（曜日の決まり）。移行の読み取り互換を確かめるためだけに残す。"""
    return [{'曜日': i, '開始': '10:00', '終了': '17:00'} for i in range(7)]


def _far_day(offset=30):
    return (date.today() + timedelta(days=offset)).isoformat()


def _far_weekday(weekday, offset=20):
    """offset 日より先で、最初にその曜日（月=0）になる日。

    SP-C のように開催曜日が決まっている講座を試すときに使う。
    """
    d = date.today() + timedelta(days=offset)
    while d.weekday() != weekday:
        d += timedelta(days=1)
    return d.isoformat()


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

    def _close(self, iso):
        """その日を外す＝担当する講座を1つも選ばずに確定する"""
        return booking.set_day_courses(self.inst['鍵'], iso, [])

    def test_外した日は予約締切になる(self):
        d = _far_day()
        self._close(d)
        info = {x['日付']: x for x in booking.open_days('SP-A')}[d]
        self.assertEqual(info['状態'], '予約締切')

    def test_外した日は申込も断る(self):
        d = _far_day()
        self._close(d)
        with self.assertRaises(ValueError):
            booking.add_booking('SP-A', d, '鈴木', 's@example.com', '', 1, '')

    def test_他人の鍵では書き換えられない(self):
        inst, err = booking.set_day_courses('でたらめな鍵', _far_day(), ['SP-A'])
        self.assertIsNone(inst)
        self.assertTrue(err)

    def test_予約が入った日は講師が閉じられない(self):
        d = _far_day()
        booking.add_booking('SP-A', d, '鈴木', 's@example.com', '', 1, '')
        inst, err = self._close(d)
        # 受講者と約束した日を、あとから一方的に消せてはいけない
        self.assertIsNone(inst)
        self.assertIn('予約が入っている', err)
        self.assertIn(d, booking.instructors()[0]['担当できる日'])
        # 定員までは追加の申込を受ける（最少催行に人を集める必要がある）
        info = {x['日付']: x for x in booking.open_days('SP-A')}[d]
        self.assertEqual(info['状態'], '予約可')

    def test_予約済みの日は他の日を空にしても申込を受けられる(self):
        # ⛔ 1人目が入った日を講師が外した瞬間に2人目が申し込めなくなると、
        #    最少催行に届かず開催できない（申込は残っているのに）
        d = _far_day()
        booking.add_booking('SP-A', d, 'A', 'a@example.com', '', 1, '')
        for iso in list(booking.registered_days(self.inst)):
            if iso != d:
                booking.set_day_courses(self.inst['鍵'], iso, [])
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
        for iso in list(booking.registered_days(self.inst)):
            booking.set_day_courses(self.inst['鍵'], iso, [])
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

    def test_講座と開催時間を1か所に出す(self):
        # ⛔ 同じ講座の情報を2つのカードに割らないこと（2026-08-12 社長ご指摘）
        html = self.c.get('/instructor/register').get_data(as_text=True)
        self.assertNotIn('担当できるコースの開催時間', html)
        i = html.index('name="courses" value="SP-A"')
        self.assertIn('10:00〜17:00', html[i:i + 400])

    def test_見出しの日数が欠けない(self):
        # ⛔ lead_days の渡し忘れで「開催の日以上前」になる（Jinjaは落ちない）
        want = f'開催の{booking.LEAD_DAYS}日以上前'
        self.assertIn(want, self.c.get('/instructor/register').get_data(as_text=True))
        # 入力もれで戻ってきた画面（⛔スパム対策の欄を入れないと、ここは
        # ボット扱いされて完了画面が返る＝エラー画面を通らない）
        antispam._RECENT.clear()
        r = self.c.post('/instructor/register', data={
            'name': '', 'email': '', antispam.HONEYPOT_FIELD: '',
            'ts': antispam.issue_token(now=time.time() - 6)})
        body = r.get_data(as_text=True)
        self.assertIn('お名前とメールアドレスは必須です', body)
        self.assertIn(want, body)

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


class Test担当できる日(unittest.TestCase):
    """予定は「日付 → その日に担当する講座」だけが正（2026-08-12 社長ご指示）。

    社長のご指摘は3段階だった:
      ① 曜日×1つの時間帯では、週ごとの変動も1日2枠も表せない
      ② そもそも曜日で登録させるのが面倒＝日付で選ばせればいい
      ③ 時間帯を自分で組ませる入力が分かりにくい＝その日に担当する
         コースを選ばせればいい（時間はコースが持っている）

    固定している事故の型:
      ・1時間の枠しか登録できておらず、終日のコースを担当できない
        （2026-08-12 実害。承認済みなのに予約カレンダーに1日も出なかった）
      ・予定の正が2つ（曜日／日付／時間帯）になり、画面と実装で答えが割れる
      ・予約が入った日を、あとから閉じたり中身を変えたりできてしまう
      ・同じ日に、開催時間の重なる講座を2つ引き受けてしまう
    """

    def setUp(self):
        _clear()

    def _reg(self, days=None, courses=('SP-A',), approve=True):
        i, t = booking.register_instructor('山田', 'y@example.com', '',
                                           list(courses), '', days or {})
        if approve:
            booking.verify_email(t)
            booking.set_state(i['id'], '承認')
        return booking.find_instructor(t), t

    def _states(self, code):
        return {d['日付']: d['状態'] for d in booking.open_days(code)}

    # ── 時間はコースが持つ
    def test_コースの開催時間は掲載値から解く(self):
        self.assertEqual(booking.course_hours('SP-A'), ('10:00', '17:00'))
        self.assertEqual(booking.course_hours('SP-C'), ('19:00', '21:30'))
        # 「10:00〜17:00 × 3日間」でも先頭の時間帯を読む
        self.assertEqual(booking.course_hours('SP-B'), ('10:00', '17:00'))

    def test_選んだ日にその講座が公開される(self):
        day = _far_day()
        inst, token = self._reg()
        booking.set_day_courses(token, day, ['SP-A'])
        st = self._states('SP-A')
        self.assertEqual(st[day], '予約可')
        self.assertEqual(st[_far_day(31)], '予約締切')   # 選んでいない日

    def test_選んでいない講座は同じ日でも公開されない(self):
        # ⛔ 「時間が同じだから」で別の講座まで公開しないこと。
        #    SP-A と GA は同じ 10:00〜17:00 だが、担当は本人が選ぶもの
        day = _far_day()
        inst, token = self._reg(courses=('SP-A', 'GA'))
        booking.set_day_courses(token, day, ['SP-A'])
        self.assertEqual(self._states('SP-A')[day], '予約可')
        self.assertEqual(self._states('GA')[day], '予約締切')

    def test_同じ日に複数の講座を担当できる(self):
        # 時間が重ならない組み合わせ（昼のSP-Aと夜のSP-C）
        # ⛔ SP-C は毎週水曜の開催なので、水曜で試すこと
        day = _far_weekday(2)
        inst, token = self._reg(courses=('SP-A', 'SP-C'))
        saved, err = booking.set_day_courses(token, day, ['SP-A', 'SP-C'])
        self.assertIsNone(err)
        self.assertEqual(booking.day_courses(saved, date.fromisoformat(day)),
                         ['SP-A', 'SP-C'])

    def test_開催時間が重なる講座は同じ日に受けられない(self):
        # ⛔ 1人が同時刻に2つの講座を担当することはできない（バッティング）
        self.assertTrue(booking.overlapping_courses(['SP-A', 'GA']))
        self.assertFalse(booking.overlapping_courses(['SP-A', 'SP-C']))
        inst, token = self._reg(courses=('SP-A', 'GA'))
        saved, err = booking.set_day_courses(token, _far_day(), ['SP-A', 'GA'])
        self.assertIsNone(saved)
        self.assertIn('重なる', err)

    def test_日によって担当する講座を変えられる(self):
        # 同じ曜日の別の週。⛔ SP-C は毎週水曜×5回なので5週ぶん登録する
        a = _far_weekday(2)
        b = (date.fromisoformat(a) + timedelta(days=7)).isoformat()
        self.assertEqual(date.fromisoformat(a).weekday(),
                         date.fromisoformat(b).weekday())
        inst, token = self._reg(courses=('SP-A', 'SP-C'))
        booking.set_day_courses(token, a, ['SP-A'])
        for iso in booking.course_dates('SP-C', b):
            booking.set_day_courses(token, iso, ['SP-C'])
        self.assertEqual(self._states('SP-A')[a], '予約可')
        self.assertEqual(self._states('SP-A')[b], '予約締切')
        self.assertEqual(self._states('SP-C')[b], '予約可')
        # ⛔ 初回以外は開始日にしない（途中から参加させない）
        self.assertEqual(self._states('SP-C')[booking.course_dates('SP-C', b)[1]],
                         '予約締切')

    def test_選択なしで確定するとその日は講義しない日になる(self):
        day = _far_day()
        inst, token = self._reg({day: ['SP-A']})
        self.assertEqual(self._states('SP-A')[day], '予約可')
        booking.set_day_courses(token, day, [])
        self.assertEqual(self._states('SP-A')[day], '予約締切')
        self.assertNotIn(day, booking.registered_days(booking.find_instructor(token)))

    # ── 受け付けない入力
    def test_担当できない講座は選べない(self):
        inst, token = self._reg(courses=('SP-A',))
        saved, err = booking.set_day_courses(token, _far_day(), ['SP-C'])
        self.assertIsNone(saved)
        self.assertIn('登録されていない', err)

    def test_日付として読めない指定は受け取らない(self):
        inst, token = self._reg()
        saved, err = booking.set_day_courses(token, 'いつか', ['SP-A'])
        self.assertIsNone(saved)
        self.assertIn('日付', err)

    def test_予約が入っている日は中身も変えられない(self):
        day = _far_day()
        inst, token = self._reg({day: ['SP-A']}, courses=('SP-A', 'SP-C'))
        booking.add_booking('SP-A', day, '鈴木', 's@example.com', '', 1, '')
        saved, err = booking.set_day_courses(token, day, ['SP-C'])
        self.assertIsNone(saved)
        self.assertIn('予約が入っている', err)
        self.assertEqual(booking.registered_days(
            booking.find_instructor(token))[day], ['SP-A'])

    # ── 他の講師との関係
    def test_他の講師の登録は禁止ではなく参考として返す(self):
        # ⛔ 同じ日に複数の講師がいても構わない（予約が入るのは1人だけ）
        day = _far_day()
        a, _ = self._reg({day: ['SP-A']})
        i2, t2 = booking.register_instructor('鈴木', 's@example.com', '',
                                             ['SP-A'], '', {day: ['SP-A']})
        booking.verify_email(t2)
        booking.set_state(i2['id'], '承認')
        others = booking.others_on(booking.find_instructor(t2),
                                   date.fromisoformat(day))
        self.assertEqual([o['氏名'] for o in others], ['山田'])
        self.assertEqual(others[0]['コース'], ['SP-A'])
        # 2人いても予約は成立する（担当は1人に決まる）
        rec, inst = booking.add_booking('SP-A', day, '受講者', 'x@example.com',
                                        '', 1, '')
        self.assertIn(inst['氏名'], ('山田', '鈴木'))

    def test_自分自身は他の講師に出てこない(self):
        day = _far_day()
        inst, _ = self._reg({day: ['SP-A']})
        self.assertEqual(booking.others_on(inst, date.fromisoformat(day)), [])

    # ── 移行（2026-08-12 より前に登録された講師）
    def test_旧い時間帯の登録でもこれまでどおり予約できる(self):
        i, token = booking.register_instructor('山田', 'y@example.com', '',
                                               ['SP-A'], '')
        booking.verify_email(token)
        booking.set_state(i['id'], '承認')
        rows = booking.instructors()
        day = _far_day()
        rows[0]['講義できる日時'] = {day: [{'開始': '10:00', '終了': '17:00'}]}
        del rows[0]['担当できる日']              # 旧いレコードを再現する
        booking._save('instructors.json', rows)
        self.assertEqual(self._states('SP-A')[day], '予約可')
        self.assertEqual(
            booking.registered_days(booking.instructors()[0])[day], ['SP-A'])

    def test_一覧と判定が同じ答えを返す(self):
        # ⛔ registered_days（一覧・集計）と day_courses（予約の判定）は
        #    同じ答えでなければならない。2026-08-12 の速度改善で片方だけが
        #    旧形式『講義できる日時』を読み落とし、実際に割れた
        base = date.today()
        for 形 in ('日付×講座', '日付×時間帯', '曜日'):
            _clear()
            i, token = booking.register_instructor('山田', 'y@example.com', '',
                                                   ['SP-A', 'SP-C'], '')
            rows = booking.instructors()
            if 形 == '日付×時間帯':
                rows[0]['講義できる日時'] = {
                    _far_day(k): [{'開始': '10:00', '終了': '17:00'}]
                    for k in (20, 21, 30)}
                del rows[0]['担当できる日']
            elif 形 == '曜日':
                rows[0]['毎週の可能時間'] = _weekly_all_days()
                rows[0]['不可の日'] = [_far_day(25)]
                del rows[0]['担当できる日']
            else:
                rows[0]['担当できる日'] = {_far_day(20): ['SP-A'],
                                          _far_weekday(2): ['SP-C']}
            booking._save('instructors.json', rows)
            inst = booking.instructors()[0]
            reg = booking.registered_days(inst)
            for k in range(0, 45):
                d = base + timedelta(days=k)
                with self.subTest(形=形, 日=d.isoformat()):
                    self.assertEqual(sorted(booking.day_courses(inst, d)),
                                     sorted(reg.get(d.isoformat()) or []))

    def test_旧い曜日の登録でもこれまでどおり予約できる(self):
        i, token = booking.register_instructor('山田', 'y@example.com', '',
                                               ['SP-A'], '')
        booking.verify_email(token)
        booking.set_state(i['id'], '承認')
        rows = booking.instructors()
        rows[0]['毎週の可能時間'] = _weekly_all_days()
        rows[0]['不可の日'] = []
        del rows[0]['担当できる日']
        booking._save('instructors.json', rows)
        self.assertIn('予約可', set(self._states('SP-A').values()))

    def test_1日ぶん確定すると旧い欄は台帳から消える(self):
        # ⛔ 旧欄を残すと「予定の正がどれか」が2つになる
        i, token = booking.register_instructor('山田', 'y@example.com', '',
                                               ['SP-A'], '')
        rows = booking.instructors()
        old_day = _far_day(40)
        rows[0]['講義できる日時'] = {old_day: [{'開始': '10:00', '終了': '17:00'}]}
        rows[0]['毎週の可能時間'] = _weekly_all_days()
        rows[0]['不可の日'] = []
        del rows[0]['担当できる日']
        booking._save('instructors.json', rows)

        booking.set_day_courses(token, _far_day(20), ['SP-A'])
        r = booking.instructors()[0]
        for old in ('毎週の可能時間', '不可の日', '日別の可能時間', '講義できる日時'):
            self.assertNotIn(old, r)
        # ⛔ 移行のときに、他の日の登録を黙って落とさないこと
        self.assertIn(old_day, r['担当できる日'])
        self.assertIn(_far_day(20), r['担当できる日'])

    def test_登録されている予定の最終日を出せる(self):
        inst, _ = self._reg({_far_day(20): ['SP-A'], _far_day(50): ['SP-A']})
        self.assertEqual(booking.availability_end(inst), _far_day(50))


class Test開催できる曜日(unittest.TestCase):
    """「毎週水曜」の講座を木曜に選ばせない（2026-08-12 社長ご指摘）。

    ⛔ 曜日の制約を hours の文章の中だけに書いていたため、判定に使えず、
       木曜の選択肢に夜間コースが並び、木曜開始の予約まで成立しうる状態だった。
    """

    def setUp(self):
        _clear()
        app.logger.disabled = True
        self.c = app.test_client()
        self.inst, self.token = booking.register_instructor(
            '山田', 'y@example.com', '', ['SP-A', 'SP-C'], '')
        booking.verify_email(self.token)
        booking.set_state(self.inst['id'], '承認')

    def _next(self, weekday, offset=20):
        d = date.today() + timedelta(days=offset)
        while d.weekday() != weekday:
            d += timedelta(days=1)
        return d.isoformat()

    def test_掲載の曜日と設定が一致している(self):
        # ⛔ hours の文章と weekdays がズレたらここで落とす
        for c in booking.COURSES:
            named = [i for i, w in enumerate(booking.WEEKDAYS)
                     if w + '曜' in c['hours']]
            with self.subTest(course=c['code']):
                self.assertEqual(named, booking.course_weekdays(c['code']) or [],
                                 f"{c['code']} の hours と weekdays が違う")

    def test_曜日の制約を持つのは夜間コースだけ(self):
        self.assertEqual(booking.course_weekdays('SP-C'), [2])   # 水曜
        self.assertIsNone(booking.course_weekdays('SP-A'))

    def test_木曜には夜間コースを選べない(self):
        thu = self._next(3)
        body = self.c.get(f'/instructor/schedule/{self.token}/day/{thu}'
                          ).get_data(as_text=True)
        i = body.index('value="SP-C"')
        # ⛔ 一覧から黙って消さず、選べない理由を出す
        self.assertIn('disabled', body[i:i + 200])
        self.assertIn('毎週水曜の開催です', body)
        # SP-A は同じ画面で選べる
        j = body.index('value="SP-A"')
        self.assertNotIn('disabled', body[j:j + 200])

    def test_水曜なら夜間コースを選べる(self):
        wed = self._next(2)
        body = self.c.get(f'/instructor/schedule/{self.token}/day/{wed}'
                          ).get_data(as_text=True)
        i = body.index('value="SP-C"')
        self.assertNotIn('disabled', body[i:i + 200])

    def test_木曜に夜間コースを送っても受け取らない(self):
        # ⛔ 画面だけ塞いでAPIが空いている状態にしない
        thu = self._next(3)
        saved, err = booking.set_day_courses(self.token, thu, ['SP-C'])
        self.assertIsNone(saved)
        self.assertIn('毎週水曜', err)
        r = self.c.post(f'/instructor/schedule/{self.token}/day/{thu}',
                        data={'courses': ['SP-C'], 'confirm': '1'})
        self.assertEqual(booking.registered_days(
            booking.find_instructor(self.token)), {})

    def test_水曜に夜間コースを保存できる(self):
        wed = self._next(2)
        saved, err = booking.set_day_courses(self.token, wed, ['SP-C'])
        self.assertIsNone(err)
        self.assertEqual(booking.registered_days(saved), {wed: ['SP-C']})
        # ⛔ 全5回なので、1回ぶんの登録では開始日にならない（正しい挙動）
        st = {d['日付']: d['状態'] for d in booking.open_days('SP-C')}
        self.assertEqual(st[wed], '予約締切')
        # 5週ぶん登録すると初回が開始日になる
        for iso in booking.course_dates('SP-C', wed):
            booking.set_day_courses(self.token, iso, ['SP-C'])
        st = {d['日付']: d['状態'] for d in booking.open_days('SP-C')}
        self.assertEqual(st[wed], '予約可')

    def test_台帳に木曜の夜間コースが残っていても公開しない(self):
        # 画面を通らない経路や、制約を入れる前の登録が残っている場合
        thu = self._next(3)
        rows = booking.instructors()
        rows[0]['担当できる日'] = {thu: ['SP-C']}
        booking._save('instructors.json', rows)
        inst = booking.instructors()[0]
        self.assertEqual(booking.day_courses(inst, date.fromisoformat(thu)), [])
        self.assertNotIn('予約可',
                         {d['状態'] for d in booking.open_days('SP-C')})
        with self.assertRaises(ValueError):
            booking.add_booking('SP-C', thu, '鈴木', 's@example.com', '', 1, '')


class Test掲載している講座が全部登録されている(unittest.TestCase):
    """掲載ページ＝唯一の出どころ。載っている講座は全部予約できること。

    ⛔ 2026-08-12 社長ご指摘：子ども向け3・業種別15・GC の計19講座が
       booking.COURSES に無く、講師登録の選択肢にも出ていなかった。
       選べない＝担当できる人が永久に0名＝その講座は一生売れない。
    """

    def _published(self):
        """掲載ページから講座コードと価格を拾う（人が書いた表に頼らない）"""
        import io
        import vibe_coding_courses
        from vibe_coding_industry import INDUSTRIES
        out = {}
        for c in vibe_coding_courses.COURSES.values():
            out[c['code']] = c['price_num']
        for ind in INDUSTRIES.values():
            for c in ind['courses']:
                out[c['code']] = int(re.sub(r'[^\d]', '', c['price']))
        # 子ども向けは掲載HTMLが出どころ（Python側に表を持っていない）
        path = os.path.join(os.path.dirname(HERE), 'templates',
                            'vibe_coding_kids.html')
        html = io.open(path, encoding='utf-8').read()
        for m in re.finditer(r'COURSE (GK\d)</div>.*?course-price">&yen;'
                             r'([\d,]+)', html, re.S):
            out[m.group(1)] = int(m.group(2).replace(',', ''))
        return out

    def test_掲載されている講座はすべて予約できる(self):
        published = self._published()
        self.assertGreaterEqual(len(published), 23, '掲載ページが読めていない')
        missing = [c for c in published if c not in booking.COURSE_BY_CODE]
        self.assertEqual(missing, [], f'予約できない講座があります: {missing}')

    def test_価格が掲載と一致している(self):
        for code, price in self._published().items():
            with self.subTest(course=code):
                self.assertEqual(booking.COURSE_BY_CODE[code]['price'], price)

    def test_業種別は5業種3段階そろっている(self):
        for pre in ('GM', 'GH', 'GF', 'GL', 'GN'):
            for lv in ('A', 'B', 'C'):
                self.assertIn(f'{pre}-{lv}', booking.COURSE_BY_CODE)

    def test_登録フォームに全講座が出る(self):
        app.logger.disabled = True
        html = app.test_client().get('/instructor/register').get_data(as_text=True)
        for code in booking.COURSE_BY_CODE:
            with self.subTest(course=code):
                self.assertIn(f'value="{code}"', html)

    def test_登録フォームは区分ごとにまとまっている(self):
        # ⛔ 26講座を1列に並べない（自分の担当を見つけられない）
        html = app.test_client().get('/instructor/register').get_data(as_text=True)
        for g in ('一人会社AI経営', '汎用', '子ども', '製造業', '建設'):
            self.assertIn(g, html)
        self.assertEqual(len(booking.grouped_courses()),
                         len({c.get('group') for c in booking.COURSES}))

    def test_定員と最少催行の関係が壊れていない(self):
        for c in booking.COURSES:
            with self.subTest(course=c['code']):
                self.assertGreater(c['price'], 0)
                self.assertGreater(c['min_people'], 0)
                self.assertGreaterEqual(c['capacity'], c['min_people'])


class Test連続する日数(unittest.TestCase):
    """SP-B は3日間つづけて開催する（2026-08-12 実装）。

    ⛔ それまで日数は hours の文章「10:00〜17:00 × 3日間」の中にしか無く、
       1日ぶんの予定しか無い講師に割り当たり、2日目から講師がいなくなる
       状態だった。曜日の制約と同じ型の穴。
    """

    def setUp(self):
        _clear()
        app.logger.disabled = True
        self.c = app.test_client()
        self.inst, self.token = booking.register_instructor(
            '山田', 'y@example.com', '', ['SP-A', 'SP-B'], '')
        booking.verify_email(self.token)
        booking.set_state(self.inst['id'], '承認')

    def _reg(self, *isos, code='SP-B'):
        for iso in isos:
            booking.set_day_courses(self.token, iso, [code])

    def _state(self, code, iso):
        return {d['日付']: d['状態'] for d in booking.open_days(code)}[iso]

    def test_掲載の回数と設定が一致している(self):
        # ⛔ hours の「× N日間」「全N回」と days がズレたらここで落とす
        for c in booking.COURSES:
            m = (re.search(r'×\s*(\d+)\s*日間', c['hours'])
                 or re.search(r'全\s*(\d+)\s*回', c['hours'])
                 or re.search(r'全\s*(\d+)\s*回', c['name']))
            with self.subTest(course=c['code']):
                self.assertEqual(int(m.group(1)) if m else 1,
                                 booking.course_days(c['code']))

    def test_毎週の講座は1週間ごとに開催する(self):
        # ⛔ 「全5回」を連続5日にしないこと（毎週水曜が水木金土日になる）
        self.assertEqual(booking.course_interval('SP-C'), 7)
        self.assertEqual(booking.course_interval('GC'), 7)
        self.assertEqual(booking.course_interval('SP-B'), 1)
        wed = _far_weekday(2)
        got = booking.course_dates('SP-C', wed)
        self.assertEqual(len(got), 5)
        self.assertTrue(all(date.fromisoformat(x).weekday() == 2 for x in got))
        self.assertEqual(
            got[1], (date.fromisoformat(wed) + timedelta(days=7)).isoformat())

    def test_開催する日を並べられる(self):
        self.assertEqual(booking.course_dates('SP-B', '2026-09-07'),
                         ['2026-09-07', '2026-09-08', '2026-09-09'])
        self.assertEqual(booking.course_dates('SP-A', '2026-09-07'),
                         ['2026-09-07'])

    def test_初日だけの登録では開始日にならない(self):
        d0 = _far_day()
        self._reg(d0)
        # ⛔ 3日間の講座に1日ぶんの予定で割り当てないこと
        self.assertEqual(self._state('SP-B', d0), '予約締切')
        with self.assertRaises(ValueError):
            booking.add_booking('SP-B', d0, '鈴木', 's@example.com', '', 1, '')

    def test_3日つづけて登録すると開始日になる(self):
        d0 = _far_day()
        days = booking.course_dates('SP-B', d0)
        self._reg(*days)
        self.assertEqual(self._state('SP-B', d0), '予約可')
        # 2日目・3日目は「その日から3日」が埋まらないので開始日にはならない
        self.assertEqual(self._state('SP-B', days[1]), '予約締切')

    def test_申込には実際の3日間が残る(self):
        d0 = _far_day()
        self._reg(*booking.course_dates('SP-B', d0))
        rec, inst = booking.add_booking('SP-B', d0, '鈴木', 's@example.com',
                                        '', 1, '')
        self.assertEqual(rec['開催日'], booking.course_dates('SP-B', d0))

    def test_予約が入ったら3日とも動かせない(self):
        d0 = _far_day()
        days = booking.course_dates('SP-B', d0)
        self._reg(*days)
        booking.add_booking('SP-B', d0, '鈴木', 's@example.com', '', 1, '')
        # ⛔ 2日目・3日目を本人が消せてはいけない
        self.assertEqual(booking.booked_days_for_instructor(self.inst['id']),
                         days)
        for iso in days:
            saved, err = booking.set_day_courses(self.token, iso, [])
            self.assertIsNone(saved, iso)
            self.assertIn('予約が入っている', err)

    def test_開催中の日に別の講座を割り当てない(self):
        # ⛔ 3日間の2日目に、時間の重なる別の講座を入れないこと
        d0 = _far_day()
        days = booking.course_dates('SP-B', d0)
        self._reg(*days)
        booking.add_booking('SP-B', d0, '鈴木', 's@example.com', '', 1, '')
        self._reg(days[1], code='SP-A')      # 2日目にSP-Aを足そうとしても
        self.assertEqual(self._state('SP-A', days[1]), '予約締切')
        with self.assertRaises(ValueError):
            booking.add_booking('SP-A', days[1], '佐藤', 'x@example.com',
                                '', 1, '')

    def test_同じ回の2人目は受けられる(self):
        # 既存のルール（最少催行に人を集める）を壊さないこと
        d0 = _far_day()
        self._reg(*booking.course_dates('SP-B', d0))
        booking.add_booking('SP-B', d0, 'A', 'a@example.com', '', 1, '')
        rec, _ = booking.add_booking('SP-B', d0, 'B', 'b@example.com', '', 1, '')
        self.assertEqual(rec['_合計人数'], 2)

    def test_日程が重なる別の回は受けない(self):
        # 8/26開始の回が入っている講師に、8/27開始の回を割り当てない
        d0 = _far_day()
        days = booking.course_dates('SP-B', d0)
        self._reg(*days, booking.course_dates('SP-B', days[1])[-1])
        booking.add_booking('SP-B', d0, 'A', 'a@example.com', '', 1, '')
        self.assertEqual(self._state('SP-B', days[1]), '予約締切')

    def test_飛び飛びに3日選んでも公開されない旨を出す(self):
        # ⛔ 「3日登録した」で安心させないこと。続いていなければ開始日は0日
        d0 = date.fromisoformat(_far_day())
        self._reg(*[(d0 + timedelta(days=k * 2)).isoformat() for k in range(3)])
        inst = booking.find_instructor(self.token)
        self.assertEqual(booking.startable_days(inst, 'SP-B'), [])
        理由 = booking.publish_blockers(inst)
        self.assertTrue(any('3日間つづけて開催します' in b for b in 理由), 理由)
        body = self.c.get('/instructor/schedule/' + self.token).get_data(as_text=True)
        self.assertIn('予約が入る日がありません', body)

    def test_続けて選べば予約が入る日として数える(self):
        d0 = _far_day()
        self._reg(*booking.course_dates('SP-B', d0))
        inst = booking.find_instructor(self.token)
        self.assertEqual(booking.startable_days(inst, 'SP-B'), [d0])
        self.assertEqual(booking.publish_blockers(inst), [])
        body = self.c.get('/instructor/schedule/' + self.token).get_data(as_text=True)
        self.assertIn('予約が入る日 1日', body)

    def test_予約画面に3日間であることを出す(self):
        body = self.c.get('/book/SP-B').get_data(as_text=True)
        self.assertIn('3日間つづけて開催します', body)
        self.assertIn('初日', body)
        self.assertNotIn('3日間つづけて開催します',
                         self.c.get('/book/SP-A').get_data(as_text=True))

    def test_毎週の講座につづけてと書かない(self):
        # ⛔ 全5回（毎週水曜）を「5日間つづけて」と書くと水木金土日に読める
        body = self.c.get('/book/SP-C').get_data(as_text=True)
        self.assertIn('全5回・1週間おきに開催します', body)
        self.assertNotIn('5日間つづけて', body)
        self.assertIn('初回の日', body)

    def test_講師の画面に続きの日の登録を促す(self):
        d0 = _far_day()
        url = f'/instructor/schedule/{self.token}/day/{d0}'
        body = self.c.get(url).get_data(as_text=True)
        self.assertIn('3日間つづけて開催します', body)
        self.assertIn('にも同じ講座を登録してください', body)
        # 3日そろえば「開始日にできます」に変わる
        self._reg(*booking.course_dates('SP-B', d0))
        body = self.c.get(url).get_data(as_text=True)
        self.assertIn('この日を開始日にできます', body)

    def test_講師の画面でも毎週の講座につづけてと書かない(self):
        i, t = booking.register_instructor('夜間 太郎', 'n@example.com', '',
                                           ['SP-C'], '')
        wed = _far_weekday(2)
        body = self.c.get(f'/instructor/schedule/{t}/day/{wed}'
                          ).get_data(as_text=True)
        self.assertIn('全5回・毎週水曜に開催します', body)
        self.assertNotIn('5日間つづけて', body)
        # ⛔ 別用途の文（weekday_note）を文中に埋め込まない
        self.assertNotIn('開催ですに', body)


class Test公開されない理由(unittest.TestCase):
    """承認したのに日程が出ない、を画面で説明できるようにする。

    ⛔ 2026-08-12 実害：承認済みの講師が 8/26 に「10:00〜11:00」「13:00〜14:00」
       だけを登録していた。コースは終日（10:00〜17:00）なので担当できず、
       予約カレンダーには1日も出なかった。判定は正しいが、本人にも運営にも
       その理由がどこにも出ていなかった。
       （いまはコースを選ぶ入力なので、この型は構造的に起きない）
    """

    def setUp(self):
        _clear()

    def _reg(self, days=None, courses=('SP-A',), approve=True):
        i, t = booking.register_instructor('山田', 'y@example.com', '',
                                           list(courses), '', days or {})
        if approve:
            booking.verify_email(t)
            booking.set_state(i['id'], '承認')
        return booking.find_instructor(t), t

    def test_日を選んでいれば理由は出ない(self):
        inst, _ = self._reg({_far_day(): ['SP-A']})
        self.assertEqual(booking.publish_blockers(inst), [])
        self.assertEqual(booking.teachable_courses(inst), ['SP-A'])

    def test_日が1日も無ければそう言う(self):
        inst, _ = self._reg({})
        self.assertIn('講義できる日が1日も登録されていません',
                      booking.publish_blockers(inst))

    def test_締切より手前の日しか無ければそう言う(self):
        soon = (date.today() + timedelta(days=3)).isoformat()
        inst, _ = self._reg({soon: ['SP-A']})
        self.assertTrue(any('日以内です' in b
                            for b in booking.publish_blockers(inst)))

    def test_未承認と未確認も理由として出す(self):
        inst, t = self._reg({_far_day(): ['SP-A']}, approve=False)
        理由 = booking.publish_blockers(inst)
        self.assertTrue(any('承認されていません' in b for b in 理由), 理由)
        self.assertTrue(any('確認が済んでいません' in b for b in 理由), 理由)

    def test_一部の講座を選んでいないことは理由にしない(self):
        # ⛔ 選んだ講座は公開されている。ここに混ぜると公開中なのに未公開と読める
        inst, _ = self._reg({_far_day(): ['SP-A']}, courses=('SP-A', 'SP-C'))
        self.assertEqual(booking.publish_blockers(inst), [])
        self.assertEqual(booking.teachable_courses(inst), ['SP-A'])

    def test_旧い時間帯の登録で担当できる講座が無ければそう言う(self):
        # 2026-08-12 に実際に起きた形（1時間の枠しか無い）
        i, token = booking.register_instructor('山田', 'y@example.com', '',
                                               ['SP-A'], '')
        booking.verify_email(token)
        booking.set_state(i['id'], '承認')
        rows = booking.instructors()
        rows[0]['講義できる日時'] = {_far_day(): [{'開始': '10:00', '終了': '11:00'},
                                                  {'開始': '13:00', '終了': '14:00'}]}
        del rows[0]['担当できる日']
        booking._save('instructors.json', rows)
        inst = booking.instructors()[0]
        self.assertEqual(booking.teachable_courses(inst), [])
        # ⛔ 「1日も登録されていません」と言わないこと（登録はしている）
        理由 = booking.publish_blockers(inst)
        self.assertTrue(any('担当できる講座がありません' in b for b in 理由), 理由)
        self.assertFalse(any('1日も登録されていません' in b for b in 理由), 理由)

    def test_予定画面と承認画面に理由を出す(self):
        app.logger.disabled = True
        c = app.test_client()
        inst, token = self._reg({})
        body = c.get('/instructor/schedule/' + token).get_data(as_text=True)
        self.assertIn('受講者に日程が公開されません', body)
        admin = c.get('/admin/instructors', headers={'X-Admin-Token': 'test-admin'},
                      query_string={'token': 'test-admin'}).get_data(as_text=True)
        self.assertIn('受講者には公開されていません', admin)


class Test1日ぶんの登録画面(unittest.TestCase):
    """カレンダー → 講座を選ぶ → 確認 → 保存 の3ステップ（2026-08-12 社長ご指示）。

    ⛔ 確認画面を挟まずに保存しないこと。
    ⛔ 「同じ曜日にまとめて入れる」は分かりにくいので置かないこと。
    """

    def setUp(self):
        _clear()
        app.logger.disabled = True
        self.c = app.test_client()
        self.inst, self.token = booking.register_instructor(
            '山田', 'y@example.com', '', ['SP-A', 'SP-C'], '')
        booking.verify_email(self.token)
        booking.set_state(self.inst['id'], '承認')

    def _url(self, iso):
        return f'/instructor/schedule/{self.token}/day/{iso}'

    def test_カレンダーの日から1日ぶんの画面へ行ける(self):
        body = self.c.get('/instructor/schedule/' + self.token).get_data(as_text=True)
        self.assertIn(self._url(_far_day()), body)
        # ⛔ まとめて入れる欄は置かない（社長ご指示で削除）
        self.assertNotIn('まとめて入れる', body)
        self.assertNotIn('曜日を1つ以上', body)

    def test_選ぶ画面に自分の担当講座と開催時間が出る(self):
        body = self.c.get(self._url(_far_day())).get_data(as_text=True)
        self.assertIn('SP-A', body)
        self.assertIn('10:00〜17:00', body)
        self.assertIn('ステップ 2 / 3', body)
        # 担当できない講座は出さない
        self.assertNotIn('GB', body)

    def test_選んだだけでは保存されない(self):
        day = _far_day()
        r = self.c.post(self._url(day), data={'courses': ['SP-A']})
        self.assertEqual(r.status_code, 200)
        self.assertIn('ステップ 3 / 3', r.get_data(as_text=True))
        # ⛔ 確認画面を出しただけで台帳を触らないこと
        self.assertEqual(booking.registered_days(booking.find_instructor(self.token)), {})

    def test_確認画面から保存すると確定する(self):
        day = _far_day()
        r = self.c.post(self._url(day),
                        data={'courses': ['SP-A'], 'confirm': '1'})
        self.assertEqual(r.status_code, 302)
        self.assertIn('saved=' + day, r.headers['Location'])
        self.assertEqual(
            booking.registered_days(booking.find_instructor(self.token)),
            {day: ['SP-A']})

    def test_重なる講座を選ぶと確認へ進めない(self):
        i2, t2 = booking.register_instructor('鈴木', 's@example.com', '',
                                             ['SP-A', 'GA'], '')
        r = self.c.post(f'/instructor/schedule/{t2}/day/{_far_day()}',
                        data={'courses': ['SP-A', 'GA']})
        body = r.get_data(as_text=True)
        self.assertIn('重なる', body)
        self.assertIn('ステップ 2 / 3', body)

    def test_予約が入っている日は変更できないと出す(self):
        day = _far_day()
        booking.set_day_courses(self.token, day, ['SP-A'])
        booking.add_booking('SP-A', day, '鈴木', 's@example.com', '', 1, '')
        body = self.c.get(self._url(day)).get_data(as_text=True)
        self.assertIn('この日は変更できません', body)

    def test_他の講師の登録を参考として出す(self):
        day = _far_day()
        i2, t2 = booking.register_instructor('鈴木', 's@example.com', '',
                                             ['SP-A'], '', {day: ['SP-A']})
        booking.verify_email(t2)
        booking.set_state(i2['id'], '承認')
        body = self.c.get(self._url(day)).get_data(as_text=True)
        self.assertIn('鈴木', body)
        # ⛔ 「重複＝禁止」と書かないこと（予約が入るのは1人だけ）
        self.assertIn('差し支えありません', body)

    def test_14日以内の日は注意を出す(self):
        soon = (date.today() + timedelta(days=3)).isoformat()
        body = self.c.get(self._url(soon)).get_data(as_text=True)
        self.assertIn('日以内のため', body)

    def test_保存するとカレンダーに戻り保存済みと出る(self):
        day = _far_day()
        self.c.post(self._url(day), data={'courses': ['SP-A'], 'confirm': '1'})
        body = self.c.get('/instructor/schedule/' + self.token,
                          query_string={'saved': day}).get_data(as_text=True)
        self.assertIn('の登録を保存しました', body)
        self.assertIn('SP-A', body)

    def test_でたらめな鍵や日付は404(self):
        self.assertEqual(self.c.get('/instructor/schedule/でたらめ/day/'
                                    + _far_day()).status_code, 404)
        self.assertEqual(
            self.c.get(f'/instructor/schedule/{self.token}/day/いつか').status_code,
            404)


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
        booking.set_day_courses(rec['鍵'], _far_day(), ['SP-A'])
        booking.set_state(rec['id'], '承認')
        # ⛔ 届かないアドレスの講師を公開しない（当日に誰も来ない事故になる）
        self.assertNotIn('予約可', {d['状態'] for d in booking.open_days('SP-A')})
        self.assertEqual(booking.approved_instructors(), [])

    def test_確認リンクを踏むと公開されカレンダーに送られる(self):
        _, rec = self._register()
        booking.set_day_courses(rec['鍵'], _far_day(), ['SP-A'])
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

    def test_メールを送れたら画面に専用URLを出さない(self):
        # ⛔ 2026-08-12 社長ご指摘。URLを出すと誰もメールを開かずに進めてしまい、
        #    アドレスの確認が意味を失う（実測：本番8件中6件が未確認のままだった）
        import booking_routes
        orig = booking_routes._send
        booking_routes._send = lambda *a, **kw: True      # 送れた体にする
        try:
            r, rec = self._register(email='ok@example.com')
        finally:
            booking_routes._send = orig
        body = r.get_data(as_text=True)
        self.assertIn('確認メールをお送りしました', body)
        self.assertIn('ok@example.com', body)
        self.assertNotIn(rec['鍵'], body)                 # 鍵そのものを出さない

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
