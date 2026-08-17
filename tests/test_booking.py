# -*- coding: utf-8 -*-
"""講座の予約（講師の登録・承認・空き日・申込）の回帰テスト。

ここで固定しているのは「事故の型」であって、機能の説明ではない。
2026-08-09 に実際に起きた4つを落とせるようにしてある:
  ① 承認していない講師の日程が受講者に公開される
  ② 存在しないIDでも承認が成功したことになる（押しても何も変わらない）
  ③ 予約が入った日を講師があとから閉じられてしまう
  ④ 選べる日が0件のページでスクリプトが落ちる／テンプレートが500になる
"""
import io
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


def _visible(html):
    """画面に見える部分だけを返す（script とコメントを落とす）。

    ⛔ 「この書き方をしていないこと」を生のHTMLで検索しないこと。⛔付きの
       注意書きや、JSのセレクタ（input[name="pay"]）に当たって落ちる。
       禁止した言葉ほど、禁止を書いたコメントに含まれている。
    """
    html = re.sub(r'<script\b.*?</script>', '', html, flags=re.S | re.I)
    html = re.sub(r'<!--.*?-->', '', html, flags=re.S)
    return re.sub(r'\{#.*?#\}', '', html, flags=re.S)


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


def _next_session_day(after):
    """その日より後の、いちばん近い開催日。"""
    d = date.fromisoformat(after) + timedelta(days=1)
    for _ in range(20):
        if booking.is_session_day(d):
            return d.isoformat()
        d += timedelta(days=1)
    raise AssertionError('開催日が見つかりません')


def _weekly_all_days():
    """旧形式（曜日の決まり）。移行の読み取り互換を確かめるためだけに残す。"""
    return [{'曜日': i, '開始': '10:00', '終了': '17:00'} for i in range(7)]


def _far_day(offset=30):
    """offset日後 以降の、いちばん近い『開催日』。

    ⛔ ただの offset 日後を返さないこと（2026-08-15）。開催日は運営が決めた
       曜日（毎週水＋第2・第4土）だけで、それ以外は講師も登録できない。
       固定の日数を返すと、テストが「その年その月の曜日」に依存して落ちる。
    """
    d = date.today() + timedelta(days=offset)
    for _ in range(14):
        if booking.is_session_day(d):
            return d.isoformat()
        d += timedelta(days=1)
    raise AssertionError('開催日が見つかりません')


def _far_weekday(weekday, offset=20):
    """offset 日より先で、最初にその曜日（月=0）になる日。

    SP-C のように開催曜日が決まっている講座を試すときに使う。
    """
    d = date.today() + timedelta(days=offset)
    while d.weekday() != weekday:
        d += timedelta(days=1)
    return d.isoformat()


def _far_session_weekday(weekday, offset=20):
    """offset 日より先で、その曜日かつ『開催日』である最初の日。

    ⛔ ただの曜日で取らないこと（2026-08-15）。土曜は第2・第4だけが開催日で、
       第1・第3土曜を渡すと set_day_courses が正しく断る。
    """
    d = date.today() + timedelta(days=offset)
    for _ in range(70):
        if d.weekday() == weekday and booking.is_session_day(d):
            return d.isoformat()
        d += timedelta(days=1)
    raise AssertionError('開催日が見つかりません')


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


class Test同じメールアドレスは1人1行(unittest.TestCase):
    """⛔ 2026-08-14 社長ご指摘。重複チェックが1行も無く、本番の台帳は
       12件すべてが同一アドレスだった＝1人が12人として並んでいた。
    """

    def setUp(self):
        _clear()
        self.a, self.ta = booking.register_instructor(
            '山田 太郎', 'y@example.com', '旧所属', ['SP-A'], 'めも')

    def test_同じアドレスで登録し直しても行が増えない(self):
        booking.register_instructor('山田 太郎', 'y@example.com', '新所属',
                                    ['SP-A', 'SP-B'], '')
        self.assertEqual(len(booking.instructors()), 1)

    def test_大文字小文字が違っても同じ人として扱う(self):
        # 同じ受信箱に届くので、別人として登録されると二重に公開される
        booking.register_instructor('山田 太郎', 'Y@Example.com', '', ['SP-A'], '')
        self.assertEqual(len(booking.instructors()), 1)

    def test_登録し直しても本人用の鍵は変わらない(self):
        # 変わると、以前に受け取ったメールのリンクが全部死ぬ
        b, tb = booking.register_instructor('山田 太郎', 'y@example.com', '',
                                            ['SP-A'], '')
        self.assertEqual(tb, self.ta)
        self.assertEqual(b['id'], self.a['id'])

    def test_登録し直すと内容が置き換わる(self):
        b, _ = booking.register_instructor('山田 花子', 'y@example.com', '新所属',
                                           ['SP-B'], 'あたらしいめも')
        self.assertEqual(b['氏名'], '山田 花子')
        self.assertEqual(b['所属'], '新所属')
        self.assertEqual(b['対応コース'], ['SP-B'])
        self.assertEqual(b['備考'], 'あたらしいめも')

    def test_メール確認済みは消さない(self):
        # 本人が受け取った証拠。消すと承認しても公開されない状態に戻る
        booking.verify_email(self.ta)
        b, _ = booking.register_instructor('山田 太郎', 'y@example.com', '',
                                           ['SP-A'], '')
        self.assertTrue(b['メール確認済み'])

    def test_登録済みの日程は消さない(self):
        booking.set_day_courses(self.ta, _far_day(), ['SP-A'])
        before = booking.registered_days(booking.find_instructor(self.ta))
        booking.register_instructor('山田 太郎', 'y@example.com', '', ['SP-A'], '')
        after = booking.registered_days(booking.find_instructor(self.ta))
        self.assertEqual(before, after)
        self.assertTrue(after)

    def test_講座を増やしても既存の承認は生きたまま(self):
        # ⛔ 審査を受けずに担当講座を増やせる状態にしないこと。ただし
        #    ⛔ 既に承認されている講座まで巻き添えで非公開にしないこと。
        #    承認は**講座ごと**に持つ（2026-08-15 社長ご指摘で修正）。
        #    旧実装は状態ごと『申請中』へ戻し、その人の日程が全部消えていた。
        booking.set_state(self.a['id'], '承認')
        b, _ = booking.register_instructor('山田 太郎', 'y@example.com', '',
                                           ['SP-A', 'SP-B'], '')
        self.assertEqual(b['状態'], '承認')
        self.assertEqual(booking.approved_courses(b), ['SP-A'])
        self.assertEqual(booking.pending_courses(b), ['SP-B'])

    def test_承認済みでも講座が増えなければ承認のまま(self):
        # 誤字を直しただけで差し戻すと、公開が止まってしまう
        booking.set_state(self.a['id'], '承認')
        b, _ = booking.register_instructor('山田 太郎', 'y@example.com', '新所属',
                                           ['SP-A'], '')
        self.assertEqual(b['状態'], '承認')

    def test_見送りの人が登録し直したら再申請として受ける(self):
        booking.set_state(self.a['id'], '見送り')
        b, _ = booking.register_instructor('山田 太郎', 'y@example.com', '',
                                           ['SP-A'], '')
        self.assertEqual(b['状態'], '申請中')

    def test_違うアドレスなら別の行になる(self):
        booking.register_instructor('鈴木', 's@example.com', '', ['SP-A'], '')
        self.assertEqual(len(booking.instructors()), 2)

    def test_find_by_emailは未登録ならNone(self):
        self.assertIsNone(booking.find_by_email('nobody@example.com'))
        self.assertIsNone(booking.find_by_email(''))

    def test_寄せる道具は残す行を間違えない(self):
        # ⛔ 選び方を間違えると、予約の入った行や確認済みの行を消してしまう
        from tools import merge_duplicate_instructors as m
        old = {'id': 'A', 'メール確認済み': None, '対応コース': ['SP-A'],
               '登録日時': '2026-01-01 00:00'}
        new = {'id': 'B', 'メール確認済み': '2026-02-02 00:00',
               '対応コース': ['SP-A'], '登録日時': '2026-02-02 00:00'}
        # メール確認済みの方を残す
        self.assertGreater(m._rank(new, set()), m._rank(old, set()))
        # ⛔ 予約が入っている行は、確認済みより優先して残す
        self.assertGreater(m._rank(old, {'A'}), m._rank(new, set()))

    def test_画面から登録し直しても行が増えず更新と分かる(self):
        # ⛔ 更新であることを画面に出すこと。出さないと「2件登録された」と
        #    誤解され、逆に前回の講座が置き換わったことにも気づけない
        c = app.test_client()
        antispam._RECENT.clear()
        r = c.post('/instructor/register', data={
            'name': '山田 太郎', 'email': 'y@example.com', 'org': '新所属',
            'courses': ['SP-A', 'SP-B'], 'note': '',
            'fee_agree': booking.FEE_TERMS_VERSION,
            antispam.HONEYPOT_FIELD: '',
            'ts': antispam.issue_token(now=time.time() - 6)})
        self.assertEqual(r.status_code, 200)          # テンプレートが500にならない
        self.assertEqual(len(booking.instructors()), 1)
        body = r.get_data(as_text=True)
        self.assertIn('更新しました', body)
        self.assertIn('新しく追加せず', body)


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
        # ⛔ 非開催日で試さないこと。状態は『非開催日』になり準備期間ではない
        d = date.today() + timedelta(days=1)
        soon = None
        while d < date.today() + timedelta(days=booking.LEAD_DAYS):
            if booking.is_session_day(d):
                soon = d.isoformat()
            d += timedelta(days=1)
        self.assertIsNotNone(soon, '14日以内に開催日が無い')
        info = {x['日付']: x for x in booking.open_days('SP-A')}.get(soon)
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

    def test_1名の申込でも開催が確定する(self):
        # ⛔ 人数で確定を判定しないこと（最少催行は撤廃）。講師料は定額なので
        #    1名でも黒字で、断ると確実に入る利益と受講者の両方を失う
        r, _ = booking.add_booking('SP-A', _far_day(), '鈴木', 's@example.com', '', 1, '')
        self.assertTrue(r['_開催確定'])
        self.assertNotIn('_最少催行', r)

    def test_最少催行という項目がどのコースにも無い(self):
        # ⛔ ここが落ちたら「復活させた」ということ。冒頭の説明を読むこと
        for c in booking.COURSES:
            self.assertNotIn('min_people', c, c['code'])

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
            'fee_agree': booking.FEE_TERMS_VERSION,
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
    def test_全コースに定員と金額と講師料がある(self):
        for c in booking.COURSES:
            with self.subTest(course=c['code']):
                self.assertGreater(c['price'], 0)
                self.assertGreater(c['capacity'], 0)
                # ⛔ 最少催行は設けない（2026-08-14 社長ご判断）
                self.assertNotIn('min_people', c)
                # 講師料が出せない講座を作らない（発注が都度交渉に戻る）
                self.assertGreater(booking.instructor_fee(c['code']), 0)

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
        # ⛔ _far_day(31) を使わないこと。開催日まで前倒しするので day と
        #    同じ日になり、「選んでいない日」の検査にならない
        other = _far_day(int(day[8:10]) and 38)
        while other == day:
            other = (date.fromisoformat(other) + timedelta(days=1)).isoformat()
            while not booking.is_session_day(other):
                other = (date.fromisoformat(other) + timedelta(days=1)).isoformat()
        self.assertEqual(st[other], '予約締切')          # 選んでいない日

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

    def test_同じ時間帯の講座も候補として同じ日に登録できる(self):
        # ⛔ 開催時間が重なることを理由に断らないこと。ここは「その日に受け
        #    られる講座」の登録で、その日に全部開催するという意味ではない。
        #    全26講座中18講座が 10:00〜17:00 なので、断ると1日1講座しか
        #    選べなくなる（2026-08-14 社長ご指摘。SP-A・SP-B・GA・GB・GD・GE）
        codes = ['SP-A', 'SP-B', 'GA', 'GB', 'GD', 'GE']
        self.assertEqual({booking.course_hours(c) for c in codes},
                         {('10:00', '17:00')})
        day = _far_day()
        inst, token = self._reg(courses=tuple(codes))
        # SP-B は3日間なので、続く日も登録しておく（開始日として成立させる）
        for iso in booking.course_dates('SP-B', day)[1:]:
            booking.set_day_courses(token, iso, ['SP-B'])
        saved, err = booking.set_day_courses(token, day, codes)
        self.assertIsNone(err)
        self.assertEqual(booking.day_courses(saved, date.fromisoformat(day)),
                         sorted(codes))
        # 6つとも受講者の予約画面に出る
        for c in codes:
            self.assertEqual(self._states(c)[day], '予約可', c)

    def test_同じ時間帯は申込が入った時点で1つに決まる(self):
        # ⛔ 登録の段階で断る代わりに、ここが確実に効いていること。
        #    1人が同時刻に2つ担当する（バッティング）のを止める唯一の関所
        day = _far_day()
        inst, token = self._reg(courses=('SP-A', 'GA', 'SP-C'))
        booking.set_day_courses(token, day, ['SP-A', 'GA'])
        booking.add_booking('SP-A', day, '鈴木', 's@example.com', '', 1, '')
        self.assertEqual(self._states('GA')[day], '予約締切')
        with self.assertRaises(ValueError):
            booking.add_booking('GA', day, '佐藤', 'x@example.com', '', 1, '')

    def test_同じ時間帯の組み合わせは注記のために取り出せる(self):
        # ⛔ 断る材料ではなく、確認画面の注記に使うだけ
        self.assertTrue(booking.same_time_courses(['SP-A', 'GA']))
        self.assertFalse(booking.same_time_courses(['SP-A', 'SP-C']))

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
        # 子ども向けは掲載ページを実際に描画して読む。
        # ⛔ テンプレートのソースを正規表現で読まないこと（2026-08-15）。
        #    価格を台帳から入れる形にした時点で、ソースには金額が
        #    書かれていないので「掲載0件」に化け、検査が素通りになる。
        html = app.test_client().get('/vibe-coding/kids').get_data(as_text=True)
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

    def test_全講座に開催時刻がある(self):
        # ⛔ 時刻が読めない講座は「同じ日に他と併せて担当できない」安全側に倒れ、
        #    受講者にも開始時刻を案内できない。26講座すべてに時刻を持たせる
        for c in booking.COURSES:
            with self.subTest(course=c['code']):
                self.assertIsNotNone(booking.course_hours(c['code']),
                                     f"{c['code']} の hours から時刻が読めない")

    def test_業種別の時刻が掲載と一致している(self):
        # ⛔ 掲載ページと予約の時刻がズレたら、案内と実運用が食い違う
        from vibe_coding_industry import INDUSTRIES
        for ind in INDUSTRIES.values():
            for c in ind['courses']:
                m = re.search(r'(\d{1,2}:\d{2})\s*〜\s*(\d{1,2}:\d{2})',
                              c['duration'])
                with self.subTest(course=c['code']):
                    self.assertIsNotNone(m, f"{c['code']} の掲載に時刻が無い")
                    self.assertEqual(booking.course_hours(c['code']),
                                     (m.group(1), m.group(2)))

    def test_子ども向けの時刻が掲載と一致している(self):
        import io
        path = os.path.join(os.path.dirname(HERE), 'templates',
                            'vibe_coding_kids.html')
        html = io.open(path, encoding='utf-8').read()
        found = re.findall(r'COURSE (GK\d)</div>.*?meta-value">\d時間<br>'
                           r'(\d{1,2}:\d{2})〜(\d{1,2}:\d{2})', html, re.S)
        self.assertEqual(len(found), 3, '掲載ページに時刻が無い')
        for code, a, b in found:
            with self.subTest(course=code):
                self.assertEqual(booking.course_hours(code), (a, b))

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

    def test_定員と金額が壊れていない(self):
        for c in booking.COURSES:
            with self.subTest(course=c['code']):
                self.assertGreater(c['price'], 0)
                self.assertGreater(c['capacity'], 0)


class Test連続する日数(unittest.TestCase):
    """SP-B は毎週土曜×3回で開催する（2026-08-15 社長ご判断で連日から変更）。

    ⛔ 連日開催に戻さないこと。開催日は運営が決めた曜日（毎週水＋第2/第4土）
       だけで、連続する日が1組も無いため、連日の講座は構造的に成立しない。
    ⛔ 日数を hours の文章の中だけに書かないこと。1日ぶんの予定しか無い
       講師に割り当たり、2回目から講師がいなくなる（曜日の制約と同じ型の穴）。
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
        self.assertEqual(booking.course_interval('SP-B'), 7)
        wed = _far_weekday(2)
        got = booking.course_dates('SP-C', wed)
        self.assertEqual(len(got), 5)
        self.assertTrue(all(date.fromisoformat(x).weekday() == 2 for x in got))
        self.assertEqual(
            got[1], (date.fromisoformat(wed) + timedelta(days=7)).isoformat())

    def test_開催する日を並べられる(self):
        # ⛔ 連日にしないこと。SP-B は毎週土曜×3回（2026-08-15 社長ご判断）
        self.assertEqual(booking.course_dates('SP-B', '2026-09-09'),
                         ['2026-09-09', '2026-09-16', '2026-09-23'])
        self.assertEqual(booking.course_dates('SP-A', '2026-09-07'),
                         ['2026-09-07'])

    def test_初日だけの登録では開始日にならない(self):
        d0 = _far_weekday(2)
        self._reg(d0)
        # ⛔ 3日間の講座に1日ぶんの予定で割り当てないこと
        self.assertEqual(self._state('SP-B', d0), '予約締切')
        with self.assertRaises(ValueError):
            booking.add_booking('SP-B', d0, '鈴木', 's@example.com', '', 1, '')

    def test_3日つづけて登録すると開始日になる(self):
        d0 = _far_weekday(2)
        days = booking.course_dates('SP-B', d0)
        self._reg(*days)
        self.assertEqual(self._state('SP-B', d0), '予約可')
        # 2日目・3日目は「その日から3日」が埋まらないので開始日にはならない
        self.assertEqual(self._state('SP-B', days[1]), '予約締切')

    def test_申込には実際の3日間が残る(self):
        d0 = _far_weekday(2)
        self._reg(*booking.course_dates('SP-B', d0))
        rec, inst = booking.add_booking('SP-B', d0, '鈴木', 's@example.com',
                                        '', 1, '')
        self.assertEqual(rec['開催日'], booking.course_dates('SP-B', d0))

    def test_予約が入ったら3日とも動かせない(self):
        d0 = _far_weekday(2)
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
        d0 = _far_weekday(2)
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
        d0 = _far_weekday(2)
        self._reg(*booking.course_dates('SP-B', d0))
        booking.add_booking('SP-B', d0, 'A', 'a@example.com', '', 1, '')
        rec, _ = booking.add_booking('SP-B', d0, 'B', 'b@example.com', '', 1, '')
        self.assertEqual(rec['_合計人数'], 2)

    def test_日程が重なる別の回は受けない(self):
        # 8/26開始の回が入っている講師に、8/27開始の回を割り当てない
        d0 = _far_weekday(2)
        days = booking.course_dates('SP-B', d0)
        self._reg(*days, booking.course_dates('SP-B', days[1])[-1])
        booking.add_booking('SP-B', d0, 'A', 'a@example.com', '', 1, '')
        self.assertEqual(self._state('SP-B', days[1]), '予約締切')

    def test_飛び飛びに3日選んでも公開されない旨を出す(self):
        # ⛔ 「3日登録した」で安心させないこと。続いていなければ開始日は0日
        d0 = date.fromisoformat(_far_weekday(2))
        self._reg(*[(d0 + timedelta(days=k * 2)).isoformat() for k in range(3)])
        inst = booking.find_instructor(self.token)
        self.assertEqual(booking.startable_days(inst, 'SP-B'), [])
        理由 = booking.publish_blockers(inst)
        self.assertTrue(any('全3回・毎週水曜に開催します' in b for b in 理由), 理由)
        body = self.c.get('/instructor/schedule/' + self.token).get_data(as_text=True)
        self.assertIn('予約が入る日がありません', body)

    def test_続けて選べば予約が入る日として数える(self):
        d0 = _far_weekday(2)
        self._reg(*booking.course_dates('SP-B', d0))
        inst = booking.find_instructor(self.token)
        self.assertEqual(booking.startable_days(inst, 'SP-B'), [d0])
        self.assertEqual(booking.publish_blockers(inst), [])
        body = self.c.get('/instructor/schedule/' + self.token).get_data(as_text=True)
        self.assertIn('予約が入る日 1日', body)

    def test_予約画面に全3回であることを出す(self):
        # ⛔ 「3日間つづけて」に戻さないこと（2026-08-15 連日開催を廃止）
        body = self.c.get('/book/SP-B').get_data(as_text=True)
        self.assertIn('全3回・毎週水曜に開催します', body)
        self.assertIn('初回の日', body)
        self.assertNotIn('つづけて開催します',
                         self.c.get('/book/SP-A').get_data(as_text=True))

    def test_毎週の講座につづけてと書かない(self):
        # ⛔ 全5回（毎週水曜）を「5日間つづけて」と書くと水木金土日に読める
        body = self.c.get('/book/SP-C').get_data(as_text=True)
        self.assertIn('全5回・毎週水曜に開催します', body)
        self.assertNotIn('5日間つづけて', body)
        self.assertIn('初回の日', body)

    def test_講師の画面に続きの日の登録を促す(self):
        d0 = _far_weekday(2)
        url = f'/instructor/schedule/{self.token}/day/{d0}'
        body = self.c.get(url).get_data(as_text=True)
        self.assertIn('全3回・毎週水曜に開催します', body)
        self.assertIn('にも同じ講座を登録してください', body)
        # 3回そろえば「開始日にできます」に変わる
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

    def test_同じ時間帯を選んでも確認へ進める(self):
        # ⛔ エラーで止めないこと（2026-08-14 社長ご指摘）。代わりに確認画面で
        #    「開催されるのはどれか1つだけ」と伝える
        i2, t2 = booking.register_instructor(
            '鈴木', 's@example.com', '', ['SP-A', 'GA', 'GB', 'GD', 'GE'], '')
        r = self.c.post(f'/instructor/schedule/{t2}/day/{_far_day()}',
                        data={'courses': ['SP-A', 'GA', 'GB', 'GD', 'GE']})
        body = r.get_data(as_text=True)
        self.assertIn('ステップ 3 / 3', body)
        self.assertNotIn('お受けいただけません', body)
        self.assertIn('どれか1つだけ', body)

    def test_選ぶ画面に重ならない組み合わせのみとは書かない(self):
        # ⛔ 26講座中18講座が同じ 10:00〜17:00 なので、この案内は嘘になる
        body = self.c.get(self._url(_far_day())).get_data(as_text=True)
        self.assertNotIn('重ならない組み合わせ', body)
        self.assertIn('いくつでも選べます', body)

    def test_予約が入っている日は変更できないと出す(self):
        day = _far_day()
        booking.set_day_courses(self.token, day, ['SP-A'])
        booking.add_booking('SP-A', day, '鈴木', 's@example.com', '', 2, '')
        body = self.c.get(self._url(day)).get_data(as_text=True)
        self.assertIn('この日は受講者の申込が入っています', body)
        # ⛔ 「予約が入っています」だけで終わらせない＝何の講座で何名かを出す
        self.assertIn('SP-A', body)
        self.assertIn('2名', body)
        # ⛔ 選べない日に「担当する講座を選ぶ」と出さない
        self.assertNotIn('ステップ 2 / 3', body)

    def test_カレンダーに申込の中身を出す(self):
        # ⛔ 青いだけの日にしない。講師が自分の担当を確かめられるようにする
        day = _far_day()
        booking.set_day_courses(self.token, day, ['SP-A'])
        booking.add_booking('SP-A', day, '鈴木', 's@example.com', '', 3, '')
        body = self.c.get('/instructor/schedule/' + self.token).get_data(as_text=True)
        self.assertIn('SP-A 3名', body)
        self.assertIn('受講者の申込が入っている（変更不可）', body)
        # ⛔ 誰の予約か分からない書き方に戻さない
        self.assertNotIn('>予約が入っている（変更不可）', body)

    def test_申込の集計は取消を数えない(self):
        day = _far_day()
        booking.set_day_courses(self.token, day, ['SP-A'])
        rec, _ = booking.add_booking('SP-A', day, '鈴木', 's@example.com',
                                     '', 2, '')
        rows = booking.bookings()
        rows[0]['状態'] = '取消'
        booking._save('bookings.json', rows)
        self.assertEqual(booking.booked_summary(self.inst['id']), {})

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
            'fee_agree': booking.FEE_TERMS_VERSION,
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


class Test最少催行を復活させない(unittest.TestCase):
    """2026-08-14 社長ご判断。固定している事故の型:

      ・人数が足りないことを理由に開催を中止する（＝確実に入る利益を捨て、
        申し込んだ受講者と看板を同時に失う）
      ・1人目の申込者に「開催されないかもしれません」と伝える文面が復活する
        （定義上100%の申込者に届き、いちばん申込を止める）
    """

    def setUp(self):
        _clear()

    def test_講師料は定額で人数に比例しない(self):
        # ⛔ 40%を人数分にしないこと。10名でも1名でも同じ額
        # ⛔ 金額を写さないこと。単価の40%であることを確かめる
        # ⛔ 受講料そのものではなく「認定試験の受験料を除いた額」の40%
        #    （2026-08-17）。試験は協会が実施する＝講師の仕事ではないので、
        #    受験料を組み込んだ日に講師料が自動で上がってはいけない。
        for code in ('SP-A', 'SP-B', 'SP-C', 'GA-P', 'GK2'):
            base = booking.teaching_price(code)
            self.assertEqual(booking.instructor_fee(code),
                             int(round(base * booking.FEE_RATE)), code)

    def test_損益分岐は1名未満なので必ず黒字(self):
        # 講師料が定額 ⇒ 1名の受講料でまかなえること（全コース）
        for c in booking.COURSES:
            with self.subTest(course=c['code']):
                self.assertLess(booking.instructor_fee(c['code']), c['price'])

    def test_申込画面に中止をにおわせる文言を出さない(self):
        booking.register_instructor('山田', 'y@example.com', '', ['SP-A'], '',
                                    _days_all())
        booking.set_state(booking.instructors()[0]['id'], '承認')
        booking.verify_email(booking.instructors()[0]['鍵'])
        html = _visible(app.test_client().get('/book/SP-A').get_data(as_text=True))
        for ng in ('最少催行', '次回へお振替', '人数が集まらない', '人数が集まり次第'):
            self.assertNotIn(ng, html, ng)
        self.assertIn('お一人から', html)

    def test_取り消した申込を定員に数えない(self):
        # ⛔ 2026-08-14 に見つけた既存の不具合。取消が残席を食っていた
        d = _far_day()
        booking.register_instructor('山田', 'y@example.com', '', ['SP-A'], '',
                                    _days_all())
        booking.set_state(booking.instructors()[0]['id'], '承認')
        booking.verify_email(booking.instructors()[0]['鍵'])
        cap = booking.COURSE_BY_CODE['SP-A']['capacity']
        rec, _ = booking.add_booking('SP-A', d, 'A', 'a@example.com', '', cap, '')
        with self.assertRaises(ValueError):
            booking.add_booking('SP-A', d, 'B', 'b@example.com', '', 1, '')
        booking.cancel_booking(rec['id'], '試験')
        rec2, _ = booking.add_booking('SP-A', d, 'B', 'b@example.com', '', 1, '')
        self.assertEqual(rec2['_合計人数'], 1)


class Test講師料の明示と同意(unittest.TestCase):
    """⛔ 「謝礼はご相談のうえ」に戻さないこと（＝1件ごとの条件交渉＝人手）。"""

    def setUp(self):
        _clear()
        app.logger.disabled = True
        self.c = app.test_client()

    def _post(self, **over):
        antispam._RECENT.clear()
        data = {'name': '佐藤', 'email': 's@example.com', 'courses': ['SP-A'],
                'note': '', 'fee_agree': booking.FEE_TERMS_VERSION,
                antispam.HONEYPOT_FIELD: '',
                'ts': antispam.issue_token(now=time.time() - 6)}
        data.update(over)
        return self.c.post('/instructor/register', data=data)

    def test_登録画面に講座ごとの金額が出る(self):
        html = self.c.get('/instructor/register').get_data(as_text=True)
        # ⛔ 金額を書き写さないこと＝受講料を変えた日にここだけ古くなる
        #    （2026-08-17 の値上げで実際に落ちた）。式から出して突き合わせる。
        for code in ('SP-A', 'SP-B'):
            self.assertIn('{:,}'.format(booking.instructor_fee(code)), html, code)
        self.assertIn('1開催あたり', html)
        # ⛔ 都度交渉に戻す文言を残さないこと
        self.assertNotIn('謝礼はご相談のうえ', html)

    def test_金額を渡し忘れると気づけること(self):
        # Jinja は未定義を空文字にするので「講師料 ¥」とだけ出る。
        # ⛔ 実際の画面でそうなっていないことを確かめる
        html = self.c.get('/instructor/register').get_data(as_text=True)
        self.assertNotIn('講師料 <strong>¥</strong>', html)

    def test_同意しないと登録できない(self):
        # ⛔ ブラウザの required だけに任せないこと（画面を通らない経路がある）
        r = self._post(fee_agree='')
        self.assertEqual(r.status_code, 200)
        self.assertIn('ご同意が必要です', r.get_data(as_text=True))
        self.assertEqual(booking.instructors(), [])

    def test_古い版への同意では登録できない(self):
        r = self._post(fee_agree='2020-01-01')
        self.assertIn('ご同意が必要です', r.get_data(as_text=True))
        self.assertEqual(booking.instructors(), [])

    def test_同意は版と日時で台帳に残る(self):
        self._post()
        rec = booking.instructors()[0]
        self.assertEqual(booking.fee_agreed_version(rec),
                         booking.FEE_TERMS_VERSION)
        self.assertEqual(len(rec['講師料同意']), 1)

    def test_同じ版の同意を積み上げない(self):
        self._post()
        self._post(org='別')                 # 同じ人が登録し直す
        rec = booking.instructors()[0]
        self.assertEqual(len(rec['講師料同意']), 1)


class Testカード決済(unittest.TestCase):
    """⛔ 払っていない人を「申込受付」にしないこと。
    ⛔ 鍵が無い環境で壊れないこと（未設定なら請求書払いだけで動く）。
    """

    def setUp(self):
        _clear()
        app.logger.disabled = True
        self.c = app.test_client()
        os.environ.pop('STRIPE_SECRET_KEY', None)
        os.environ.pop('STRIPE_WEBHOOK_SECRET', None)
        booking.register_instructor('山田', 'y@example.com', '', ['SP-A'], '',
                                    _days_all())
        booking.set_state(booking.instructors()[0]['id'], '承認')
        booking.verify_email(booking.instructors()[0]['鍵'])

    def tearDown(self):
        os.environ.pop('STRIPE_SECRET_KEY', None)
        os.environ.pop('STRIPE_WEBHOOK_SECRET', None)

    def test_鍵が無ければカードを選ばせない(self):
        # 2026-08-17 社長ご指示で「銀行振込（前払い）」を足したので、支払方法の
        # 選択そのものは出る。⛔ ただしカードの選択肢は出さないこと（押した先で
        # 「未設定です」と断ることになる）。
        import payments
        self.assertFalse(payments.enabled())
        html = self.c.get('/book/SP-A').get_data(as_text=True)
        self.assertNotIn('value="card"', html)
        self.assertIn('value="invoice"', html)
        self.assertIn('value="bank"', html)
        t = _visible(html)
        self.assertIn('請求書払い', t)
        self.assertIn('銀行振込', t)
        self.assertNotIn('クレジットカード', t)

    def test_鍵が無いときにカードを指定されても請求書で受ける(self):
        # ⛔ 未設定の環境で「決済へ」を返さないこと（行き先が無い）
        antispam._RECENT.clear()
        r = self.c.post('/api/book', json={
            'course': 'SP-A', 'day': _far_day(), 'name': '鈴木',
            'email': 's@example.com', 'people': 1, 'pay': 'card',
            antispam.HONEYPOT_FIELD: '',
            'ts': antispam.issue_token(now=time.time() - 6)})
        j = r.get_json()
        self.assertTrue(j.get('ok'), j)
        self.assertNotIn('決済へ', j)
        self.assertEqual(booking.bookings()[0]['状態'], '申込受付')

    def test_決済待ちは申込受付にしない(self):
        rec, _ = booking.add_booking('SP-A', _far_day(), '鈴木',
                                     's@example.com', '', 1, '', pending=True)
        self.assertEqual(rec['状態'], booking.PENDING)

    def test_決済が終わって初めて成立する(self):
        rec, _ = booking.add_booking('SP-A', _far_day(), '鈴木',
                                     's@example.com', '', 1, '', pending=True)
        booking.attach_checkout(rec['id'], 'cs_test_1')
        got, inst = booking.mark_paid('cs_test_1', 'pi_1')
        self.assertIsNotNone(got)
        self.assertEqual(got['状態'], '申込受付')
        self.assertEqual(got['支払方法'], 'card')
        self.assertIsNotNone(inst)

    def test_同じ通知が二度来ても一度しか成立させない(self):
        # ⛔ Stripe は再送する。冪等でないと確認メールが何通も届く
        rec, _ = booking.add_booking('SP-A', _far_day(), '鈴木',
                                     's@example.com', '', 1, '', pending=True)
        booking.attach_checkout(rec['id'], 'cs_test_2')
        self.assertIsNotNone(booking.mark_paid('cs_test_2')[0])
        self.assertIsNone(booking.mark_paid('cs_test_2')[0])

    def test_決済されなければ席を解放する(self):
        d = _far_day()
        rec, _ = booking.add_booking('SP-A', d, '鈴木', 's@example.com', '',
                                     1, '', pending=True)
        booking.attach_checkout(rec['id'], 'cs_test_3')
        self.assertEqual(len(booking.bookings_for('SP-A', d)), 1)
        booking.mark_unpaid('cs_test_3')
        self.assertEqual(booking.bookings_for('SP-A', d), [])

    def test_放置された決済待ちは時間で席を返す(self):
        # ⛔ Stripe の期限切れ通知が届かなくても、席を永久に押さえない
        d = _far_day()
        rec, _ = booking.add_booking('SP-A', d, '鈴木', 's@example.com', '',
                                     1, '', pending=True)
        self.assertTrue(booking.is_live(rec))
        old = booking.now_jst() - timedelta(
            minutes=booking.payments_session_ttl_min() + 5)
        rows = booking.bookings()
        rows[0]['申込日時'] = old.strftime('%Y-%m-%d %H:%M')
        booking._save('bookings.json', rows)
        self.assertFalse(booking.is_live(booking.bookings()[0]))
        self.assertEqual(booking.bookings_for('SP-A', d), [])

    def test_署名の無い通知は受け付けない(self):
        os.environ['STRIPE_WEBHOOK_SECRET'] = 'whsec_test'
        r = self.c.post('/api/stripe/webhook',
                        data=b'{"type":"checkout.session.completed"}',
                        content_type='application/json')
        self.assertEqual(r.status_code, 400)

    def test_偽の署名は受け付けない(self):
        import payments
        os.environ['STRIPE_WEBHOOK_SECRET'] = 'whsec_test'
        body = b'{"type":"checkout.session.completed"}'
        sig = f't={int(time.time())},v1=' + 'f' * 64
        self.assertIsNone(payments.verify_webhook(body, sig)[0])

    def test_正しい署名なら受け取れる(self):
        import hashlib
        import hmac as _h
        import json as _j
        import payments
        os.environ['STRIPE_WEBHOOK_SECRET'] = 'whsec_test'
        body = _j.dumps({'type': 'ping'}).encode('utf-8')
        ts = str(int(time.time()))
        v1 = _h.new(b'whsec_test', ts.encode() + b'.' + body,
                    hashlib.sha256).hexdigest()
        ev, err = payments.verify_webhook(body, f't={ts},v1={v1}')
        self.assertIsNone(err)
        self.assertEqual(ev['type'], 'ping')

    def test_古い署名は受け付けない(self):
        import hashlib
        import hmac as _h
        import payments
        os.environ['STRIPE_WEBHOOK_SECRET'] = 'whsec_test'
        body = b'{}'
        ts = str(int(time.time()) - payments.TOLERANCE_SEC - 60)
        v1 = _h.new(b'whsec_test', ts.encode() + b'.' + body,
                    hashlib.sha256).hexdigest()
        self.assertIsNotNone(payments.verify_webhook(body, f't={ts},v1={v1}')[1])

    def test_受信設定が無ければ通知を信じない(self):
        import payments
        self.assertIsNotNone(payments.verify_webhook(b'{}', 't=1,v1=x')[1])

    def test_円は100倍しない(self):
        # ⛔ 0桁通貨。×100すると請求が100倍になる
        import inspect
        import payments
        src = inspect.getsource(payments.create_checkout)
        self.assertIn("'unit_amount': price", src)
        self.assertNotIn('* 100', src)


class Test特商法の表記(unittest.TestCase):
    """⛔ 講座の売主は ZebraQuantum（教材もシステムも同社が開発・提供し、
    協会の看板で販売する商流）。⛔協会名を販売業者として書かないこと。
    """

    def setUp(self):
        self.c = app.test_client()
        self.html = self.c.get('/tokutei').get_data(as_text=True)

    def test_講座の販売業者はZebraQuantum(self):
        self.assertIn('株式会社ZebraQuantum', self.html)
        self.assertIn(booking.SELLER['officer'], self.html)

    def test_協会が受講料を受け取ると読める記述を残さない(self):
        # 社長ご判断 2026-08-17（A案）。協会サイトの「資金」欄が
        # 「会費、検定受験料、研修受講料、その他事業収入」となっており、
        # **協会が受講料を受け取る**と読めた。特商法の表記（販売業者＝
        # ZebraQuantum）と食い違うと「どちらが売主か」を突かれ、法人の経理・
        # 助成金の実績報告・収益事業判定のすべてで詰まる。
        # ⛔ 検定受験料は協会の収入なので消さないこと。
        t = _visible(self.c.get('/company-info').get_data(as_text=True))
        self.assertIn('検定受験料', t)
        self.assertNotIn('研修受講料', t)
        # 売主は1か所（booking.SELLER）から出す。協会名を販売業者にしない
        self.assertIn('株式会社ZebraQuantum', self.html)
        self.assertNotIn('販売業者名</th>\n                    <td>一般社団法人',
                         self.html)

    def test_講座にデジタルコンテンツの返金文言を使わない(self):
        # ⛔ 講座は開催日のある役務。動画教材の文言を流用しない
        self.assertNotIn('デジタルコンテンツのため', self.html)

    def test_提供していない支払方法を書かない(self):
        # 2026-08-17 実害。Stripe の鍵が入っていないのに、この法定表示だけが
        # 「クレジットカード決済（VISA、MasterCard、JCB…）」を掲げていた
        # ＝提供していない支払方法を表示していた。⛔決済手段を直書きしないこと。
        #   出どころは payments.enabled()（申込画面の選択肢と同じ判定）。
        import payments
        t = _visible(self.html)
        book = _visible(self.c.get('/book/SP-A').get_data(as_text=True))
        sub = _visible(self.c.get('/subsidy').get_data(as_text=True))
        if payments.enabled():
            self.assertIn('クレジットカード', t)
        else:
            for page, name in ((t, '特商法'), (book, '申込画面'), (sub, '助成金')):
                self.assertNotIn('クレジットカード', page, name)
                self.assertNotIn('カード払い', page, name)
            self.assertIn('請求書・銀行振込のみ', t)
        # ⛔ どちらの設定でも銀行振込は必ず載っていること
        self.assertIn('銀行振込', t)

    def test_キャンセル規定は1か所から出す(self):
        self.assertIn('13〜7日前', self.html)
        self.assertIn(booking.CANCEL_POLICY.split('／')[0].strip(), self.html)

    def test_1名から開催すると明記する(self):
        self.assertIn('お一人の場合でも開催', self.html)

    def test_申込画面から特商法へ行ける(self):
        booking.register_instructor('山田', 'z@example.com', '', ['SP-A'], '',
                                    _days_all())
        booking.set_state(booking.instructors()[-1]['id'], '承認')
        booking.verify_email(booking.instructors()[-1]['鍵'])
        html = self.c.get('/book/SP-A').get_data(as_text=True)
        self.assertIn('/tokutei', html)
        self.assertIn('株式会社ZebraQuantum', html)

    def test_特定継続的役務提供の線を越えていない(self):
        # ⛔ 越えたら概要書面・契約書面・クーリングオフの対応が要る。
        #    回数や間隔を変えたときに、ここで気づけるようにしてある
        self.assertEqual(booking.continuing_service_alerts(), {})

    def test_線を越えたら検知できる(self):
        # 判定そのものが効いていることを確かめる（効かない検査を置かない）
        booking.COURSE_BY_CODE['__TEST__'] = {
            'code': '__TEST__', 'name': '試', 'price': 68000,
            'days': 12, 'interval_days': 7}
        try:
            self.assertIsNotNone(booking.continuing_service_risk('__TEST__'))
        finally:
            booking.COURSE_BY_CODE.pop('__TEST__', None)


class Test助成金の判定(unittest.TestCase):
    """東京しごと財団 DXリスキリング助成金（令和8年度）。

    固定している事故の型:
      ・講座名から買い手を決めつけ、対象になる講座を対象外と案内する
        （2026-08-15 社長ご指摘。SP-A を「代表者向けだから対象外」と誤判定した）
      ・条件を書かずに「助成金対象」とだけ出す（自腹の受講は対象外なのに、
        申し込んでから受けられないと分かる＝いちばん信用を失う）
      ・金額を各ページに手打ちし、制度が変わった日に片方だけ古くなる
    """

    def setUp(self):
        _clear()
        self.c = app.test_client()

    def test_対象を決めるのは講座名ではなく研修時間(self):
        # ⛔ SP-A は「一人会社」の講座だが、法人が従業員を送れば対象になる
        self.assertTrue(booking.subsidy_for('SP-A')['eligible'])
        # SP-B・SP-C も、回ごとに独立した研修として掲載し直して対象になった
        # （2026-08-17）。⛔ 講座名や格で決めていないことを固定する。
        for code in ('SP-B', 'SP-C'):
            self.assertTrue(booking.subsidy_for(code)['eligible'], code)
        # 対象外になるのは立場（受講者が従業員でない）だけ
        for code in ('GK1', 'GK2', 'GK3'):
            s = booking.subsidy_for(code)
            self.assertFalse(s['eligible'], code)
            self.assertIn('従業員', s['reason'])
            self.assertNotIn('時間', s['reason'])

    def test_時間の境目で切り替わる(self):
        # 3時間以上10時間未満（GK1は3時間ちょうど＝時間の要件は満たす）
        self.assertEqual(booking.TRAINING_HOURS['GK1'], 3)
        self.assertEqual(booking.TRAINING_HOURS['GM-A'], 4)
        self.assertEqual(booking.TRAINING_HOURS['SP-A'], 6)

    def test_子どもは時間ではなく立場で対象外(self):
        # ⛔ 3時間ちょうどで時間の要件は満たすが、受講者が従業員でない
        s = booking.subsidy_for('GK1')
        self.assertFalse(s['eligible'])
        self.assertIn('従業員', s['reason'])

    def test_消費税を助成対象に含めない(self):
        # 税込59,600（受講料49,800＋認定試験の受験料9,800）
        #  → 税抜54,181 → その3/4 = 40,635
        # ⛔ 受験料を別の費目として差し引かないこと。DXリスキリング助成金の
        #    対象経費に「受験料」という費目は無く、受講料に含まれる1本の
        #    金額として申請する（2026-08-17）。
        s = booking.subsidy_for('SP-A')
        self.assertEqual(s['base'], 54181)
        self.assertEqual(s['grant'], 40635)
        self.assertEqual(s['net'], 59600 - 40635)

    def test_1研修あたりの上限を超えない(self):
        # ⛔ 上限は「1人1研修あたり」75,000円。分割掲載の講座は研修の本数だけ
        #    受けられるので、講座単位の合計で判定しないこと（2026-08-17）。
        for code in booking.subsidy_courses():
            s = booking.subsidy_for(code)
            self.assertLessEqual(s.get('grant_unit', s['grant']),
                                 booking.SUBSIDY['cap_per_person'], code)
            # 合計は 1研修あたり × 本数 でなければならない
            self.assertEqual(s['grant'],
                             s.get('grant_unit', s['grant']) * s['sessions'], code)

    def test_対象講座は24件(self):
        # 2026-08-17 社長ご指示で、長時間の講座を「回ごとに独立した研修」として
        # 掲載し直し、13講座を新たに対象化した（B/C・GC・SP-B・SP-C）。
        # ⛔ 子ども向け（GK1〜3）は受講者が従業員でないので時間に関係なく対象外。
        self.assertEqual(
            sorted(booking.subsidy_courses()),
            sorted(['SP-A', 'SP-B', 'SP-C', 'GA', 'GA-P', 'GB', 'GC', 'GD', 'GE',
                    'GM-A', 'GM-B', 'GM-C', 'GH-A', 'GH-B', 'GH-C',
                    'GF-A', 'GF-B', 'GF-C', 'GL-A', 'GL-B', 'GL-C',
                    'GN-A', 'GN-B', 'GN-C']))

    def test_1研修あたりが3時間以上10時間未満に収まる(self):
        # ⛔ 下限3時間も効く。夜間コース（1回2.5時間）を回ごとにばらすと
        #    下限を割って逆に対象外になる（GC・SP-C を2本にしているのはこのため）。
        for code, n in booking.SESSIONS.items():
            h = booking.unit_hours(code)
            self.assertGreaterEqual(h, booking.SUBSIDY['min_hours'], code)
            self.assertLess(h, booking.SUBSIDY['max_hours'], code)

    def test_分割掲載の受講料は1研修単価かける本数(self):
        # ⛔ 価格を手打ちしないこと（SESSIONS を触って価格を直し忘れる事故を防ぐ）
        for code, n in booking.SESSIONS.items():
            self.assertEqual(booking.COURSE_BY_CODE[code]['price'],
                             booking.UNIT_PRICE * n, code)

    def test_研修時間は全講座に登録されている(self):
        # ⛔ 未登録があると、その講座だけ判定できず黙って対象外になる
        for c in booking.COURSES:
            self.assertIn(c['code'], booking.TRAINING_HOURS, c['code'])

    def test_条件を書かずに助成金対象と出さない(self):
        tag = booking.subsidy_tag('SP-A')
        self.assertIn('法人研修なら', tag)
        # 2026-08-17：認定試験の受験料（¥9,800）を受講料に組み込んだので
        # ¥49,800 → ¥59,600、実質負担 ¥15,846 → ¥18,965。
        # ⛔ 受験料そのものの ¥9,800 は法人のご負担ではない（3/4が助成される）
        self.assertIn('18,965', tag)
        # ⛔ 例に SP-B を使わないこと＝2026-08-17 に対象になった。
        #    時間に関係なく対象外なのは子ども向けだけ。
        self.assertEqual(booking.subsidy_tag('GK1'), '')

    def test_掲載ページの金額は計算値と一致する(self):
        # ⛔ 旧「実質 ¥24,800〜」（事業外スキルアップの値）が残っていたら落とす
        import solo_ceo
        import vibe_coding_courses as vc
        import vibe_coding_industry as vi
        seen = list(solo_ceo.COURSES.values()) + list(vc.COURSES.values())
        for ind in vi.INDUSTRIES.values():
            seen += ind.get('courses') or []
        for c in seen:
            with self.subTest(course=c['code']):
                self.assertEqual(c['subsidy_text'],
                                 booking.subsidy_tag(c['code']))
                self.assertNotIn('24,800', c['subsidy_text'])

    def test_テンプレートに助成額を直書きしない(self):
        # ⛔ 2026-08-15 実害。module 側だけを見る検査は、テンプレートに散った
        #    旧「実質¥24,800〜」を1件も捕まえられなかった（落ちようがない検査）。
        #    画面のファイルを実際に読むこと
        tpl = os.path.join(os.path.dirname(HERE), 'templates')
        bad = []
        for name in os.listdir(tpl):
            if not name.endswith('.html'):
                continue
            body = io.open(os.path.join(tpl, name), encoding='utf-8').read()
            body = re.sub(r'\{#.*?#\}', '', body, flags=re.S)   # 注意書きは除く
            for m in re.findall(r'¥([0-9]{1,3},[0-9]{3})', body):
                # 受講料そのものは直書きでよい。助成後の金額だけを禁じる
                if m.replace(',', '') not in {
                        str(c['price']) for c in booking.COURSES}:
                    bad.append(f'{name}: ¥{m}')
        self.assertEqual(bad, [], '助成後の金額が直書きされています: %s' % bad)

    def test_旧助成金の金額が残っていない(self):
        # 事業外スキルアップ助成金（上限25,000円）の値。制度を切り替えたので
        # どこかに残っていたら、その画面だけ古い金額を出し続ける
        root = os.path.dirname(HERE)
        bad = []
        for d in (root, os.path.join(root, 'templates')):
            for name in os.listdir(d):
                if not name.endswith(('.html', '.py')):
                    continue
                p = os.path.join(d, name)
                body = io.open(p, encoding='utf-8').read()
                body = re.sub(r'\{#.*?#\}', '', body, flags=re.S)
                body = re.sub(r'^\s*#.*$', '', body, flags=re.M)
                if '24,800' in body or '24,900' in body:
                    bad.append(name)
        self.assertEqual(bad, [], '旧助成金の金額が残っています: %s' % bad)

    def test_実質のご負担を出す画面には必ず注釈を出す(self):
        # 社長ご指摘 2026-08-17「制度改正などにより、必ず補償が受けられることを
        # 保証するものではないという注釈があった方がいいのでは」→ そのとおりで、
        # 実測すると実質の金額を出している8ページのうち注釈があったのは
        # /subsidy の1行だけ（しかも「審査により決定」だけで、予算の上限・
        # 制度改正に触れていなかった）。金額だけが独り歩きすると、受けられ
        # なかった法人との間で「そう書いてあった」になる。
        # ⛔ 各画面に文を書き起こさないこと。出どころは booking の1か所。
        pages = ('/', '/vibe-coding', '/vibe-coding/course-ga',
                 '/solo-ceo/course-spa', '/vibe-coding/manufacturing',
                 '/subsidy', '/book/SP-A')
        bad = []
        for p in pages:
            t = _visible(self.c.get(p).get_data(as_text=True))
            if '実質' not in t:
                continue                       # 実質を出していない画面は対象外
            if ('保証するものではありません' not in t):
                bad.append(p)
        self.assertEqual(bad, [],
                         '実質のご負担を出しているのに注釈がない画面: %s' % bad)

    def test_注釈は制度改正と予算に触れる(self):
        # ⛔ 「審査により決定されます」だけにしないこと。社長のご指摘は
        #    「制度改正など」で受けられない場合があることの明示だった。
        for text in (booking.SUBSIDY_DISCLAIMER,
                     booking.SUBSIDY_DISCLAIMER_SHORT):
            self.assertIn('保証するものではありません', text)
            self.assertIn('制度', text)
            self.assertIn('予算', text)
        # 長い版は「表示している金額は満額支給の目安」まで言い切る
        self.assertIn('目安', booking.SUBSIDY_DISCLAIMER)

    def test_注釈を画面に手打ちしない(self):
        # ⛔ 制度が変わった日に、直し忘れた画面だけが古い言い方で残る
        root = os.path.dirname(HERE)
        bad = []
        for d in (root, os.path.join(root, 'templates')):
            for name in sorted(os.listdir(d)):
                if not name.endswith(('.html', '.py')) or name == 'booking.py':
                    continue
                body = io.open(os.path.join(d, name), encoding='utf-8').read()
                body = re.sub(r'\{#.*?#\}', '', body, flags=re.S)
                body = re.sub(r'^\s*#.*$', '', body, flags=re.M)
                if '保証するものではありません' in body:
                    bad.append(name)
        self.assertEqual(bad, [], '注釈が画面に直書きされています: %s' % bad)

    def test_対象講座には習得する知識技能がある(self):
        # ⛔ 無いと法人が研修計画を自分で書き起こすことになる（申請の障害）
        for code in booking.subsidy_courses():
            self.assertGreater(len(booking.dx_skills(code)), 30, code)

    def test_案内ページが出る(self):
        t = _visible(self.c.get('/subsidy').get_data(as_text=True))
        self.assertIn('4分の3', t)
        self.assertIn('代表者ご本人・個人事業主ご本人は対象外', t)
        self.assertIn('受講証明書', t)
        # 対象外の講座も理由つきで出す（黙って消さない）
        self.assertIn('SP-B', t)

    def test_申込画面に条件と期限が出る(self):
        booking.register_instructor('山田', 'y@example.com', '', ['SP-A'], '',
                                    _days_all())
        booking.set_state(booking.instructors()[0]['id'], '承認')
        booking.verify_email(booking.instructors()[0]['鍵'])
        t = _visible(self.c.get('/book/SP-A').get_data(as_text=True))
        # 2026-08-17：認定試験の受験料を組み込み ¥15,846 → ¥18,965
        self.assertIn('18,965', t)
        self.assertIn('代表者ご本人・個人事業主ご本人は対象外', t)
        self.assertIn('請求書払い', t)
        # ⛔ 期限は「何日前」ではなく実際の日付で出す
        want = (booking.today_jst() + timedelta(
            days=booking.SUBSIDY['lead_days'])).isoformat()
        self.assertIn(want, t)

    def test_対象外の講座に助成金の案内を出さない(self):
        # ⛔ 例に SP-C を使わないこと＝2026-08-17 に対象になった。
        booking.register_instructor('鈴木', 's@example.com', '', ['GK1'], '',
                                    _days_all(('GK1',)))
        booking.set_state(booking.instructors()[-1]['id'], '承認')
        booking.verify_email(booking.instructors()[-1]['鍵'])
        t = _visible(self.c.get('/book/GK1').get_data(as_text=True))
        self.assertNotIn('4分の3', t)


class Test背景と同じ色の文字を置かない(unittest.TestCase):
    """2026-08-15 ブラウザで実測して発見。濃紺の帯（.iv-head など）に
    同じ濃紺の文字を置いており、リンクが1文字も見えていなかった。

    ⛔ 「白背景のカードは文字色を必ず指定する」の裏返し。色は目で見ないと
       気づけないので、機械で照合する。
    ⛔ HTMLを読むだけの検査にしないこと。色の指定はCSSと style 属性の
       両方にあるので、同じファイル内で突き合わせる。
    """

    # 濃い背景を持つ帯（この中の文字は明るい色でなければ読めない）
    DARK = {'#0d1b3e', '#041f4e', '#312e81', '#1e3a5f', '#0f766e'}

    def test_濃い帯の中に同じ色の文字を置かない(self):
        tpl = os.path.join(os.path.dirname(HERE), 'templates')
        bad = []
        for name in sorted(os.listdir(tpl)):
            if not name.endswith('.html'):
                continue
            body = io.open(os.path.join(tpl, name), encoding='utf-8').read()
            body = re.sub(r'\{#.*?#\}', '', body, flags=re.S)
            # 「濃い背景」を宣言している要素の class 名を集める
            dark_cls = set()
            for m in re.finditer(r'\.([\w-]+)\s*\{[^}]*background\s*:\s*(#[0-9a-fA-F]{6})',
                                 body):
                if m.group(2).lower() in self.DARK:
                    dark_cls.add(m.group(1))
            for cls in dark_cls:
                # その class の子孫に、同じ色の文字色を指定していないか
                for m in re.finditer(r'\.' + re.escape(cls) +
                                     r'[^{]*\{[^}]*(?<![-\w])color\s*:\s*(#[0-9a-fA-F]{6})', body):
                    if m.group(1).lower() in self.DARK:
                        bad.append(f'{name}: .{cls} の中に {m.group(1)}')
            # style 属性での直書きも見る（同じ帯の中に置かれがち）
            for m in re.finditer(r'class="(' + '|'.join(map(re.escape, dark_cls or {'\0'})) +
                                 r')"[^>]*>(.{0,900}?)</div>', body, re.S):
                for c in re.findall(r'style="[^"]*(?<![-\w])color:\s*(#[0-9a-fA-F]{6})',
                                    m.group(2)):
                    if c.lower() in self.DARK:
                        bad.append(f'{name}: .{m.group(1)} の中の style に {c}')
        self.assertEqual(bad, [], '背景と同じ色の文字があります: %s' % bad)


class Test講師への割り当て(unittest.TestCase):
    """2026-08-15 社長ご判断で「担当回数が少ない順」に変更。

    ⛔ 「登録が早い順」に戻さないこと。最初に登録した1人に仕事が集中し、
       2人目以降は一度も声がかからない。マッチング事業で講師を失う
       いちばんの理由になる（変更前の実測：1講座に3件入ると全部同じ人）。
    ⛔ ただし「同じ日・同じ講座の2人目は同じ講師」は崩さないこと。
       崩すと同じ回が二重開催になる。
    """

    def setUp(self):
        _clear()
        app.logger.disabled = True
        self.codes = ['GA', 'GB', 'GD', 'GE', 'SP-A']
        self.days = booking.session_days(3)[4:12]
        self.toks = []
        for i in range(5):
            rec, tok = booking.register_instructor(
                f'講師{i + 1}', f'i{i}@example.com', '', self.codes, '',
                fee_agreed=booking.FEE_TERMS_VERSION)
            booking.verify_email(tok)
            booking.set_state(rec['id'], '承認')
            for d in self.days:
                booking.set_day_courses(tok, d, self.codes)
            self.toks.append(tok)
            time.sleep(0.02)          # 登録日時に差を付ける（同順位の検査用）

    def _names(self, code, n):
        out = []
        for k in range(n):
            _, inst = booking.add_booking(code, self.days[k], f'X{k}',
                                          f'x{k}@example.com', '', 1, '')
            out.append(inst['氏名'])
        return out

    def test_同じ講座でも別の日なら別の講師に回る(self):
        got = self._names('GB', 5)
        self.assertEqual(len(set(got)), 5, f'5名に回っていない: {got}')

    def test_一巡したら二巡目に入る(self):
        got = self._names('GB', 8)
        c = {}
        for n in got:
            c[n] = c.get(n, 0) + 1
        self.assertEqual(sorted(c.values()), [1, 1, 2, 2, 2], got)
        self.assertLessEqual(max(c.values()) - min(c.values()), 1,
                             f'差が2回以上ついている: {c}')

    def test_同じ回の2人目は同じ講師のまま(self):
        got = self._names('GB', 1)
        _, inst = booking.add_booking('GB', self.days[0], '2人目',
                                      'y@example.com', '', 1, '')
        self.assertEqual(inst['氏名'], got[0])

    def test_同じ回に何名来ても担当回数は1回(self):
        # ⛔ 申込の件数で数えないこと。講師の仕事は1回で、講師料も定額
        for k in range(3):
            booking.add_booking('GB', self.days[0], f'Z{k}',
                                f'z{k}@example.com', '', 1, '')
        inst = booking.find_instructor(self.toks[0])
        self.assertEqual(booking.assignment_counts().get(inst['id']), 1)

    def test_取り消した回は担当回数に数えない(self):
        rec, inst = booking.add_booking('GB', self.days[0], 'A',
                                        'a@example.com', '', 1, '')
        self.assertEqual(booking.assignment_counts().get(inst['id']), 1)
        booking.cancel_booking(rec['id'], '試験')
        self.assertIsNone(booking.assignment_counts().get(inst['id']))

    def test_同数なら登録が早い順で決まる(self):
        # ⛔ 並びが決定的でないと、同じ状況で毎回違う人に当たる
        first = self._names('GB', 1)[0]
        _clear()
        self.setUp()
        self.assertEqual(self._names('GB', 1)[0], first)

    def test_古い担当は数えない(self):
        # ⛔ 全期間で数えると、あとから入った講師が永久に有利になる
        self.assertGreater(booking.ASSIGN_WINDOW_DAYS, 0)
        rec, inst = booking.add_booking('GB', self.days[0], 'A',
                                        'a@example.com', '', 1, '')
        rows = booking.bookings()
        old = (booking.today_jst()
               - timedelta(days=booking.ASSIGN_WINDOW_DAYS + 10)).isoformat()
        rows[0]['希望日'] = old
        booking._save('bookings.json', rows)
        self.assertIsNone(booking.assignment_counts().get(inst['id']))


class Test開催日を運営が決める(unittest.TestCase):
    """2026-08-15 社長ご判断。講師は運営が決めた開催日からしか選べない。

    ⛔ 講師に自由に日を選ばせないこと。5名が別々の日を選ぶと申込が散り、
       1回あたりの人数が減る。講師料は1開催あたりの定額なので、開催回数が
       増えたぶんだけ利益がそのまま消える。
    固定している事故の型:
      ・開催日でない日に登録できてしまう（画面を通らない経路がある）
      ・複数回の講座が、毎週ではない曜日に置かれて途中で途切れる
      ・連日開催の講座が残り、開催日が連続しないため永久に成立しない
    """

    def setUp(self):
        _clear()
        app.logger.disabled = True
        self.c = app.test_client()
        rec, self.token = booking.register_instructor(
            '山田', 'y@example.com', '', ['SP-A'], '',
            fee_agreed=booking.FEE_TERMS_VERSION)
        booking.verify_email(self.token)
        booking.set_state(rec['id'], '承認')

    def test_開催日でない日は登録できない(self):
        d = date.today() + timedelta(days=30)
        while booking.is_session_day(d):
            d += timedelta(days=1)
        got, err = booking.set_day_courses(self.token, d.isoformat(), ['SP-A'])
        self.assertIsNone(got)
        self.assertIn('開催日ではありません', err)

    def test_開催日なら登録できる(self):
        got, err = booking.set_day_courses(self.token, _far_day(), ['SP-A'])
        self.assertIsNone(err)
        self.assertIsNotNone(got)

    def test_取り消しは開催日でなくてもできる(self):
        # ⛔ 規則を変えた後、過去に登録された日を消せなくしないこと
        d = date.today() + timedelta(days=30)
        while booking.is_session_day(d):
            d += timedelta(days=1)
        got, err = booking.set_day_courses(self.token, d.isoformat(), [])
        self.assertIsNone(err)

    def test_開催日でない日は受講者にも公開しない(self):
        d = date.today() + timedelta(days=30)
        while booking.is_session_day(d):
            d += timedelta(days=1)
        st = {x['日付']: x['状態'] for x in booking.open_days('SP-A')}
        # ⛔ 「予約締切」と出さないこと（締切は講師の都合で閉じた日の意味）
        self.assertEqual(st[d.isoformat()], '非開催日')

    def test_複数回の講座は毎週ある曜日に置く(self):
        # ⛔ 土曜（第2・第4だけ）に複数回の講座を置かないこと。第3週で途切れ、
        #    その講座は永久に成立しない（2026-08-15 実装中に実際に踏んだ）
        self.assertEqual(booking.multi_session_courses_ok(), [])

    def test_連日開催の講座を作らない(self):
        # ⛔ 開催日は連続しないので、連日の講座は構造的に成立しない
        bad = [c['code'] for c in booking.COURSES
               if booking.course_days(c['code']) > 1
               and booking.course_interval(c['code']) == 1]
        self.assertEqual(bad, [])

    def test_全講座が実際に成立する(self):
        # ⛔ 規則を変えたら、全27講座に「開始日にできる日」があることを確かめる。
        #    1つでも0日なら、その講座は永久に売れない
        codes = [c['code'] for c in booking.COURSES]
        rec, tok = booking.register_instructor(
            '全部', 'all@example.com', '', codes, '',
            fee_agreed=booking.FEE_TERMS_VERSION)
        booking.verify_email(tok)
        booking.set_state(rec['id'], '承認')
        for iso in booking.session_days(3):
            booking.set_day_courses(tok, iso, codes)
        inst = booking.find_instructor(tok)
        dead = [c for c in codes if not booking.startable_days(inst, c)]
        self.assertEqual(dead, [], f'開始日が0日の講座: {dead}')

    def test_開催日の決まりを画面に出す(self):
        t = _visible(self.c.get(
            f'/instructor/schedule/{self.token}').get_data(as_text=True))
        self.assertIn(booking.session_day_note(), t)


class Test担当講座の変更(unittest.TestCase):
    """2026-08-15 社長ご指摘（講師をすぐ5名集められる）を受けての実装。

    固定している事故の型:
      ・担当講座を1つ足しただけで、その人の日程が全部 予約カレンダーから消える
        （旧実装は状態ごと『申請中』へ戻していた）
      ・逆に、審査を通さずに担当を増やせてしまう
      ・受講者の申込が入っている講座を、本人が担当から外せてしまう
    """

    def setUp(self):
        _clear()
        app.logger.disabled = True
        self.c = app.test_client()
        rec, self.token = booking.register_instructor(
            '山田', 'y@example.com', '', ['GA', 'GB'], '',
            _days_all(('GA', 'GB')), fee_agreed=booking.FEE_TERMS_VERSION)
        booking.verify_email(self.token)
        booking.set_state(rec['id'], '承認')

    def _open(self, code):
        return sum(1 for d in booking.open_days(code) if d['状態'] == '予約可')

    def test_承認時に担当講座が承認済みになる(self):
        inst = booking.find_instructor(self.token)
        self.assertEqual(sorted(booking.approved_courses(inst)), ['GA', 'GB'])
        self.assertEqual(booking.pending_courses(inst), [])

    def test_講座を足しても既存の公開が止まらない(self):
        # ⛔ ここが今回の本題。旧実装ではGA・GBまで非公開になっていた
        before = self._open('GA')
        self.assertGreater(before, 0)
        got, err = booking.set_instructor_courses(self.token, ['GA', 'GB', 'GD'])
        self.assertIsNone(err)
        self.assertEqual(self._open('GA'), before)      # 止まっていない
        self.assertEqual(got['状態'], '承認')            # 申請中に戻さない

    def test_足した講座は審査を通すまで公開しない(self):
        booking.set_instructor_courses(self.token, ['GA', 'GB', 'GD'])
        self.assertEqual(self._open('GD'), 0)
        inst = booking.find_instructor(self.token)
        self.assertEqual(booking.pending_courses(inst), ['GD'])

    def test_運営が承認すると公開される(self):
        booking.set_instructor_courses(self.token, ['GA', 'GB', 'GD'])
        inst = booking.find_instructor(self.token)
        # 日程を入れ直す（担当に加わったので）
        booking.set_day_courses(self.token, _far_day(), ['GA', 'GB', 'GD'])
        booking.approve_courses(inst['id'])
        self.assertGreater(self._open('GD'), 0)

    def test_外した講座は公開されなくなる(self):
        booking.set_instructor_courses(self.token, ['GA'])
        self.assertEqual(self._open('GB'), 0)
        self.assertGreater(self._open('GA'), 0)

    def test_申込が入っている講座は外せない(self):
        day = _far_day()
        booking.add_booking('GA', day, '鈴木', 's@example.com', '', 1, '')
        got, err = booking.set_instructor_courses(self.token, ['GB'])
        self.assertIsNone(got)
        self.assertIn('GA', err)
        self.assertIn('外すことはできません', err)

    def test_登録し直しでも承認済みは残る(self):
        # ⛔ 講座を足す再登録で、既存の承認まで落とさないこと
        booking.register_instructor('山田', 'y@example.com', '',
                                    ['GA', 'GB', 'GD'], '',
                                    fee_agreed=booking.FEE_TERMS_VERSION)
        inst = booking.find_instructor(self.token)
        self.assertEqual(inst['状態'], '承認')
        self.assertEqual(sorted(booking.approved_courses(inst)), ['GA', 'GB'])
        self.assertEqual(booking.pending_courses(inst), ['GD'])

    def test_画面から変更できる(self):
        url = f'/instructor/schedule/{self.token}/courses'
        self.assertEqual(self.c.get(url).status_code, 200)
        r = self.c.post(url, data={'courses': ['GA', 'GD']})
        self.assertEqual(r.status_code, 200)
        self.assertIn('変更を保存しました', r.get_data(as_text=True))
        self.assertEqual(sorted(booking.find_instructor(self.token)['対応コース']),
                         ['GA', 'GD'])

    def test_予定画面から辿れる(self):
        t = self.c.get(f'/instructor/schedule/{self.token}').get_data(as_text=True)
        self.assertIn(f'/instructor/schedule/{self.token}/courses', t)

    def test_講師5名が同じ日に別々の講座を担当できる(self):
        # ⛔ 開催日を絞る運用の前提。ここが壊れると1日1講座しか売れない
        _clear()
        day = _far_day(40)
        codes = ['GA', 'GB', 'GD', 'GE', 'SP-A']
        for i in range(5):
            rec, tok = booking.register_instructor(
                f'講師{i}', f'i{i}@example.com', '', codes, '',
                fee_agreed=booking.FEE_TERMS_VERSION)
            booking.verify_email(tok)
            booking.set_state(rec['id'], '承認')
            booking.set_day_courses(tok, day, codes)
        who = set()
        for c in codes:
            rec, inst = booking.add_booking(c, day, 'x', f'{c}@example.com',
                                            '', 1, '')
            who.add(inst['id'])
        self.assertEqual(len(who), 5, '5講座が別々の講師に割り当たること')

    def test_同じ講座の2人目は同じ講師に寄る(self):
        # ⛔ 別の講師に割り当てると同じ日・同じ講座が二重開催になる
        day = _far_day()
        _, a = booking.add_booking('GA', day, 'A', 'a@example.com', '', 1, '')
        _, b2 = booking.add_booking('GA', day, 'B', 'b@example.com', '', 1, '')
        self.assertEqual(a['id'], b2['id'])


class Test赤字にしない(unittest.TestCase):
    """2026-08-15 社長ご指示「赤字にならないような工夫をすること大前提」。

    受講料は講義そのものの対価。会場を使う諸経費（会場費・機材費・講師の
    交通費／宿泊費）は**別途お見積り**にして、自社の固定費をゼロに保つ。

    固定している事故の型:
      ・会場費を受講料に含め、1名開催で赤字になる
      ・子ども向けを「親子で会場に来る」前提にして、いちばん単価の低い
        講座（GK1 ¥9,800）が会場費で即赤字になる
      ・追加費用を特商法に書かないまま請求する（表示義務違反）
    """

    def setUp(self):
        _clear()
        self.c = app.test_client()

    def test_全講座が1名で黒字(self):
        for c in booking.COURSES:
            with self.subTest(course=c['code']):
                self.assertGreater(booking.profit_at(c['code'], 1), 0)

    def test_人数が増えても原価は増えない(self):
        # 講師料は定額。2人目以降は受講料がまるごと利益に近づく
        a = booking.profit_at('SP-A', 1)
        b = booking.profit_at('SP-A', 2)
        self.assertGreater(b - a, booking.COURSE_BY_CODE['SP-A']['price'] * 0.9)

    def test_子ども向けも会場を前提にしない(self):
        # ⛔ 「親子で会場に来る」前提に戻さないこと（2026-08-15 社長ご指示）
        for code in ('GK1', 'GK2', 'GK3'):
            self.assertIn('オンライン', booking.delivery_label(code), code)
        self.assertGreater(booking.profit_at('GK1', 1), 0)

    def test_掲載ページの開催方法が1か所から出ている(self):
        import solo_ceo
        import vibe_coding_courses as vc
        import vibe_coding_industry as vi
        seen = list(solo_ceo.COURSES.values()) + list(vc.COURSES.values())
        for ind in vi.INDUSTRIES.values():
            seen += ind.get('courses') or []
        for c in seen:
            with self.subTest(course=c['code']):
                self.assertEqual(c['format'], booking.delivery_label(c['code']))
                # ⛔ 「会場＋オンライン同時開催」を既定に戻さない
                self.assertNotEqual(c['format'], '会場＋オンライン同時開催')

    def test_掲載ページの価格が台帳と一致する(self):
        # ⛔ 価格を掲載ページに手打ちしないこと。値上げのたびに片方だけ
        #    古くなり、安い方を見て申し込んだお客様に高い額を請求することになる
        import solo_ceo
        import vibe_coding_courses as vc
        import vibe_coding_industry as vi
        seen = list(solo_ceo.COURSES.values()) + list(vc.COURSES.values())
        for ind in vi.INDUSTRIES.values():
            seen += ind.get('courses') or []
        for c in seen:
            with self.subTest(course=c['code']):
                live = booking.COURSE_BY_CODE.get(c['code'])
                self.assertIsNotNone(live, c['code'])
                self.assertEqual(c['price_num'], live['price'])
                self.assertEqual(c['price'], '{:,}'.format(live['price']))

    def test_子どもページの価格も台帳から出す(self):
        t = _visible(self.c.get('/vibe-coding/kids').get_data(as_text=True))
        for code in ('GK1', 'GK2', 'GK3'):
            self.assertIn('{:,}'.format(booking.COURSE_BY_CODE[code]['price']),
                          t, code)
        # 値下げ前の価格が残っていたら落とす
        self.assertNotIn('29,800', t)
        self.assertNotIn('49,800', t)

    def test_画面の助成額が講座ごとに正しい(self):
        # ⛔ 代表値（GAの金額）を全講座に使い回さないこと（2026-08-15 実害）。
        #    GB を値上げした後も、LPの助成金の表だけ GB 行が ¥49,800／
        #    実質¥15,846 のまま残っていた（社長のご確認で発覚）。
        t = _visible(self.c.get('/vibe-coding').get_data(as_text=True))
        for code in ('GA', 'GB', 'GD', 'GE'):
            s = booking.subsidy_for(code)
            with self.subTest(course=code):
                self.assertIn('¥{:,}'.format(s['net']), t)
                self.assertIn('¥{:,}'.format(s['grant']), t)
        # GB の行が GA の金額になっていないこと
        i = t.find('GB: バイブコーディング実践')
        self.assertGreater(i, 0)
        row = t[i:i + 90]
        self.assertIn('{:,}'.format(booking.COURSE_BY_CODE['GB']['price']), row)
        self.assertNotIn('49,800', row)

    def test_法人向けは助成の上限を使い切る(self):
        # ⛔ 上限は「対象経費10万円まで3/4」。GA-P はそこにぴったり合わせてある
        s = booking.subsidy_for('GA-P')
        self.assertTrue(s['eligible'])
        self.assertGreaterEqual(s['grant'], booking.SUBSIDY['cap_per_person'] - 1)
        self.assertLessEqual(s['net'], 35100)

    def test_個人向けの入口を廃止しない(self):
        # ⛔ GA を消さないこと。助成金を使えない方（代表者ご本人・個人事業主
        #    ご本人）はこちらしか選べない。
        # 2026-08-17：認定試験の受験料を組み込んだので ¥49,800 → ¥59,600。
        #    ⛔ 値上げではない（同額の受験料が含まれるようになった）。
        #    守るのは「個人が選べるいちばん安い入口が残っていること」であって
        #    特定の金額ではない。⛔ 逆に、上乗せしてよいのは実際に提供する
        #    受験料ぶんだけ（値上げの隠れ蓑にしない）。
        ga = booking.COURSE_BY_CODE['GA']['price']
        self.assertEqual(ga, 49800 + booking.exam_fee('GA'))
        self.assertLess(ga, booking.COURSE_BY_CODE['GA-P']['price'])
        # 大人向けでいちばん安い＝個人の入口として機能している
        self.assertEqual(ga, min(c['price'] for c in booking.COURSES
                                 if c['code'] not in booking._SUBSIDY_NEVER))
        self.assertIn('GA', booking.subsidy_courses())

    def test_法人出張は1回いくらで人数に比例しない(self):
        # ⛔ 「1名あたり」に戻さないこと。1名で来られると市場の1/6になる
        one, _ = booking.corporate_quote(1, 1)
        ten, _ = booking.corporate_quote(1, 10)
        self.assertEqual(one, ten)                    # 10名までは同額
        self.assertEqual(booking.corporate_quote(3, 10)[0], ten * 3)
        self.assertGreater(booking.corporate_quote(1, 20)[0], ten)

    def test_法人出張の案内が画面に出る(self):
        t = _visible(self.c.get('/subsidy').get_data(as_text=True))
        self.assertIn('{:,}'.format(booking.CORPORATE['day_price']), t)
        self.assertIn('オーダーメイド研修', t)
        self.assertIn('会場費も助成の対象', t)

    def test_特商法に追加料金を書く(self):
        # ⛔ 「なし」に戻さないこと（会場開催では諸経費を請求する）
        t = _visible(self.c.get('/tokutei').get_data(as_text=True))
        self.assertIn('別途お見積り', t)
        self.assertIn('役務の提供場所', t)
        self.assertIn('オンライン開催：なし', t)

    def test_予約できる日が0件でもお取引の条件を出す(self):
        # ⛔ 諸経費・販売事業者・キャンセル規定を申込フォームの中に置かない
        #    こと。日程が無いとフォームごと消え、特定商取引法にかかわる
        #    表示まで画面から無くなる（2026-08-15 実害・全27講座で発生）。
        _clear()                          # 講師なし＝予約できる日は0件
        for code in ('GA', 'GA-P', 'GK1', 'GM-C'):
            with self.subTest(course=code):
                t = _visible(self.c.get('/book/' + code).get_data(as_text=True))
                self.assertIn('いまお選びいただける日程がありません', t)
                self.assertIn('別途お見積り', t)          # 諸経費
                self.assertIn(booking.SELLER['name'], t)  # 販売事業者
                self.assertIn('お一人からでも開催します', t)
                self.assertIn('13〜7日前', t)             # キャンセル規定

    def test_予約できる日が0件でも助成金の案内を出す(self):
        _clear()
        t = _visible(self.c.get('/book/GA-P').get_data(as_text=True))
        s = booking.subsidy_for('GA-P')
        self.assertIn('{:,}'.format(s['net']), t)
        # 対象外の講座には出さない（日程の有無に関わらず）
        # ⛔ 例に GC を使わないこと＝2026-08-17 に回ごとの研修として掲載し直して
        #    対象になった。時間に関係なく対象外なのは子ども向け（受講者が従業員でない）。
        t2 = _visible(self.c.get('/book/GK1').get_data(as_text=True))
        self.assertNotIn('4分の3', t2)

    def test_申込画面に開催方法と諸経費を出す(self):
        booking.register_instructor('山田', 'y@example.com', '', ['GK1'], '',
                                    _days_all(('GK1',)))
        booking.set_state(booking.instructors()[0]['id'], '承認')
        booking.verify_email(booking.instructors()[0]['鍵'])
        t = _visible(self.c.get('/book/GK1').get_data(as_text=True))
        self.assertIn('オンライン', t)
        self.assertIn('別途お見積り', t)


class Test受講証明書(unittest.TestCase):
    """⛔ 当社が発行できないと、法人は助成金を受け取れない（実績報告で必須）。"""

    def setUp(self):
        _clear()
        app.logger.disabled = True
        self.c = app.test_client()
        booking.register_instructor('山田', 'y@example.com', '', ['SP-A'], '',
                                    _days_all())
        booking.set_state(booking.instructors()[0]['id'], '承認')
        booking.verify_email(booking.instructors()[0]['鍵'])

    def _book(self, **kw):
        rec, _ = booking.add_booking('SP-A', _far_day(), '鈴木',
                                     's@example.com', '株式会社テスト', 1, '',
                                     **kw)
        return rec

    def test_必要な項目が揃う(self):
        d = booking.certificate_data(self._book()['id'])
        self.assertEqual(d['研修名'], 'SP-A AI経営 入門1日')
        self.assertEqual(d['企業名'], '株式会社テスト')
        self.assertEqual(d['総研修時間数'], 6)
        self.assertEqual(d['必要出席時間数'], 4.8)     # 8割
        self.assertEqual(d['教育機関'], booking.SELLER['name'])

    def test_出席時間はこちらで埋めない(self):
        # ⛔ 推測で埋めると虚偽の証明になる
        self.assertIsNone(booking.certificate_data(self._book()['id'])['出席時間数'])

    def test_カード払いは助成対象外だと分かる(self):
        rec = self._book(pending=True)
        booking.attach_checkout(rec['id'], 'cs_c1')
        booking.mark_paid('cs_c1')
        d = booking.certificate_data(rec['id'])
        self.assertIn('振込払いが要件', d['注意'])

    def test_合言葉がなければ出さない(self):
        rec = self._book()
        self.assertEqual(self.c.get(f'/admin/booking/{rec["id"]}/certificate')
                         .status_code, 403)
        r = self.c.get(f'/admin/booking/{rec["id"]}/certificate',
                       headers={'X-Admin-Token': 'test-admin'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()['総研修時間数'], 6)

    def test_無い申込は404(self):
        self.assertEqual(self.c.get('/admin/booking/xxxx/certificate',
                                    headers={'X-Admin-Token': 'test-admin'}
                                    ).status_code, 404)

    def test_申請に間に合うかを判定できる(self):
        # ⛔ _far_day は開催日まで前倒しするので、ここでは使わないこと
        #    （期限そのものの判定なので、開催日かどうかは関係ない）
        n = booking.SUBSIDY['lead_days']
        raw = lambda k: (date.today() + timedelta(days=k)).isoformat()
        self.assertTrue(booking.subsidy_deadline_ok(raw(n + 1)))
        self.assertFalse(booking.subsidy_deadline_ok(raw(n - 1)))


class Test協会サイトのヘッダーを明るく塗り替えない(unittest.TestCase):
    """2026-08-16 社長ご指摘「ヘッダーデザインなどが生成AI協会トップページの
    デザインと違う」。

    course_detail.html と thank_you.html だけが base.html のヘッダー・
    フッターを「白テーマ化」（白い固定バー／紺のロゴ・メニュー／明るい
    フッター）で上書きしており、講座の6ページ（course-ga/gap/gb/gc/gd/ge）
    と送信完了ページだけ、同じサイトを出たように見えていた。

    ⛔ 検査するのは「濃さ」であって上書きの有無ではない。kids・industry の
       ように背景を別の濃色（#09090b）に替えるのは、ロゴもメニューも白の
       ままなので協会サイトの顔として成立している。壊れるのは
       「文字が濃くなる／下地が明るくなる」ときだけ。
    ⛔ ページ固有の色は本文の中で完結させること（.course-body / .lp-body）。
    """

    # ⛔ BEM の要素（.nav-menu-list__item）は .nav-menu-list では拾えない
    #    （境界の (?![\w-]) に _ が引っかかる）。実際に書かれる形で並べること。
    CHROME = ('.header-nav', '.nav-menu-list', '.nav-menu-list__item',
              '.nav-profile', '.nav-logo', '.logo-text', '.logo-sub',
              '.hamburger', '.footer', '.footer__inner', '.footer__copyright')

    @staticmethod
    def _lum(css):
        """CSS の色から相対輝度を返す。読めない色は None（判定しない）。"""
        m = re.match(r'#([0-9a-fA-F]{6})$', css)
        if m:
            rgb = [int(m.group(1)[i:i + 2], 16) for i in (0, 2, 4)]
        else:
            m = re.match(r'rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)', css)
            if not m:
                return None
            rgb = [int(m.group(i)) for i in (1, 2, 3)]
        f = lambda v: (v / 255) / 12.92 if v / 255 <= 0.03928 \
            else (((v / 255) + 0.055) / 1.055) ** 2.4
        r, g, b = map(f, rgb)
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    def _rules(self, body):
        """ヘッダー・フッターに当たる規則を (選択子, 中身) で返す"""
        body = re.sub(r'\{#.*?#\}', '', body, flags=re.S)
        body = re.sub(r'/\*.*?\*/', '', body, flags=re.S)
        for m in re.finditer(r'([^{}]+)\{([^{}]*)\}', body):
            sel = m.group(1).strip()
            if any(re.search(re.escape(c) + r'(?![\w-])', sel) for c in self.CHROME):
                yield sel, m.group(2)

    def test_ヘッダーの文字を濃い色にしない(self):
        tpl = os.path.join(os.path.dirname(HERE), 'templates')
        bad = []
        for name in sorted(os.listdir(tpl)):
            if not name.endswith('.html') or name == 'base.html':
                continue
            body = io.open(os.path.join(tpl, name), encoding='utf-8').read()
            for sel, decl in self._rules(body):
                for v in re.findall(r'(?<![-\w])color\s*:\s*([^;!}]+)', decl):
                    L = self._lum(v.strip())
                    if L is not None and L < 0.18:
                        bad.append('%s: %s → color %s' % (name, sel, v.strip()))
        self.assertEqual(
            bad, [],
            'ヘッダー・フッターの文字を濃い色にしています（下地は協会サイトの'
            '濃紺なので読めません／その1ページだけ別サイトに見えます）: %s' % bad)

    def test_ヘッダーの下地を明るくしない(self):
        tpl = os.path.join(os.path.dirname(HERE), 'templates')
        bad = []
        for name in sorted(os.listdir(tpl)):
            if not name.endswith('.html') or name == 'base.html':
                continue
            body = io.open(os.path.join(tpl, name), encoding='utf-8').read()
            for sel, decl in self._rules(body):
                for v in re.findall(r'(?<![-\w])background(?:-color)?\s*:\s*([^;!}]+)',
                                    decl):
                    L = self._lum(v.strip())
                    if L is not None and L > 0.35:
                        bad.append('%s: %s → background %s' % (name, sel, v.strip()))
        self.assertEqual(
            bad, [],
            'ヘッダー・フッターの下地を明るくしています（協会サイトの'
            '他ページと違う顔になります）: %s' % bad)

    def test_ヘッダーを固定しない(self):
        """協会サイトのヘッダーはページと一緒に流れる。1ページだけ画面上端に
        貼り付くと、スクロール中ずっと別サイトのように見える。"""
        tpl = os.path.join(os.path.dirname(HERE), 'templates')
        bad = []
        for name in sorted(os.listdir(tpl)):
            if not name.endswith('.html') or name == 'base.html':
                continue
            body = io.open(os.path.join(tpl, name), encoding='utf-8').read()
            for sel, decl in self._rules(body):
                if '.header-nav' in sel and re.search(r'position\s*:\s*fixed', decl):
                    bad.append('%s: %s' % (name, sel))
        self.assertEqual(bad, [], 'ヘッダーを固定しているページがあります: %s' % bad)


class Testコース色を宣言として書く(unittest.TestCase):
    """2026-08-16 発見。COURSES の 'gradient' は「linear-gradient(...)」という
    *値* なのに、course_detail.html は `{{ c.gradient }};` と裸で書いていた。

    プロパティ名の無い宣言はブラウザがその1行だけ黙って捨てるので、
    ヒーロー・コースのバッジ・講師アイコン・「送信する」ボタンの色が
    4か所とも消え、申込ボタンは灰色＝押せないように見えていた。

    ⛔ エラーも出ず、テンプレートの見た目も自然なので、目で見るまで
       気づけない型。機械で固定する。
    """

    def test_値をそのまま宣言の位置に置かない(self):
        tpl = os.path.join(os.path.dirname(HERE), 'templates')
        bad = []
        for name in sorted(os.listdir(tpl)):
            if not name.endswith('.html'):
                continue
            body = io.open(os.path.join(tpl, name), encoding='utf-8').read()
            body = re.sub(r'\{#.*?#\}', '', body, flags=re.S)
            body = re.sub(r'/\*.*?\*/', '', body, flags=re.S)
            for n, line in enumerate(body.split('\n'), 1):
                s = line.strip()
                if not s.startswith('{{'):
                    continue
                # 直前にプロパティ名（`background:` 等）が無いまま値だけ置いた行
                if re.match(r'^\{\{[^}]*\}\}\s*;\s*$', s):
                    bad.append('%s:%d %s' % (name, n, s))
        self.assertEqual(
            bad, [],
            'プロパティ名の無いCSS宣言があります（ブラウザが黙って捨てます）: %s' % bad)


class Testページに絵文字を使わない(unittest.TestCase):
    """2026-08-16 社長ご指示「絵文字をよく使うのをやめてほしい。lucide.dev を使って
    プロフェッショナルなデザインにしてほしい」。

    それまで公開ページには絵文字が310箇所あった。絵文字は端末（Windows /
    iPhone / Android）ごとに絵柄も色も変わるので、法人のお客様に見せる講座案内
    としては見た目が定まらない。アイコンは icons.py（Lucide・ISC）に一本化した。

    ⛔ 検査するのは「実際に描画されたHTML」＝ソースを見るだけでは、
       HTMLの数値参照（&#128640; のような書き方）で書かれた絵文字を見逃す。
       実際に2026-08-16の初回調査で87個と数え、数値参照を戻したら310個だった。
    ⛔ コード中のコメントの ⛔ は対象外（利用者には出ない）。
    """

    # 絵文字・装飾記号。矢印（→）は文章の記号として使うので対象にしない。
    EMOJI = re.compile('[⌚-⏿☀-➿⬀-⯿'
                       '\U0001F000-\U0001FAFF]️?')

    PAGES = ['/', '/company-info', '/team-members', '/course', '/member', '/join-us',
             '/contact', '/gpu-guide', '/subsidy', '/tokutei', '/vibe-coding',
             '/vibe-coding/kids', '/vibe-coding/course-ga', '/vibe-coding/course-gb',
             '/vibe-coding/course-gc', '/vibe-coding/course-gd', '/vibe-coding/course-ge',
             '/vibe-coding/course-gap', '/vibe-coding/manufacturing',
             '/vibe-coding/healthcare', '/vibe-coding/finance', '/vibe-coding/logistics',
             '/vibe-coding/construction', '/book/GA', '/instructor/register', '/solo-ceo']

    def setUp(self):
        import app as _app
        self.c = _app.app.test_client()

    @staticmethod
    def _visible_text(body):
        """利用者の目に入る文字だけを取り出す。

        ⛔ 正規表現で <script>〜</script> を剥がす方法は使わないこと。
           2026-08-16 に実際に取りこぼした＝JSの中に "</script" を含む文字列が
           あると対応が1つずれ、剥がれない塊が残る。JSやCSSのコメントに書いた
           ⛔ を「ページに絵文字がある」と誤検知した。
        """
        from html.parser import HTMLParser

        class _T(HTMLParser):
            def __init__(self):
                super().__init__(convert_charrefs=True)
                self.skip = 0
                self.buf = []

            def handle_starttag(self, tag, attrs):
                if tag in ('script', 'style'):
                    self.skip += 1

            def handle_endtag(self, tag):
                if tag in ('script', 'style') and self.skip:
                    self.skip -= 1

            def handle_data(self, d):
                if not self.skip:
                    self.buf.append(d)

        t = _T()
        t.feed(body)
        return ''.join(t.buf)

    def test_公開ページに絵文字が出ない(self):
        bad = []
        for p in self.PAGES:
            r = self.c.get(p)
            if r.status_code != 200:
                continue
            found = self.EMOJI.findall(self._visible_text(r.get_data(as_text=True)))
            if found:
                bad.append('%s: %s' % (p, ''.join(sorted(set(found)))))
        self.assertEqual(bad, [], '絵文字が残っているページがあります: %s' % bad)

    def test_アイコンが実際に描かれている(self):
        """絵文字を消しただけで何も出ていない、という壊れ方を防ぐ。"""
        thin = []
        for p in ['/vibe-coding', '/vibe-coding/kids', '/vibe-coding/manufacturing',
                  '/solo-ceo', '/gpu-guide']:
            r = self.c.get(p)
            n = r.get_data(as_text=True).count('class="lc')
            if n < 3:
                thin.append('%s: %d個' % (p, n))
        self.assertEqual(thin, [], 'アイコンが描かれていないページがあります: %s' % thin)


class Testアイコン名が実在する(unittest.TestCase):
    """icons.icon() は知らない名前を例外にする（黙って空白にしない）。
    ⛔ その代わり、書き間違えると本番で500になる。ここで先に落とす。"""

    def test_テンプレートとモジュールが呼ぶアイコンはすべて登録済み(self):
        import icons
        root = os.path.dirname(HERE)
        known = icons.names()
        bad = []
        pat = re.compile(r"""icon\(\s*['"]([a-z0-9-]+)['"]""")
        for sub in ('', 'templates'):
            d = os.path.join(root, sub)
            for name in sorted(os.listdir(d)):
                if not name.endswith(('.html', '.py')):
                    continue
                body = io.open(os.path.join(d, name), encoding='utf-8-sig').read()
                for m in pat.finditer(body):
                    if m.group(1) not in known:
                        bad.append('%s: %s' % (name, m.group(1)))
        self.assertEqual(bad, [], '登録されていないアイコン名です: %s' % bad)

    def test_業界データのアイコン名がすべて登録済み(self):
        import icons
        import vibe_coding_industry as ind
        known = icons.names()
        bad = []
        for slug, c in ind.INDUSTRIES.items():
            for key in ('challenges', 'use_cases'):
                for item in c.get(key, []):
                    if item.get('icon') not in known:
                        bad.append('%s/%s: %r' % (slug, key, item.get('icon')))
        self.assertEqual(bad, [], '登録されていないアイコン名です: %s' % bad)

    def test_知らない名前は黙って空にせず例外にする(self):
        import icons
        with self.assertRaises(KeyError):
            icons.icon('そんなアイコンはない')

    def test_データURIの色が二重にエンコードされていない(self):
        """2026-08-16 実際に踏んだ。CSS の背景としてSVGを敷くとき、色の # を
        先に %23 にしてから quote() を通すと %2523 になり、色が無効になる。
        ブラウザはエラーを出さず線を描かないだけなので、画面から印が消えても
        「絵文字を消した」ように見えて気づけない。

        ⛔ url("data:image/svg+xml,…") の中に %25 が出たら二重エンコード。
        """
        root = os.path.dirname(HERE)
        bad = []
        for sub in ('', 'templates'):
            d = os.path.join(root, sub)
            for name in sorted(os.listdir(d)):
                if not name.endswith(('.html', '.py')):
                    continue
                body = io.open(os.path.join(d, name), encoding='utf-8-sig').read()
                for m in re.finditer(r'data:image/svg\+xml,([^"\')]+)', body):
                    if '%25' in m.group(1):
                        bad.append('%s: %s' % (name, m.group(1)[:60]))
        self.assertEqual(bad, [], 'データURIが二重エンコードされています: %s' % bad)


class Test協会サイトの背景を消さない(unittest.TestCase):
    """2026-08-16 社長ご指摘（2度目）「/vibe-coding/manufacturing のヘッダー
    デザインなどがトップページと違う」。

    業種別5ページ（manufacturing / healthcare / finance / logistics /
    construction）は body を #ffffff で塗り、協会サイトの背景
    （base.html の .particles-background）を display:none で消していた。
    すると真上にある協会ヘッダー（透明・白ロゴ・白メニュー）が白地に白で
    読めなくなるので、辻褄合わせでヘッダーだけ真っ黒の帯にしていた
    ＝これが「トップページとデザインが違う」の正体。

    ⛔ 既存の Test協会サイトのヘッダーを明るく塗り替えない では捕まらない。
       あちらは「ヘッダーの文字が濃いか／固定か」を見るので、
       「白い本文＋黒い帯」は素通りする。下地の側を見張るのがこの検査。
    """

    def _css(self, name):
        tpl = os.path.join(os.path.dirname(HERE), 'templates')
        body = io.open(os.path.join(tpl, name), encoding='utf-8').read()
        body = re.sub(r'\{#.*?#\}', '', body, flags=re.S)
        return re.sub(r'/\*.*?\*/', '', body, flags=re.S)

    def _templates(self):
        tpl = os.path.join(os.path.dirname(HERE), 'templates')
        for name in sorted(os.listdir(tpl)):
            if name.endswith('.html') and name != 'base.html':
                yield name

    def test_サイト背景を消さない(self):
        bad = []
        for name in self._templates():
            css = self._css(name)
            for m in re.finditer(r'([^{}]*(?:particles|polygon)-background[^{}]*)'
                                 r'\{([^{}]*)\}', css):
                if re.search(r'display\s*:\s*none', m.group(2)):
                    bad.append('%s: %s' % (name, m.group(1).strip()))
        self.assertEqual(
            bad, [],
            '協会サイトの背景を消しているページがあります（白くするのは本文の '
            'ラッパーだけにしてください）: %s' % bad)

    def test_bodyを明るい色で塗り替えない(self):
        """⛔ 白くするのは本文のラッパー（.lp-body / .course-body / .ind-body）。
        body ごと白くすると、ヘッダーとフッターまで巻き添えになる。"""
        bad = []
        for name in self._templates():
            css = self._css(name)
            for m in re.finditer(r'(^|\})\s*(html\s*,\s*)?body\s*\{([^{}]*)\}', css):
                for v in re.findall(r'background(?:-color)?\s*:\s*([^;!}]+)',
                                    m.group(3)):
                    L = Test協会サイトのヘッダーを明るく塗り替えない._lum(
                        v.strip().split()[0] if v.strip() else '')
                    if L is not None and L > 0.35:
                        bad.append('%s: body background %s' % (name, v.strip()))
        self.assertEqual(
            bad, [], 'body を明るく塗り替えているページがあります: %s' % bad)


class Test差し込んだJavaScriptをscriptで囲む(unittest.TestCase):
    """2026-08-16 発見。vibe_coding_industry.html の extra_js ブロックが

        {% block extra_js %}{{ page_js|safe }}{% endblock %}

    と <script> 無しで書かれていた。base.html の extra_js は中身をそのまま
    置くだけなので、囲み忘れると JavaScript が「ページ末尾の地の文」として
    印字され、しかも1行も実行されない。本番の業種別5ページはこの状態で、
    ヒーローの粒子・FAQの開閉・お問い合わせの「送信する」が全部死んでいた
    （submitInquiry is not defined）。

    ⛔ 画面が壊れて見えないので、目視でも気づけない（本文は普通に出る）。
    """

    def test_extra_jsに置いた変数はscriptで囲む(self):
        tpl = os.path.join(os.path.dirname(HERE), 'templates')
        bad = []
        for name in sorted(os.listdir(tpl)):
            if not name.endswith('.html') or name == 'base.html':
                continue
            body = io.open(os.path.join(tpl, name), encoding='utf-8').read()
            for m in re.finditer(
                    r'\{%-?\s*block\s+extra_js\s*-?%\}(.*?)\{%-?\s*endblock',
                    body, flags=re.S):
                chunk = re.sub(r'\{#.*?#\}', '', m.group(1), flags=re.S)
                if '{{' in chunk and '<script' not in chunk:
                    bad.append(name)
        self.assertEqual(
            bad, [],
            'JavaScript を <script> で囲まずに置いているページがあります'
            '（実行されず、地の文として画面に出ます）: %s' % bad)


class Test対象判定を画面に直書きしない(unittest.TestCase):
    """2026-08-17 実害。GC を「1研修6.25時間 × 全2研修」として掲載し直して
    助成の対象にしたのに、講座LPと業種別ページの5箇所が
    「助成金対象外（10時間超のため）」と**固定文字列**で出し続けていた。
    価格は自動で更新されるので、金額だけ新しく判定だけ古い、という
    いちばん質の悪いズレになる（法人はそれを見て申請を諦める）。
    ⛔ 対象／対象外は booking.subsidy_for() からしか出さないこと。
    """

    def test_対象外と固定文字列で書かない(self):
        import glob
        bad = []
        targets = (glob.glob(os.path.join(os.path.dirname(HERE), 'templates', '*.html'))
                   + glob.glob(os.path.join(os.path.dirname(HERE), 'vibe_coding*.py'))
                   + [os.path.join(os.path.dirname(HERE), 'solo_ceo.py')])
        for path in targets:
            body = io.open(path, encoding='utf-8').read()
            for ng in ('助成金対象外', '10時間超のため', '10時間以上のため'):
                # ⛔ 注意書き（このルールを説明するコメント）は除く
                for line in body.splitlines():
                    if ng in line and '⛔' not in line and '書かない' not in line:
                        bad.append('%s: %s' % (os.path.basename(path), line.strip()[:60]))
        self.assertEqual(
            bad, [],
            '助成金の対象判定が画面に直書きされています'
            '（構成を変えた日に、ここだけ古い判定を出し続けます）: %s' % bad)

    def test_対象の講座を対象外と表示しない(self):
        # 実際に描画して、対象の講座のページに「対象外」の断りが出ていないこと
        c = app.test_client()
        for path in ('/vibe-coding', '/vibe-coding/manufacturing'):
            html = c.get(path).get_data(as_text=True)
            self.assertNotIn('助成金対象外', html, path)


class Test講師が担当できなくなったとき(unittest.TestCase):
    """社長ご質問 2026-08-17「予約が入ったら講師に知らせたり、本人に受け付けさせ
    たり、間に入る管理者の手間が減るように作り込んでいるの？」
    → 通知は出ていたが、**講師が辞退する口が1つも無かった**。しかも依頼メールは
      「ご自身の予定画面からその日を『不可』にしてください」と案内しているのに、
      set_day_courses は予約の入った日を拒否する＝**できない操作を案内していた**。
      行き先は info@jgaia.org へのメールだけで、そこから先は運営が手で追っていた。

    固定している事故の型:
      ・講師の都合で受講者の予約が消える
      ・受講者へ自動で「中止」が届く（代わりを立てれば開催できるのに）
      ・理由なしで申告できる（運営が代わりを立てる判断ができない）
      ・申告したのに画面が変わらず、講師が何度も押す
      ・できない操作をメールで案内する
    """

    def setUp(self):
        _clear()
        app.logger.disabled = True
        self.c = app.test_client()
        booking.register_instructor('山田', 'y@example.com', '', ['SP-A'], '',
                                    _days_all())
        self.inst = booking.instructors()[0]
        booking.set_state(self.inst['id'], '承認')
        booking.verify_email(self.inst['鍵'])
        self.token = self.inst['鍵']
        self.day = _far_day()
        self.rec, _ = booking.add_booking('SP-A', self.day, '受講 太郎',
                                          's@example.com', 'A社', 2, '')

    def _say(self, **kw):
        body = {'token': self.token, 'iso': self.day, 'reason': '急な出張のため'}
        body.update(kw)
        return self.c.post('/api/instructor/unavailable', json=body)

    def test_申告できる(self):
        r = self._say()
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True))
        self.assertEqual(len(booking.replacement_waiting()), 1)

    def test_予約は取り消さない(self):
        # ⛔ 受講者との約束。別の講師を立てられれば開催できる
        self._say()
        rec = booking.bookings()[0]
        self.assertEqual(rec['状態'], '申込受付')
        self.assertTrue(booking.is_live(rec))

    def test_理由がなければ断る(self):
        for bad in ('', '   ', 'あ'):
            self.assertEqual(self._say(reason=bad).status_code, 400)
        self.assertEqual(booking.replacement_waiting(), [])

    def test_本人の鍵でなければ断る(self):
        self.assertEqual(self._say(token='nosuch').status_code, 400)
        self.assertEqual(self._say(iso='2030-01-01').status_code, 400)
        self.assertEqual(booking.replacement_waiting(), [])

    def test_申告済みは画面に出る(self):
        # ⛔ 届いたか分からないと、講師は何度も押す
        h = self.c.get('/instructor/schedule/%s' % self.token).get_data(as_text=True)
        self.assertIn('担当できなくなった', h)
        self.assertNotIn('運営に連絡済み', h)
        self._say()
        h = self.c.get('/instructor/schedule/%s' % self.token).get_data(as_text=True)
        self.assertIn('運営に連絡済み', h)

    def test_できない操作をメールで案内しない(self):
        # ⛔ 予約の入った日は set_day_courses が拒否する。その操作を案内しない
        src = io.open(os.path.join(os.path.dirname(HERE), 'booking_routes.py'),
                      encoding='utf-8').read()
        src = re.sub(r'^\s*#.*$', '', src, flags=re.M)
        self.assertNotIn('その日を「不可」にしてください', src)
        # 予約の入った日は、いまも本人には変更させない（受講者が待っている）
        got, err = booking.set_day_courses(self.token, self.day, [])
        self.assertIsNone(got)
        self.assertIn('予約が入っている', err)

    def test_受講者に自動で連絡しない(self):
        # ⛔ 代わりが立つか確かめる前に「中止」と伝わるのがいちばん重い
        src = io.open(os.path.join(os.path.dirname(HERE), 'booking_routes.py'),
                      encoding='utf-8').read()
        i = src.index('def api_instructor_unavailable')
        body = src[i:src.index('@app.route', i + 10)]
        # ⛔ 受講者へ直接メールを出す口を使わないこと。運営あて（notify_payload）
        #    だけを通す。⛔ 'to=' で探さないこと＝reply_to= に当たる（雑な検査）
        self.assertNotIn('resend.Emails.send', body)
        self.assertNotIn("'to':", body)
        self.assertIn('notify_payload', body)
        # 受講者の連絡先は「運営が連絡できるように本文へ載せる」だけ
        self.assertIn("b['連絡先']", body)


class Test請求書と入金(unittest.TestCase):
    """社長ご指示 2026-08-17「請求書の発行に着手して。銀行振込も受け付けるように」。
    それまで受講者に「お申し込み後に請求書をお送りします」と約束しながら、
    請求書を作る機能がどこにも無かった＝請求書払いの全件が手作業だった。

    固定している事故の型:
      ・振込先が空のまま請求書を出す（お客様が払えない）
      ・登録番号が無いのに適格請求書のように見せる（買手の控除の扱いが変わる）
      ・取り消した申込の請求書が出る
      ・請求書番号が出すたびに変わる（同じ請求が二重に見える）
      ・入金を二重に記録する／機械で自動に消し込む
      ・請求書払いと銀行振込を1つにまとめ、前払いの方に期日を伝えない
    """

    def setUp(self):
        _clear()
        app.logger.disabled = True
        self.c = app.test_client()
        booking.register_instructor('山田', 'y@example.com', '', ['SP-A'], '',
                                    _days_all())
        i = booking.instructors()[0]
        booking.set_state(i['id'], '承認')
        booking.verify_email(i['鍵'])
        self.day = _far_day()
        # ⛔ 元の値を決め打ちで戻さないこと。2026-08-17 に登録番号が実在の
        #    値になり、'' に戻す書き方だと以後のテストへ汚染が漏れる
        self._seller = dict(booking.SELLER)
        booking.SELLER['bank'] = 'テスト銀行 銀座支店 普通 1234567 ゼブラクオンタム(カ'

    def tearDown(self):
        booking.SELLER.update(self._seller)

    def _book(self, pay='invoice', people=1):
        rec, _ = booking.add_booking('SP-A', self.day, '受講 太郎',
                                     's@example.com', 'A社', people, '',
                                     pay=pay)
        return rec

    def test_振込先が未登録なら発行しない(self):
        # ⛔ 空のまま出すとお客様が払えない
        booking.SELLER['bank'] = '〔要記入：金融機関名…〕'
        rec = self._book()
        data, err = booking.invoice_data(rec['id'])
        self.assertIsNone(data)
        self.assertIn('お振込先が未登録', err)

    def test_請求書の中身(self):
        rec = self._book(people=2)
        d, err = booking.invoice_data(rec['id'])
        self.assertIsNone(err)
        self.assertEqual(d['合計_税込_円'], rec['請求額_円'])
        # ⛔ 税は割り戻して出す（1円ずれない）
        self.assertEqual(d['小計_税抜_円'] + d['消費税_円'], d['合計_税込_円'])
        self.assertEqual(d['数量'], 2)
        self.assertEqual(d['単価_円'], rec['受講料_円'])
        self.assertIn('テスト銀行', d['振込先'])

    def test_登録番号が無ければ適格請求書だと名乗らない(self):
        rec = self._book()
        booking.SELLER['invoice_no'] = ''
        d, _ = booking.invoice_data(rec['id'])
        self.assertEqual(d['登録番号'], '')
        self.assertIn('適格請求書ではありません', d['注記'])
        booking.SELLER['invoice_no'] = 'T2010001240988'
        d2, _ = booking.invoice_data(rec['id'])
        self.assertEqual(d2['登録番号'], 'T2010001240988')
        self.assertEqual(d2['注記'], '')

    def test_登録番号は実在の法人番号(self):
        # 2026-08-17 国税庁の法人番号公表サイトで照合済み
        #   2010001240988 = 株式会社ＺｅｂｒａＱｕａｎｔｕｍ（所在地も一致）
        # ⛔ 検査用数字が合わない番号を置かないこと（請求書が無効になる）
        no = self._seller['invoice_no']
        self.assertTrue(no.startswith('T') and len(no) == 14, no)
        body = no[1:]
        rev = [int(x) for x in body[1:][::-1]]
        s = sum(d * (1 if (i + 1) % 2 else 2) for i, d in enumerate(rev))
        self.assertEqual(int(body[0]), 9 - (s % 9), '検査用数字が合いません')

    def test_設定できているかを外から確かめられる(self):
        # ⛔ 「入ったかどうか」を推測で済ませないこと。振込先が未設定だと
        #    請求書が1枚も出せないのに、申込は普通に入り続ける
        #    ＝「請求書をお送りします」の約束だけが積み上がる。
        # ⛔ 口座番号そのものを出さないこと。
        import json
        d = json.loads(self.c.get('/healthz').get_data(as_text=True))
        self.assertEqual(d['seller_bank'], 'configured')
        self.assertEqual(d['invoice_no'], 'configured')
        self.assertNotIn('1234567', json.dumps(d, ensure_ascii=False))
        booking.SELLER['bank'] = ''
        d2 = json.loads(self.c.get('/healthz').get_data(as_text=True))
        self.assertEqual(d2['seller_bank'], 'missing')

    def test_口座番号をリポジトリに置かない(self):
        # ⛔ jqca/jgaia は公開リポジトリ（匿名で読める）。口座番号を置くと
        #    「口座が変わりました」型の詐欺の材料になり、履歴からも消せない。
        #    値は環境変数 SELLER_BANK で渡す。
        root = os.path.dirname(HERE)
        src = io.open(os.path.join(root, 'booking.py'), encoding='utf-8').read()
        self.assertIn("os.environ.get('SELLER_BANK'", src)
        for d in (root, os.path.join(root, 'templates')):
            for name in sorted(os.listdir(d)):
                if not name.endswith(('.py', '.html')):
                    continue
                body = io.open(os.path.join(d, name), encoding='utf-8').read()
                self.assertNotIn('2313611', body, '%s に口座番号がある' % name)

    def test_番号は何度出しても同じ(self):
        # ⛔ 出すたびに変わると、同じ請求が二重に見える
        rec = self._book()
        a, _ = booking.invoice_data(rec['id'])
        b, _ = booking.invoice_data(rec['id'])
        self.assertEqual(a['請求書番号'], b['請求書番号'])

    def test_取消の請求書は出さない(self):
        rec = self._book()
        booking.cancel_booking(rec['id'], '動作確認のため')
        d, err = booking.invoice_data(rec['id'])
        self.assertIsNone(d)
        self.assertIn('取り消され', err)

    def test_前払いと後払いで期日が違う(self):
        # ⛔ 1つにまとめないこと。お金をいただく順番が違う
        inv, _ = booking.invoice_data(self._book('invoice')['id'])
        _clear_bk = booking.bookings()
        bank, _ = booking.invoice_data(self._book('bank')['id'])
        self.assertIn('後払い', inv['支払方法'])
        self.assertIn('前払い', bank['支払方法'])
        # 前払いは開催日の7日前まで
        first = self.day
        want = (date.fromisoformat(first)
                - timedelta(days=booking.TRANSFER_DUE_DAYS)).isoformat()
        self.assertEqual(bank['支払期日'], want)
        # 後払いは発行日から30日
        self.assertEqual(inv['支払期日'],
                         (booking.today_jst()
                          + timedelta(days=booking.INVOICE_DUE_DAYS)).isoformat())

    def test_知らない支払方法は請求書払いに寄せる(self):
        # ⛔ 画面から来た値をそのまま入れない
        rec = self._book(pay='paypay')
        self.assertEqual(rec['支払方法'], 'invoice')

    def test_入金を記録できる(self):
        rec = self._book('bank')
        self.assertEqual(len(booking.unpaid_bookings()), 1)
        got, err = booking.mark_transfer_paid(rec['id'], note='テスト')
        self.assertIsNone(err)
        self.assertEqual(got['入金']['金額_円'], rec['請求額_円'])
        self.assertEqual(booking.unpaid_bookings(), [])
        # ⛔ 二重に記録しない
        _g, err2 = booking.mark_transfer_paid(rec['id'])
        self.assertIn('すでに入金済み', err2)

    def test_APIは合言葉が要る(self):
        rec = self._book()
        self.assertEqual(self.c.get('/admin/booking/%s/invoice' % rec['id'])
                         .status_code, 403)
        self.assertEqual(self.c.post('/api/booking/%s/paid' % rec['id'],
                                     json={}).status_code, 403)
        r = self.c.get('/admin/booking/%s/invoice?token=test-admin' % rec['id'])
        self.assertEqual(r.status_code, 200)
        self.assertIn('請求書番号', r.get_json())

    def test_申込画面で支払方法を選べる(self):
        h = self.c.get('/book/SP-A').get_data(as_text=True)
        self.assertIn('value="invoice"', h)
        self.assertIn('value="bank"', h)
        # ⛔ 文言を画面に手打ちしないこと
        self.assertIn(booking.PAY_METHODS['bank']['label'], h)

    def test_入金を機械で自動に消し込まない(self):
        # ⛔ 振込名義が申込者と違うのは普通にある。機械で当てると
        #    別の方の入金で確定してしまう
        src = io.open(os.path.join(os.path.dirname(HERE), 'booking.py'),
                      encoding='utf-8').read()
        self.assertNotIn('def auto_reconcile', src)
        routes = io.open(os.path.join(os.path.dirname(HERE),
                                      'booking_routes.py'),
                         encoding='utf-8').read()
        self.assertEqual(routes.count('mark_transfer_paid'), 1)


class Test申込を取り消せる(unittest.TestCase):
    """2026-08-17 発見。画面にキャンセルポリシーを出しているのに、運営が申込を
    取り消す口がどこにも無かった＝間違った申込・試験の申込が台帳に残り続け、
    定員と講師の枠を食う（本番で動作確認をしようとして気づいた）。

    固定している事故の型:
      ・合言葉なしで取り消せる（誰でも他人の申込を消せる）
      ・理由なしで取り消せる（後から誰も判断できない）
      ・行ごと消す（何件失ったかが残らない）
      ・取り消したのに席が空かない
    """

    def setUp(self):
        _clear()
        app.logger.disabled = True
        self.c = app.test_client()
        booking.register_instructor('山田', 'y@example.com', '', ['SP-A'], '',
                                    _days_all())
        i = booking.instructors()[0]
        booking.set_state(i['id'], '承認')
        booking.verify_email(i['鍵'])
        self.day = _far_day()
        self.rec, _ = booking.add_booking('SP-A', self.day, 'A', 'a@example.com',
                                          '', 1, '')

    def _cancel(self, **kw):
        body = {'reason': '動作確認のため'}
        body.update(kw)
        return self.c.post('/api/booking/%s/cancel' % self.rec['id'],
                           json=body, headers={'X-Admin-Token': 'test-admin'})

    def test_合言葉が無いと取り消せない(self):
        r = self.c.post('/api/booking/%s/cancel' % self.rec['id'],
                        json={'reason': '動作確認のため'})
        self.assertEqual(r.status_code, 403)
        self.assertEqual(booking.bookings()[0]['状態'], '申込受付')

    def test_理由が無いと取り消せない(self):
        self.assertEqual(self._cancel(reason='').status_code, 400)
        self.assertEqual(self._cancel(reason='は').status_code, 400)
        self.assertEqual(booking.bookings()[0]['状態'], '申込受付')

    def test_取り消すと席が空く(self):
        before = [d for d in booking.open_days('SP-A', months=4)
                  if d['日付'] == self.day][0]
        r = self._cancel()
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True))
        rows = booking.bookings()
        # ⛔ 行は消さない（何件失ったかが残る）
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['状態'], '取消')
        self.assertEqual(rows[0]['取消理由'], '動作確認のため')
        self.assertFalse(booking.is_live(rows[0]))
        after = [d for d in booking.open_days('SP-A', months=4)
                 if d['日付'] == self.day][0]
        self.assertGreater(after['残り'], before['残り'])

    def test_二重に取り消さない(self):
        self.assertEqual(self._cancel().status_code, 200)
        self.assertEqual(self._cancel().status_code, 404)

    def test_申込の一覧からidと証明書に辿れる(self):
        # ⛔ id を出す口が無いと、受講証明書（助成金の実績報告に必須）を
        #    事実上発行できない（2026-08-17 に本番でそうなっていた）
        r = self.c.get('/api/bookings')
        self.assertEqual(r.status_code, 403)          # 合言葉なしは拒否
        r = self.c.get('/api/bookings', headers={'X-Admin-Token': 'test-admin'})
        self.assertEqual(r.status_code, 200)
        j = r.get_json()
        self.assertEqual(j['件数'], 1)
        row = j['rows'][0]
        self.assertEqual(row['id'], self.rec['id'])
        self.assertTrue(row['席を押さえている'])
        r2 = self.c.get(row['証明書'] + '?token=test-admin')
        self.assertEqual(r2.status_code, 200)
        # 取り消しても一覧からは消さない（何件失ったかが残る）
        self._cancel()
        j2 = self.c.get('/api/bookings',
                        headers={'X-Admin-Token': 'test-admin'}).get_json()
        self.assertEqual(j2['件数'], 1)
        self.assertFalse(j2['rows'][0]['席を押さえている'])

    def test_無い申込は404(self):
        r = self.c.post('/api/booking/nosuch/cancel',
                        json={'reason': '動作確認のため'},
                        headers={'X-Admin-Token': 'test-admin'})
        self.assertEqual(r.status_code, 404)


class Test研修ごとに申し込める(unittest.TestCase):
    """社長ご指示 2026-08-17「20万円未満だと現場の担当者の決裁権限の内側」。

    値引きではなく**買う単位**で解く＝分割掲載の講座は「今回いくつ申し込むか」を
    選べるようにし、担当者が起案する金額を1研修 ¥110,000（税抜10万円）にする。
    全部お申し込みになれば受講料の合計は従来と同じ。

    固定している事故の型:
      ・画面から来た研修数をそのまま金額に使う（値引き放題になる）
      ・受講証明書に講座全体の時間を書く（財団は8割以上をこの数字で判定する）
      ・申し込んでいない回まで実施日に並べる（虚偽の証明）
      ・講師の枠・定員を申込研修数に合わせて緩める（当日に講師が居ない）
      ・カード決済に講座全体の金額を渡す
    """

    def setUp(self):
        _clear()
        booking.register_instructor('山田', 'y@example.com', '',
                                    ['GM-B', 'GA'], '',
                                    _days_all(('GM-B', 'GA')))
        i = booking.instructors()[0]
        booking.set_state(i['id'], '承認')
        booking.verify_email(i['鍵'])
        self.day = [d for d in booking.open_days('GM-B', months=4)
                    if d['講師数'] > 0][0]['日付']

    def _book(self, sessions=None, code='GM-B', day=None, people=1):
        rec, _ = booking.add_booking(
            code, day or self.day, 'テスト', 't@example.com', '株式会社A',
            people, '', sessions=sessions)
        return rec

    def test_1研修だけ申し込むと決裁ラインの内側になる(self):
        rec = self._book(1)
        self.assertEqual(rec['受講料_円'], booking.UNIT_PRICE)
        self.assertLess(rec['受講料_円'], 200000)
        # 税抜も20万円未満（稟議は税抜で見る）
        self.assertLess(rec['受講料_円'] / 1.1, 200000)

    def test_全部申し込めば合計は従来どおり(self):
        # ⛔ 値引きにしないこと
        rec = self._book(None)
        self.assertEqual(rec['受講料_円'],
                         booking.COURSE_BY_CODE['GM-B']['price'])
        self.assertEqual(rec['研修数'], booking.sessions_of('GM-B'))

    def test_画面から来た値をそのまま金額にしない(self):
        # ⛔ 範囲外・不正な値は必ず丸める（0や負で値引きされない）
        for bad, want in ((0, 1), (-5, 1), (99, 3), ('x', 3), (None, 3)):
            self.assertEqual(booking.normalize_sessions('GM-B', bad), want, bad)
        self.assertEqual(self._book(0)['受講料_円'], booking.UNIT_PRICE)
        self.assertEqual(self._book(99)['受講料_円'],
                         booking.COURSE_BY_CODE['GM-B']['price'])

    def test_人数は研修数と別に掛かる(self):
        rec = self._book(1, people=3)
        self.assertEqual(rec['請求額_円'], booking.UNIT_PRICE * 3)

    def test_申し込んでいない回を実施日に並べない(self):
        # ⛔ 受講証明書の実施日になる。出ない日を書けば虚偽の証明
        self.assertEqual(len(self._book(1)['開催日']), 1)
        self.assertEqual(len(self._book(2)['開催日']), 2)
        self.assertEqual(len(self._book(None)['開催日']), 3)

    def test_受講証明書の時間を申込研修数に合わせる(self):
        # 財団は「8割以上の受講」をこの数字で判定する
        full = booking.TRAINING_HOURS['GM-B']
        n = booking.sessions_of('GM-B')
        c1 = booking.certificate_data(self._book(1)['id'])
        self.assertEqual(c1['総研修時間数'], round(full / n, 2))
        self.assertEqual(c1['必要出席時間数'], round(full / n * 0.8, 1))
        # ⛔ 1研修あたりが助成の時間要件（3時間以上10時間未満）に収まること
        self.assertGreaterEqual(c1['総研修時間数'], booking.SUBSIDY['min_hours'])
        self.assertLess(c1['総研修時間数'], booking.SUBSIDY['max_hours'])
        cN = booking.certificate_data(self._book(None)['id'])
        self.assertEqual(cN['総研修時間数'], full)
        self.assertIn('全3研修のうち', cN['研修名'])

    def test_古い申込は全研修ぶんとして扱う(self):
        # ⛔ 研修数を持たない過去の行で証明書が壊れないこと
        rec = self._book(None)
        rows = booking.bookings()
        for r in rows:
            if r['id'] == rec['id']:
                r.pop('研修数', None)
                r.pop('全研修数', None)
        booking._save('bookings.json', rows)
        c = booking.certificate_data(rec['id'])
        self.assertEqual(c['総研修時間数'], booking.TRAINING_HOURS['GM-B'])

    def test_1本の講座には研修数の欄を出さない(self):
        # 「全1研修のうち1研修」は意味が無い
        day = [d for d in booking.open_days('GA', months=4)
               if d['講師数'] > 0][0]['日付']
        rec = self._book(None, code='GA', day=day)
        self.assertEqual(rec['受講料_円'], booking.COURSE_BY_CODE['GA']['price'])
        c = booking.certificate_data(rec['id'])
        self.assertNotIn('研修のうち', c['研修名'])
        html = app.test_client().get('/book/GA').get_data(as_text=True)
        # ⛔ JS は常に getElementById('bk-sessions') を呼ぶ（無ければ送らない）。
        #    見るのは「欄が出ているか」＝見出しの有無
        self.assertNotIn('今回お申し込みになる研修数', html)
        self.assertNotIn('<select id="bk-sessions"', html)

    def test_申込画面に研修数の欄と単価が出る(self):
        html = app.test_client().get('/book/GM-B').get_data(as_text=True)
        self.assertIn('bk-sessions', html)
        self.assertIn('今回お申し込みになる研修数', html)
        self.assertIn('{:,}'.format(booking.UNIT_PRICE), html)

    def test_1研修ずつ買えることを講座ページに書く(self):
        # ⛔ 画面の約束を実装より先に出さないこと（2026-08-17 に一度、申込は
        #    セットのみなのに「1研修ごとにお申し込みができます」と出ていた）。
        #    実装した以上は、買い方を分割掲載の全ページに出す。
        for p in ('/vibe-coding/course-gc', '/solo-ceo/course-spb',
                  '/vibe-coding/manufacturing'):
            html = app.test_client().get(p).get_data(as_text=True)
            self.assertIn('1研修ずつお申し込みいただけます', html, p)
        # 1本の講座には出さない
        html = app.test_client().get('/vibe-coding/course-ga').get_data(as_text=True)
        self.assertNotIn('1研修ずつお申し込みいただけます', html)

    def test_講師の枠と定員は全研修ぶんで押さえたまま(self):
        # ⛔ 1研修だけの申込でも、開催は予定どおり全回行う。講師の枠を
        #    緩めると当日に講師が居ない事故になる
        cap = booking.COURSE_BY_CODE['GM-B']['capacity']
        self._book(1, people=cap)
        with self.assertRaises(ValueError):
            self._book(1, people=1)

    def test_APIから研修数が届く(self):
        # ⛔ 画面→サーバーの配線が抜けていると、選んでも全研修ぶん請求される
        import antispam
        import time as _t
        antispam._RECENT.clear()
        app.logger.disabled = True
        r = app.test_client().post('/api/book', json={
            'course': 'GM-B', 'day': self.day, 'name': '鈴木 花子',
            'email': 's@example.com', 'company': '株式会社A', 'people': 1,
            'message': '', 'sessions': '1', 'pay': 'invoice',
            antispam.HONEYPOT_FIELD: '',
            'ts': antispam.issue_token(now=_t.time() - 6)})
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True))
        rows = booking.bookings()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['研修数'], 1)
        self.assertEqual(rows[0]['受講料_円'], booking.UNIT_PRICE)

    def test_カード決済に講座全体の金額を渡さない(self):
        import payments
        seen = {}

        def fake_post(path, fields):
            seen.update(fields)
            return {'url': 'https://example.com/x', 'id': 'cs_test'}, None

        orig = payments._post
        payments._post = fake_post
        try:
            course = booking.COURSE_BY_CODE['GM-B']
            payments.create_checkout(course, 1, 'a@example.com', 'bid',
                                     's', 'c', amount=booking.UNIT_PRICE)
        finally:
            payments._post = orig
        amounts = [v for k, v in seen.items() if k.endswith('[unit_amount]')]
        self.assertEqual(amounts, [booking.UNIT_PRICE])


class Test紹介ページから予約に行ける(unittest.TestCase):
    """社長ご質問 2026-08-17「紹介ページの最後のお問い合わせ・申込フォームは、
    講師の予定がある講座では非表示になるの？ それとも問い合わせという意味だけ？」
    → **どちらも実装されていなかった**。実測で /book/ へのリンクは
    一人会社の3講座にしかなく、バイブコーディングの23講座は日程が公開されても
    紹介ページから予約に行けず、「お問い合わせ・お申し込み」を名乗るフォームが
    メールを送るだけだった。

    固定している事故の型:
      ・日程があるのに予約への導線が出ない（お客様は /book/ を知らない）
      ・メールを送るだけのフォームが「お申し込み」を名乗る
        （予約台帳に入らない＝席も押さえず、講師も割り当たらず、
          受講証明書も出せない。申し込んだつもりの方をここで受けてしまう）
      ・日程が無いのに予約ボタンを出す（押した先が行き止まりに見える）
    """

    def setUp(self):
        _clear()
        self.c = app.test_client()

    def _open(self, code):
        booking.register_instructor('山田', 'y@example.com', '', [code], '',
                                    _days_all((code,)))
        i = booking.instructors()[0]
        booking.set_state(i['id'], '承認')
        booking.verify_email(i['鍵'])

    def test_日程が無いときは予約ボタンを出さない(self):
        # ⛔ 押した先が「いまお選びいただける日程がありません」になる
        for p in ('/vibe-coding/course-ga', '/vibe-coding/manufacturing'):
            h = self.c.get(p).get_data(as_text=True)
            self.assertNotIn('/book/', h, p)
            self.assertNotIn('開催日を見て申し込む', h, p)

    def test_日程があれば予約へ送る(self):
        self._open('GA')
        h = self.c.get('/vibe-coding/course-ga').get_data(as_text=True)
        self.assertIn('/book/GA', h)
        self.assertIn('開催日を見て申し込む', h)

    def test_日程があるフォームはお申し込みを名乗らない(self):
        # ⛔ ここはメールを送るだけで、予約台帳には入らない
        self._open('GA')
        t = _visible(self.c.get('/vibe-coding/course-ga').get_data(as_text=True))
        self.assertIn('お問い合わせ・ご相談', t)
        self.assertNotIn('お問い合わせ・お申し込み', t)
        self.assertIn('開催日を選ぶ画面', t)

    def test_業種別も講座ごとに切り替わる(self):
        # ⛔ 1つの講座に日程が入ったからといって、他の講座にも予約ボタンを
        #    出さないこと（講座ごとに講師の予定が違う）
        self._open('GM-A')
        h = self.c.get('/vibe-coding/manufacturing').get_data(as_text=True)
        self.assertIn('/book/GM-A', h)
        self.assertNotIn('/book/GM-B', h)
        self.assertNotIn('/book/GM-C', h)

    def test_判断の出どころは1か所(self):
        # ⛔ 各ページで open_days を数え直さないこと（判断がずれる）
        import solo_ceo
        self.assertEqual(solo_ceo.booking_summary('SP-A'),
                         booking.open_slots('SP-A'))
        root = os.path.dirname(HERE)
        src = io.open(os.path.join(root, 'vibe_coding_courses.py'),
                      encoding='utf-8').read()
        self.assertIn('open_slots', src)
        self.assertNotIn('open_days(', src)

    def test_子ども向けも予約に行ける(self):
        # ⛔ 「助成対象外だから予約導線も要らない」と読み替えないこと
        #    （2026-08-17 に実際そう書いて、この3講座の欠陥を検査ごと飛ばした）。
        #    助成の可否と、予約できるかどうかは別の話。
        h = self.c.get('/vibe-coding/kids').get_data(as_text=True)
        self.assertNotIn('/book/', h)               # 日程が無いうちは出さない
        self.assertIn('詳細・お申し込み', h)
        self._open('GK1')
        h = self.c.get('/vibe-coding/kids').get_data(as_text=True)
        self.assertIn('/book/GK1', h)
        self.assertIn('開催日を見て申し込む', h)
        # ⛔ 日程が入っていない他の2講座には出さない
        self.assertNotIn('/book/GK2', h)
        self.assertNotIn('/book/GK3', h)

    def test_掲載している全講座に紹介ページがある(self):
        # ⛔ 一覧に足した講座を、紹介ページの無いまま放置しないこと
        #    （どこからも辿れない講座になる）
        # ⛔ 全講座テストの一覧（tools/e2e_all_courses.INTRO）は業種別を
        #    ループで組み立てるので、コード名の直書きを探すのでは足りない。
        #    実際に読み込んで突き合わせる（⛔ 実行はしない＝副作用を出さない）。
        import importlib.util
        path = os.path.join(os.path.dirname(HERE), 'tools',
                            'e2e_all_courses.py')
        src = io.open(path, encoding='utf-8').read()
        head = src[:src.index('def reset()')]        # 一覧の定義までで切る
        ns = {'__name__': 'e2e_intro_only'}
        exec(compile(head[head.index('INTRO = {'):], path, 'exec'), ns)
        missing = [c['code'] for c in booking.COURSES
                   if c['code'] not in ns['INTRO']]
        self.assertEqual(missing, [],
                         '紹介ページが決まっていない講座: %s' % missing)

    def test_一人会社の講座は元から切り替わっている(self):
        # ⛔ 直したついでに壊さないこと
        h = self.c.get('/solo-ceo/course-spa').get_data(as_text=True)
        self.assertNotIn('/book/SP-A', h)
        self._open('SP-A')
        h = self.c.get('/solo-ceo/course-spa').get_data(as_text=True)
        self.assertIn('/book/SP-A', h)


class Test受講料の単位を出す(unittest.TestCase):
    """社長ご提案 2026-08-17「¥xxxx より ¥xxxx/人 の方がいいのでは？」。

    賛成した理由は見た目ではなく2つ。
      ・当社は「1名あたり」の講座と「1回あたり」の出張研修（10名まで同額）を
        同じサイトで併売している＝単位が無いと ¥330,000 を1開催まとめての額と
        読まれうる。金額が上がったぶん誤読の実害が大きい。
      ・DXリスキリング助成金の要件2＝「一般に公開された受講案内に**受講者
        1人1研修単位の経費**が明記されていること」。

    固定している事故の型:
      ・単位が一部のページにしか無い（2026-08-17 実測＝業種別だけ「/名」）
      ・分割掲載の講座に「1研修あたりいくら」が出ていない（時間数だけでは
        「経費」にならない。一人会社ページには1件も出ていなかった）
      ・子ども向けの「1組」に「/名」を当ててしまう（GK1・GK3 は親子1組の額）
    """

    def setUp(self):
        _clear()
        self.c = app.test_client()

    def test_大人向けの講座ページに単位が出る(self):
        for p in ('/vibe-coding', '/vibe-coding/course-ga', '/solo-ceo',
                  '/solo-ceo/course-spa', '/vibe-coding/manufacturing'):
            h = self.c.get(p).get_data(as_text=True)
            self.assertIn(booking.PRICE_UNIT, h, p)

    def test_分割掲載の講座は1研修あたりの金額を出す(self):
        # ⛔ 助成の要件2。⛔ 時間数だけでは「経費」にならない
        for p in ('/vibe-coding/course-gc', '/solo-ceo/course-spb',
                  '/vibe-coding/manufacturing', '/vibe-coding'):
            h = self.c.get(p).get_data(as_text=True)
            self.assertIn('1研修 ¥', h, p)

    def test_1研修あたりの金額は単価かける本数と合う(self):
        for code, n in booking.SESSIONS.items():
            note = booking.unit_price_note(code)
            self.assertIn('{:,}'.format(booking.UNIT_PRICE), note, code)
            self.assertIn('全{}研修'.format(n), note, code)
            self.assertIn(booking.PRICE_UNIT, note, code)
        # 1本の講座には出さない（「全1研修」は意味が無い）
        self.assertEqual(booking.unit_price_note('GA'), '')

    def test_子ども向けに名を当てない(self):
        # ⛔ GK1・GK3 は親子1組の額。「/名」を当てると1人分に見える
        h = self.c.get('/vibe-coding/kids').get_data(as_text=True)
        self.assertNotIn(booking.PRICE_UNIT, h)
        self.assertIn('1組', h)

    def test_単位を画面に手打ちしない(self):
        # ⛔ 出どころは booking.PRICE_UNIT の1か所。⛔ 子ども向けは単位が違うので
        #    このページだけ自前の表記でよい（1組・お一人）
        root = os.path.dirname(HERE)
        bad = []
        for d in (root, os.path.join(root, 'templates')):
            for name in sorted(os.listdir(d)):
                if not name.endswith(('.html', '.py')) or name in (
                        'booking.py', 'vibe_coding_kids.html'):
                    continue
                body = io.open(os.path.join(d, name), encoding='utf-8').read()
                body = re.sub(r'\{#.*?#\}', '', body, flags=re.S)
                body = re.sub(r'^\s*#.*$', '', body, flags=re.M)
                body = re.sub(r'/\*.*?\*/', '', body, flags=re.S)
                for line in body.splitlines():
                    if '/名（税込）' in line:
                        bad.append('%s: %s' % (name, line.strip()[:70]))
        self.assertEqual(bad, [], '単位が直書きされています: %s' % bad)


class Test認定試験を受講料に組み込む(unittest.TestCase):
    """社長ご指示 2026-08-17「JGAIAが実施している資格受験料を組み込む講座にして」。

    なぜ組み込むのか＝受験料のままでは、どの制度からも1円も出ないため。
      ・DXリスキリング助成金の助成対象経費（募集要項 p8）に「受験料」という
        費目は無い。⛔見積書に別行で立てたらその行は落ちる。
      ・「資格試験（講習を受講しなくても単独で受験して資格を得られるもの）」は
        助成対象外の研修（同 p7 ４（２）⑦）。QAI-Zen は講座が無料・受験料だけ
        有料＝この除外にそのまま当たる形だった。

    固定している事故の型:
      ・受験料を上乗せしたのに助成の枠を超え、法人の持ち出しが増える
      ・受講料に含めたのに講師料まで自動で上がる（試験は講師の仕事ではない）
      ・紹介ページにだけ書いて、申込画面・確認メールに出ない
      ・試験名や受験料を画面に手打ちし、変えた日にそこだけ古くなる
      ・子ども向け講座に受験を組み込む
    """

    def setUp(self):
        _clear()
        self.c = app.test_client()

    def test_子ども向けには組み込まない(self):
        # ⛔ 受験者にしないのが方針。助成の対象でもない
        for code in booking._SUBSIDY_NEVER:
            self.assertIsNone(booking.exam_for(code), code)
            self.assertEqual(booking.exam_note(code), '')

    def test_大人向けは全講座に組み込まれている(self):
        # ⛔ 1つでも抜けると、その講座だけ「受験料は別」になり案内が食い違う
        for c in booking.COURSES:
            if c['code'] in booking._SUBSIDY_NEVER:
                continue
            self.assertIsNotNone(booking.exam_for(c['code']), c['code'])

    def test_上乗せしても助成の枠に収まる(self):
        # ⛔ ここが本題。1研修あたりの税抜が10万円（＝助成上限75,000円の点）を
        #    超えると、上乗せ分がまるごと法人の持ち出しになる。
        for c in booking.COURSES:
            unit = c['price'] // booking.sessions_of(c['code'])
            self.assertLessEqual(unit, booking.UNIT_PRICE, c['code'])

    def test_分割掲載の講座には上乗せしない(self):
        # 1研修が既に上限ちょうど＝上乗せの余地がゼロ。据え置きで試験を含める
        for code in booking.SESSIONS:
            self.assertEqual(booking.COURSE_BY_CODE[code]['price'],
                             booking.UNIT_PRICE * booking.SESSIONS[code], code)
            self.assertIsNotNone(booking.exam_for(code), code)

    def test_法人の負担増は受験料の3分の1にとどまる(self):
        # これが本題＝受験料 ¥9,800 が、法人にとっては ¥3,119 になる。
        # 内訳: 受験料は税込なので税抜 8,909 に落ち、その3/4（6,681）が助成
        #       される。残り 9,800 − 6,681 = 3,119 が法人のご負担。
        # ⛔ 消費税は助成対象外なので「4分の1になる」ではない（2026-08-17 に
        #    実際に取り違えた）。率は SUBSIDY の値から導き、写さないこと。
        rate = booking.SUBSIDY['rate']
        tax = booking.SUBSIDY['tax_rate']
        for code in ('SP-A', 'GA', 'GD', 'GE', 'GM-A'):
            fee = booking.exam_fee(code)
            self.assertEqual(booking.COURSE_BY_CODE[code]['price'], 49800 + fee)
            self.assertEqual(booking.subsidy_for(code)['net'], 18965)
            # 組み込む前の実質負担は 15,846 だった
            grew = 18965 - 15846
            self.assertEqual(grew, 3119, code)
            self.assertLessEqual(grew, fee * (1 - rate / (1 + tax)) + 1, code)

    def test_講師料に受験料を含めない(self):
        # ⛔ 試験は協会が実施する＝講師の仕事ではない。受講料そのものの40%に
        #    すると、受験料を組み込んだ日に講師料が自動で上がる
        for c in booking.COURSES:
            code = c['code']
            self.assertEqual(booking.teaching_price(code),
                             c['price'] - booking.exam_fee(code), code)
            self.assertEqual(booking.instructor_fee(code),
                             int(round(booking.teaching_price(code)
                                       * booking.FEE_RATE)), code)

    def test_申込画面と確認画面に出る(self):
        # ⛔ 紹介ページだけに書かないこと。お申し込みの直前で「受験料は別では」と
        #    迷わせる。⛔ 確認メールの本文も同じ理由で出す（別テストで固定）
        booking.register_instructor('山田', 'y@example.com', '', ['SP-A'], '',
                                    _days_all())
        booking.set_state(booking.instructors()[0]['id'], '承認')
        booking.verify_email(booking.instructors()[0]['鍵'])
        t = _visible(self.c.get('/book/SP-A').get_data(as_text=True))
        self.assertIn('生成AIジェネラリスト検定', t)
        self.assertIn('受講料に', t)

    def test_講座ページに出る(self):
        for path, want in (('/vibe-coding/course-ga', '生成AIジェネラリスト検定'),
                           ('/vibe-coding/course-gb', '生成AIエンジニア認定'),
                           ('/solo-ceo/course-spa', '生成AIジェネラリスト検定'),
                           ('/vibe-coding/manufacturing', '生成AIジェネラリスト検定')):
            t = self.c.get(path).get_data(as_text=True)
            self.assertIn(want, t, path)

    def test_助成金のページに含まれる試験を出す(self):
        t = _visible(self.c.get('/subsidy').get_data(as_text=True))
        self.assertIn('生成AIジェネラリスト検定', t)
        self.assertIn('受講料に含まれています', t)
        # ⛔ 「受験料も助成されます」と書かないこと。助成されるのは受講料で、
        #    認定試験はその受講料に含まれる修了認定という位置づけ
        self.assertNotIn('受験料も助成', t)

    def test_試験名と受験料を画面に直書きしない(self):
        # ⛔ 出どころは booking.EXAMS の1か所。受験料を変えた日に、直し忘れた
        #    画面だけが古い額を出し続ける（助成額の直書きと同じ事故の型）
        names = [e['name'] for e in booking.EXAMS.values()]
        fees = {'{:,}'.format(e['fee']) for e in booking.EXAMS.values()}
        root = os.path.dirname(HERE)
        bad = []
        for d in (root, os.path.join(root, 'templates')):
            for name in sorted(os.listdir(d)):
                if not name.endswith(('.html', '.py')) or name == 'booking.py':
                    continue
                body = io.open(os.path.join(d, name), encoding='utf-8').read()
                body = re.sub(r'\{#.*?#\}', '', body, flags=re.S)
                body = re.sub(r'^\s*#.*$', '', body, flags=re.M)
                body = re.sub(r'/\*.*?\*/', '', body, flags=re.S)
                for line in body.splitlines():
                    if any(n in line for n in names) and any(f in line for f in fees):
                        bad.append('%s: %s' % (name, line.strip()[:70]))
        self.assertEqual(bad, [],
                         '試験名と受験料が画面に直書きされています: %s' % bad)

    def test_実装を教える講座にはエンジニア認定を割り当てる(self):
        # ⛔ 講座で教えない範囲の試験を割り当てないこと（受講者が落ちる＝
        #    受験料を含めたことが逆に信用を落とす）
        for code in ('GB', 'GC', 'GM-B', 'GM-C', 'GF-C'):
            self.assertEqual(booking.exam_for(code)['name'],
                             booking.EXAMS['engineer']['name'], code)
        for code in ('SP-A', 'GA', 'GA-P', 'GD', 'GE', 'GM-A'):
            self.assertEqual(booking.exam_for(code)['name'],
                             booking.EXAMS['generalist']['name'], code)

    def test_総研修時間数を試験のぶん水増ししない(self):
        # ⛔ 試験は受講後にオンラインで受ける。実際の研修時間と違う数字を
        #    申請書に書かせることになる
        self.assertEqual(booking.TRAINING_HOURS['SP-A'], 6)
        self.assertEqual(booking.TRAINING_HOURS['GM-A'], 4)


if __name__ == '__main__':
    unittest.main(verbosity=2)
