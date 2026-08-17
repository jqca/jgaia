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
import payments


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
        # ⛔ 講師料の材料を渡し忘れないこと。Jinjaは未定義を空文字にするので
        #    落ちずに「講師料 ¥」とだけ出る（金額の伏せられた同意になる）
        fee_ctx = dict(
            fees={c['code']: booking.instructor_fee(c['code'])
                  for c in booking.COURSES},
            fee_terms=booking.fee_terms_text(),
            fee_version=booking.FEE_TERMS_VERSION)

        if request.method == 'GET':
            return render_template('instructor_register.html',
                                   courses=booking.COURSES,
                                   groups=booking.grouped_courses(),
                                   lead_days=booking.LEAD_DAYS,
                                   weekdays=booking.WEEKDAYS, **fee_ctx)

        import antispam
        if antispam.check(request, request.form.to_dict()):
            app.logger.info('[instructor_register] スパムとして遮断')
            return render_template('instructor_register.html', done=True,
                                   courses=booking.COURSES,
                                   weekdays=booking.WEEKDAYS, **fee_ctx)

        name = (request.form.get('name') or '').strip()
        email = (request.form.get('email') or '').strip()
        # ⛔ 同意の確認をブラウザの required だけに任せないこと。この画面を
        #    通らない経路（開発者ツール・自動化）では素通りする
        agreed = (request.form.get('fee_agree') or '').strip()
        err = None
        if not name or not email:
            err = 'お名前とメールアドレスは必須です。'
        elif agreed != booking.FEE_TERMS_VERSION:
            err = '講師料の条件へのご同意が必要です。'
        if err:
            # ⛔ lead_days を渡し忘れないこと。見出しが「開催の日以上前」と
            #    数字だけ欠けて出る（Jinjaは未定義を空文字にするので落ちない）
            return render_template('instructor_register.html',
                                   error=err,
                                   courses=booking.COURSES,
                                   groups=booking.grouped_courses(),
                                   lead_days=booking.LEAD_DAYS,
                                   weekdays=booking.WEEKDAYS, **fee_ctx)

        # ⛔ 登録の前に既存を見ること。同じアドレスなら行は増えず更新になるので、
        #    完了画面の文面を変えないと「2件登録された」と誤解される（逆に、
        #    黙って上書きされたことにも気づけない）。
        before = booking.find_by_email(email)
        updated = bool(before)
        was_verified = bool(before and before.get('メール確認済み'))

        # ⛔ ここで予定を聞かない。日付はこの後のカレンダー画面で選ぶ
        rec, token = booking.register_instructor(
            name, email, (request.form.get('org') or '').strip(),
            request.form.getlist('courses'),
            (request.form.get('note') or '').strip(),
            fee_agreed=agreed)

        app.logger.info('[instructor_register] %s: %s',
                        '更新' if updated else '申請', name)
        # ⛔ 送れなくても登録は成立させる。ただし黙らないこと＝完了画面に出し、
        #    専用URLは画面にも必ず表示する（メールだけが受け渡し口だと消える）
        mailed = _notify_registered(app, rec, token)
        return render_template('instructor_register.html', done=True,
                               token=token, rec=rec, mailed=mailed,
                               updated=updated, was_verified=was_verified,
                               courses=booking.COURSES,
                               weekdays=booking.WEEKDAYS, **fee_ctx)

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

    # ─────────────── 講師本人が担当講座を変更
    @app.route('/instructor/schedule/<token>/courses', methods=['GET', 'POST'])
    def instructor_courses(token):
        """⛔ ここが無いと、担当を変える唯一の手段が『登録し直し』になる。
           旧実装ではそれをすると承認が外れ、その人の日程が全部消えていた。
        """
        inst = booking.find_instructor(token)
        if not inst:
            return 'この画面のリンクが正しくありません。運営にお問い合わせください。', 404
        error = saved = None
        if request.method == 'POST':
            got, error = booking.set_instructor_courses(
                token, request.form.getlist('courses'))
            if got:
                inst, saved = got, True
        # 受講者の申込が入っている講座は外せない
        locked = sorted({b.get('コース') for b in booking.bookings()
                         if b.get('担当講師id') == inst.get('id')
                         and booking.is_live(b)})
        return render_template(
            'instructor_courses.html', inst=inst, token=token,
            groups=booking.grouped_courses(),
            chosen=inst.get('対応コース') or [],
            approved=booking.approved_courses(inst),
            pending=booking.pending_courses(inst),
            locked=locked, saved=saved, error=error,
            fees={c['code']: booking.instructor_fee(c['code'])
                  for c in booking.COURSES})

    # ─────────────── 講師本人が予定を編集
    @app.route('/instructor/schedule/<token>')
    def instructor_schedule(token):
        inst = booking.find_instructor(token)
        if not inst:
            return 'この画面のリンクが正しくありません。運営にお問い合わせください。', 404
        # 登録済みの日（旧い形で持っている方は、その内容を日付として見せる）
        # ⛔ ここで台帳を書き換えないこと。本人が1日ぶん保存したときに移る
        days = booking.registered_days(inst)
        # ⛔ 「登録した日数」ではなく「開始日にできる日数」を出すこと。
        #    3日間の講座を飛び飛びに3日登録しても、予約が入る日は0日
        occ = booking.occupied_days(inst['id'])       # 台帳の読み直しは1回だけ
        counts = {c['code']: len(booking.startable_days(
                      inst, c['code'], occ=occ, reg=days))
                  for c in booking.COURSES
                  if c['code'] in (inst.get('対応コース') or [])}
        mine = [c for c in booking.COURSES
                if c['code'] in (inst.get('対応コース') or [])]
        return render_template('instructor_schedule.html', inst=inst, token=token,
                               just_verified=bool(request.args.get('verified')),
                               saved=request.args.get('saved', ''),
                               blockers=booking.publish_blockers(inst, reg=days),
                               pending_courses=booking.pending_courses(inst),
                               # ⛔ 開催日を渡し忘れないこと。Jinjaは未定義を
                               #    空にするので全部が「開催日でない」になる
                               session_days=set(booking.session_days()),
                               session_note=booking.session_day_note(),
                               weekdays=booking.WEEKDAYS,
                               months=_month_grids(3),
                               days=days, counts=counts, courses=mine,
                               teachable=booking.teachable_courses(inst, reg=days),
                               lead_days=booking.LEAD_DAYS,
                               today=booking.today_jst().isoformat(),
                               booked_days=booking.booked_days_for_instructor(inst['id']),
                               booked_info=booking.booked_summary(inst['id']),
                               earliest=(booking.today_jst()
                                         + timedelta(days=booking.LEAD_DAYS)).isoformat())

    # ─────────────── 1日ぶんの登録（選ぶ → 確認 → 保存）
    @app.route('/instructor/schedule/<token>/day/<iso>',
               methods=['GET', 'POST'])
    def instructor_day(token, iso):
        inst = booking.find_instructor(token)
        if not inst or not _is_day(iso):
            return 'この画面のリンクが正しくありません。', 404

        day = date.fromisoformat(iso)
        booked = iso in booking.booked_days_for_instructor(inst['id'])
        earliest = booking.today_jst() + timedelta(days=booking.LEAD_DAYS)
        # 選べるのは、登録時に「担当できる」とされた講座のうち、
        # その曜日に開催できるものだけ。⛔ 選べないものを黙って消さず、
        # 理由（毎週水曜の開催です等）を添えて出す（無いと「なぜ出ないのか」が分からない）
        mine = []
        for c in booking.COURSES:
            if c['code'] not in (inst.get('対応コース') or []):
                continue
            n = booking.course_days(c['code'])
            # 3日間の講座は、開始日として使うには続く日も選んでおく必要がある。
            # ⛔ 選ばせておいて「なぜ予約が入らないのか」を黙らないこと
            run = booking.course_dates(c['code'], iso) if n > 1 else []
            missing = [x for x in run[1:]
                       if c['code'] not in booking.day_courses(
                           inst, date.fromisoformat(x))]
            mine.append(dict(
                c, 選べる=booking.course_open_on(c['code'], day),
                理由=booking.weekday_note(c['code']),
                日数=n, 日程=run, 続きが未登録=missing,
                # ⛔ 毎週の講座に「つづけて開催」と書かないこと（連続日に読める）
                回の説明=booking.series_note(c['code'])))
        chosen = [c for c in (request.form.getlist('courses')
                              if request.method == 'POST'
                              else booking.day_courses(inst, day))
                  if booking.course_open_on(c, day)]

        def render(step, error=None):
            # 掲載ページと同じまとまりで出す（担当が多い方は1列だと探せない）
            by_code = {m['code']: m for m in mine}
            groups = [(g, [by_code[c['code']] for c in items])
                      for g, items in booking.grouped_courses(list(by_code))]
            # ⛔ 時間が重なることを「エラー」にしないこと。開催されるのは1つだけ
            #    なので、そう伝えるだけにとどめる（2026-08-14 社長ご指摘）
            same_time = sorted({c for pair in booking.same_time_courses(chosen)
                                for c in pair})
            return render_template(
                'instructor_day.html', inst=inst, token=token, iso=iso,
                day=day, weekday=booking.WEEKDAYS[day.weekday()],
                mine=mine, groups=groups, chosen=chosen, step=step, error=error,
                same_time=same_time,
                booked_rows=booking.booked_summary(inst['id']).get(iso, []),
                booked=booked, too_soon=day < earliest,
                earliest=earliest.isoformat(), lead_days=booking.LEAD_DAYS,
                others=booking.others_on(inst, day))

        if request.method == 'GET':
            return render('select')

        if request.form.get('confirm') != '1':
            # ⛔ いきなり保存しないこと。ここは確認画面を出すだけ
            return render('confirm')

        saved, err = booking.set_day_courses(token, iso, chosen)
        if err:
            return render('select', err)
        return redirect(url_for('instructor_schedule', token=token, saved=iso))

    # ─────────────── 承認画面
    @app.route('/admin/instructors')
    def admin_instructors():
        ok = _admin_ok()
        if ok is None:
            return {'error': 'disabled',
                    'message': '管理用の合言葉が未設定のため無効です。'}, 503
        if not ok:
            return {'error': 'forbidden'}, 403
        rows = []
        for r in booking.instructors():
            reg = booking.registered_days(r)          # 1人1回だけ展開する
            rows.append(dict(r, 公開されない理由=booking.publish_blockers(r, reg=reg),
                             確認待ちの講座=booking.pending_courses(r),
                             登録済みの日=reg))
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
            # ⛔ 同じ要求の中で registered_days を何度も呼ばないこと
            #    （旧形式は180日ぶんの展開が走る＝実測で4秒かかっていた）
            reg = booking.registered_days(r)
            rows.append(dict(
                r,
                予約件数=len(mine),
                予約人数=sum(int(b.get('人数') or 1) for b in mine),
                公開されない理由=booking.publish_blockers(r, reg=reg),
                             確認待ちの講座=booking.pending_courses(r),
                担当できる講座=booking.teachable_courses(r, reg=reg),
                登録済みの日=reg,
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
                               course_days=booking.course_days(code),
                               course_interval=booking.course_interval(code),
                               # 分割掲載の講座で「今回いくつ申し込むか」を選ばせる。
                               # ⛔ 単価をテンプレートで計算しないこと
                               sessions_all=booking.sessions_of(code),
                               unit_price=booking.unit_price_of(code),
                               series_note=booking.series_note(code),
                               lead_days=booking.LEAD_DAYS,
                               session_note=booking.session_day_note(),
                               cancel_policy=booking.CANCEL_POLICY,
                               pay_note=(booking.PAY_NOTE if payments.enabled()
                                         else booking.PAY_NOTE_INVOICE),
                               card_enabled=payments.enabled(),
                               seller=booking.SELLER,
                               extra_cost_note=booking.EXTRA_COST_NOTE,
                               subsidy=booking.subsidy_for(code),
                               subsidy_lead=booking.SUBSIDY['lead_days'],
                               # ⛔ 助成金が使える最も近い日を出すこと。「45日前まで」
                               #    とだけ書くと、どの日なら間に合うのか読み手が
                               #    数えることになる
                               subsidy_from=(booking.today_jst() + timedelta(
                                   days=booking.SUBSIDY['lead_days'])).isoformat(),
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

        # ⛔ 支払い方法を画面の言い値で決め切らないこと。カードは鍵が
        #    設定されているときだけ。未設定なら請求書払いに落とす（画面も
        #    そう出しているので、利用者の見たものと実際が一致する）
        want_card = (data.get('pay') or 'card') == 'card' and payments.enabled()

        try:
            rec, inst = booking.add_booking(
                data.get('course'), data.get('day'), name, email,
                (data.get('company') or '').strip(),
                data.get('people') or 1, (data.get('message') or '').strip(),
                pending=want_card,
                # ⛔ ここで丸めないこと。booking.normalize_sessions が
                #    1〜全研修数に必ず収める（金額の出どころを1か所にする）
                sessions=data.get('sessions'))
        except ValueError as e:
            return {'error': str(e)}, 400
        except Exception:
            app.logger.exception('[book] 申込の保存に失敗')
            return {'error': '受付処理に失敗しました。info@jgaia.org までご連絡ください。'}, 500

        if want_card:
            course = booking.COURSE_BY_CODE[rec['コース']]
            url, sid, err = payments.create_checkout(
                course, rec['人数'], email, rec['id'],
                # ⛔ course['price'] を渡さないこと。分割掲載の講座は
                #    申し込まれた研修数ぶんしか請求しない（2026-08-17）
                amount=rec['受講料_円'],
                success_url=url_for('book_done', code=rec['コース'],
                                    _external=True) + '?ok=1',
                cancel_url=url_for('book_course', code=rec['コース'],
                                   _external=True),
                day_label='・'.join(rec.get('開催日') or [rec['希望日']]))
            if err or not url:
                # ⛔ 席を押さえたまま返さないこと（決済に進めないのに定員が減る）
                booking.cancel_booking(rec['id'], '決済ページを作れませんでした')
                app.logger.error('[book] Checkout作成に失敗: %s', err)
                return {'error': f'{err}。info@jgaia.org までご連絡ください。'}, 502
            booking.attach_checkout(rec['id'], sid)
            # ⛔ ここでは受講者にメールを送らないこと。まだ払っていない
            return {'ok': True, '決済へ': url}

        _notify_booking(app, rec, inst)
        return {'ok': True,
                '開催確定': rec['_開催確定'],
                '合計人数': rec['_合計人数']}

    @app.route('/admin/booking/<booking_id>/certificate')
    def admin_certificate(booking_id):
        """受講証明書（参考様式2）に転記する項目を出す。

        ⛔ 当社が発行できないと、法人は助成金を受け取れない（実績報告で必須）。
        ⛔ 出席時間だけは空で返す。当日確認して埋めるもので、推測で埋めると
           虚偽の証明になる。
        """
        ok = _admin_ok()
        if ok is None:
            return {'error': 'disabled',
                    'message': '管理用の合言葉が未設定のため無効です。'}, 503
        if not ok:
            return {'error': 'forbidden'}, 403
        data = booking.certificate_data(booking_id)
        if not data:
            return {'error': 'not_found'}, 404
        return data

    @app.route('/book/<code>/done')
    def book_done(code):
        """決済から戻ってきた受講者に見せる画面。

        ⛔ この画面が開いたことを「決済が終わった」証拠にしないこと。
           URLは誰でも開ける。成立させるのは webhook の署名検証だけ。
        """
        course = booking.COURSE_BY_CODE.get(code)
        if not course:
            return 'コースが見つかりません', 404
        return render_template('course_done.html', c=course,
                               cancel_policy=booking.CANCEL_POLICY,
                               seller=booking.SELLER)

    @app.route('/api/stripe/webhook', methods=['POST'])
    def stripe_webhook():
        """Stripe からの決済通知。⛔署名を検証してからしか信じない。"""
        event, err = payments.verify_webhook(
            request.get_data(), request.headers.get('Stripe-Signature', ''))
        if err:
            app.logger.warning('[stripe] 通知を受け取れません: %s', err)
            return {'error': err}, 400
        kind = event.get('type')
        obj = (event.get('data') or {}).get('object') or {}
        sid = obj.get('id') or ''
        if kind == 'checkout.session.completed':
            # ⛔ 未払いのまま成立させないこと（後払い手段では completed でも
            #    payment_status が unpaid のことがある）
            if obj.get('payment_status') != 'paid':
                return {'ok': True, 'skipped': 'unpaid'}
            rec, inst = booking.mark_paid(sid, obj.get('payment_intent') or '')
            if rec:
                _notify_booking(app, rec, inst)
                app.logger.info('[stripe] 決済完了: %s %s', rec['コース'], rec['氏名'])
            return {'ok': True}
        if kind in ('checkout.session.expired', 'checkout.session.async_payment_failed'):
            if booking.mark_unpaid(sid):
                app.logger.info('[stripe] 未決済で取消: %s', sid)
            return {'ok': True}
        return {'ok': True, 'ignored': kind}


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

        # ⛔ 3日間の講座に開始日だけを書かないこと（受講者は1日だと思って申し込む）
        日程 = '・'.join(rec.get('開催日') or [rec['希望日']])
        # ⛔ 支払い方法を決め打ちしないこと。カードで決済済みの方に
        #    「請求書をお送りします」と届くと、二重払いの問い合わせになる
        if rec.get('支払方法') == 'card':
            pay_note = ('お支払いは完了しております（クレジットカード）。'
                        '領収書が必要な場合は info@jgaia.org までご連絡ください。')
        else:
            pay_note = booking.PAY_NOTE_INVOICE
        body = '\n'.join([
            f"コース: {rec['コース']} {rec['コース名']}",
            f"開催希望日: {日程}",
            f"お名前: {rec['氏名']}",
            f"メール: {rec['連絡先']}",
            f"会社名: {rec['会社名']}" if rec['会社名'] else '',
            f"人数: {rec['人数']}名",
            # ⛔ 分割掲載の講座は「全何研修のうち何研修」を必ず出すこと。
            #    出さないと、運営も講師も全回来る前提で準備してしまう
            (f"研修数: 全{rec['全研修数']}研修のうち {rec['研修数']}研修"
             if int(rec.get('全研修数') or 1) > 1 else ''),
            f"担当講師: {rec['担当講師']}",
            f"この日の合計: {rec['_合計人数']}名 → 開催確定",
            f"講師料（定額）: {booking.instructor_fee(rec['コース']):,}円",
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
            f"■ 開催希望日: {日程}\n"
            f"■ 人数: {rec['人数']}名\n"
            # ⛔ 何研修ぶんのお申し込みかを書かずに金額だけ出さないこと
            + (f"■ 研修数: 全{rec['全研修数']}研修のうち {rec['研修数']}研修"
               f"（1研修 {booking.unit_price_of(rec['コース']):,}円）\n"
               if int(rec.get('全研修数') or 1) > 1 else '')
            + f"■ 受講料: {rec['受講料_円']:,}円（税込）\n"
            # ⛔ 受験料を別の行の金額として書かないこと。受講料に含まれる1本の
            #    金額であることが、助成金の交付申請（1人1研修単位の経費）の前提。
            + (f"■ 認定試験: {booking.exam_for(rec['コース'])['name']}"
               f"（受験料は上記の受講料に含まれます）\n"
               if booking.exam_for(rec['コース']) else '')
            + f"\n{pay_note}\n\n"
            # ⛔ 「人数が集まれば開催します」と書かないこと（最少催行は撤廃済み）。
            #    1人目の申込者には定義上100%その文面が届く＝いちばん申込を止める
            f"【開催について】\n"
            f"お一人からでも開催いたします。上記の日程で開催が確定しています。\n"
            + f"\n【キャンセルについて】\n{booking.CANCEL_POLICY}\n\n"
            + booking.seller_footer())
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
                         f"■ 日付: {日程}\n"
                         f"■ コース: {rec['コース']} {rec['コース名']}\n"
                         f"■ 現在の人数: {rec['_合計人数']}名\n"
                         # ⛔ 講師料を人数と並べて書かないこと（連動していると
                         #    読まれる）。定額であることを明記する
                         f"■ 講師料: {booking.instructor_fee(rec['コース']):,}円"
                         f"（1開催あたりの定額・人数によって変わりません）\n\n"
                         f"ご都合が変わった場合は、ご自身の予定画面から"
                         f"その日を「不可」にしてください。\n"
                         + booking.seller_footer())})
    except Exception:
        app.logger.exception('[book] 通知メールに失敗。申込は保存済み: %s', rec['氏名'])
