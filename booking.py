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
import re
import secrets
import threading
from datetime import date, datetime, timedelta, timezone

JST = timezone(timedelta(hours=9))
_LOCK = threading.Lock()

# 予約は開催日の何日以上先から受けるか（兼業の講師に準備期間を残す）
LEAD_DAYS = 14

# 講座の一覧。⛔価格・時間は各コースページの掲載値と一致させること
# weekdays      … 開催できる曜日（月=0）。省略＝どの曜日でもよい。
# days          … 開催の回数。省略＝1回。⛔ 回数を hours の文章（「× 3日間」
#                 「全5回」）の中だけに書かないこと。1日ぶんの予定しか無い
#                 講師が割り当たる（2026-08-12 実装まで実際にそうだった）。
# interval_days … 回と回の間隔。1＝連続した日（既定）／7＝毎週
# group         … 登録フォームでのまとまり（掲載ページの区分に合わせる）
# ⛔ 掲載している講座をここに載せ忘れないこと。載っていない講座は講師登録の
#    選択肢に出ず、担当できる人が永久に0名になる（2026-08-12 社長ご指摘＝
#    子ども向け3・業種別15・GC の計19講座が抜けていた）。tests が突き合わせる。
# ⛔ 曜日の制約を hours の文字列の中だけに書かないこと。文章は判定に使えず、
#    「毎週水曜」の講座が木曜にも選べて予約まで成立していた（2026-08-12 実測）。
#    hours と weekdays がズレたら tests/test_booking.py が落ちる。
COURSES = [
    # ── 一人会社AI経営講座 /solo-ceo
    {'code': 'SP-A', 'name': 'AI経営 入門1日', 'price': 49800,
     'hours': '10:00〜17:00', 'min_people': 4, 'capacity': 20,
     'group': '一人会社AI経営'},
    {'code': 'SP-B', 'name': 'AI経営 実践3日間マスター', 'price': 128000,
     'hours': '10:00〜17:00 × 3日間', 'days': 3,
     'min_people': 3, 'capacity': 15, 'group': '一人会社AI経営'},
    {'code': 'SP-C', 'name': 'AI経営 夜間マスター 全5回', 'price': 68000,
     'hours': '毎週水曜 19:00〜21:30', 'weekdays': [2],
     'days': 5, 'interval_days': 7,          # 毎週水曜に5回
     'min_people': 5, 'capacity': 30, 'group': '一人会社AI経営'},
    # ── バイブコーディング認定講座（汎用）/vibe-coding
    {'code': 'GA', 'name': '生成AI入門1日', 'price': 49800,
     'hours': '10:00〜17:00', 'min_people': 4, 'capacity': 20,
     'group': '汎用'},
    {'code': 'GB', 'name': 'バイブコーディング実践1日', 'price': 49800,
     'hours': '10:00〜17:00', 'min_people': 4, 'capacity': 15,
     'group': '汎用'},
    {'code': 'GC', 'name': 'AI業務自動化マスター 全5回', 'price': 68000,
     'hours': '毎週水曜 19:00〜21:30', 'weekdays': [2],
     'days': 5, 'interval_days': 7,
     'min_people': 5, 'capacity': 30, 'group': '汎用'},
    {'code': 'GD', 'name': 'AIセキュリティ・ガバナンス', 'price': 49800,
     'hours': '10:00〜17:00', 'min_people': 4, 'capacity': 15,
     'group': '汎用'},
    {'code': 'GE', 'name': 'AIクリエイティブデザイン', 'price': 49800,
     'hours': '10:00〜17:00', 'min_people': 4, 'capacity': 15,
     'group': '汎用'},

    # ── 子ども向け /vibe-coding/kids
    # ⛔ 開始・終了の時刻は掲載ページに無い（所要時間だけ）。書き足さないこと＝
    #    時刻が読めない講座は「同じ日に他の講座と併せて担当できない」安全側に倒れる。
    #    時刻が決まったら hours を '10:00〜13:00' の形にすれば併記できるようになる。
    {'code': 'GK1', 'name': 'キッズ体験（半日・親子）', 'price': 9800,
     'hours': '3時間（半日）', 'min_people': 1, 'capacity': 10,
     'group': '子ども'},
    {'code': 'GK2', 'name': 'ジュニア入門（1日・中学生）', 'price': 29800,
     'hours': '6時間（1日）', 'min_people': 4, 'capacity': 15,
     'group': '子ども'},
    {'code': 'GK3', 'name': '親子ペアコース（1日）', 'price': 49800,
     'hours': '6時間（1日）', 'min_people': 1, 'capacity': 10,
     'group': '子ども'},
]

# ── 業種別（5業種 × 3段階）/vibe-coding/<業種>
# 掲載ページ（vibe_coding_industry.INDUSTRIES）と同じ価格・定員・期間にする。
# ⛔ ここを手で書き換えないこと。掲載と食い違ったら tests が落ちる。
for _slug, _label in (('GM', '製造業'), ('GH', '医療・ヘルスケア'),
                      ('GF', '金融'), ('GL', '物流'), ('GN', '建設')):
    COURSES += [
        {'code': f'{_slug}-A', 'name': f'{_label}AI入門（半日）', 'price': 49800,
         'hours': '4時間（半日）', 'min_people': 4, 'capacity': 20,
         'group': _label},
        {'code': f'{_slug}-B', 'name': f'{_label}AIマスター（3日間）',
         'price': 128000, 'hours': '各7時間 × 3日間', 'days': 3,
         'min_people': 3, 'capacity': 15, 'group': _label},
        {'code': f'{_slug}-C', 'name': f'{_label}AIアーキテクト（5日間）',
         'price': 228000, 'hours': '各7時間 × 5日間', 'days': 5,
         'min_people': 3, 'capacity': 10, 'group': _label},
    ]
COURSE_BY_CODE = {c['code']: c for c in COURSES}


def grouped_courses(codes=None):
    """[(区分, [講座, ...]), ...] 掲載ページと同じまとまりで返す。

    ⛔ 26講座を1列に並べないこと。選ぶ側が自分の担当を見つけられない。
    codes を渡すとその講座だけに絞る（講師本人の担当だけを出すとき）。
    """
    out = []
    for c in COURSES:
        if codes is not None and c['code'] not in codes:
            continue
        g = c.get('group') or 'その他'
        if not out or out[-1][0] != g:
            out.append((g, []))
        out[-1][1].append(c)
    return out

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
    """受講者に公開してよい講師。

    ⛔ 承認だけでは公開しないこと。メールの確認（本人がリンクを踏んだ）が
       済んでいない相手を公開すると、申込が入った日に依頼メールが届かず、
       当日に誰も来ない事故になる。打ち間違いのアドレスでも登録は通るため、
       ここが唯一の到達性の担保になる。
    """
    return [i for i in instructors()
            if i.get('状態') == '承認' and i.get('メール確認済み')]


def verify_email(token):
    """本人が確認リンクを踏んだ。戻り値: 講師 or None（鍵が違う）

    ⛔ 何度踏まれても最初の日時を残すこと（受け取った証拠なので上書きしない）。
    """
    rows = instructors()
    hit = None
    for r in rows:
        if r.get('鍵') == token:
            if not r.get('メール確認済み'):
                r['メール確認済み'] = now_jst().strftime('%Y-%m-%d %H:%M')
            hit = r
    if hit:
        _save('instructors.json', rows)
    return hit


def find_instructor(token):
    for i in instructors():
        if i.get('鍵') == token:
            return i
    return None


def register_instructor(name, email, org, courses, note, days=None):
    """講師候補の申請を受ける。戻り値: (講師, 本人用の鍵)

    ⛔ 状態は必ず『申請中』で始める。ここで承認にしてはいけない。

    ⛔ 謝礼の希望額はここでは受け取らない（2026-08-11 社長ご指示で
       登録フォームから削除）。謝礼はご相談のうえ、書面かメールで
       条件をお示ししてから発注する。項目を戻さないこと。

    ⛔ 登録フォームで予定を聞かないこと（2026-08-11 社長ご指示）。
       日付はカレンダー画面で選ぶ。登録の入口を軽くする方が申請が増える。
       days（{'2026-08-26': ['SP-A']}）は移行・試験用で、画面からは渡らない。
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
        # 本人が確認リンクを踏んだ日時。空＝未確認で、承認しても公開されない
        'メール確認済み': None,
        # 予定は「日付 → その日に担当する講座」だけが正
        # {'2026-08-26': ['SP-A', 'GA']}。時刻は COURSES が持つ
        '担当できる日': {k: sorted(c for c in v if c in COURSE_BY_CODE)
                        for k, v in (days or {}).items()
                        if _is_iso(k) and v},
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


"""⛔ 予定の書き込み口は set_day_courses（1日ずつ確定）だけ。

2026-08-12 社長ご指示で「日を選ぶ → その日に担当するコースを選ぶ →
確認 → 保存」の1日単位に変えたため、時間帯をまとめて送る旧APIは廃止した。
⛔ 書き込み口を2つにしないこと（同じ予定に別々の作法ができ、片方だけ直す
   壊れ方が起きる）。"""


# ────────────────────────────── 講義できる時間帯
def _hhmm(v):
    """'9:00' → '09:00'。時刻として読めなければ None"""
    m = re.match(r'^\s*(\d{1,2}):(\d{2})\s*$', str(v or ''))
    if not m or int(m.group(1)) > 23 or int(m.group(2)) > 59:
        return None
    return '%02d:%s' % (int(m.group(1)), m.group(2))


def normalize_slots(slots):
    """時間帯の並びを整える。読めないもの・開始≧終了は落とす。

    ⛔ 落としたものを黙って0件にしないのは呼び出し側の仕事。
       ここは「そのまま保存すると壊れる値」を通さないためだけにある。
    """
    out = []
    for s in (slots or []):
        a, b = _hhmm(s.get('開始')), _hhmm(s.get('終了'))
        # ⛔ まったく同じ枠を2本残さないこと。画面では同じ行が並ぶだけだが、
        #    講師には「押した回数だけ増える」壊れ方に見える（2026-08-11 実測）
        if a and b and a < b and {'開始': a, '終了': b} not in out:
            out.append({'開始': a, '終了': b})
    return sorted(out, key=lambda s: (s['開始'], s['終了']))


def normalize_weekly(weekly):
    """毎週の枠。同じ曜日に何本あってもよい（朝と夜など）。"""
    out = []
    for w in (weekly or []):
        if not str(w.get('曜日')).isdigit() or not 0 <= int(w['曜日']) <= 6:
            continue
        for s in normalize_slots([w]):
            out.append({'曜日': int(w['曜日']), **s})
    return sorted(out, key=lambda w: (w['曜日'], w['開始'], w['終了']))


def _is_iso(v):
    try:
        date.fromisoformat(str(v))
        return True
    except ValueError:
        return False


def normalize_daily(daily):
    """特定の日だけ差し替える枠。{'2026-09-05': [{'開始','終了'}]}

    ⛔ 空の枠は保存しない。日を閉じる手段は『不可の日』1つに寄せる
       （同じ意味を2通りで書けると、画面と実装で答えが割れる）。
    """
    out = {}
    for k, v in (daily or {}).items():
        try:
            date.fromisoformat(str(k))
        except ValueError:
            continue
        slots = normalize_slots(v)
        if slots:
            out[str(k)] = slots
    return dict(sorted(out.items()))


def slots_on(inst, d):
    """その講師がその日に講義できる時間帯。空リスト＝その日は不可。

    予定は『日付ごとの枠』（講義できる日時）だけが正
    ＝2026-08-11 社長ご指摘「曜日ではなく日付で選ばせればいい」。
    曜日の決まりは、講師に自分の予定を"規則"へ翻訳させる作りで、
    そのために例外（不可の日）と上書き（日別）が要り、概念が3つになっていた。
    いまは画面の「まとめて入れる」が日付を並べるだけで、保存されるのは日付。

    ⛔ 曜日ルールを判定に戻さないこと。戻した瞬間に正が2つになる。
    """
    days = inst.get('講義できる日時')
    if days is not None:
        return normalize_slots(days.get(d.isoformat()) or [])

    # ── ここから下は 2026-08-11 より前に登録された講師だけが通る読み取り互換。
    #    本人が予定画面で1回保存すれば日付形式に置き換わる（保存側で旧欄を落とす）。
    iso = d.isoformat()
    special = (inst.get('日別の可能時間') or {}).get(iso)
    if special:
        return normalize_slots(special)
    if iso in (inst.get('不可の日') or []):
        return []
    return [{'開始': w['開始'], '終了': w['終了']}
            for w in normalize_weekly(inst.get('毎週の可能時間'))
            if int(w['曜日']) == d.weekday()]


def materialize(inst, start, end):
    """start〜end の各日について、講義できる時間帯を日付ごとに並べる。

    旧式（曜日の決まり）で登録された講師の予定を、画面に日付として見せるために使う。
    ⛔ ここで保存しないこと。本人が画面で保存したときに日付形式へ移る
       （見ただけで台帳が書き換わると、本人の意図しない内容が確定する）。
    """
    out, d = {}, start
    while d <= end:
        ss = slots_on(inst, d)
        if ss:
            out[d.isoformat()] = ss
        d += timedelta(days=1)
    return out


def course_weekdays(course_code):
    """その講座を開催できる曜日（月=0）。制約が無ければ None"""
    wd = (COURSE_BY_CODE.get(course_code) or {}).get('weekdays')
    return list(wd) if wd else None


def course_open_on(course_code, d):
    """その日にその講座を開催できるか（曜日の制約）。

    ⛔ 「毎週水曜」の講座を木曜に選ばせないこと。選べてしまうと、
       木曜開始の予約が成立する（2026-08-12 社長ご指摘で判明）。
    """
    wd = course_weekdays(course_code)
    return wd is None or d.weekday() in wd


def series_note(course_code):
    """複数回の講座の説明を1行で。1回だけの講座なら空文字。

    ⛔ 毎週の講座に「つづけて開催」と書かないこと（水木金土日に読める）。
    ⛔ weekday_note（「毎週水曜の開催です」）を文中に埋め込まないこと。
       「毎週水曜の開催ですに開催します」になる（2026-08-12 実機で発生）。
    """
    n = course_days(course_code)
    if n <= 1:
        return ''
    if course_interval(course_code) > 1:
        wd = course_weekdays(course_code)
        when = ('毎週' + '・'.join(WEEKDAYS[i] for i in wd) + '曜'
                if wd else '1週間おき')
        return f'全{n}回・{when}に開催します'
    return f'{n}日間つづけて開催します'


def weekday_note(course_code):
    """曜日の制約を1行で。制約が無ければ空文字"""
    wd = course_weekdays(course_code)
    if not wd:
        return ''
    return '毎週' + '・'.join(WEEKDAYS[i] for i in wd) + '曜の開催です'


def day_courses(inst, d):
    """その日に担当すると登録されている講座コード。

    2026-08-12 社長ご指示で「時間帯を自分で組む」→「その日に担当できる
    コースを選ぶ」に変えた。時間はコースが持っているので、講師が
    10:00〜11:00 のような担当できない枠を作ってしまう余地が消える。

    ⛔ 時刻は COURSES の hours が唯一の出どころ。ここで持たないこと。
    ⛔ 曜日の制約（例：SP-C は毎週水曜）をここで必ず効かせること。台帳に
       木曜の SP-C が残っていても、読み出した時点で落とす。過去に保存された
       ものや、画面を通らない経路から入ったものを公開しないため。
    """
    iso = d.isoformat()
    days = inst.get('担当できる日')
    if days is not None:
        return [c for c in (days.get(iso) or []) if c in COURSE_BY_CODE
                and course_open_on(c, d)]

    # ── 以下は 2026-08-12 より前の登録（時間帯で持っていた）の読み取り互換。
    #    本人が1日ぶんでも確定すると新しい形に移る（保存側で旧欄を落とす）。
    slots = slots_on(inst, d)
    out = []
    for c in (inst.get('対応コース') or []):
        h = course_hours(c)
        if h and course_open_on(c, d) and any(
                s['開始'] <= h[0] and s['終了'] >= h[1] for s in slots):
            out.append(c)
    return out


def overlapping_courses(codes):
    """同時に担当できない組み合わせ（開催時間が重なるもの）を返す。

    ⛔ 同じ日に時間の重なる2つを受け付けないこと。1人が同時刻に
       2つの講座を担当することはできない（＝バッティング）。
    """
    hours = {}
    for c in codes:
        h = course_hours(c)
        if h:
            hours[c] = h
    bad = []
    seen = sorted(hours)
    for i, a in enumerate(seen):
        for b in seen[i + 1:]:
            if hours[a][0] < hours[b][1] and hours[b][0] < hours[a][1]:
                bad.append((a, b))
    return bad


def set_day_courses(token, iso, codes):
    """1日ぶんを確定する。戻り値: (講師, エラー文 or None)

    ⛔ 予約が入っている日は変更させないこと（受講者に案内済み）。
    ⛔ 担当できない講座（対応コース外）を受け付けないこと。
    """
    inst = find_instructor(token)
    if not inst:
        return None, 'リンクが正しくありません'
    try:
        date.fromisoformat(iso)
    except ValueError:
        return None, '日付が正しくありません'
    if iso in booked_days_for_instructor(inst.get('id')):
        return None, ('この日はすでに予約が入っているため変更できません。'
                      'info@jgaia.org までご連絡ください')

    ok = [c for c in (codes or []) if c in (inst.get('対応コース') or [])]
    ng = [c for c in (codes or []) if c not in ok]
    if ng:
        return None, '担当できる講座として登録されていないものが含まれています'
    # ⛔ 曜日の合わない講座を受け取らないこと（画面を通らない経路もある）
    d = date.fromisoformat(iso)
    bad_wd = [c for c in ok if not course_open_on(c, d)]
    if bad_wd:
        c = bad_wd[0]
        return None, (f'{c} は{weekday_note(c)}。'
                      f'{WEEKDAYS[d.weekday()]}曜のこの日にはお受けいただけません')
    bad = overlapping_courses(ok)
    if bad:
        a, b = bad[0]
        return None, (f'{a} と {b} は開催時間が重なるため、同じ日には'
                      'お受けいただけません')

    rows = instructors()
    hit = None
    for r in rows:
        if r.get('鍵') != token:
            continue
        days = dict(r.get('担当できる日') or {})
        if days == {} and r.get('担当できる日') is None:
            # 旧い形で持っていた予定を、いまの形に写してから触る
            # ⛔ 写さずに上書きすると、他の日の登録が黙って消える
            days = _legacy_day_courses(r)
        if ok:
            days[iso] = sorted(ok)
        else:
            days.pop(iso, None)          # 選択なし＝その日は講義しない
        r['担当できる日'] = dict(sorted(days.items()))
        for old in ('毎週の可能時間', '不可の日', '日別の可能時間', '講義できる日時'):
            r.pop(old, None)
        r['更新日時'] = now_jst().strftime('%Y-%m-%d %H:%M')
        hit = r
    if hit:
        _save('instructors.json', rows)
    return hit, None


def others_on(inst, d):
    """その日に、他の承認済み講師が担当すると登録している講座。

    ⛔ これは「重複＝禁止」ではない（同じ日に複数の講師がいて構わない）。
       予約が入るのは1人だけなので、知らせるだけにとどめること。
    """
    out = []
    for r in approved_instructors():
        if r.get('id') == inst.get('id'):
            continue
        cs = day_courses(r, d)
        if cs:
            out.append({'氏名': r.get('氏名'), 'コース': cs})
    return out


def _legacy_day_courses(inst, span=180):
    """旧い形（時間帯・曜日）の予定を「日付→担当コース」に写す。

    ⛔ 1日ごとに slots_on を呼ばないこと。曜日の枠を毎日 normalize_weekly で
       作り直すため、180日×講師数ぶん効いて画面が数秒単位で遅くなる
       （2026-08-12 実測：承認画面 3.9秒／_hhmm が 25,352回）。
       曜日の枠と講座の開催時間は先に1回だけ用意する。
    """
    # ⛔ slots_on と同じ優先順位で読むこと。ここだけ読み落とすと、判定
    #    （open_days）と一覧（registered_days）で答えが割れる
    #    ＝2026-08-12 の速度改善で『講義できる日時』を落として実際に割れた。
    per_date = inst.get('講義できる日時')       # 2026-08-11 の形（日付×時間帯）
    by_wd, daily, blocked = {}, {}, set()
    if per_date is None:
        for w in normalize_weekly(inst.get('毎週の可能時間')):
            by_wd.setdefault(int(w['曜日']), []).append(
                {'開始': w['開始'], '終了': w['終了']})
        daily = normalize_daily(inst.get('日別の可能時間'))
        blocked = set(inst.get('不可の日') or [])
    codes = [c for c in (inst.get('対応コース') or []) if course_hours(c)]
    hours = {c: course_hours(c) for c in codes}

    out, d = {}, today_jst()
    end = d + timedelta(days=span)
    while d <= end:
        iso = d.isoformat()
        if per_date is not None:
            slots = normalize_slots(per_date.get(iso) or [])
        else:
            slots = (daily.get(iso) or ([] if iso in blocked
                                        else by_wd.get(d.weekday(), [])))
        if slots:
            cs = [c for c in codes
                  if course_open_on(c, d)
                  and any(s['開始'] <= hours[c][0] and s['終了'] >= hours[c][1]
                          for s in slots)]
            if cs:
                out[iso] = sorted(cs)
        d += timedelta(days=1)
    return out


def teachable_courses(inst, reg=None):
    """その講師の登録内容で、実際に担当できる講座コード。

    ⛔ 「登録した日数」で判断しないこと。コースは終日（例 10:00〜17:00）なので、
       1時間の枠を何本並べても担当できない（2026-08-12 本番で実際に起きた）。
    ⛔ reg を渡せるようにしてあるのは、旧形式の展開が重いため。同じ要求の中で
       何度も registered_days を呼ばないこと。
    """
    out = []
    for cs in (registered_days(inst) if reg is None else reg).values():
        for c in cs:
            if c not in out:
                out.append(c)
    return [c for c in (inst.get('対応コース') or []) if c in out]


def registered_days(inst):
    """{'2026-08-26': ['SP-A', ...]} 登録されている日と、その日の担当講座。

    ⛔ day_courses と同じ関所（実在する講座か・その曜日に開催できるか）を
       ここでも通すこと。ここだけ素通しにすると、台帳に残った木曜の SP-C が
       画面の一覧や集計にだけ現れ、判定と表示が食い違う。
    """
    days = inst.get('担当できる日')
    if days is None:
        return {k: v for k, v in sorted(_legacy_day_courses(inst).items()) if v}
    out = {}
    for iso, codes in sorted(days.items()):
        try:
            d = date.fromisoformat(iso)
        except (ValueError, TypeError):
            continue
        ok = [c for c in (codes or [])
              if c in COURSE_BY_CODE and course_open_on(c, d)]
        if ok:
            out[iso] = ok
    return out


def startable_days(inst, course_code, occ=None, reg=None):
    """その講師が『開始日にできる』日。予約が入りうる日はこれだけ。

    ⛔ 3日間の講座で「登録した日数」を成果として見せないこと。飛び飛びに
       3日登録しても開始日は0日で、受講者からは1日も見えない。
    ⛔ 講座ごとに occ / reg を作り直さないこと。occupied_days は予約台帳を、
       registered_days は旧形式だと180日ぶんの展開を毎回やる＝講座の数だけ
       重くなる（7講座×講師数。実測でテストが10分を超えた）。
    """
    occ = occupied_days(inst.get('id')) if occ is None else occ
    reg = registered_days(inst) if reg is None else reg
    out = []
    for iso, codes in reg.items():
        if course_code in codes and instructor_can_start(
                inst, date.fromisoformat(iso), course_code, occ, reg=reg):
            out.append(iso)
    return out


def publish_blockers(inst, reg=None):
    """受講者に公開されない理由。空リスト＝公開されている。

    ⛔ 公開されない状態を、画面のどこにも書かないまま放置しないこと。
       承認したのに日程が出ない、という問い合わせの原因がこれ。
    """
    out = []
    if inst.get('状態') != '承認':
        out.append('まだ承認されていません（運営の承認待ちです）')
    if not inst.get('メール確認済み'):
        out.append('メールアドレスの確認が済んでいません')

    days = registered_days(inst) if reg is None else reg
    if not days:
        # ⛔ 旧い形（時間帯）で登録した方に「1日も登録されていません」と言わない。
        #    登録はしている。その時間帯では担当できる講座が無いだけ
        legacy = (inst.get('担当できる日') is None
                  and (inst.get('講義できる日時') or inst.get('毎週の可能時間')))
        out.append('登録されている時間帯では、担当できる講座がありません'
                   '（講座は開催時間を通しで担当する必要があります）。'
                   'カレンダーから日付を選び直してください'
                   if legacy else '講義できる日が1日も登録されていません')
        return out

    # 受付は LEAD_DAYS 日以上先だけ。手前しか無ければ実質公開されない
    earliest = (today_jst() + timedelta(days=LEAD_DAYS)).isoformat()
    if not [k for k in days if k >= earliest]:
        out.append(f'登録された日がすべて{LEAD_DAYS}日以内です'
                   f'（予約は{earliest}以降の日にしか入りません）')

    # ⛔ 「一部の講座を選んでいない」は公開されない理由ではない（選んだ講座は
    #    公開されている）。ここに混ぜると、公開中なのに未公開と読める
    can = teachable_courses(inst, reg=days)
    if not can:
        out.append('どの日にも担当する講座が選ばれていません')
    # ⛔ 選んだのに開始日が1日も無い講座を黙らないこと（連続日数が足りない）
    multi = [c for c in can if course_days(c) > 1]
    if multi:
        occ = occupied_days(inst.get('id'))          # 台帳の読み直しは1回だけ
        for c in multi:
            if not startable_days(inst, c, occ=occ, reg=days):
                out.append(f'{c} は{course_days(c)}日間つづけて開催します。'
                           f'{course_days(c)}日続けて選んだ日が無いため、'
                           'この講座は公開されません')
    return out


def availability_end(inst):
    """登録されている予定の最終日（ISO）。無ければ None

    ⛔ 日付形式は「入れた先まで」しか公開されない。いつまで入っているかを
       画面に出さないと、気づかないうちに予約可の日が尽きる。
    """
    days = list(registered_days(inst))
    return max(days) if days else None


_HOURS_CACHE = {}


def course_hours(course_code):
    """コースの開催時間 → ('10:00','17:00')。読めなければ None

    ⛔ 時刻を別表に書き写さないこと。COURSES の hours が唯一の出どころで、
       掲載ページと同じ値（ここがズレると案内と実運用が食い違う）。
    ⛔ 毎回 hours を正規表現で読み直さないこと（判定の内側で何千回も呼ばれる）。
       COURSES は起動中変わらないので、解いた結果を覚えておく。
    """
    if course_code in _HOURS_CACHE:
        return _HOURS_CACHE[course_code]
    c = COURSE_BY_CODE.get(course_code) or {}
    m = re.search(r'(\d{1,2}:\d{2})\s*[〜~ー－-]\s*(\d{1,2}:\d{2})',
                  str(c.get('hours') or ''))
    out = None
    if m:
        a, b = _hhmm(m.group(1)), _hhmm(m.group(2))
        out = (a, b) if a and b and a < b else None
    _HOURS_CACHE[course_code] = out
    return out


def course_days(course_code):
    """開催の回数（既定1）。3日間の講座なら3、全5回の講座なら5。"""
    try:
        return max(1, int((COURSE_BY_CODE.get(course_code) or {}).get('days', 1)))
    except (TypeError, ValueError):
        return 1


def course_interval(course_code):
    """回と回の間隔（日）。1＝連続した日、7＝毎週。"""
    try:
        return max(1, int((COURSE_BY_CODE.get(course_code) or {}).get(
            'interval_days', 1)))
    except (TypeError, ValueError):
        return 1


def course_dates(course_code, start_iso):
    """開催する日の並び。

    3日間の講座なら開始日を含む3日、全5回（毎週）なら5週ぶんの同じ曜日。
    ⛔ 「全5回」を連続5日として扱わないこと。毎週水曜の夜間コースが
       水木金土日になる（2026-08-12 まで、そもそも初回しか押さえていなかった）。
    """
    d0 = date.fromisoformat(start_iso)
    step = course_interval(course_code)
    return [(d0 + timedelta(days=k * step)).isoformat()
            for k in range(course_days(course_code))]


def _hours_overlap(a, b):
    """2つの講座の開催時間が重なるか。読めないものは重なる扱い（安全側）。"""
    ha, hb = course_hours(a), course_hours(b)
    if not ha or not hb:
        return True
    return ha[0] < hb[1] and hb[0] < ha[1]


def occupied_days(instructor_id):
    """その講師が予約で押さえられている日 → {'2026-08-26': {('SP-B','2026-08-26')}}

    ⛔ 3日間の講座は3日ぶんを押さえること。開始日しか見ないと、2日目・3日目に
       別の講座が入り、同じ講師が同時刻に2つ担当することになる。
    """
    out = {}
    for b in bookings():
        if b.get('担当講師id') != instructor_id or b.get('状態') == '取消':
            continue
        start = b.get('希望日')
        for iso in (b.get('開催日') or course_dates(b.get('コース'), start)):
            out.setdefault(iso, set()).add((b.get('コース'), start))
    return out


def instructor_free_on(inst, d, booked=None):
    """その講師がその日に講義できるか（コースを問わない）。

    booked にその講師の予約済みの日を渡すと、その日は「空いている」扱いにする。
    ⛔ ここを落とすと、1人目の申込が入った日を講師が週の設定から外した瞬間に
       2人目が申し込めなくなり、最少催行に届かず開催できない（申込は残る）。
    """
    if booked and d.isoformat() in booked:
        return True
    return bool(slots_on(inst, d))


def instructor_can_teach(inst, d, course_code, occ=None, start=None, reg=None):
    """その講師が『そのコースを』その日に担当できるか。

    occ … occupied_days() の結果。start … 申し込もうとしている回の開始日。

    ⛔ 曜日だけで判定しないこと。夜間コース（水 19:00〜21:30）に
       10:00〜17:00 でしか登録していない講師が割り当たっていた
       （2026-08-11 実測。時間帯は登録させておいて1か所も使っていなかった）。
    ⛔ 「予約が入っている日＝空いている」と単純に返さないこと。それは
       **同じ回に2人目を受ける**ためのもので、別の講座・別の回まで通すと
       同じ講師が同時刻に2つ担当することになる。
    """
    iso = d.isoformat()
    start = start or iso
    mine = (occ or {}).get(iso) or set()
    if (course_code, start) in mine:
        return True                      # 同じ回の追加申込は受ける
    for other, _s in mine:
        if _hours_overlap(course_code, other):
            return False                 # 別の回・別の講座と時間が重なる
    # reg（registered_days の結果）があれば使う。⛔旧形式は day_courses が
    # 1日ごとに曜日の枠を作り直すので、3日間の講座では日数ぶん効いて重くなる
    if reg is not None:
        return course_code in (reg.get(iso) or [])
    return course_code in day_courses(inst, d)


def instructor_can_start(inst, d, course_code, occ=None, reg=None):
    """その日を開始日として、その講座を最後まで担当できるか。

    ⛔ 3日間の講座で初日しか見ないこと。2日目に別の予定が入っている講師に
       割り当たると、2日目から講師がいなくなる。
    """
    if not course_open_on(course_code, d):
        return False
    start = d.isoformat()
    for iso in course_dates(course_code, start):
        if not instructor_can_teach(inst, date.fromisoformat(iso),
                                    course_code, occ, start=start, reg=reg):
            return False
    return True


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
    occ = {i['id']: occupied_days(i['id']) for i in people}
    # ⛔ 登録済みの日も1人1回だけ展開すること。ここを毎日やり直すと、旧形式の
    #    講師では 90日×講座の日数 ぶん効いて、受講者の予約画面が10秒を超える
    #    （2026-08-12 本番実測：/book/SP-A が23秒）
    reg = {i['id']: registered_days(i) for i in people}
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
            # ⛔ 3日間の講座は「最後まで担当できる日」だけを開始日として出す
            who = [i for i in people
                   if instructor_can_start(i, d, course_code,
                                           occ.get(i['id']), reg.get(i['id']))]
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
              and instructor_can_start(i, d, course_code,
                                       occupied_days(i['id']),
                                       registered_days(i))]
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
    """その講師に既に予約が入っている日（3日間の講座なら3日ぶん）。

    ⛔ 予約が入っている日を、本人が「不可」に変えられないようにするために使う
       （受講者が待っている日を静かに閉じられると事故になる）。
    ⛔ 開始日だけを返さないこと。2日目・3日目を本人が消せてしまう。
    """
    return sorted(occupied_days(instructor_id))


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
        # 3日間の講座は開催する日をすべて残す。⛔ 開始日だけだと、あとから
        #    日数の設定を変えたときに過去の予約の実際の日程が変わってしまう
        '開催日': course_dates(course_code, day),
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
