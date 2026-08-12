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

        # ⛔ ここで予定を聞かない。日付はこの後のカレンダー画面で選ぶ
        rec, token = booking.register_instructor(
            name, email, (request.form.get('org') or '').strip(),
            request.form.getlist('courses'),
            (request.form.get('note') or '').strip())

        app.logger.info('[instructor_register] 申請: %s', name)
        # ⛔ 送れなくても登録は成立させる。ただし黙らないこと＝完了画面に出し、
        #    専用URLは画面にも必ず表示する（メールだけが受け渡し口だと消える）
        mailed = _notify_registered(app, rec, token)
        return render_template('instructor_register.html', done=True,
                               token=token, rec=rec, mailed=mailed,
                               courses=booking.COURSES,
                               weekdays=booking.WEEKDAYS)

    # ─────────────── メールの確認（仮登録 → 本登録）
    @app.route('/instructor/verify/<token>')
    def instructor_verify(token):
        inst = booking.verify_email(token)
        if not inst:
            return ('このリンクは正しくありません。'
                    'info@jgaia.org までお問い合わせください。', 404)
        # 確認できたら、そのまま日程を選べる画面へ送る（もう1手を要求しない）
        return redirect(url_for('instructor_schedule', token=token,
                                verified=1))

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
        months = _month_grids(3)
        # 旧式（曜日の決まり）で登録された方には、その内容を日付として見せる。
        # ⛔ ここで台帳を書き換えないこと。本人が保存したときに移る
        compat = {}
        if inst.get('講義できる日時') is None:
            first = date.fromisoformat([d for d in months[0]['日'] if d][0])
            last = date.fromisoformat([d for d in months[-1]['日'] if d][-1])
            compat = booking.materialize(inst, first, last)
        return render_template('instructor_schedule.html', inst=inst, token=token,
                               just_verified=bool(request.args.get('verified')),
                               blockers=booking.publish_blockers(inst),
                               weekdays=booking.WEEKDAYS,
                               months=months, compat_days=compat,
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
        # 予定は日付ごとの枠だけ {'2026-09-05': [{'開始','終了'}]}
        days = {k: v for k, v in (data.get('days') or {}).items()
                if _is_day(k) and isinstance(v, list)}
        inst = booking.update_availability(token, days)
        # ⛔ 送られた内容ではなく保存された内容を返すこと。予約が入っている日は
        #    サーバ側で据え置くので、画面がそれを写せないと表示が実態とズレる
        # ⛔ 保存できたことと、公開されることは別。担当できる講座が無い予定を
        #    「保存しました」だけで返すと、本人は公開されたつもりで待ち続ける
        return {'ok': True, '更新日時': inst.get('更新日時'),
                'days': inst.get('講義できる日時') or {},
                '公開されない理由': booking.publish_blockers(inst)}

    # ─────────────── 承認画面
    @app.route('/admin/instructors')
    def admin_instructors():
        ok = _admin_ok()
        if ok is None:
            return {'error': 'disabled',
                    'message': '管理用の合言葉が未設定のため無効です。'}, 503
        if not ok:
            return {'error': 'forbidden'}, 403
        rows = [dict(r, 公開されない理由=booking.publish_blockers(r))
                for r in booking.instructors()]
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
                公開されない理由=booking.publish_blockers(r),
                担当できる講座=booking.teachable_courses(r),
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

        inst = next((i for i in booking.instructors()
                     if str(i.get('id')) == str(data.get('id'))), None)
        out = {'ok': True}
        if inst and state in ('承認', '見送り'):
            # ⛔ 判定を本人に伝えること。承認しても何も届かないと、講師は
            #    自分が公開されたことも、日程を入れる画面があることも知らない
            out['通知'] = _send(app, [_instructor_mail(inst, inst['鍵'], state)],
                                'instructor_decide', inst['氏名'])
        if inst and state == '承認' and not inst.get('メール確認済み'):
            # ⛔ 承認したのに公開されない理由を、押した人にその場で伝える
            out['警告'] = ('この方はメールの確認がまだ済んでいません。'
                           '確認されるまで受講者には公開されません。')
        return out

    @app.route('/api/instructor/resend', methods=['POST'])
    def api_instructor_resend():
        """確認メールを送り直す（運営用）。届かない・消したという連絡への対応。"""
        ok = _admin_ok()
        if ok is None or not ok:
            return {'error': 'forbidden'}, 403
        data = request.get_json(silent=True) or {}
        inst = next((i for i in booking.instructors()
                     if str(i.get('id')) == str(data.get('id'))), None)
        if not inst:
            return {'error': 'その講師が見つかりませんでした'}, 404
        sent = _notify_registered(app, inst, inst['鍵'])
        if not sent:
            return {'error': 'メールを送れませんでした（送信設定をご確認ください）'}, 502
        return {'ok': True, '宛先': inst['連絡先']}

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


SIGN = ('---\n一般社団法人日本生成AI協会（JGAIA）\n'
        '〒104-0061 東京都中央区銀座1-22-11 銀座大竹ビジデンス2階\n'
        'info@jgaia.org / https://www.jgaia.org/\n')


def _send(app, payloads, tag, who):
    """メールを送る。戻り値: 送れたか（True/False）

    ⛔ 送れなくても登録・申込は保存済み。ここで例外を投げないこと
       （メールは付随物。落ちたら本体まで巻き添えになる作りにしない）。
    ⛔ 失敗を握りつぶさないこと＝ログに残し、呼び出し元は画面に出す。
    """
    key = os.environ.get('RESEND_API_KEY', '')
    if not key:
        app.logger.error('[%s] 送信手段が未設定（RESEND_API_KEY）。保存は済み: %s',
                         tag, who)
        return False
    try:
        import resend
        resend.api_key = key
        for p in payloads:
            resend.Emails.send(p)
        return True
    except Exception:
        app.logger.exception('[%s] 送信に失敗。保存は済み: %s', tag, who)
        return False


def _instructor_mail(rec, token, kind):
    """講師あての本文を1か所で組み立てる。kind: 仮登録 / 承認 / 見送り

    ⛔ 本文をルートごとに書き散らさないこと（同じ案内が3通りに割れる）。
    """
    from mail_targets import FROM_EMAIL
    verify_url = url_for('instructor_verify', token=token, _external=True)
    cal_url = url_for('instructor_schedule', token=token, _external=True)
    courses = ' / '.join(rec.get('対応コース') or []) or '未選択'
    if kind == '仮登録':
        subject = '【JGAIA】講師のご登録ありがとうございます（メールのご確認をお願いします）'
        text = (f"{rec['氏名']} 様\n\n"
                "JGAIA／JQCA の認定講座 講師にご登録いただき、ありがとうございます。\n"
                "まず、このメールが届くことの確認をお願いいたします。\n\n"
                "▼ こちらを押すと確認が完了し、そのまま\n"
                "　「講義できる日」を選ぶカレンダーが開きます\n"
                f"{verify_url}\n\n"
                "カレンダーは日付を押すだけです。1日に朝と夜のような\n"
                "複数の時間帯も登録でき、あとからいつでも変更できます。\n\n"
                f"■ 担当できる講座: {courses}\n"
                f"■ 受付日時: {rec.get('登録日時')}\n\n"
                "内容を確認のうえ、運営より2営業日以内にご連絡いたします。\n"
                "承認までは、選んだ日程が受講者に公開されることはありません。\n\n"
                "※このリンクはあなた専用です。他の方に転送しないでください。\n"
                "※お心当たりがない場合は、このメールを破棄してください。\n\n"
                + SIGN)
    elif kind == '承認':
        subject = '【JGAIA】講師のご登録を承認しました'
        text = (f"{rec['氏名']} 様\n\n"
                "講師のご登録を承認いたしました。ありがとうございます。\n"
                "選んでいただいた日程が、受講者の予約カレンダーに公開されます。\n\n"
                "▼ 講義できる日はこちらからいつでも変更できます\n"
                f"{cal_url}\n\n"
                "※すでに予約が入った日は、変更できません。\n"
                "　ご都合が変わった場合は info@jgaia.org までご連絡ください。\n\n"
                + SIGN)
    else:
        subject = '【JGAIA】講師のご登録について'
        text = (f"{rec['氏名']} 様\n\n"
                "このたびは講師にご登録いただき、ありがとうございました。\n"
                "検討の結果、今回はご一緒できる講座がございませんでした。\n"
                "講座が増えた際に、あらためてご相談させてください。\n\n"
                + SIGN)
    return {'from': f'JGAIA <{FROM_EMAIL}>', 'to': [rec['連絡先']],
            'subject': subject, 'text': text}


def _notify_registered(app, rec, token):
    """仮登録メール（本人）と新規申請の通知（運営）。戻り値: 本人に送れたか"""
    from mail_targets import notify_payload
    admin = notify_payload(
        f"【講師登録】{rec['氏名']} 様（{ ' / '.join(rec.get('対応コース') or []) or '講座未選択'}）",
        reply_to=rec['連絡先'],
        text=('講師の登録申請が届きました。\n\n'
              f"お名前: {rec['氏名']}\n"
              f"メール: {rec['連絡先']}\n"
              f"ご所属: {rec.get('所属') or '—'}\n"
              f"担当できる講座: {' / '.join(rec.get('対応コース') or []) or '未選択'}\n"
              f"ご経歴・ご要望: {rec.get('備考') or '—'}\n"
              f"受付日時: {rec.get('登録日時')}\n\n"
              '本人がメールの確認リンクを踏むまでは、承認しても公開されません。\n'
              f"承認画面: {url_for('admin_instructors', _external=True)}\n"))
    # ⛔ 本人あてと運営あてを1回の呼び出しで送ること。分けると、本人には
    #    届いたのに運営には届かない（または逆）が静かに起きる
    return _send(app, [_instructor_mail(rec, token, '仮登録'), admin],
                 'instructor_register', rec['氏名'])


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
