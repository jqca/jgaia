# -*- coding: utf-8 -*-
"""講師の登録・承認、コースごとの予約の画面と受付。

画面:
  /instructor/register          講師候補の登録（誰でも申請できる）
  /instructor/schedule/<鍵>     講師本人が自分の講義できる日を編集
  /admin/instructors            承認画面（管理用の合言葉が必要）
  /book/<コース>                コースごとの予約フォーム

⛔ 承認していない講師の枠を公開しないこと（booking.approved_instructors を使う）。
⛔ 管理画面は合言葉が未設定なら機能ごと閉じる（設定忘れで誰でも見える状態にしない）。
"""
import hmac
import os
from datetime import date, datetime, timedelta

from flask import (jsonify, redirect, render_template, request, url_for)

import booking


# ⛔ 合言葉は両端を剥ぐこと（旧実装は先頭だけの lstrip）。末尾のBOMでも
#    照合だけが静かに落ちる。PowerShell の標準入力経由で設定すると実際に混入する。
_TRIM = '﻿ \t\r\n'


def _weekly_from_form(form):
    """登録フォームの曜日×時間帯を読む。1つの曜日に複数の枠を書ける。

    欄の名前: wd{i} / from{i} / to{i} が1本目、from{i}_2 / to{i}_2 が2本目…
    （画面のJSが2本目以降を足す。JSが動かない環境でも1本目だけは必ず通る）
    ⛔ 本数を決め打ちで2本までにしないこと。朝・昼・夜と分ける方がいる。
    """
    weekly = []
    for i in range(7):
        if not form.get(f'wd{i}'):
            continue
        pairs = [(form.get(f'from{i}'), form.get(f'to{i}'))]
        for n in range(2, 13):
            a, b = form.get(f'from{i}_{n}'), form.get(f'to{i}_{n}')
            if a and b:
                pairs.append((a, b))
        for a, b in pairs:
            weekly.append({'曜日': i, '開始': a or '10:00', '終了': b or '17:00'})
    # ⛔ ここで正規化まで済ませない（保存側 register_instructor が唯一の関所）
    return weekly


def _admin_ok():
    expected = (os.environ.get('INQUIRY_ADMIN_TOKEN') or '').strip(_TRIM)
    if not expected:
        return None                      # 未設定＝機能ごと閉じる
    given = ((request.args.get('token') or request.form.get('token')
              or request.headers.get('X-Admin-Token') or '')
             .strip(_TRIM))
    return hmac.compare_digest(given.encode(), expected.encode())


def register_booking_routes(app):

    # ─────────────── 講師候補の登録
    @app.route('/instructor/register', methods=['GET', 'POST'])
    def instructor_register():
        if request.method == 'GET':
            return render_template('instructor_register.html',
                                   courses=booking.COURSES,
                                   weekdays=booking.WEEKDAYS)

        import antispam
        if antispam.check(request, request.form.to_dict()):
            app.logger.info('[instructor_register] スパムとして遮断')
            return render_template('instructor_register.html', done=True,
                                   courses=booking.COURSES,
                                   weekdays=booking.WEEKDAYS)

        name = (request.form.get('name') or '').strip()
        email = (request.form.get('email') or '').strip()
        if not name or not email:
            return render_template('instructor_register.html',
                                   error='お名前とメールアドレスは必須です。',
                                   courses=booking.COURSES,
                                   weekdays=booking.WEEKDAYS)

        weekly = _weekly_from_form(request.form)
        rec, token = booking.register_instructor(
            name, email, (request.form.get('org') or '').strip(),
            request.form.getlist('courses'),
            (request.form.get('note') or '').strip(), weekly)

        app.logger.info('[instructor_register] 申請: %s', name)
        return render_template('instructor_register.html', done=True,
                               token=token, rec=rec,
                               courses=booking.COURSES,
                               weekdays=booking.WEEKDAYS)

    # ─────────────── 講師本人が予定を編集
    @app.route('/instructor/schedule/<token>')
    def instructor_schedule(token):
        inst = booking.find_instructor(token)
        if not inst:
            return 'この画面のリンクが正しくありません。運営にお問い合わせください。', 404
        # 開催時間は COURSES の hours から解いて渡す（画面で書き写さない）
        courses = []
        for c in booking.COURSES:
            h = booking.course_hours(c['code'])
            courses.append(dict(c, 開始=h[0] if h else '', 終了=h[1] if h else ''))
        return render_template('instructor_schedule.html', inst=inst, token=token,
                               weekdays=booking.WEEKDAYS,
                               months=_month_grids(3),
                               lead_days=booking.LEAD_DAYS,
                               booked_days=booking.booked_days_for_instructor(inst['id']),
                               earliest=(booking.today_jst()
                                         + timedelta(days=booking.LEAD_DAYS)).isoformat(),
                               courses=courses)

    @app.route('/api/instructor/schedule', methods=['POST'])
    def api_instructor_schedule():
        data = request.get_json(silent=True) or {}
        token = (data.get('token') or '').strip()
        if not booking.find_instructor(token):
            return {'error': 'リンクが正しくありません'}, 403
        weekly = [w for w in (data.get('weekly') or [])
                  if str(w.get('曜日')).isdigit()]
        blocked = [d for d in (data.get('blocked') or []) if _is_day(d)]
        # その日だけ時間を変える枠 {'2026-09-05': [{'開始','終了'}]}
        daily = {k: v for k, v in (data.get('daily') or {}).items()
                 if _is_day(k) and isinstance(v, list)}
        inst = booking.update_availability(token, weekly, blocked, daily)
        return {'ok': True, '更新日時': inst.get('更新日時'),
                '日別の可能時間': inst.get('日別の可能時間') or {},
                '不可の日': inst.get('不可の日') or []}

    # ─────────────── 承認画面
    @app.route('/admin/instructors')
    def admin_instructors():
        ok = _admin_ok()
        if ok is None:
            return {'error': 'disabled',
                    'message': '管理用の合言葉が未設定のため無効です。'}, 503
        if not ok:
            return {'error': 'forbidden'}, 403
        rows = booking.instructors()
        return render_template('admin_instructors.html', rows=rows,
                               token=request.args.get('token', ''),
                               weekdays=booking.WEEKDAYS,
                               courses=booking.COURSES,
                               bookings=booking.bookings())

    @app.route('/api/instructors')
    def api_instructors():
        """講師の一覧をJSONで返す（SoloOS の承認画面が読む）。

        ⛔ この口を合言葉なしで開けないこと。連絡先と本人用の鍵を含む。
        ⛔ 画面(/admin/instructors)と別の集計を書かないこと＝同じ booking を読む。
        """
        ok = _admin_ok()
        if ok is None:
            return {'error': 'disabled',
                    'message': '管理用の合言葉が未設定のため無効です。'}, 503
        if not ok:
            return {'error': 'forbidden'}, 403
        bookings = booking.bookings()
        rows = []
        for r in booking.instructors():
            mine = [b for b in bookings if b.get('担当講師id') == r.get('id')]
            rows.append(dict(
                r,
                予約件数=len(mine),
                予約人数=sum(int(b.get('人数') or 1) for b in mine),
                予定URL=url_for('instructor_schedule', token=r.get('鍵'),
                                _external=True),
            ))
        return {'ok': True, 'rows': rows,
                'courses': [{'code': c['code'], 'name': c['name']}
                            for c in booking.COURSES],
                'weekdays': booking.WEEKDAYS,
                'lead_days': booking.LEAD_DAYS,
                '申込件数': len(bookings),
                '登録URL': url_for('instructor_register', _external=True)}

    @app.route('/api/instructor/decide', methods=['POST'])
    def api_instructor_decide():
        ok = _admin_ok()
        if ok is None or not ok:
            return {'error': 'forbidden'}, 403
        data = request.get_json(silent=True) or {}
        state = data.get('state')
        if state not in ('承認', '見送り', '申請中'):
            return {'error': 'state が不正です'}, 400
        if not booking.set_state(data.get('id'), state):
            # 画面を再読込しても直らないので、押した人にそのまま伝える
            return {'error': 'その講師が見つかりませんでした。画面を再読込してください'}, 404
        return {'ok': True}

    # ─────────────── コースごとの予約
    @app.route('/book/<code>')
    def book_course(code):
        course = booking.COURSE_BY_CODE.get(code)
        if not course:
            return 'コースが見つかりません', 404
        days = {d['日付']: d for d in booking.open_days(code)}
        return render_template('course_book.html', c=course, days=days,
                               months=_month_grids(3),
                               lead_days=booking.LEAD_DAYS,
                               cancel_policy=booking.CANCEL_POLICY,
                               pay_note=booking.PAY_NOTE,
                               courses=booking.COURSES,
                               open_count=sum(1 for d in days.values()
                                              if d['状態'] == '予約可'))

    @app.route('/api/book', methods=['POST'])
    def api_book():
        data = request.get_json(silent=True) or {}

        import antispam
        if antispam.check(request, data):
            app.logger.info('[book] スパムとして遮断')
            return {'ok': True}          # ボットに教えない

        name = (data.get('name') or '').strip()
        email = (data.get('email') or '').strip()
        if not name or not email or not data.get('day'):
            return {'error': 'お名前・メールアドレス・希望日は必須です'}, 400

        try:
            rec, inst = booking.add_booking(
                data.get('course'), data.get('day'), name, email,
                (data.get('company') or '').strip(),
                data.get('people') or 1, (data.get('message') or '').strip())
        except ValueError as e:
            return {'error': str(e)}, 400
        except Exception:
            app.logger.exception('[book] 申込の保存に失敗')
            return {'error': '受付処理に失敗しました。info@jgaia.org までご連絡ください。'}, 500

        _notify_booking(app, rec, inst)
        return {'ok': True,
                '開催確定': rec['_開催確定'],
                '合計人数': rec['_合計人数'],
                '最少催行': rec['_最少催行']}


def _is_day(s):
    try:
        date.fromisoformat(str(s))
        return True
    except Exception:
        return False


def _month_grids(n):
    """当月から n か月ぶんの、日曜始まりではなく月曜始まりの月表。"""
    out = []
    d = booking.today_jst().replace(day=1)
    for _ in range(n):
        first_wd = d.weekday()               # 月=0
        days = []
        for _ in range(first_wd):
            days.append(None)                # 月初の空白
        cur = d
        while cur.month == d.month:
            days.append(cur.isoformat())
            cur += timedelta(days=1)
        while len(days) % 7:
            days.append(None)
        out.append({'年': d.year, '月': d.month, '日': days})
        d = cur
    return out


def _notify_booking(app, rec, inst):
    """申込を運営と講師と受講者に知らせる。

    ⛔ 送れなくても申込は保存済み。ここで例外を投げないこと。
    """
    key = os.environ.get('RESEND_API_KEY', '')
    if not key:
        app.logger.error('[book] 送信手段が未設定。申込は保存済み: %s', rec['氏名'])
        return
    try:
        import resend
        from mail_targets import FROM_EMAIL, notify_payload
        resend.api_key = key

        body = '\n'.join([
            f"コース: {rec['コース']} {rec['コース名']}",
            f"開催希望日: {rec['希望日']}",
            f"お名前: {rec['氏名']}",
            f"メール: {rec['連絡先']}",
            f"会社名: {rec['会社名']}" if rec['会社名'] else '',
            f"人数: {rec['人数']}名",
            f"担当講師: {rec['担当講師']}",
            f"この日の合計: {rec['_合計人数']}名（最少催行 {rec['_最少催行']}名）"
            + ('→ 開催確定' if rec['_開催確定'] else '→ まだ最少催行に達していません'),
            f"ご要望: {rec['ご要望']}" if rec['ご要望'] else '',
        ])
        resend.Emails.send(notify_payload(
            f"【受講申込】{rec['コース']} {rec['希望日']} {rec['氏名']}様",
            reply_to=rec['連絡先'], text=body))

        # 受講者へ
        confirm = (
            f"{rec['氏名']} 様\n\n"
            f"お申し込みありがとうございます。以下の内容で承りました。\n\n"
            f"■ コース: {rec['コース']} {rec['コース名']}\n"
            f"■ 開催希望日: {rec['希望日']}\n"
            f"■ 人数: {rec['人数']}名\n"
            f"■ 受講料: {rec['受講料_円']:,}円（税込）\n\n"
            f"{booking.PAY_NOTE}\n\n"
            f"【開催の確定について】\n"
            f"このコースは{rec['_最少催行']}名以上で開催します。"
            + ('現時点で開催が確定しています。\n'
               if rec['_開催確定'] else
               '人数が集まり次第、開催の確定をご連絡します。'
               '集まらない場合は次回へお振替いただけます。\n')
            + f"\n【キャンセルについて】\n{booking.CANCEL_POLICY}\n\n"
            '---\n一般社団法人日本生成AI協会（JGAIA）\n'
            '〒104-0061 東京都中央区銀座1-22-11 銀座大竹ビジデンス2階\n'
            'info@jgaia.org / https://www.jgaia.org/\n')
        resend.Emails.send({'from': f'JGAIA <{FROM_EMAIL}>', 'to': [rec['連絡先']],
                            'subject': f"【JGAIA】{rec['コース名']} お申し込みを承りました",
                            'text': confirm})

        # 講師へ
        if inst.get('連絡先'):
            resend.Emails.send({
                'from': f'JGAIA <{FROM_EMAIL}>', 'to': [inst['連絡先']],
                'subject': f"【JGAIA】{rec['希望日']} {rec['コース']} の担当のご依頼",
                'text': (f"{inst['氏名']} 様\n\n"
                         f"下記の受講申込が入りました。ご担当をお願いできますでしょうか。\n\n"
                         f"■ 日付: {rec['希望日']}\n"
                         f"■ コース: {rec['コース']} {rec['コース名']}\n"
                         f"■ 現在の人数: {rec['_合計人数']}名"
                         f"（最少催行 {rec['_最少催行']}名）\n\n"
                         f"ご都合が変わった場合は、ご自身の予定画面から'"
                         f"'その日を「不可」にしてください。\n"
                         '---\n一般社団法人日本生成AI協会（JGAIA）\n')})
    except Exception:
        app.logger.exception('[book] 通知メールに失敗。申込は保存済み: %s', rec['氏名'])
