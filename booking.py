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

決定事項（2026-08-09 社長承認／2026-08-14 改定）:
    最少催行人数  ⛔ 設けない（下記）
    講師料        単価の40%を1開催あたりの定額（人数に依存しない）
    支払い        カード決済（Stripe）を既定。法人向けに請求書払いを併存
    キャンセル    14日前まで無料 / 13〜7日前 50% / 6日前以降 100%

⛔ 最少催行人数を復活させないこと（2026-08-14 社長ご判断）。講師料は
   「単価の40%」を1開催あたり払う**定額**で、人数が増えても増えない。
   よって2人目以降は受講料がまるごと利益になり、損益分岐は全コース
   0.42名相当（40% ÷ 96.4%）＝**1名で必ず黒字**。人数を理由に中止すると、
   確実に入る利益を捨てたうえ、申し込んだ受講者と看板を失う。
   実測: SP-A に3名で中止すると ¥124,101 を捨てる。
   席が埋まらない問題は「公開する日を絞る」（供給側）で解くこと。
"""
import json
import os
import re
import secrets
import threading
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_DOWN

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
     'hours': '10:00〜17:00', 'capacity': 20,
     'group': '一人会社AI経営'},
    {'code': 'SP-B', 'name': 'AI経営 実践マスター 全3回', 'price': 128000,
     'hours': '毎週水曜 10:00〜17:00', 'weekdays': [2],
     'days': 3, 'interval_days': 7,
     'capacity': 15, 'group': '一人会社AI経営'},
    {'code': 'SP-C', 'name': 'AI経営 夜間マスター 全5回', 'price': 128000,
     'hours': '毎週水曜 19:00〜21:30', 'weekdays': [2],
     'days': 5, 'interval_days': 7,          # 毎週水曜に5回
     'capacity': 30, 'group': '一人会社AI経営'},
    # ── バイブコーディング認定講座（汎用）/vibe-coding
    {'code': 'GA', 'name': '生成AI入門1日', 'price': 49800,
     'hours': '10:00〜17:00', 'capacity': 20,
     'group': '汎用'},
    {'code': 'GB', 'name': 'バイブコーディング実践1日', 'price': 98000,
     'hours': '10:00〜17:00', 'capacity': 15,
     'group': '汎用'},
    {'code': 'GC', 'name': 'AI業務自動化マスター 全5回', 'price': 128000,
     'hours': '毎週水曜 19:00〜21:30', 'weekdays': [2],
     'days': 5, 'interval_days': 7,
     'capacity': 30, 'group': '汎用'},
    {'code': 'GD', 'name': 'AIセキュリティ・ガバナンス', 'price': 49800,
     'hours': '10:00〜17:00', 'capacity': 15,
     'group': '汎用'},
    {'code': 'GE', 'name': 'AIクリエイティブデザイン', 'price': 49800,
     'hours': '10:00〜17:00', 'capacity': 15,
     'group': '汎用'},
    # ⛔ この価格（税込11万＝税抜10万）は、助成金の対象経費の上限にぴったり
    #    合わせたもの。DXリスキリング助成金は「対象経費10万円まで3/4」で
    #    上限¥75,000。¥49,800（税抜45,272）では枠の45%しか使えていない。
    #    11万にすると助成は上限の¥75,000、法人の実質負担は¥35,000で、
    #    公開講座の市場相場（インソース 37,700〜41,000円）とほぼ同じまま
    #    当社の売上は2.2倍になる（2026-08-15 市場調査・社長ご承認）。
    # ⛔ 金額を動かすときは助成の上限を必ず再計算すること。11万を超えても
    #    助成は増えず、超えた分はまるごと法人の持ち出しになる。
    # ⛔ GA（¥49,800）を廃止しないこと。個人・小規模の入口で、助成金を
    #    使えない方（代表者ご本人など）はこちらしか選べない。
    {'code': 'GA-P', 'name': '生成AI入門1日（法人向け・少人数）', 'price': 110000,
     'hours': '10:00〜17:00', 'capacity': 12,
     'group': '汎用'},

    # ── 子ども向け /vibe-coding/kids
    # 開催時刻は 2026-08-12 に決定（社長ご一任）。1日コースは他と同じ 10:00〜17:00、
    # 子どもの半日だけ午前に置く（集中力が続く時間帯・昼食前に終わる）。
    # ⛔ 掲載ページ（templates/vibe_coding_kids.html）の「時間」欄と必ず一致させること。
    {'code': 'GK1', 'name': 'キッズ体験（半日・親子）', 'price': 9800,
     'hours': '10:00〜13:00', 'capacity': 10,
     'group': '子ども'},
    {'code': 'GK2', 'name': 'ジュニア入門（1日・中学生）', 'price': 12000,
     'hours': '10:00〜17:00', 'capacity': 15,
     'group': '子ども'},
    {'code': 'GK3', 'name': '親子ペアコース（1日）', 'price': 20000,
     'hours': '10:00〜17:00', 'capacity': 10,
     'group': '子ども'},
]

# ── 業種別（5業種 × 3段階）/vibe-coding/<業種>
# 掲載ページ（vibe_coding_industry.INDUSTRIES）と同じ価格・定員・期間にする。
# ⛔ ここを手で書き換えないこと。掲載と食い違ったら tests が落ちる。
for _slug, _label in (('GM', '製造業'), ('GH', '医療・ヘルスケア'),
                      ('GF', '金融'), ('GL', '物流'), ('GN', '建設')):
    COURSES += [
        # 半日は午後に置く（午前の業務を片付けてから参加でき、遠方からでも間に合う）。
        # 1日は他の講座と同じ 10:00〜17:00 に揃える（会場・講師の手配が同じ枠で回る）。
        {'code': f'{_slug}-A', 'name': f'{_label}AI入門（半日）', 'price': 49800,
         'hours': '13:00〜17:00', 'capacity': 20,
         'group': _label},
        {'code': f'{_slug}-B', 'name': f'{_label}AIマスター（全3回）',
         'price': 128000, 'hours': '毎週水曜 10:00〜17:00',
         'weekdays': [2], 'days': 3, 'interval_days': 7,
         'capacity': 15, 'group': _label},
        {'code': f'{_slug}-C', 'name': f'{_label}AIアーキテクト（全5回）',
         'price': 228000, 'hours': '毎週水曜 10:00〜17:00',
         'weekdays': [2], 'days': 5, 'interval_days': 7,
         'capacity': 10, 'group': _label},
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

# ── 開催日（2026-08-15 社長ご判断）
# 受講者が予約できる日を運営が先に決め、講師はその中からしか選べない。
# ⛔ 講師に自由に日を選ばせないこと。5名が別々の日を選ぶと申込が散り、
#    1回あたりの人数が減る。講師料は1開催あたりの定額なので、開催回数が
#    増えるほど利益がそのまま減る（GA 1回 ¥19,920／業種別C 1回 ¥91,200）。
# ⛔ 水曜を間引かないこと。SP-C と GC は「毎週水曜×5回」なので、水曜が
#    毎週 開催日でないとこの2講座は永久に成立しない（実装で確認済み）。
# 土曜は会社員の方が来られる日として第2・第4に置く。
SESSION_WEEKLY = [2]                 # 毎週（水）
SESSION_NTH = {5: [2, 4]}            # 第2・第4（土）
# 臨時の開催日／休止日。⛔ 規則を書き換えず、ここに足して調整すること
SESSION_EXTRA = []                   # 例: ['2026-09-21']
SESSION_SKIP = []                    # 例: ['2026-12-31']


def is_session_day(d):
    """その日を開催日にしているか（True の日だけ講師が選べる／公開される）。"""
    if isinstance(d, str):
        try:
            d = date.fromisoformat(d)
        except ValueError:
            return False
    iso = d.isoformat()
    if iso in SESSION_SKIP:
        return False
    if iso in SESSION_EXTRA:
        return True
    if d.weekday() in SESSION_WEEKLY:
        return True
    nth = (d.day - 1) // 7 + 1
    if nth in SESSION_NTH.get(d.weekday(), []):
        return True
    return False


def session_day_for(codes, d):
    """その日に、これらの講座のどれかを登録してよいか。

    ⛔ 連日開催（3日つづけて等）の講座を作らないこと（2026-08-15 社長ご判断）。
       開催日は毎週水＋第2/第4土で連続する日が1組も無いため、連日の講座は
       構造的に成立しない。複数回の講座はすべて『毎週◯曜×N回』にしてある。
    """
    return is_session_day(d)


def session_days(months=3):
    """これから先の開催日の一覧（画面の案内用）。"""
    out, d = [], today_jst()
    limit = d + timedelta(days=31 * months)
    while d <= limit:
        if is_session_day(d):
            out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def multi_session_courses_ok():
    """複数回の講座が、毎週ある開催日の曜日に置かれているかを確かめる。

    ⛔ 「毎週◯曜×N回」の講座を、毎週ではない曜日（土＝第2・第4のみ）に
       置かないこと。途中の回が開催日から外れ、その講座は永久に成立しない
       （2026-08-15 実装中に検知。SP-B を土曜にして第3土曜で切れた）。
    """
    bad = []
    for c in COURSES:
        if course_days(c['code']) <= 1:
            continue
        wd = c.get('weekdays')
        if not wd or any(w not in SESSION_WEEKLY for w in wd):
            bad.append(c['code'])
    return bad


def session_day_note():
    """開催日の決まりを日本語で1文にする。⛔画面に文言を手打ちしないこと。"""
    w = '・'.join(WEEKDAYS[i] for i in SESSION_WEEKLY)
    parts = ['毎週{}曜'.format(w)] if SESSION_WEEKLY else []
    for wd, nths in SESSION_NTH.items():
        parts.append('第{}{}曜'.format('・'.join(str(n) for n in nths),
                                       WEEKDAYS[wd]))
    return '開催日は{}です。'.format('と'.join(parts))

CANCEL_POLICY = ('開催14日前まで：無料 ／ 13〜7日前：受講料の50% ／ '
                 '6日前〜当日：受講料の100%')

# ── 開催方法と諸経費（2026-08-15 社長ご判断）
# 受講料は「講義そのもの」の対価。**会場を使う場合の諸経費は別途お見積り**にする。
# ⛔ 会場費・講師の交通費／宿泊費・配信の機材費を受講料に含めないこと。含めると
#    自社の固定費になり、1名開催で赤字になる（社長の大前提＝赤字にしないこと）。
# ⛔ 子ども向けを「親子で会場に来る」前提にしないこと（2026-08-15 社長ご指示）。
#    子どもだけオンラインで参加できる。会場を必須にすると、いちばん単価の低い
#    GK1（¥9,800）が会場費で即赤字になる。
# 既定は全講座オンライン。会場開催は諸経費を別途見積として受ける。
ONLINE_DEFAULT = True
EXTRA_COST_NOTE = ('会場を使用して開催する場合の諸経費（会場費・機材費・'
                   '講師の交通費および宿泊費）は、受講料に含まれません。'
                   '別途お見積りいたします。')
DELIVERY_NOTE = ('オンライン開催（同時双方向）が既定です。'
                 '会場開催・会場＋オンライン同時開催もお受けします（諸経費は別途お見積り）。')


# ── 法人出張開催（2026-08-15 市場調査・社長ご承認）
# ⛔ 「1名あたり」で値付けしないこと。市場の講師派遣は**1回いくら**
#    （DX研修 1日30〜60万／生成AI研修 1日80〜150万）。1名あたりだと、
#    1名で来られたとき市場の1/6にしかならず、逆に大人数だと割高になる。
# ⛔ 諸経費（会場費・機材費・講師の交通費／宿泊費）はこの金額に含めない。
#    含めると自社の固定費になり、遠方ほど赤字に近づく。
# ⛔ カード決済の導線に載せないこと。金額が見積で確定するため、
#    Stripe（確定額を先に決める仕組み）では扱えない。
CORPORATE = {
    'day_price': 350000,        # 1日（6時間）あたり・10名まで
    'included': 10,             # この人数まで追加料金なし
    'extra_person': 25000,      # 11名以降・1名あたり
    'min_days': 1,
    'note': ('貴社の会議室またはオンラインで実施します。'
             '会場費・機材費・講師の交通費および宿泊費は別途お見積りです。'),
}


def corporate_quote(days=1, people=10):
    """法人出張開催の概算。戻り値: (金額, 内訳の説明)

    ⛔ 諸経費は含めない（別途見積）。ここで概算に混ぜると、見積の前に
       確定額があるかのように読まれる。
    """
    days = max(CORPORATE['min_days'], int(days))
    people = max(1, int(people))
    extra = max(0, people - CORPORATE['included']) * CORPORATE['extra_person']
    total = CORPORATE['day_price'] * days + extra
    detail = '{}日 × ¥{:,}'.format(days, CORPORATE['day_price'])
    if extra:
        detail += '（{}名超過分 {}名 × ¥{:,}）'.format(
            CORPORATE['included'], people - CORPORATE['included'],
            CORPORATE['extra_person'])
    return total, detail


def delivery_label(course_code=None):
    """掲載ページに出す開催方法。⛔各ページに文言を手打ちしないこと。"""
    return 'オンライン開催（会場開催も可・諸経費別途）'


def apply_delivery(courses, code_key='code'):
    """掲載ページの講座dictに開催方法を入れる（表示を1か所から作る）。"""
    for c in courses:
        c['format'] = delivery_label(c.get(code_key))
        c['extra_cost_note'] = EXTRA_COST_NOTE
    return courses


def apply_prices(courses, code_key='code'):
    """掲載ページの講座dictの価格を COURSES から入れ直す。

    ⛔ 価格を掲載ページ側に手打ちしないこと。値上げ・値下げのたびに
       片方だけ古くなり、**申込画面と紹介ページで金額が食い違う**
       （助成金の実質負担額で実際にそれが起きた。2026-08-15）。
    ⛔ 予約と決済が使うのは COURSES の price。掲載が古いと、安い方を
       見て申し込んだお客様に高い金額を請求することになる。
    """
    for c in courses:
        live = COURSE_BY_CODE.get(c.get(code_key) or '')
        if not live:
            continue
        c['price_num'] = live['price']
        c['price'] = '{:,}'.format(live['price'])
        # ⛔ 単位と「1研修あたり」を掲載ページ側に手打ちしないこと。
        #    2026-08-17 時点で単位は業種別ページにしか無く、1研修あたりの
        #    金額に至っては一人会社ページに1件も出ていなかった（助成の要件2）。
        c['price_unit'] = PRICE_UNIT
        c['price_suffix'] = PRICE_SUFFIX
        c['unit_note'] = unit_price_note(live['code'])
        c['order_note'] = order_note(live['code'])
    return courses


def profit_at(course_code, people=1, card=True):
    """その講座を people 名で開催したときの粗利（円）。

    ⛔ 会場費を引かないこと。諸経費は受講者・法人の負担で、当社は立て替えない。
    ⛔ 講師料に人数を掛けないこと（1開催あたりの定額）。
    """
    c = COURSE_BY_CODE.get(course_code)
    if not c:
        return None
    gross = c['price'] * max(1, int(people))
    fee = instructor_fee(course_code) or 0
    stripe = int(gross * 0.036) if card else 0
    return gross - fee - stripe


# ── 総研修時間数（助成金の判定に使う。単位＝時間・昼休憩を含まない）
# ⛔ 開催時間（hours）から引き算で作らないこと。10:00〜17:00 は7時間だが
#    実際の研修時間は6時間（昼休憩1時間）で、休憩の有無は講座ごとに違う。
#    ここは掲載ページの「duration」の数字を写したもので、tests が突き合わせる。
# ⛔ 掲載ページの時間を変えたら、必ずここも直すこと。助成金の対象／対象外が
#    3時間以上10時間未満で切り替わるので、ズレると法人の申請が通らない。
TRAINING_HOURS = {
    'SP-A': 6, 'SP-B': 18, 'SP-C': 12.5,
    'GA': 6, 'GA-P': 6, 'GB': 6, 'GC': 12.5, 'GD': 6, 'GE': 6,
    'GK1': 3, 'GK2': 6, 'GK3': 6,
}
for _s in ('GM', 'GH', 'GF', 'GL', 'GN'):
    TRAINING_HOURS[f'{_s}-A'] = 4
    TRAINING_HOURS[f'{_s}-B'] = 18
    TRAINING_HOURS[f'{_s}-C'] = 30

# ── 1講座を「独立した複数の研修」として掲載する（社長ご指示 2026-08-17）
# 助成の要件は「**1研修あたり**の総研修時間数が3時間以上10時間未満」だけで、
# 講座の格・内容・段階は関係ない。複数日開催も条文が認めている
# （募集要項 要件10・※11）。そして要件2「レディメイド研修＝一般に公開された
# 受講案内に**受講者1人1研修単位の経費**が明記されていること」より、
# **1研修の区切りは当社が受講案内（自社サイト）にどう書くかで決まる**。
# → 長時間の講座を、回ごとに独立した研修として掲載し直すことで対象になる。
#
# 値 = その講座を何本の研修として掲載するか。
# ⛔ 1本あたりが3時間以上10時間未満に収まること（下限も効く）。
#    夜間コース（1回2.5時間）を回ごとにばらすと下限3時間を割って**逆に対象外**になる。
#    GC・SP-C を2本にしているのはこのため。
# ⛔ 本数を増やすほど法人の負担額が増える（1研修 = UNIT_PRICE のため）。
#    掲載回をそのまま単位にするのが、いまの受講料より安くなる範囲で最大。
SESSIONS = {
    'SP-B': 3, 'SP-C': 2, 'GC': 2,
}
for _s in ('GM', 'GH', 'GF', 'GL', 'GN'):
    SESSIONS[f'{_s}-B'] = 3
    SESSIONS[f'{_s}-C'] = 5

# 1研修あたりの受講料（税込）。税抜ちょうど10万円＝助成上限75,000円を使い切る点。
# ⛔ ここを下げると助成の取りこぼしになる（税抜10万円未満は3/4しか出ない）。
# ⛔ 上げても助成は増えない（1人1研修あたり75,000円で頭打ち）。差額は法人の持ち出し。
UNIT_PRICE = 110000


# ⛔ 分割掲載する講座の受講料は手打ちしないこと。1研修 UNIT_PRICE × 本数で導出する
#    （SESSIONS を触ったのに価格を直し忘れる、を構造的に防ぐ）。
#    COURSE_BY_CODE は同じ dict を参照しているので、ここで書き換えれば両方に効く。
for _c in COURSES:
    _n = SESSIONS.get(_c['code'])
    if _n:
        _c['price'] = UNIT_PRICE * _n


# ── JGAIA が実施する認定試験を受講料に組み込む（社長ご指示 2026-08-17）
# 出典: https://www.qai-zen.com/examinations （2026-08-17 実測。JGAIA実施は2試験）
#
# なぜ「組み込む」のか＝受験料のままでは、どの制度からも1円も出ないため。
#   ・DXリスキリング助成金の助成対象経費は5つだけ（募集要項 p8「６ 助成対象経費」）＝
#     受講料／教科書・教材代／研修に付随する登録料・管理料／ヒアリング料／会場費。
#     **受験料という費目は存在しない**。⛔見積書に「受験料 ¥9,800」と単独で
#     立てたら、その行は落ちる。
#   ・さらに「資格試験（講習を受講しなくても単独で受験して資格を得られるもの）」は
#     助成対象外の研修（同 p7「４（２）⑦」）。QAI-Zen は講座が無料・受験料だけ有料
#     ＝この除外にそのまま当たる形だった。
#   ・厚労省の人材開発支援助成金も同じ考え方（「資格試験の受験料単独で支給申請は
#     できません。訓練と一体となったものであることが必要です」）。教育訓練給付金は
#     検定試験の受験料を明文で対象外にしている。
#   ・一方、要件3（同 p6）は「…知識・技能の習得・向上を目的とする研修
#     **又は専門的な資格を取得するための研修**」＝資格取得を目的とした講座は
#     明示的に対象。⛔「資格系だから対象外」と読み違えないこと。
# → 認定試験は講座の修了認定として研修に含め、受講案内・見積書には
#   **「受講料（認定試験の受験料を含む）」の1行**で1人1研修単位の金額を出す。
# ⛔ 内訳を「受講料＋受験料」に割って書かないこと（割った瞬間に受験料分が対象外になる）。
# ⛔ 総研修時間数（TRAINING_HOURS）を試験のぶん水増ししないこと。試験は受講後に
#    オンラインで受ける。実際の研修時間と違う数字を申請書に書かせることになる。
EXAMS = {
    'generalist': {
        'name': '生成AIジェネラリスト検定',
        'fee': 9800,
        'about': ('生成AIの基本概念から活用事例まで、ビジネスパーソンに'
                  '必要な知識を体系的に評価する検定です。'),
    },
    'engineer': {
        'name': '生成AIエンジニア認定',
        'fee': 9800,
        'about': ('プロンプトエンジニアリングから業務アプリの実装まで、'
                  '生成AIの実装・応用スキルを評価する認定試験です。'),
    },
}
EXAM_URL = 'https://www.qai-zen.com/examinations'

# 講座 → 組み込む試験。
# ⛔ 講座で教えない範囲の試験を割り当てないこと（受講者が落ちる＝受験料を
#    含めたことが逆に信用を落とす）。実装・アプリ開発を扱う講座だけ engineer。
# ⛔ 子ども向け（GK1〜3）には入れない。受験者にしないのが方針で、助成の対象でもない。
EXAM_FOR = {
    'SP-A': 'generalist', 'SP-B': 'generalist', 'SP-C': 'generalist',
    'GA': 'generalist', 'GA-P': 'generalist',
    'GD': 'generalist', 'GE': 'generalist',
    'GB': 'engineer', 'GC': 'engineer',
}
for _s in ('GM', 'GH', 'GF', 'GL', 'GN'):
    EXAM_FOR[f'{_s}-A'] = 'generalist'
    EXAM_FOR[f'{_s}-B'] = 'engineer'
    EXAM_FOR[f'{_s}-C'] = 'engineer'

# 受験料を受講料に上乗せするのは「上乗せしても助成の枠に収まる講座」だけ。
# ⛔ 1研修あたりが UNIT_PRICE（税抜10万円＝助成上限75,000円の点）を超えると
#    助成は1円も増えず、上乗せ分がまるごと法人の持ち出しになる。分割掲載の講座は
#    1研修が既に UNIT_PRICE ちょうど＝余地がゼロなので、価格を上げずに試験を含める。
# ⛔ 上乗せ額を手打ちしないこと（試験の受験料を変えた日に片方だけ古くなる）。
for _c in COURSES:
    _key = EXAM_FOR.get(_c['code'])
    if not _key or SESSIONS.get(_c['code']):
        continue
    _fee = EXAMS[_key]['fee']
    if _c['price'] + _fee <= UNIT_PRICE:
        _c['price'] += _fee


# ── 受講料の単位（社長ご提案 2026-08-17「¥xxxx/人 の方がいいのでは？」）
# 賛成する理由は見た目ではなく2つ。
#   ① 当社は「1名あたり」の講座と「1回あたり」の出張研修（10名まで同額）を
#      同じサイトで併売している＝単位が無いと、¥330,000 を1開催まとめての額と
#      読まれうる。金額が上がったぶん誤読の実害が大きい。
#   ② DXリスキリング助成金の要件2が「一般に公開された受講案内に**受講者
#      1人1研修単位の経費**が明記されていること」。単位の無い金額はこの要件に弱い。
# 「人」ではなく「名」にしたのは、サイト内の他の表記（1名／2〜4名／5〜9名／
# 10名以上／業種別カードの「/名（税込）」）が既に「名」で揃っているため。
# ⛔ 各画面に「（税込）」や「/名」を手打ちしないこと。ここが唯一の出どころで、
#    テンプレートには context_processor（app._subsidy_globals）から届く。
PRICE_UNIT = '/名'
PRICE_SUFFIX = '（税込）'


def unit_price_note(course_code):
    """分割掲載の講座に出す「1研修あたりいくら」。1本の講座なら空文字。

    ⛔ これを出さないと、助成金の要件2（受講案内に受講者1人1研修単位の経費が
       明記されていること）を満たさない。⛔ 時間数だけでは「経費」にならない
       ＝2026-08-17 時点で、業種別ページにしか金額が出ていなかった。
    """
    n = SESSIONS.get(course_code)
    if not n:
        return ''
    c = COURSE_BY_CODE.get(course_code)
    if not c:
        return ''
    return '1研修 ¥{:,}{}{} × 全{}研修'.format(
        c['price'] // n, PRICE_UNIT, PRICE_SUFFIX, n)


# 分割掲載の講座の買い方（2026-08-17 社長ご指示で1研修ずつ申し込めるようにした）。
# ⛔ この一文を各画面で書き起こさないこと。⛔ 実装（add_booking の sessions）を
#    外したらこの文も消すこと＝画面の約束を実装より先に出さない。
ORDER_NOTE = ('各回が独立した研修です。1研修ずつお申し込みいただけます'
              '（あとから追加も可能）。交付申請・受講証明書も1研修ごとにお出しします。')


def order_note(course_code):
    """分割掲載の講座に出す「買い方」の一言。1本の講座なら空文字。"""
    return ORDER_NOTE if SESSIONS.get(course_code) else ''


def exam_for(course_code):
    """その講座の受講料に含まれる認定試験。組み込んでいなければ None。"""
    key = EXAM_FOR.get(course_code)
    if not key:
        return None
    e = dict(EXAMS[key])
    e['key'] = key
    e['url'] = EXAM_URL
    return e


def exam_fee(course_code):
    """その講座の受講料に含まれる受験料（円）。無ければ0。"""
    e = exam_for(course_code)
    return e['fee'] if e else 0


def teaching_price(course_code):
    """講師料の算定に使う受講料＝認定試験の受験料を除いた額。

    ⛔ 受験料は協会が実施する試験の対価で、講師の仕事ではない。ここを分けないと
       受験料を組み込んだ日に講師料が自動で上がる（2026-08-17）。
    """
    c = COURSE_BY_CODE.get(course_code)
    if not c or not c.get('price'):
        return None
    return int(c['price']) - exam_fee(course_code)


def exam_note(course_code):
    """講座ページ・申込画面・メールに出す一言。組み込んでいなければ空文字。

    ⛔ 金額や試験名を各画面に手打ちしないこと。受験料を変えた日に、直し忘れた
       画面だけが古い額を出し続ける。
    """
    e = exam_for(course_code)
    if not e:
        return ''
    return '受講料に「{}」の受験料（¥{:,}）を含みます'.format(e['name'], e['fee'])


def apply_exam(courses, code_key='code'):
    """掲載ページの講座dictに認定試験の情報を入れる（表示を1か所から作る）。"""
    for c in courses:
        code = c.get(code_key) or ''
        e = exam_for(code)
        c['exam'] = bool(e)
        c['exam_name'] = e['name'] if e else ''
        c['exam_fee'] = e['fee'] if e else 0
        c['exam_about'] = e['about'] if e else ''
        c['exam_note'] = exam_note(code)
    return courses


# ⛔ 申込画面・申込完了・メールが読むのは COURSE_BY_CODE（この COURSES と同じ dict）で、
#    掲載ページ側の COURSES ではない。ここで入れておかないと、紹介ページには
#    「受験料を含む」と出ているのに申込画面には出ない、という食い違いになる。
#    apply_prices と違って新しい鍵を足すだけなので、price の計算には影響しない。
apply_exam(COURSES)


def open_slots(course_code, logger=None):
    """その講座の「いちばん近い開催日」と「選べる日数」。

    紹介ページが「申し込む」を出すか「まず相談する」を出すかの判断に使う。
    ⛔ 開催日を手で書いた文字列と併存させないこと。講師が日程を変えたときに
       画面の日付だけ古くなり、誤案内になる。
    ⛔ ここが例外でページを落とさないこと（紹介は予約より上位の役目）。
    ⛔ 2026-08-17 まで solo_ceo.py にしか無く、バイブコーディングの23講座は
       この判断を一切していなかった＝日程が公開されても紹介ページからは
       予約に行けず、「お申し込み」を名乗るフォームがメールを送るだけだった。
    """
    try:
        days = [d for d in open_days(course_code) if d['状態'] == '予約可']
        if not days:
            return {'件数': 0, '最短': None, '表示': '調整中'}
        first = days[0]['日付']
        _y, m, d = first.split('-')
        return {'件数': len(days), '最短': first,
                '表示': ('{}月{}日〜（他{}日）'.format(int(m), int(d), len(days) - 1)
                         if len(days) > 1 else '{}月{}日'.format(int(m), int(d)))}
    except Exception:                            # noqa: BLE001
        if logger:
            logger.exception('[booking] 開催日の集計に失敗しました')
        return {'件数': 0, '最短': None, '表示': '調整中'}


def sessions_of(course_code):
    """その講座を何本の研修として掲載しているか（分割していなければ1）。"""
    return SESSIONS.get(course_code, 1)


def unit_price_of(course_code):
    """1研修あたりの受講料（円・税込）。分割していない講座は受講料そのもの。

    ⛔ UNIT_PRICE を直接使わないこと。掲載価格から割り出す（価格を動かした日に
       申込金額だけ古い単価で計算される、を構造的に防ぐ）。
    """
    c = COURSE_BY_CODE.get(course_code)
    if not c:
        return None
    return int(c['price']) // sessions_of(course_code)


def normalize_sessions(course_code, want):
    """今回申し込む研修数を 1〜全研修数 に丸める。省略・不正なら全部。

    社長ご指示 2026-08-17。法人の担当者が起案する金額を決裁権限の内側
    （1研修 ¥110,000＝税抜10万円）に収めるため、分割掲載の講座は
    「今回何研修ぶん申し込むか」を選べるようにした。
    ⛔ 値引きではない。3研修受ければ受講料の合計は従来と同じ。
    ⛔ 画面から来た数字をそのまま金額に使わないこと（ここで必ず丸める）。
    """
    n = sessions_of(course_code)
    if n <= 1:
        return 1
    try:
        v = int(want)
    except (TypeError, ValueError):
        return n
    return max(1, min(n, v))


def unit_hours(course_code):
    """1研修あたりの総研修時間数。助成の判定はこちらで行う。"""
    h = TRAINING_HOURS.get(course_code)
    if h is None:
        return None
    return h / sessions_of(course_code)


# ── 東京しごと財団「DXリスキリング助成金」（令和8年度）
# 出典: https://www.koyokankyo.shigotozaidan.or.jp/jigyo/skillup/skill-R8dx-risk.html
# ⛔ 数字を画面に直書きしないこと。制度が変わった日に、直し忘れた画面が
#    古い金額を出し続ける（法人はその金額で申請して落ちる）。
SUBSIDY = {
    'name': '東京しごと財団 DXリスキリング助成金（令和8年度）',
    'rate': 0.75,                 # 助成対象経費の3/4
    'cap_per_person': 75000,      # 1人1研修あたりの上限
    'cap_per_company': 1000000,   # 1企業あたりの上限
    'min_hours': 3,               # 総研修時間数 3時間以上
    'max_hours': 10,              # 10時間未満
    'lead_days': 45,              # 研修開始の1か月前までに申請。余裕を見て45日
    'url': ('https://www.koyokankyo.shigotozaidan.or.jp/jigyo/skillup/'
            'skill-R8dx-risk.html'),
    'tax_rate': 0.10,             # 消費税は助成対象外なので税抜に直して計算する
}

# ── 助成金の注釈（社長ご指摘 2026-08-17「制度改正などにより、必ず補償が
#    受けられることを保証するものではないという注釈があった方がいいのでは」）
# ⛔ 実質のご負担額を出す画面には、必ずこの注釈も一緒に出すこと。
#    2026-08-17 実測で、実質の金額を出している8ページのうち注釈があったのは
#    /subsidy の1行だけ（しかも「審査により決定」だけで、制度改正・予算の
#    上限に触れていなかった）。金額だけが独り歩きすると、受けられなかった
#    法人との間で「そう書いてあった」になる。
# ⛔ 各画面に文を書き起こさないこと。制度が変わった日に、直し忘れた画面だけが
#    古い言い方で残る（助成額の直書きと同じ事故の型）。
# ⛔ 表示している金額は「満額支給された場合の目安」だと言い切ること。
SUBSIDY_DISCLAIMER_SHORT = (
    '※ 助成金の受給を保証するものではありません'
    '（審査・予算の上限・制度改正により受けられない場合があります）')
SUBSIDY_DISCLAIMER = (
    '助成の可否は東京しごと財団の審査により決定されます。'
    '予算の上限に達した場合の受付終了、制度の改正・変更、'
    '要件（受講者の立場・お支払い方法・出席時間）を満たさない場合など、'
    '助成を受けられないことがあります。当社は受給を保証するものではありません。'
    '表示している実質のご負担額は、助成金が満額支給された場合の目安です。')

# ⛔ 子ども向けは受講者が従業員でないので、時間に関係なく対象外
_SUBSIDY_NEVER = ('GK1', 'GK2', 'GK3')


def subsidy_for(course_code):
    """その講座が助成金の対象か。戻り値の dict は画面とメールが共通で使う。

    ⛔ 「代表者本人は対象外」を「この講座は対象外」と読み替えないこと
       （2026-08-15 社長ご指摘）。対象を決めるのは講座名ではなく
       **受講者の立場・誰が払うか・研修時間**の3つ。同じ講座でも、
       法人が従業員を研修として送れば対象になる。
    ⛔ 逆に「対象です」とだけ書かないこと。個人が自腹で受ける場合は
       対象外で、そちらの方が申込としては多い見込み。条件を必ず併記する。
    """
    c = COURSE_BY_CODE.get(course_code)
    if not c:
        return None
    n = sessions_of(course_code)
    hours = unit_hours(course_code)          # ⛔ 講座全体ではなく1研修あたりで判定する
    out = {'name': SUBSIDY['name'], 'url': SUBSIDY['url'],
           'hours': hours, 'total_hours': TRAINING_HOURS.get(course_code),
           'sessions': n, 'unit_price': c['price'] // n if c else 0,
           'eligible': False, 'reason': '',
           'grant': 0, 'net': c['price'] if c else 0,
           'lead_days': SUBSIDY['lead_days']}
    if course_code in _SUBSIDY_NEVER:
        out['reason'] = '受講者が企業の従業員ではないため対象外です'
        return out
    if hours is None:
        out['reason'] = '総研修時間数が未登録のため判定できません'
        return out
    if not (SUBSIDY['min_hours'] <= hours < SUBSIDY['max_hours']):
        out['reason'] = ('1研修あたりの総研修時間数が{}時間で、助成の要件'
                         '（{}時間以上{}時間未満）から外れます'.format(
                             hours, SUBSIDY['min_hours'], SUBSIDY['max_hours']))
        return out
    # 消費税は助成対象外。税込価格から税抜に直してから助成率をかける。
    # ⛔ 端数は切り上げないこと。案内した助成額が実際より多いと、法人は
    #    その差額を自腹で被る（少なく見せる側に倒すのが安全）。
    # ⛔ float で割らないこと＝110,000/1.1 が 99999.99… になり、税抜が99,999円、
    #    助成が74,999円と1円少なく出る（2026-08-17 実測）。Decimal で計算する。
    unit = Decimal(c['price']) / Decimal(n)
    base_d = (unit / (Decimal(1) + Decimal(str(SUBSIDY['tax_rate'])))
              ).quantize(Decimal('1'), rounding=ROUND_DOWN)
    grant_unit = min(
        int((base_d * Decimal(str(SUBSIDY['rate']))).quantize(
            Decimal('1'), rounding=ROUND_DOWN)),
        SUBSIDY['cap_per_person'])
    grant = grant_unit * n
    out.update(eligible=True, grant=grant, net=c['price'] - grant,
               base=int(base_d), grant_unit=grant_unit,
               reason=('法人が従業員を研修として派遣し、受講料の全額を'
                       '法人が負担する場合に対象となります'))
    return out


def subsidy_courses():
    """助成の対象になり得る講座コードの一覧。"""
    return [c['code'] for c in COURSES
            if (subsidy_for(c['code']) or {}).get('eligible')]


# ── 交付申請の「研修計画」にそのまま書ける、習得する知識・技能
# ⛔ 作文しないこと。各講座の掲載ページの curriculum / outcomes から起こす
#    （実際に教えないことを申請書に書かせると、実績報告で食い違う）。
# ⛔ 講座名だけでDX研修と判断されるとは限らない。「一人会社AI経営」のような
#    名称は、所管が中身を測れるようにこちらが言葉を用意する
#    （2026-08-15 社長ご指摘：障害は中身ではなく名称）。
DX_SKILLS = {
    # ── 回ごとに独立した研修として掲載する講座（2026-08-17）。
    #    ⛔ 文言は掲載ページの features / curriculum から起こしたもの。作文しない。
    #    ⛔ 対象講座に1つでも欠けると tests が落ちる＝法人が交付申請の
    #       「研修計画（様式第3号）」を書けないまま「対象です」と案内することになる。
    'SP-B': ('部門構築と役割定義、AIでアプリを作る、営業・マーケティング自動'
             '化システム、経理・バックオフィス自動化、AI経営ダッシュボード、'
             'スケーリング戦略と収益化。各回は独立した研修として実施し、1研修'
             'ごとに受講証明書を発行します。'),
    'SP-C': ('AI経営の設計図を描く、AI秘書・経理を構築する、営業・集客をA'
             'Iで自動化する、バイブコーディングで業務アプリを作る、統合・運用'
             '・スケーリング。各回は独立した研修として実施し、1研修ごとに受講'
             '証明書を発行します。'),
    'GC': ('プロンプト設計の深化、RAG（検索拡張生成）でナレッジベース構築'
             '、AIエージェント入門、ワークフロー自動化、卒業制作＋発表会。各'
             '回は独立した研修として実施し、1研修ごとに受講証明書を発行します'
             '。'),
    'GM-B': ('製造業分野における主要AIコーディングツール 完全習得、設備予知'
             '保全AIアプリの開発、品質管理SPC自動化ダッシュボード構築、工'
             '程最適化エンジンの実装。各回は独立した研修として実施し、1研修ご'
             'とに受講証明書を発行します。'),
    'GM-C': ('製造業分野におけるデジタルツイン設計・構築実践、IoTセンサーデ'
             'ータ×生成AI連携、AI生産管理システム設計・アーキテクチャ、本'
             '番デプロイ・運用保守体制構築。各回は独立した研修として実施し、1'
             '研修ごとに受講証明書を発行します。'),
    'GH-B': ('医療・ヘルスケア分野における主要AIコーディングツール 完全習得'
             '、電子カルテ連携AIアプリ開発、医療画像AI基礎・診断支援ツール'
             '構築、患者コミュニケーション最適化AI実装。各回は独立した研修と'
             'して実施し、1研修ごとに受講証明書を発行します。'),
    'GH-C': ('医療・ヘルスケア分野における病院DXシステム設計・アーキテクチャ'
             '、リモート患者モニタリングAI構築、医薬品管理AI・在庫最適化実'
             '装、本番デプロイ・運用保守体制構築。各回は独立した研修として実施'
             'し、1研修ごとに受講証明書を発行します。'),
    'GF-B': ('金融分野における主要AIコーディングツール 完全習得、リスク分析'
             'ダッシュボード開発、不正検知AIモデルの構築・実装、審査自動化ワ'
             'ークフロー構築。各回は独立した研修として実施し、1研修ごとに受講'
             '証明書を発行します。'),
    'GF-C': ('金融分野におけるALM最適化システム設計、信用スコアリングAIモ'
             'デル構築、規制対応AIチェックシステム実装、本番デプロイ・運用保'
             '守体制構築。各回は独立した研修として実施し、1研修ごとに受講証明'
             '書を発行します。'),
    'GL-B': ('物流分野における主要AIコーディングツール 完全習得、倉庫自動化'
             'AIシステム設計、サプライチェーン可視化ダッシュボード構築、ラス'
             'トワンマイル最適化エンジン実装。各回は独立した研修として実施し、'
             '1研修ごとに受講証明書を発行します。'),
    'GL-C': ('物流分野における物流DXプラットフォーム設計・アーキテクチャ、I'
             'oTセンサー×AI統合管理システム構築、リアルタイム配送ダッシュ'
             'ボードAPI開発、本番デプロイ・SaaS商用化。各回は独立した研'
             '修として実施し、1研修ごとに受講証明書を発行します。'),
    'GN-B': ('建設分野における主要AIコーディングツール 完全習得、BIM×A'
             'I連携アプリ開発、工程管理AIダッシュボード構築、品質検査自動化'
             'システム実装。各回は独立した研修として実施し、1研修ごとに受講証'
             '明書を発行します。'),
    'GN-C': ('建設分野における建設DX統合プラットフォーム設計、ドローン×AI'
             '検査システム構築、i-Construction対応AI実装、本番'
             'デプロイ・運用保守体制構築。各回は独立した研修として実施し、1研'
             '修ごとに受講証明書を発行します。'),
    'SP-A': ('生成AIを用いた社内業務の自動化（スケジュール管理・経費処理・'
             '請求書発行）、営業・マーケティング業務の自動化、'
             '業務用AIツールの比較・選定基準、AI利用に伴う情報セキュリティと'
             '法務リスクの管理。自社のDX導入計画の設計演習を含む。'),
    'GA': ('主要な生成AIツール（ChatGPT／Claude／Gemini）の特性理解と業務への'
           '適用、報告書作成・議事録要約・データ整理を効率化するプロンプト設計、'
           '機密情報漏洩・誤情報・著作権侵害リスクの理解と社内利用ルールの策定。'),
    'GA-P': ('主要な生成AIツール（ChatGPT／Claude／Gemini）の特性理解と業務への'
             '適用、自社の業務を対象としたプロンプト設計演習、社内利用ルールの'
             '策定。少人数制で、貴社の実業務を題材に演習を行います。'),
    'GB': ('プログラミング不要でのWeb業務アプリ開発（生成AIによるコード生成）、'
           '開発ツールの使い分け、作成したアプリの公開・運用。'
           '社内の定型業務をアプリ化して自動化するための実装技能。'),
    'GD': ('社内AI利用ガイドラインの策定、AI固有のセキュリティリスク'
           '（プロンプトインジェクション・データ漏洩・誤情報）の評価と対策の'
           '優先順位付け、AI起因のインシデント発生時の初動対応と再発防止。'),
    'GE': ('生成AIによる画像・動画・音声コンテンツの制作、ブランドガイドラインに'
           '沿った販促物制作ワークフローの構築、AI生成物の著作権・商用利用に'
           '関する法的リスクの判断基準。'),
}
for _s, _label in (('GM', '製造業'), ('GH', '医療・ヘルスケア'), ('GF', '金融'),
                   ('GL', '物流'), ('GN', '建設')):
    DX_SKILLS[f'{_s}-A'] = (
        f'{_label}の業務課題に対する生成AIの適用（業務データの分析・予測・'
        f'点検業務の自動化）、プログラミング不要での業務アプリ試作、'
        f'{_label}におけるAI導入のロードマップ策定。')


def dx_skills(course_code):
    """研修計画に書く「習得する知識・技能」。未登録なら空文字。"""
    return DX_SKILLS.get(course_code, '')


def subsidy_tag(course_code):
    """講座ページに出す助成金の一言。対象外なら空文字。

    ⛔ 「助成金対象」とだけ書かないこと。個人が自腹で受ける場合は対象外で、
       条件を落とすと、申し込んでから受けられないと分かる形で信用を失う。
    """
    s = subsidy_for(course_code) or {}
    if not s.get('eligible'):
        return ''
    return '法人研修なら助成金対象（実質 ¥{:,}）'.format(s['net'])


def apply_subsidy_tags(courses, code_key='code'):
    """掲載ページの講座dictに subsidy / subsidy_text を入れる。

    ⛔ 各ページに金額を手打ちしないこと。制度が変わった日に、直し忘れた
       ページだけが古い金額を出し続ける（法人はその額で申請して落ちる）。
    """
    for c in courses:
        code = c.get(code_key) or ''
        s = subsidy_for(code) or {}
        tag = subsidy_tag(code)
        c['subsidy'] = bool(tag)
        c['subsidy_text'] = tag
        # ⛔ テンプレート側で金額を直書きさせないための材料。無いと
        #    「実質 ¥24,800〜」のような古い数字が画面に残る（2026-08-15 実害）
        c['subsidy_grant'] = s.get('grant', 0)
        c['subsidy_net'] = s.get('net', c.get('price_num') or 0)
    return courses


# ── 講師料（2026-08-14 社長ご判断）
# 「単価の40%」を **1開催あたりの定額** で払う。⛔受講者の人数を掛けないこと。
# 10名でも1名でも同じ額（＝2人目以降は受講料がまるごと利益になる）。
FEE_RATE = 0.40
# 講師料の条件を提示した版。⛔条件を変えたらこの日付を上げること
#    （誰がどの条件に同意したかを追えなくなる）。
FEE_TERMS_VERSION = '2026-08-14'


def instructor_fee(course_code):
    """その講座を1回担当したときの講師料（円・定額）。読めなければ None。

    ⛔ 人数を掛けないこと。⛔ この式を画面やメールに書き写さないこと
       （率を変えた日に、直し忘れた場所が古い金額を出し続ける）。
    ⛔ c['price'] を直接使わないこと。受講料には認定試験の受験料が入っており、
       試験は協会が実施する＝講師の仕事ではない（2026-08-17）。
    """
    base = teaching_price(course_code)
    if base is None:
        return None
    return int(round(base * FEE_RATE))


def fee_terms_text():
    """講師登録画面とメールに出す、講師料の条件（1か所で作る）。"""
    return ('講師料は、その講座の受講料（認定試験の受験料を除く）の{}%を'
            '1開催あたりの定額でお支払いします。'
            '受講者が何名でも金額は変わりません（お一人でも開催します）。'
            'お支払いは開催月の翌月末までのお振込みです。'.format(
                int(FEE_RATE * 100)))


PAY_NOTE = ('お支払いはクレジットカード決済です。'
            '法人で請求書払いをご希望の場合は info@jgaia.org までご連絡ください。')
PAY_NOTE_INVOICE = ('お支払いは請求書（銀行振込）です。'
                    'お申し込み後に請求書をお送りします。')

# ── 講座の販売事業者（2026-08-14 社長ご説明で確定）
# 商流: 教材もシステムも ZebraQuantum が開発・提供し、JQCA／JGAIA の看板で販売する。
# よって受講契約の相手方（＝特定商取引法の「販売業者」）は ZebraQuantum。
# ⛔ 協会名を販売事業者として書かないこと。協会は看板（認定）であって売主ではない。
# ⛔ ここを1か所に保つこと。画面・メール・特商法表記が別々の名義を出すと、
#    どれが売主か分からなくなる（QAI-Zen は既に Zebra 名義で公開済み）。
# ⚠️ officer の氏名は要確認。公開中の法定表示（qai-zen.com/legal）は「諒雅」、
#    社内資料は「涼雅」。登記どおりに確定すること。直すのはこの1行だけで済む。
SELLER = {
    'name': '株式会社ZebraQuantum',
    'officer': '代表取締役 寺園 諒雅',
    'address': '〒104-0061 東京都中央区銀座1丁目22番11号 銀座大竹ビジデンス2F',
    'email': 'info@jgaia.org',
    'brand': '一般社団法人日本生成AI協会（JGAIA）',
}


def seller_footer():
    """メール末尾の署名。⛔売主と看板の両方を出すこと（片方だけだと誤認になる）。"""
    return ('---\n'
            '{brand}　認定講座\n'
            '販売事業者：{name}（{officer}）\n'
            '{address}\n'
            '{email} / https://www.jgaia.org/\n'.format(**SELLER))


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


def _norm_email(v):
    """照合用にそろえる。⛔ 大文字小文字を区別しないこと。
    Taro@ と taro@ は同じ受信箱に届くので、別人として登録されると
    同じ人が二重に公開される。
    """
    return (v or '').strip().lower()


def find_by_email(email):
    """同じメールアドレスの既存の登録を返す（無ければ None）。

    ⛔ 最初の1件を返すこと。2026-08-14 以前は重複チェックが無く、本番に
       同一アドレスの行が12件並んでいた（既存の重複は最も古い行に寄せる）。
    """
    e = _norm_email(email)
    if not e:
        return None
    for r in instructors():
        if _norm_email(r.get('連絡先')) == e:
            return r
    return None


def register_instructor(name, email, org, courses, note, days=None,
                        fee_agreed=''):
    """講師候補の申請を受ける。戻り値: (講師, 本人用の鍵)

    fee_agreed … 同意した講師料の条件の版（FEE_TERMS_VERSION）。
    ⛔ 同意の記録を上書きで消さないこと。いつ・どの版に同意したかは、
       条件を変えた後に「その人が何に同意していたか」を答える唯一の材料。

    ⛔ 同じメールアドレスなら行を増やさず既存を更新する（下記）。新規かどうかは
       呼ぶ前に find_by_email() で見ること（戻り値の形は変えていない＝
       呼び出し側30箇所以上が (rec, token) で受けているため）。

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

    # ── 同じメールアドレスなら、行を増やさず既存の登録を更新する
    # ⛔ append に戻さないこと（2026-08-14 社長ご指摘）。重複チェックが
    #    無かったため、本番の台帳は12件すべてが同一アドレスで、1人が
    #    12人として並んでいた。承認画面でどれが本物か分からなくなり、
    #    承認済みの行が2つ残ると同じ人が公開カレンダーに二重に出る。
    # ⛔ 鍵・id・登録日時・メール確認済み・担当できる日 は据え置くこと。
    #    鍵を振り直すと、本人が以前に受け取ったメールのリンクが死ぬ。
    #    メール確認済みは「本人が受け取った証拠」なので消さない。
    # ⛔ 再登録を「コースの変更手段」として塞がないこと。登録後にコースを
    #    変える画面が他に無いため、ここが唯一の入口になっている。
    old = find_by_email(email)
    if old:
        cur = old  # rows の中の同一オブジェクト（instructors() は同じ実体）
        for r in rows:
            if str(r.get('id')) == str(old.get('id')):
                cur = r
                break
        # ⛔ 承認済みの講座を、ここで巻き添えにしないこと（2026-08-15 修正）。
        #    旧実装は講座が1つ増えただけで状態ごと『申請中』へ戻しており、
        #    既に承認されている講座の日程まで予約カレンダーから消えていた。
        #    講師が5名いれば、誰かが担当を足すたびにその人が丸ごと消える。
        keep = set(approved_courses(cur))
        cur['氏名'] = name
        cur['連絡先'] = email
        cur['所属'] = org
        cur['対応コース'] = courses
        cur['備考'] = note
        # 承認済みは「今も選ばれているもの」だけ残す。足した分は審査待ち。
        # ⛔ 審査を通さずに担当を増やせる状態にはしないこと（承認は講座ごと）。
        cur['承認済みコース'] = sorted(keep & set(courses))
        # 見送りからの再登録は「再申請」として受ける（行を増やせば今日も
        # 同じことができるので、更新の方が実害が小さい）。
        if cur.get('状態') == '見送り':
            cur['状態'] = '申請中'
            cur.pop('判定日時', None)
        _record_fee_consent(cur, fee_agreed)
        cur['更新日時'] = now_jst().strftime('%Y-%m-%d %H:%M')
        _save('instructors.json', rows)
        return cur, cur.get('鍵')

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
        # 講師料の条件に同意した記録（版と日時）。⛔追記のみ・消さない
        '講師料同意': [],
    }
    _record_fee_consent(rec, fee_agreed)
    rows.append(rec)
    _save('instructors.json', rows)
    return rec, token


def _record_fee_consent(rec, version):
    """講師料の条件への同意を1件追記する。

    ⛔ 同じ版を何度も積まないこと（再登録のたびに行が増える）。
    ⛔ 過去の同意を消さないこと。条件を改定したあと「その人が何に同意して
       いたか」を答えられるのはこの記録だけ。
    """
    if not version:
        return rec
    log = list(rec.get('講師料同意') or [])
    if any(x.get('版') == version for x in log):
        return rec
    log.append({'版': version,
                '日時': now_jst().strftime('%Y-%m-%d %H:%M')})
    rec['講師料同意'] = log
    return rec


def approved_courses(inst):
    """その講師が『公開してよい』と承認されている講座。

    ⛔ 担当講座を1つ足しただけで、その人の日程を全部隠さないこと
       （2026-08-15 社長ご指摘）。旧実装は承認済みの人が講座を追加すると
       状態ごと『申請中』へ戻していたため、既に承認されている講座の日程まで
       予約カレンダーから消えていた。講師を増やすほどこの事故が増える。
    ⛔ かといって、審査を通さずに担当を増やせる状態にもしないこと。
       承認は**講座ごと**に持ち、足した分だけが審査待ちになる。
    """
    if inst.get('状態') != '承認':
        return []
    got = inst.get('承認済みコース')
    if got is None:
        # 2026-08-15 より前に承認された方。当時は対応コース＝承認済み
        return list(inst.get('対応コース') or [])
    return [c for c in got if c in (inst.get('対応コース') or [])]


def pending_courses(inst):
    """承認待ちの講座（本人が足したが、まだ審査されていないもの）。"""
    ok = set(approved_courses(inst))
    return [c for c in (inst.get('対応コース') or []) if c not in ok]


def set_instructor_courses(token, codes):
    """講師本人が担当講座を選び直す。戻り値: (講師, エラー文 or None)

    ⛔ 外した講座に予約が入っている場合は外させないこと（受講者が待っている）。
    ⛔ 足した講座をその場で公開しないこと（審査を通さず担当を増やせてしまう）。
    ⛔ 承認済みの講座まで巻き添えで非公開にしないこと（上記）。
    """
    inst = find_instructor(token)
    if not inst:
        return None, 'リンクが正しくありません'
    codes = [c for c in (codes or []) if c in COURSE_BY_CODE]
    if not codes:
        return None, '担当できる講座を1つ以上お選びください'
    # 予約が入っている講座は外せない
    booked = {b.get('コース') for b in bookings()
              if b.get('担当講師id') == inst.get('id') and is_live(b)}
    lost = sorted(booked - set(codes))
    if lost:
        return None, ('{} には受講者のお申し込みが入っているため、'
                      '担当から外すことはできません。'
                      'info@jgaia.org までご連絡ください'.format(' / '.join(lost)))
    rows = instructors()
    hit = None
    for r in rows:
        if r.get('鍵') != token:
            continue
        before = set(approved_courses(r))
        r['対応コース'] = codes
        # 承認済みは「今も選ばれているもの」だけを残す（外した分は消える）
        r['承認済みコース'] = sorted(before & set(codes))
        # ⛔ 状態は動かさない。足した分は pending_courses に出るだけ
        r['更新日時'] = now_jst().strftime('%Y-%m-%d %H:%M')
        # 担当できなくなった講座の日程は、その日から落とす
        days = dict(r.get('担当できる日') or {})
        for iso, cs in list(days.items()):
            keep = [c for c in cs if c in codes]
            if keep:
                days[iso] = keep
            else:
                days.pop(iso, None)
        r['担当できる日'] = days
        hit = r
    if hit:
        _save('instructors.json', rows)
    return hit, None


def approve_courses(instructor_id, codes=None):
    """運営が講座ごとに承認する。codes 省略で対応コース全部。"""
    rows = instructors()
    hit = None
    for r in rows:
        if str(r.get('id')) != str(instructor_id):
            continue
        want = codes if codes is not None else (r.get('対応コース') or [])
        ok = set(approved_courses(r)) | {c for c in want
                                         if c in (r.get('対応コース') or [])}
        r['承認済みコース'] = sorted(ok)
        hit = r
    if hit:
        _save('instructors.json', rows)
    return hit


def fee_agreed_version(inst):
    """その講師が同意している最新の条件の版（未同意なら None）。"""
    log = inst.get('講師料同意') or []
    return log[-1].get('版') if log else None


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
            # ⛔ 承認は講座ごとに持つ。承認を押した時点の担当を承認済みにする
            if state == '承認':
                r['承認済みコース'] = sorted(r.get('対応コース') or [])
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
    # ⛔ ここは本人の登録内容。承認で絞らないこと（絞ると旧形式の移行で
    #    他の日の登録が黙って消える）。公開の判定は open_days が行う
    for c in (inst.get('対応コース') or []):
        h = course_hours(c)
        if h and course_open_on(c, d) and any(
                s['開始'] <= h[0] and s['終了'] >= h[1] for s in slots):
            out.append(c)
    return out


def same_time_courses(codes):
    """開催時間が同じ（重なる）組み合わせを返す。⛔ 断る材料ではない。

    講師が選ぶのは「その日に**受けられる**講座（候補）」であって、
    「その日に全部開催する」ではない。実際に開催されるのは申込が入った
    1つだけで、時間の重なる他の講座はその時点で instructor_can_teach が
    自動的に閉じる（＝バッティングはそこで確実に止まる）。

    ⛔ ここを理由に登録を断らないこと。全26講座のうち18講座が 10:00〜17:00
       なので、断ると「1日1講座しか選べない」ことになり、複数選ぶ画面その
       ものが嘘になる（2026-08-14 社長ご指摘。SP-A・SP-B・GA・GB・GD・GE の
       6つを選んだだけでエラーになっていた）。
    ⛔ 使ってよいのは確認画面の注記まで（どれか1つだけ開催されると伝える）。
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
    # ⛔ 開催日でない日を受け取らないこと（画面を通らない経路もある）。
    #    ここを開けると、講師が自由に日を選べる状態に戻り、申込が散る
    d = date.fromisoformat(iso)
    if codes and not session_day_for(codes, d):
        return None, ('{}は開催日ではありません。{}'
                      .format(iso, session_day_note()))
    # ⛔ 曜日の合わない講座を受け取らないこと（画面を通らない経路もある）
    bad_wd = [c for c in ok if not course_open_on(c, d)]
    if bad_wd:
        c = bad_wd[0]
        return None, (f'{c} は{weekday_note(c)}。'
                      f'{WEEKDAYS[d.weekday()]}曜のこの日にはお受けいただけません')
    # ⛔ 開催時間が重なることを理由に断らないこと（same_time_courses の説明を参照）。
    #    ここは「その日に受けられる講座」の登録で、開催されるのは1つだけ。

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
                out.append(f'{c} は{series_note(c)}。'
                           f'{course_days(c)}回そろえて選んだ日が無いため、'
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


def continuing_service_risk(course_code):
    """特定継続的役務提供（パソコン教室）に当たりうるかを返す。理由 or None。

    特定商取引法は「パソコン教室」を対象役務にしており、**期間2か月超 かつ
    5万円超**の両方を満たすと、概要書面・契約書面の交付義務、クーリングオフ、
    中途解約権が発生する。バイブコーディング／AI経営の講座はこの役務に
    当たりうるので、線を越えたら気づけるようにしておく。

    2026-08-14 時点は全26講座とも非該当（最長でも SP-C の約5週間）。
    ⛔ この判定を消さないこと。回数や間隔を少し変えただけで越える。
    ⛔ 「当たらないから関係ない」と読まないこと。越えた瞬間に必要な書面が
       増える（画面を作り直す話になる）。
    """
    c = COURSE_BY_CODE.get(course_code)
    if not c:
        return None
    span = (course_days(course_code) - 1) * course_interval(course_code)
    # 2か月＝62日で見る（暦月の端数で判定がぶれないよう長い方に寄せる）
    if span > 62 and int(c.get('price') or 0) > 50000:
        return ('期間{}日・{:,}円のため、特定継続的役務提供（パソコン教室）に'
                '当たる可能性があります。概要書面・契約書面の交付、'
                'クーリングオフ、中途解約権の対応が必要です。'
                ).format(span, int(c['price']))
    return None


def continuing_service_alerts():
    """線を越えている講座の一覧（起動時とテストで見る）。"""
    return {c['code']: continuing_service_risk(c['code'])
            for c in COURSES if continuing_service_risk(c['code'])}


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
        if b.get('担当講師id') != instructor_id or not is_live(b):
            continue
        start = b.get('希望日')
        for iso in (b.get('開催日') or course_dates(b.get('コース'), start)):
            out.setdefault(iso, set()).add((b.get('コース'), start))
    return out


def instructor_free_on(inst, d, booked=None):
    """その講師がその日に講義できるか（コースを問わない）。

    booked にその講師の予約済みの日を渡すと、その日は「空いている」扱いにする。
    ⛔ ここを落とすと、1人目の申込が入った日を講師が週の設定から外した瞬間に
       2人目が申し込めなくなる。講師料は定額なので2人目以降は受講料がまるごと
       利益になる＝ここを塞ぐと、いちばん儲かる申込だけを取りこぼす。
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
              if course_code in approved_courses(i)]
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
        # ⛔ 取消・期限切れを残席から引かないこと（2026-08-14 修正）
        if b.get('コース') == course_code and is_live(b):
            taken[b.get('希望日')] = taken.get(b.get('希望日'), 0) + int(b.get('人数') or 1)

    out = []
    d = start
    while d <= limit:
        # ⛔ 開催日以外を「予約締切」と出さないこと。締切は講師の都合で閉じた
        #    日の意味で、そもそも開催しない日とは別物（カレンダーが締切だらけ
        #    に見えて「やっていない」と読まれる）
        if not is_session_day(d):
            state, who = '非開催日', []
        elif d < earliest:
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


# 担当回数を数える窓（日）。これより古い担当は数えない。
# ⛔ 全期間で数えないこと。あとから入った講師が永久に有利になり、
#    先に登録した方が長く干される。
ASSIGN_WINDOW_DAYS = 90


def assignment_counts(since_days=ASSIGN_WINDOW_DAYS):
    """講師id → 直近の担当回数（開催の回数）。

    ⛔ 申込の件数で数えないこと。同じ回に3名申し込んでも講師の仕事は1回で、
       講師料も1開催あたりの定額。件数で数えると「人気講座を担当した人」が
       不当に干される。
    ⛔ 取り消し・未決済を数えないこと（is_live）。
    """
    limit = (today_jst() - timedelta(days=since_days)).isoformat()
    seen, out = set(), {}
    for b in bookings():
        if not is_live(b):
            continue
        if (b.get('希望日') or '') < limit:
            continue
        key = (b.get('担当講師id'), b.get('コース'), b.get('希望日'))
        if key in seen:
            continue
        seen.add(key)
        out[b.get('担当講師id')] = out.get(b.get('担当講師id'), 0) + 1
    return out


def pick_instructor(course_code, d):
    """その日に割り当てる講師を決める。

    順番（2026-08-15 社長ご判断で「担当回数が少ない順」に変更）:
      1. その日・その講座に既に担当が決まっている人（最優先）
      2. 直近{}日の担当回数が少ない人
      3. 同数なら登録が早い人（並びを決定的にするため）

    ⛔ 「登録が早い順」に戻さないこと。最初に登録した1人に仕事が集中し、
       2人目以降は一度も声がかからない。マッチング事業で講師を失う
       いちばんの理由になる（実測：1講座に3件入ると全部同じ人だった）。
    ⛔ 「講師未定」で受講者に案内しない。予約が成立した時点で確定させる。
    """.format(ASSIGN_WINDOW_DAYS)
    # 同じ日に既に担当が決まっている講師を優先する（2人目の申込を同じ講師に寄せる）。
    # ⛔ 別の講師を割り当てると、同じ日・同じコースが二重開催になる
    people = [i for i in approved_instructors()
              if course_code in approved_courses(i)
              and instructor_can_start(i, d, course_code,
                                       occupied_days(i['id']),
                                       registered_days(i))]
    same_day = {b.get('担当講師id') for b in bookings_for(course_code, d.isoformat())}
    counts = assignment_counts()
    people.sort(key=lambda i: (i['id'] not in same_day,
                               counts.get(i['id'], 0),
                               i.get('登録日時') or ''))
    return people[0] if people else None


# ────────────────────────────── 申込
# 申込の状態:
#   お支払い待ち … カード決済の画面を開いた直後。席は押さえるが、決済が
#                  終わらなければ SESSION_TTL_MIN で自動的に解放する
#   申込受付     … 成立（カード決済済み、または請求書払いで受付）
#   取消         … 決済されなかった／取り消した
PENDING = 'お支払い待ち'


def bookings():
    return _load('bookings.json', [])


def is_live(b):
    """その申込を「席を押さえているもの」として数えるか。

    ⛔ 取消を数えないこと。ここを見ていなかったため、取り消した申込が
       いつまでも定員に数えられていた（open_days の残席・2026-08-14 に発見）。
    ⛔ 決済画面を開いたまま放置された申込を、永久に席を押さえたままにしない
       こと。1件で定員が1つ減り、誰も気づけない（Stripe の expired 通知が
       届かない場合の保険。届けばその場で取消になる）。
    """
    if b.get('状態') == '取消':
        return False
    if b.get('状態') == PENDING:
        try:
            started = datetime.strptime(b.get('申込日時', ''), '%Y-%m-%d %H:%M')
        except ValueError:
            return True                  # 読めないものは安全側（席を押さえる）
        limit = timedelta(minutes=payments_session_ttl_min())
        return (now_jst().replace(tzinfo=None) - started) <= limit
    return True


def payments_session_ttl_min():
    """決済画面の有効時間（分）。payments 側の設定を1か所から読む。

    ⛔ 数字をここに写さないこと（片方だけ変えると席が解放されない）。
    """
    try:
        import payments
        return int(payments.SESSION_TTL_MIN)
    except Exception:
        return 60


def bookings_for(course_code, day):
    return [b for b in bookings()
            if b.get('コース') == course_code and b.get('希望日') == day
            and is_live(b)]


def booked_summary(instructor_id):
    """予約が入っている日 → その日に担当する回の一覧（受講者の申込）。

    {'2026-09-14': [{'コース':'SP-B','コース名':'…','開始日':'2026-09-14','人数':3}]}
    ⛔ 「予約が入っている」とだけ画面に出さないこと。誰の何の予約かが
       分からないと、講師は自分がその日に何をするのか確かめられない
       （2026-08-13 社長ご質問）。
    """
    per, dates, wait = {}, {}, {}
    for b in bookings():
        if b.get('担当講師id') != instructor_id or not is_live(b):
            continue
        key = (b.get('コース'), b.get('希望日'))
        per[key] = per.get(key, 0) + int(b.get('人数') or 1)
        dates[key] = (b.get('開催日')
                      or course_dates(b.get('コース'), b.get('希望日')))
        # ⛔ 申告済みかどうかを画面に出すこと。出さないと、講師は届いたのか
        #    分からず何度も押す（2026-08-17 新設）
        if b.get('担当交代待ち'):
            wait[key] = b['担当交代待ち']
    out = {}
    for (code, start), people in sorted(per.items()):
        row = {'コース': code,
               'コース名': (COURSE_BY_CODE.get(code) or {}).get('name', ''),
               '開始日': start, '人数': people,
               '日程': dates[(code, start)],
               '担当交代待ち': wait.get((code, start))}
        for iso in dates[(code, start)]:
            out.setdefault(iso, []).append(row)
    return out


def booked_days_for_instructor(instructor_id):
    """その講師に既に予約が入っている日（3日間の講座なら3日ぶん）。

    ⛔ 予約が入っている日を、本人が「不可」に変えられないようにするために使う
       （受講者が待っている日を静かに閉じられると事故になる）。
    ⛔ 開始日だけを返さないこと。2日目・3日目を本人が消せてしまう。
    """
    return sorted(occupied_days(instructor_id))


def add_booking(course_code, day, name, email, company, people, message,
                pending=False, sessions=None):
    """申込を1件受ける。戻り値: (申込, 割り当てた講師 or None)

    pending=True … カード決済の画面へ送る前に席を押さえる（状態＝お支払い待ち）。
    ⛔ 決済が終わるまで「申込受付」にしないこと。払っていない人に
       「お申し込みを承りました」と届き、当日その席が空く。

    sessions … 分割掲載の講座で「今回申し込む研修数」（省略＝全部）。
    ⛔ 講師の割り当てと定員は全研修ぶんで判定したまま変えないこと。開催そのものは
       予定どおり全回行う（他のお客様は全回お申し込みになる）ので、講師の枠は
       全回ぶん押さえる必要がある。ここを緩めると当日に講師が居ない事故になる。
    """
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
    # 今回申し込む研修数。⛔ 画面の値をそのまま金額に使わないこと
    n_all = sessions_of(course_code)
    n_take = normalize_sessions(course_code, sessions)
    fee = unit_price_of(course_code) * n_take
    rec = {
        'id': secrets.token_hex(8),
        'コース': course_code, 'コース名': course['name'],
        '希望日': day,
        # 3日間の講座は開催する日をすべて残す。⛔ 開始日だけだと、あとから
        #    日数の設定を変えたときに過去の予約の実際の日程が変わってしまう
        # ⛔ 申し込んだ研修数ぶんだけを残すこと。全回ぶん書くと、受講証明書の
        #    実施日が実際に出ない日まで並ぶ（虚偽の証明になる）
        '開催日': course_dates(course_code, day)[:n_take],
        '氏名': name, '連絡先': email, '会社名': company,
        '人数': want, 'ご要望': message,
        '担当講師': inst['氏名'], '担当講師id': inst['id'],
        '研修数': n_take, '全研修数': n_all,
        '受講料_円': fee,
        '請求額_円': fee * want,
        '状態': PENDING if pending else '申込受付',
        '支払方法': 'card' if pending else 'invoice',
        '申込日時': now_jst().strftime('%Y-%m-%d %H:%M'),
    }
    rows.append(rec)
    _save('bookings.json', rows)

    total = already + rec['人数']
    rec['_合計人数'] = total
    # ⛔ 「_開催確定」を人数で判定しないこと（最少催行は撤廃済み・冒頭の説明を参照）。
    #    申込が1件入った時点で開催は確定する
    rec['_開催確定'] = True
    return rec, inst


def attach_checkout(booking_id, session_id):
    """決済ページの識別子を申込に結びつける（あとで照合するため）。"""
    rows = bookings()
    hit = None
    for r in rows:
        if r.get('id') == booking_id:
            r['決済id'] = session_id
            hit = r
    if hit:
        _save('bookings.json', rows)
    return hit


def mark_paid(session_id, payment_id=''):
    """決済が終わった申込を成立させる。戻り値: (申込, 講師) / (None, None)

    ⛔ 何度呼ばれても1回だけ成立させること。Stripe は同じ通知を再送するので、
       ここが冪等でないと受講者に確認メールが何通も届く。
    """
    rows = bookings()
    hit = None
    for r in rows:
        if r.get('決済id') != session_id:
            continue
        if r.get('状態') != PENDING:
            return None, None            # すでに処理済み（再送）
        r['状態'] = '申込受付'
        r['支払方法'] = 'card'
        r['決済日時'] = now_jst().strftime('%Y-%m-%d %H:%M')
        if payment_id:
            r['決済番号'] = payment_id
        hit = r
    if not hit:
        return None, None
    _save('bookings.json', rows)
    inst = None
    for i in instructors():
        if i.get('id') == hit.get('担当講師id'):
            inst = i
    hit['_合計人数'] = sum(int(b.get('人数') or 1) for b in
                       bookings_for(hit['コース'], hit['希望日']))
    hit['_開催確定'] = True
    return hit, inst


def certificate_data(booking_id):
    """受講証明書（参考様式2）に書く項目を、申込から組み立てて返す。

    ⛔ 総研修時間数を画面で手入力させないこと。財団は「8割以上の受講」を
       この数字で判定するので、講座ごとの実数（TRAINING_HOURS）から出す。
    ⛔ 出席時間はこちらで埋めないこと。実際に何時間出席されたかは当日
       確認するもので、推測で書けば虚偽の証明になる。
    """
    rec = None
    for b in bookings():
        if b.get('id') == booking_id:
            rec = b
    if not rec:
        return None
    code = rec.get('コース')
    # ⛔ 講座全体の時間を書かないこと。財団は「8割以上の受講」をこの数字で
    #    判定するので、実際に申し込まれた研修数ぶんに直す（2026-08-17）。
    #    ⛔ 古い申込（研修数を持たない行）は全研修ぶんとして扱う。
    hours = TRAINING_HOURS.get(code)
    n_all = sessions_of(code)
    n_take = int(rec.get('研修数') or n_all)
    if hours is not None and n_all > 1:
        hours = round(hours / n_all * n_take, 2)
    s = subsidy_for(code) or {}
    return {
        '申込id': booking_id,
        '受講者': rec.get('氏名'),
        '企業名': rec.get('会社名') or '（未入力）',
        '研修名': '{} {}{}'.format(
            code, rec.get('コース名'),
            '' if n_all <= 1 else '（全{}研修のうち{}研修）'.format(n_all, n_take)),
        '研修数': n_take, '全研修数': n_all,
        '実施日': rec.get('開催日') or [rec.get('希望日')],
        '総研修時間数': hours,
        '必要出席時間数': (round(hours * 0.8, 1) if hours else None),
        '出席時間数': None,          # ⛔当日に確認して埋める
        '受講料_円': rec.get('受講料_円'),
        '支払方法': rec.get('支払方法'),
        '助成対象': s.get('eligible', False),
        '対象外の理由': '' if s.get('eligible') else s.get('reason', ''),
        '教育機関': SELLER['name'],
        '発行者': SELLER['officer'],
        # ⛔ カード払い・個人払いは助成の対象外。証明書を出す前に気づけるようにする
        '注意': ('' if rec.get('支払方法') != 'card' else
                 '受講料がクレジットカードで支払われています。助成金は'
                 '申請企業の口座からの振込払いが要件のため、この申込は'
                 '助成の対象になりません。'),
    }


def subsidy_deadline_ok(day_iso):
    """その開催日が、助成金の申請に間に合うか。"""
    try:
        d = date.fromisoformat(day_iso)
    except (TypeError, ValueError):
        return None
    return d >= today_jst() + timedelta(days=SUBSIDY['lead_days'])


def request_replacement(token, iso, reason=''):
    """講師が「その日は担当できなくなった」と申告する（社長ご質問 2026-08-17）。

    ⛔ 2026-08-17 まで、この口がどこにも無かった。講師への依頼メールは
       「ご都合が変わった場合はご自身の予定画面からその日を『不可』にしてください」
       と案内しているのに、set_day_courses は予約の入った日を拒否する＝
       **できない操作を案内していた**。行き先は info@jgaia.org へのメールだけで、
       そこから先は運営が手で追うしかなかった。

    ⛔ 予約そのものを取り消さないこと。受講者との約束であって、講師の都合で
       消してよいものではない（別の講師を立てられるなら開催できる）。
    ⛔ 受講者へ自動で連絡しないこと。代わりが立つかどうかを確かめてから、
       人が伝える（「中止」と誤って伝わるのがいちばん重い）。
    戻り値: (印を付けた申込のリスト, エラー文 or None)
    """
    inst = find_instructor(token)
    if not inst:
        return [], 'リンクが正しくありません'
    reason = (reason or '').strip()
    if len(reason) < 4:
        return [], '理由を書いてください（4文字以上）'
    rows = bookings()
    hit = []
    for b in rows:
        if b.get('担当講師id') != inst.get('id') or not is_live(b):
            continue
        if iso not in (b.get('開催日') or [b.get('希望日')]):
            continue
        b['担当交代待ち'] = {'申告日時': now_jst().strftime('%Y-%m-%d %H:%M'),
                             '理由': reason, '対象日': iso,
                             '元の講師': inst.get('氏名')}
        hit.append(b)
    if not hit:
        return [], 'その日には、あなたが担当する申込がありません'
    _save('bookings.json', rows)
    return hit, None


def replacement_waiting():
    """代わりの講師を立てる必要がある申込（運営が見る）。"""
    return [b for b in bookings() if b.get('担当交代待ち') and is_live(b)]


def cancel_booking(booking_id, reason=''):
    """申込を取り消して席を解放する。⛔行は消さない（何件失ったかが残る）。"""
    rows = bookings()
    hit = None
    for r in rows:
        if r.get('id') == booking_id and r.get('状態') != '取消':
            r['状態'] = '取消'
            r['取消理由'] = reason
            hit = r
    if hit:
        _save('bookings.json', rows)
    return hit


def mark_unpaid(session_id):
    """決済されずに終わった申込を取り消して、席を解放する。

    ⛔ 行を消さないこと。何件が決済まで至らなかったかが分からなくなる。
    """
    rows = bookings()
    hit = None
    for r in rows:
        if r.get('決済id') == session_id and r.get('状態') == PENDING:
            r['状態'] = '取消'
            r['取消理由'] = 'お支払いが完了しませんでした'
            hit = r
    if hit:
        _save('bookings.json', rows)
    return hit
