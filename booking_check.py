# -*- coding: utf-8 -*-
"""掲載している全講座について「いま受講者が予約できるか」を1枚で見る画面。

社長ご指示 2026-08-17「GAしか講師の講義可能な日付登録がないせいか、他の講座に
ついて受講生が予約登録できるか目視確認できません。全講座で予約登録可能か
目視確認できるようにして」。

それまでは講座ごとに紹介ページ（8ページ）を開いて回るしか確かめる手が無く、
どの講座が生きていてどれが行き止まりなのかを**一覧で見る場所が無かった**。

⛔ ここで「予約できるか」を別のやり方で判定しないこと。出どころは
   booking.open_slots()／open_days() の1か所＝紹介ページが「申し込む」を出すか
   「調整中」と出すかと**同じ判断**を読む。別に数えると、この画面は緑なのに
   紹介ページは調整中、という食い違いが黙って起きる。
⛔ 0件のときは必ず理由を出すこと。件数だけだと「なぜ出ないのか」が分からず、
   放っておいても永久に変わらない状態を「調整中」と読み違える。
⛔ 合言葉なしで開けないこと（担当講師の氏名と申込人数が出る）。
"""
import booking
from flask import render_template, request, url_for

from booking_routes import _admin_ok      # ⛔ 合言葉の照合を2つ書かないこと


# 講座コード → その講座を紹介しているページ。
# ⛔ 予約ページ（/book/<code>）だけを出さないこと。受講者が実際に通るのは
#    紹介ページの「申し込む」ボタンなので、そこに導線が出ているかまで見て
#    はじめて「予約できる」と言える。
# ⛔ 講座を足したらここにも足すこと（tests/test_booking_check.py が落ちる）。
INTRO = {
    'SP-A': '/solo-ceo/course-spa',
    'SP-B': '/solo-ceo/course-spb',
    'SP-C': '/solo-ceo/course-spc',
    'GA': '/vibe-coding/course-ga',
    'GA-P': '/vibe-coding/course-gap',
    'GB': '/vibe-coding/course-gb',
    'GC': '/vibe-coding/course-gc',
    'GD': '/vibe-coding/course-gd',
    'GE': '/vibe-coding/course-ge',
    'GK1': '/vibe-coding/kids',
    'GK2': '/vibe-coding/kids',
    'GK3': '/vibe-coding/kids',
}
for _pre, _slug in (('GM', 'manufacturing'), ('GH', 'healthcare'),
                    ('GF', 'finance'), ('GL', 'logistics'),
                    ('GN', 'construction')):
    for _lv in ('A', 'B', 'C'):
        INTRO['%s-%s' % (_pre, _lv)] = '/vibe-coding/' + _slug


def course_rows(logger=None):
    """全講座ぶんの「いま予約できるか」。画面とJSONで同じものを使う。"""
    people = booking.approved_instructors()
    rows = []
    for c in booking.COURSES:
        code = c['code']
        slot = booking.open_slots(code, logger)
        # ⛔ 「承認されている講師」を「予約を受けられる講師」として出さないこと。
        #    承認済みでも日程が無ければ1件も受けられない（実測：社長の行は
        #    登録日が締切内の1日だけなのに、全講座の担当者として並んでいた）。
        who = [i for i in people if code in booking.approved_courses(i)]
        ready = sorted({n for d in booking.open_days(code)
                        if d['状態'] == '予約可' for n in d['講師']})
        # ⛔ 「担当できる講師がいない」と「日が無い」を混ぜないこと。
        #    直す相手が違う（承認する／日程を入れてもらう）
        if slot['件数']:
            reason = ''
        elif not who:
            reason = ('この講座を担当できる承認済みの講師が0名です'
                      '（登録・承認するまで、この講座は永久に予約できません）')
        else:
            reason = ('担当できる講師は{}名いますが、{}日以上先の開催日に'
                      'この講座の予約枠がありません'
                      '（日程が未登録／満席／開催日でない曜日のみ登録）'
                      .format(len(who), booking.LEAD_DAYS))
        rows.append({
            'code': code,
            'name': c['name'],
            'group': c.get('group') or 'その他',
            'price': c['price'],
            'hours': c.get('hours') or '',
            'days': booking.course_days(code),
            '件数': slot['件数'],
            '最短': slot['最短'],
            '表示': slot['表示'],
            '講師数': len(ready),
            '講師': ready,
            '承認済み講師数': len(who),
            # 承認はされているのに、日程が無くて1件も受けられない方
            '日程待ちの講師': [i.get('氏名') for i in who
                               if i.get('氏名') not in ready],
            '理由': reason,
            '予約URL': url_for('book_course', code=code),
            '紹介URL': INTRO.get(code, ''),
        })
    return rows


def register_booking_check_routes(app):

    @app.route('/admin/booking-check')
    def admin_booking_check():
        ok = _admin_ok()
        if ok is None:
            return {'error': 'disabled',
                    'message': '管理用の合言葉が未設定のため無効です。'}, 503
        if not ok:
            return {'error': 'forbidden'}, 403

        rows = course_rows(app.logger)
        live = [r for r in rows if r['件数']]
        if (request.args.get('format') or '').lower() == 'json':
            return {'ok': True, '講座数': len(rows), '予約できる講座': len(live),
                    'lead_days': booking.LEAD_DAYS, 'rows': rows}

        # 掲載ページと同じまとまりで出す（1列に27講座を並べると探せない）
        by_code = {r['code']: r for r in rows}
        groups = [(g, [by_code[c['code']] for c in items])
                  for g, items in booking.grouped_courses()]
        return render_template(
            'admin_booking_check.html', groups=groups, rows=rows,
            live=len(live), total=len(rows),
            lead_days=booking.LEAD_DAYS,
            session_note=booking.session_day_note(),
            token=(request.args.get('token') or ''),
            instructors=booking.instructors())
