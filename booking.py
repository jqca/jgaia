# -*- coding: utf-8 -*-
"""講師の登録・承認と、コースごとの予約受付。

なぜこの形か（2026-08-09 社長ご指示）:
    ・講義はJQCA/JGAIAの講師候補の方に任せる
    ・兼業の方が多いので、直前の予約は入れない（開催の2週間以上先だけ）
    ・講師の都合が悪い日は「予約締切」と表示する
    ・講師が自分で「講義できる曜日と時間」を登録し、それが公開カレンダーに出る

⛔ 講師名簿を手で編集しないこと。2026-08-09時点で、手編集の名簿には
   架空の見本9名（example.com など）が入っており、週次点検が
   「稼働可能な講師9名」と誤報していた。登録は本人が画面から行う。

⛔ 承認していない講師の枠を公開しないこと。有料講座なので、
   審査前の人が表に出ると取り返しがつかない。

決定事項（2026-08-09 社長承認）:
    最少催行人数  SP-A 4名 / SP-B 3名 / SP-C 5名（その他は4名）
    支払い        請求書（銀行振込）。決済は導入しない
    キャンセル    14日前まで無料 / 13〜7日前 50% / 6日前以降 100%
"""
import json
import os
import secrets
import threading
from datetime import date, datetime, timedelta, timezone

JST = timezone(timedelta(hours=9))
_LOCK = threading.Lock()

# 予約は開催日の何日以上先から受けるか（兼業の講師に準備期間を残す）
LEAD_DAYS = 14

# 講座の一覧。⛔価格・時間は各コースページの掲載値と一致させること
COURSES = [
    {'code': 'SP-A', 'name': 'AI経営 入門1日', 'price': 49800,
     'hours': '10:00〜17:00', 'min_people': 4, 'capacity': 20},
    {'code': 'SP-B', 'name': 'AI経営 実践3日間マスター', 'price': 128000,
     'hours': '10:00〜17:00 × 3日間', 'min_people': 3, 'capacity': 15},
    {'code': 'SP-C', 'name': 'AI経営 夜間マスター 全5回', 'price': 68000,
     'hours': '毎週水曜 19:00〜21:30', 'min_people': 5, 'capacity': 30},
    {'code': 'GA', 'name': '生成AI入門1日', 'price': 49800,
     'hours': '10:00〜17:00', 'min_people': 4, 'capacity': 20},
    {'code': 'GB', 'name': 'バイブコーディング実践1日', 'price': 49800,
     'hours': '10:00〜17:00', 'min_people': 4, 'capacity': 20},
    {'code': 'GD', 'name': 'AIセキュリティ・ガバナンス', 'price': 49800,
     'hours': '10:00〜17:00', 'min_people': 4, 'capacity': 20},
    {'code': 'GE', 'name': 'AIクリエイティブデザイン', 'price': 49800,
     'hours': '10:00〜17:00', 'min_people': 4, 'capacity': 20},
]
COURSE_BY_CODE = {c['code']: c for c in COURSES}

WEEKDAYS = ['月', '火', '水', '木', '金', '土', '日']

CANCEL_POLICY = ('開催14日前まで：無料 ／ 13〜7日前：受講料の50% ／ '
                 '6日前〜当日：受講料の100%')
PAY_NOTE = 'お支払いは請求書（銀行振込）です。お申し込み後に請求書をお送りします。'


# ────────────────────────────── 保存先
def _dir():
    d = os.environ.get('INQUIRY_LOG_DIR') or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'data')
    os.makedirs(d, exist_ok=True)
    return d


def _path(name):
    return os.path.join(_dir(), name)


def _load(name, default):
    p = _path(name)
    if not os.path.exists(p):
        return default
    try:
        # ⛔ open を閉じずに渡さないこと。読むだけでも取っ手が溜まり、
        #    Windows では次の os.replace（保存）が失敗しうる
        with open(p, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        # ⛔ 壊れていても既存を上書きしない。空を返して気づけるようにする
        return default


def _save(name, data):
    p = _path(name)
    with _LOCK:
        tmp = p + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, p)


def now_jst():
    return datetime.now(JST)


def today_jst():
    return now_jst().date()


# ────────────────────────────── 講師
def instructors():
    return _load('instructors.json', [])


def approved_instructors():
    return [i for i in instructors() if i.get('状態') == '承認']


def find_instructor(token):
    for i in instructors():
        if i.get('鍵') == token:
            return i
    return None


def register_instructor(name, email, org, courses, note, weekly):
    """講師候補の申請を受ける。戻り値: (講師, 本人用の鍵)

    ⛔ 状態は必ず『申請中』で始める。ここで承認にしてはいけない。

    ⛔ 謝礼の希望額はここでは受け取らない（2026-08-11 社長ご指示で
       登録フォームから削除）。謝礼はご相談のうえ、書面かメールで
       条件をお示ししてから発注する。項目を戻さないこと。
    """
    name = (name or '').strip()
    email = (email or '').strip()
    courses = [c for c in (courses or []) if c in COURSE_BY_CODE]
    if not name or not email:
        raise ValueError('お名前とメールアドレスをご入力ください')
    # ⛔ 担当講座が空の登録を通さないこと。どのコースにも出てこない
    #    「登録したのに一度も声がかからない講師」が出来る（本人には理由が見えない）
    if not courses:
        raise ValueError('担当できる講座を1つ以上お選びください')
    rows = instructors()
    token = secrets.token_urlsafe(16)
    rec = {
        'id': secrets.token_hex(8),
        '鍵': token,                       # 本人が自分の予定を編集するための鍵
        '氏名': name, '連絡先': email, '所属': org,
        '対応コース': courses,
        '備考': note,
        '状態': '申請中',                   # 申請中 / 承認 / 見送り
        '毎週の可能時間': weekly,           # [{'曜日':5,'開始':'10:00','終了':'17:00'}]
        '不可の日': [],                     # ['2026-09-03', ...]
        '登録日時': now_jst().strftime('%Y-%m-%d %H:%M'),
    }
    rows.append(rec)
    _save('instructors.json', rows)
    return rec, token


def set_state(instructor_id, state):
    """承認／見送りを記録する。該当が無ければ False を返す。

    ⛔ 見つからなくても成功を返さないこと。運営が［承認する］を押したのに
       何も変わらない、という壊れ方が黙って起きる（押した側は気づけない）。
    """
    rows = instructors()
    hit = False
    for r in rows:
        if str(r.get('id')) == str(instructor_id):
            r['状態'] = state
            r['判定日時'] = now_jst().strftime('%Y-%m-%d %H:%M')
            hit = True
    if hit:
        _save('instructors.json', rows)
    return hit


def update_availability(token, weekly, blocked):
    """講師本人が自分の予定を書き換える。

    ⛔ すでに受講者の申込が入っている日は閉じられない。約束した日を
       あとから一方的に消せると、受講料をいただいた講座が無人になる。
       日程の変更が必要なときは運営（info@jgaia.org）が個別に調整する。
    """
    rows = instructors()
    hit = None
    for r in rows:
        if r.get('鍵') == token:
            booked = set(booked_days_for_instructor(r.get('id')))
            r['毎週の可能時間'] = weekly
            r['不可の日'] = sorted(set(blocked) - booked)
            r['更新日時'] = now_jst().strftime('%Y-%m-%d %H:%M')
            hit = r
    if hit:
        _save('instructors.json', rows)
    return hit


# ────────────────────────────── 予約できる日
def _weekly_days(inst):
    return {int(w.get('曜日')) for w in (inst.get('毎週の可能時間') or [])
            if str(w.get('曜日')).isdigit()}


def instructor_free_on(inst, d, booked=None):
    """その講師がその日に講義できるか。

    booked にその講師の予約済みの日を渡すと、その日は「空いている」扱いにする。
    ⛔ ここを落とすと、1人目の申込が入った日を講師が週の設定から外した瞬間に
       2人目が申し込めなくなり、最少催行に届かず開催できない（申込は残る）。
    """
    iso = d.isoformat()
    if booked and iso in booked:
        return True
    if iso in (inst.get('不可の日') or []):
        return False
    return d.weekday() in _weekly_days(inst)


def open_days(course_code, months=3):
    """予約できる日を返す。

    条件:
      ・開催日が LEAD_DAYS 日以上先（兼業の講師に準備期間を残す）
      ・そのコースを担当できる承認済み講師が1名以上空いている
    ⛔ 「空いている日だけ」を返すのではなく、全日を状態つきで返す。
       閉じている日も見せないと「いつなら空くのか」が伝わらない。
    """
    start = today_jst()
    limit = start + timedelta(days=31 * months)
    earliest = start + timedelta(days=LEAD_DAYS)
    people = [i for i in approved_instructors()
              if course_code in (i.get('対応コース') or [])]
    # 予約済みの日は1回だけ集める（日ごとにファイルを読むと3か月ぶんで90回になる）
    booked = {i['id']: set(booked_days_for_instructor(i['id'])) for i in people}
    # その日までに埋まっている人数
    cap = (COURSE_BY_CODE.get(course_code) or {}).get('capacity', 10**6)
    taken = {}
    for b in bookings():
        if b.get('コース') == course_code:
            taken[b.get('希望日')] = taken.get(b.get('希望日'), 0) + int(b.get('人数') or 1)

    out = []
    d = start
    while d <= limit:
        if d < earliest:
            state, who = '準備期間', []
        else:
            who = [i for i in people
                   if instructor_free_on(i, d, booked.get(i['id']))]
            state = '予約可' if who else '予約締切'
            # ⛔ 定員に達した日を「予約可」のまま出さないこと。押してから
            #    「残り0名です」と断ることになり、選び直しの手間を増やす
            if state == '予約可' and taken.get(d.isoformat(), 0) >= cap:
                state = '予約締切'
        out.append({'日付': d.isoformat(), '状態': state,
                    '講師数': len(who),
                    '申込人数': taken.get(d.isoformat(), 0),
                    '残り': max(0, cap - taken.get(d.isoformat(), 0)),
                    '講師': [i['氏名'] for i in who]})
        d += timedelta(days=1)
    return out


def pick_instructor(course_code, d):
    """その日に割り当てる講師を決める。登録が早い方から。

    ⛔ 「講師未定」で受講者に案内しない。予約が成立した時点で確定させる。
    """
    # 同じ日に既に担当が決まっている講師を優先する（2人目の申込を同じ講師に寄せる）。
    # ⛔ 別の講師を割り当てると、同じ日・同じコースが二重開催になる
    people = [i for i in approved_instructors()
              if course_code in (i.get('対応コース') or [])
              and instructor_free_on(i, d, booked_days_for_instructor(i['id']))]
    same_day = {b.get('担当講師id') for b in bookings_for(course_code, d.isoformat())}
    people.sort(key=lambda i: (i['id'] not in same_day, i.get('登録日時') or ''))
    return people[0] if people else None


# ────────────────────────────── 申込
def bookings():
    return _load('bookings.json', [])


def bookings_for(course_code, day):
    return [b for b in bookings()
            if b.get('コース') == course_code and b.get('希望日') == day
            and b.get('状態') != '取消']


def booked_days_for_instructor(instructor_id):
    """その講師に既に予約が入っている日。

    ⛔ 予約が入っている日を、本人が「不可」に変えられないようにするために使う
       （受講者が待っている日を静かに閉じられると事故になる）。
    """
    return sorted({b['希望日'] for b in bookings()
                   if b.get('担当講師id') == instructor_id
                   and b.get('状態') != '取消'})


def add_booking(course_code, day, name, email, company, people, message):
    """申込を1件受ける。戻り値: (申込, 割り当てた講師 or None)"""
    course = COURSE_BY_CODE.get(course_code)
    if not course:
        raise ValueError('コースが見つかりません')
    name = (name or '').strip()
    email = (email or '').strip()
    if not name or not email:
        raise ValueError('お名前とメールアドレスをご入力ください')
    d = date.fromisoformat(day)
    if d < today_jst() + timedelta(days=LEAD_DAYS):
        raise ValueError(f'開催日は{LEAD_DAYS}日以上先をお選びください')
    # ⛔ 講師が決まらない申込を作らないこと。「講師未定」で受け付けると
    #    当日に誰も来られない事故になる（受講料をいただいている）
    inst = pick_instructor(course_code, d)
    if not inst:
        raise ValueError('その日は講師の都合がつきません')

    rows = bookings()
    already = sum(int(b.get('人数') or 1) for b in bookings_for(course_code, day))
    want = max(1, int(people or 1))
    # ⛔ 定員を超えて受け付けないこと。会場・演習端末が足りない
    if already + want > course['capacity']:
        left = course['capacity'] - already
        raise ValueError('この日は残り{}名です（定員{}名）'.format(
            max(0, left), course['capacity']))
    rec = {
        'id': secrets.token_hex(8),
        'コース': course_code, 'コース名': course['name'],
        '希望日': day,
        '氏名': name, '連絡先': email, '会社名': company,
        '人数': want, 'ご要望': message,
        '担当講師': inst['氏名'], '担当講師id': inst['id'],
        '受講料_円': course['price'],
        '状態': '申込受付',
        '申込日時': now_jst().strftime('%Y-%m-%d %H:%M'),
    }
    rows.append(rec)
    _save('bookings.json', rows)

    total = already + rec['人数']
    rec['_合計人数'] = total
    rec['_最少催行'] = course['min_people']
    rec['_開催確定'] = total >= course['min_people']
    return rec, inst
