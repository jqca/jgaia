"""JGAIA バイブコーディング講座 子ども向けコース（GK1/GK2/GK3）"""
import os
from flask import render_template, request, jsonify

RESEND_API_KEY = os.getenv('RESEND_API_KEY', '')


def register_vibe_coding_kids_routes(app):
    @app.route('/vibe-coding/kids')
    def vibe_coding_kids():
        # ⛔ 価格をテンプレートに直書きしないこと。booking.COURSES が唯一の
        #    出どころで、ここがズレると紹介と申込で金額が食い違う
        import booking
        # ⛔ 開催日があるのに「お申し込み」がフォームに落ちること（2026-08-17）。
        #    子ども向けも予約できる（実測22日）のに、このページだけ導線が
        #    無かった。判断は booking.open_slots() の1か所。
        return render_template(
            'vibe_coding_kids.html',
            kids={k: booking.COURSE_BY_CODE[k]['price']
                  for k in ('GK1', 'GK2', 'GK3')},
            slots={k: booking.open_slots(k) for k in ('GK1', 'GK2', 'GK3')})

    @app.route('/api/kids-inquiry', methods=['POST'])
    def kids_inquiry_api():
        data = request.get_json() or {}
        parent_name = data.get('parent_name', '')
        child_age = data.get('child_age', '')
        email = data.get('email', '')
        phone = data.get('phone', '')
        course = data.get('course', '')
        message = data.get('message', '')

        # スパム判定。⛔ 弾いたことをボットに教えない（成功と同じ形で返す）。
        import antispam
        if antispam.check(request, {**data, 'name': parent_name}):
            return jsonify({'success': True})

        if not all([parent_name, child_age, email, course]):
            return jsonify({'success': False, 'error': 'missing fields'})

        # ⛔ メールより先に保存する（枠切れ・障害で問い合わせを失わない）
        try:
            from inquiry_store import save_inquiry
            save_inquiry('kids', {'name': parent_name, 'email': email,
                                  'child_age': child_age, 'phone': phone,
                                  'course': course, 'message': message})
        except Exception:
            app.logger.exception('[kids-inquiry] 保存に失敗しました')

        if not RESEND_API_KEY:
            return jsonify({'success': True})

        try:
            import resend
            resend.api_key = RESEND_API_KEY

            admin_body = f"""【JGAIA キッズ講座 お問い合わせ】

保護者名: {parent_name}
お子さまの年齢: {child_age}
メール: {email}
電話: {phone or '未入力'}
希望コース: {course}
メッセージ: {message or 'なし'}
"""
            from mail_targets import notify_payload
            resend.Emails.send(notify_payload(
                f"【キッズ講座】お問い合わせ: {parent_name}様",
                reply_to=email, text=admin_body))

            confirm_body = f"""{parent_name} 様

この度はJGAIA キッズ・バイブコーディング講座にご関心をいただきありがとうございます。
以下の内容でお問い合わせを受け付けました。

━━━━━━━━━━━━━━━━━━━━
保護者名: {parent_name}
お子さまの年齢: {child_age}
希望コース: {course}
━━━━━━━━━━━━━━━━━━━━

担当者より2営業日以内にご連絡いたします。
ご質問は info@jgaia.org までお気軽にどうぞ。

一般社団法人 日本生成AI協会（JGAIA）
キッズ・バイブコーディング講座 事務局
https://www.jgaia.org/vibe-coding/kids
"""
            resend.Emails.send({
                "from": "JGAIA キッズ講座 <info@jgaia.org>",
                "to": [email],
                "subject": "【JGAIA キッズ講座】お問い合わせを受け付けました",
                "text": confirm_body,
            })

            return jsonify({'success': True})
        except Exception as e:
            print(f'Resend error: {e}')
            return jsonify({'success': True})
