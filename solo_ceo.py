"""JGAIA 一人会社AI経営講座 — 概要LP + コース詳細 + 問い合わせAPI

ルート:
  /solo-ceo               概要LP（メイン集客ページ）
  /solo-ceo/course-spa    SP-A: AI経営 入門1日
  /solo-ceo/course-spb    SP-B: AI経営 実践3日間
  /solo-ceo/course-spc    SP-C: AI経営 夜間マスター全5回
  /api/solo-inquiry       問い合わせAPI（Resend自動返信）
"""
import json
import os

from flask import render_template, request

from inquiry_store import inquiry_key, mark_mailed, save_inquiry

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")

# 直近のメール送信失敗。/healthz から見えるようにして、
# 「鍵はあるのに実際は送れていない」状態を外から検知する。
# 2026-08-04: 鍵は設定済みなのに日次上限で送信が落ちていた。
# 設定の有無だけを見ていると正常に見えてしまう。
LAST_MAIL_ERROR = {"at": None, "kind": None}


def _now_jst():
    from datetime import datetime, timezone, timedelta
    return datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M:%S")
FROM_EMAIL = "info@jgaia.org"
NOTIFY_EMAIL = "takano.hidetaka@gmail.com"

COURSES = {
    "spa": {
        "id": "spa",
        "code": "SP-A",
        "title": "AI経営 入門1日",
        "subtitle": "AIチームの構築から業務自動化まで、一人会社AI経営の全体像を1日で掴む",
        "gradient": "linear-gradient(135deg, #1e3a5f, #2563eb)",
        "accent": "#2563eb",
        "accent_light": "#93c5fd",
        "duration": "1日（6時間）",
        "price": "49,800",
        "price_num": 49800,
        "target": "一人会社経営者・フリーランス・副業経営者",
        "format": "会場＋オンライン同時開催",
        "capacity": "20名",
        "schedule": "10:00〜17:00（昼休憩1時間）",
        # 開催日。決まったらここに "2026年9月12日（土）" のように書けば
        # LPとコース詳細の両方に出る。空のままなら「調整中」と表示する。
        # ⛔ 未定を空欄のまま隠さないこと（日程が見つからないと問い合わせ前に離脱する）
        "next_date": "",
        "subsidy": False,
        "subsidy_text": "",
        "curriculum": [
            ("一人会社AI経営の全体設計",
             "なぜ今「AI×一人会社」なのか。AIチーム体制の実例から、組織設計の考え方と導入ステップを学びます。"),
            ("AI秘書・経理の構築",
             "スケジュール管理、経費処理、請求書発行をAIに任せる方法。即日導入できるツール選定と設定を実践します。"),
            ("営業・マーケティングの自動化",
             "提案書自動生成、顧客管理、SNS運用をAIで効率化。人を雇わずに営業力を10倍にする仕組みを構築します。"),
            ("AIツール比較と選定基準",
             "ChatGPT / Claude / Gemini の使い分け。コスト・品質・セキュリティの判断軸で自社最適なAIを選びます。"),
            ("セキュリティと法務リスク",
             "機密情報の取り扱い、AI生成物の著作権、個人情報保護。一人会社だからこそ押さえるべきリスク管理を学びます。"),
            ("ハンズオン：自社AI経営プランの設計",
             "あなたの事業に合わせたAI導入計画を設計。講師フィードバック付きで実行可能なプランに仕上げます。"),
        ],
        "outcomes": [
            ("AI経営の全体像を理解できる",
             "一人会社でAIチームを構築する設計思想と具体的な導入ステップを理解し、自社への適用方針を持ち帰れます。"),
            ("即日使えるAI業務自動化を習得",
             "秘書・経理・営業の3領域で、受講当日から使えるAI自動化の設定方法を実践的に学びます。"),
            ("投資判断に必要なコスト感覚を掴む",
             "AIツールの月額コスト、導入工数、ROI の現実的な数値を把握し、経営判断に活かせます。"),
        ],
        "faq": [
            ("プログラミング経験がなくても大丈夫ですか？",
             "はい、プログラミング経験は一切不要です。AIへの指示（プロンプト）を書く力を養う講座です。"),
            ("どのような業種の方を想定していますか？",
             "コンサルタント、士業、デザイナー、EC運営者など、人を雇わずに事業を運営されている方を想定した内容です。"),
            ("受講後のサポートはありますか？",
             "受講後30日間のメールサポートと、修了者限定コミュニティへの招待を提供しています。"),
        ],
    },
    "spb": {
        "id": "spb",
        "code": "SP-B",
        "title": "AI経営 実践3日間マスター",
        "subtitle": "3日間の集中トレーニングで、AIが回す経営システムを自社に実装する",
        "gradient": "linear-gradient(135deg, #312e81, #4f46e5)",
        "accent": "#4f46e5",
        "accent_light": "#a5b4fc",
        "duration": "3日間（各6時間 計18時間）",
        "price": "128,000",
        "price_num": 128000,
        "target": "一人会社経営者・スタートアップ創業者",
        "format": "会場開催",
        "capacity": "15名",
        "schedule": "10:00〜17:00 × 3日間（昼休憩1時間）",
        "next_date": "",
        "subsidy": False,
        "subsidy_text": "",
        "curriculum": [
            ("Day1: AI組織設計 — 部門構築と役割定義",
             "秘書・経理・営業・開発の4部門をAIで構築。各部門の役割定義、ツール選定、データフローを設計します。"),
            ("Day1: バイブコーディング基礎 — AIでアプリを作る",
             "コードを書かずにAIへの指示だけで業務アプリを構築。顧客管理・タスク管理・ダッシュボードを1日目で形にします。"),
            ("Day2: 営業・マーケティング自動化システム",
             "提案書自動生成、メルマガ配信、SNS運用、リード管理の自動化パイプラインを構築します。"),
            ("Day2: 経理・バックオフィス自動化",
             "経費管理、請求書発行、売上集計、決算予測をAIで自動化。領収書OCR読取の実装も行います。"),
            ("Day3: 統合と運用 — AI経営ダッシュボード",
             "全部門のAIを統合する操縦席（コックピット）を構築。KPI監視、タスク管理、部門間連携を一元化します。"),
            ("Day3: スケーリング戦略と収益化",
             "AIシステムを活用した事業拡大戦略。複数事業の並行運営、外注管理、パートナー連携の設計を行います。"),
        ],
        "outcomes": [
            ("AI経営システムを自社に実装できる",
             "3日間で秘書・経理・営業・開発の4部門をAIで構築し、実際に稼働するシステムを持ち帰れます。"),
            ("バイブコーディングでアプリが作れる",
             "コードを書かずにAIへの指示だけで業務アプリを構築するスキルを習得。受講後も自力で開発を続けられます。"),
            ("事業拡大の実行計画を策定",
             "AI活用による業務効率化で生まれた時間を事業拡大に投資。具体的な収益化ロードマップを設計します。"),
        ],
        "faq": [
            ("SP-Aを受講していなくても参加できますか？",
             "はい、SP-Bは独立したカリキュラムです。ただしAIツールの基本操作経験があるとスムーズです。"),
            ("3日間連続で受講する必要がありますか？",
             "はい、Day1→Day2→Day3と積み上げ式のカリキュラムのため、連続受講をお願いしています。"),
            ("受講に必要なツール・環境は？",
             "ノートPC（Chrome推奨）とインターネット環境があれば参加可能です。使用するAIツールのアカウントは事前にご案内します。"),
            ("法人研修として実施できますか？",
             "はい、法人向けカスタマイズ研修も承っています。お問い合わせフォームからご連絡ください。"),
        ],
    },
    "spc": {
        "id": "spc",
        "code": "SP-C",
        "title": "AI経営 夜間マスター 全5回",
        "subtitle": "毎週水曜夜、働きながら5週間でAI経営スキルを体系的に習得",
        "gradient": "linear-gradient(135deg, #0f766e, #0d9488)",
        "accent": "#0d9488",
        "accent_light": "#5eead4",
        "duration": "全5回（毎週水曜 19:00-21:30 / 計12.5時間）",
        "price": "68,000",
        "price_num": 68000,
        "target": "本業を持ちながら一人会社を立ち上げたい方・副業経営者",
        "format": "オンライン（Zoom）",
        "capacity": "30名",
        "schedule": "毎週水曜 19:00〜21:30（全5回）",
        "next_date": "",
        "subsidy": False,
        "subsidy_text": "",
        "curriculum": [
            ("Week 1: AI経営の設計図を描く",
             "一人会社の全体設計。AIで代替する業務と人がやるべき業務の切り分け。自社の「AI組織図」を作成します。"),
            ("Week 2: AI秘書・経理を構築する",
             "スケジュール管理、経費処理、請求書発行の自動化。Google Workspace連携で即稼働する体制を構築します。"),
            ("Week 3: 営業・集客をAIで自動化する",
             "SNS投稿、メルマガ、提案書の自動生成。YouTube・LinkedIn・Xの運用をAIで効率化する方法を学びます。"),
            ("Week 4: バイブコーディングで業務アプリを作る",
             "コード不要のアプリ開発。顧客管理・予約システム・ダッシュボードをAIへの指示だけで構築します。"),
            ("Week 5: 統合・運用・スケーリング",
             "全システムの統合テスト。KPI設定、改善サイクル、事業拡大に向けたロードマップを完成させます。"),
        ],
        "outcomes": [
            ("仕事と両立しながらAI経営を習得",
             "夜間オンライン形式で、本業に影響を与えずにAI経営スキルを5週間で段階的に習得できます。"),
            ("毎週の宿題で着実にシステム構築",
             "各回の宿題で自社のAIシステムを少しずつ構築。5週間後には実稼働するシステムが完成しています。"),
            ("同期受講者とのネットワーク形成",
             "同じ志を持つ一人会社経営者とのコミュニティに参加。情報交換や協業の機会が生まれます。"),
        ],
        "faq": [
            ("欠席した回はどうなりますか？",
             "全回録画を提供します。欠席回は録画で学習し、次回までに宿題を提出いただければ問題ありません。"),
            ("途中からの参加はできますか？",
             "カリキュラムは積み上げ式のため、第1回からの参加をお願いしています。"),
            ("オンラインのみですか？",
             "はい、全5回Zoom開催です。日本国内・海外どこからでも受講可能です。"),
            ("受講後のフォローアップは？",
             "修了後3ヶ月間のメールサポートと、受講者限定コミュニティへの永続的なアクセス権を提供します。"),
        ],
    },
}


def register_solo_ceo_routes(app):

    @app.route("/solo-ceo")
    def solo_ceo():
        return render_template("solo_ceo.html", courses=COURSES)

    @app.route("/solo-ceo/course-<course_id>")
    def solo_ceo_course(course_id):
        course = COURSES.get(course_id)
        if not course:
            return "コースが見つかりません", 404
        return render_template("solo_ceo_course.html", c=course, courses=COURSES)

    @app.route("/admin/inquiries")
    def admin_inquiries():
        """保存済みの申込を取り出す。メールが送れないときの受け取り口。

        メール送信は外部サービスの日次上限で落ちることがある。そのとき申込は
        保存されているが誰も気づけないため、取り出す口をここに用意する。
        合言葉（環境変数 INQUIRY_ADMIN_TOKEN）が未設定なら機能ごと閉じる＝
        設定し忘れで中身が誰でも見える状態にはしない。
        """
        import hmac
        from inquiry_store import read_inquiries

        # 値の前後の空白とBOMを落としてから比べる。
        # 環境変数の設定経路によっては先頭にBOM(EF BB BF)が入り、
        # 画面で見えないまま一致しなくなる（2026-08-04に実際に発生）。
        # さらに hmac.compare_digest は str だと非ASCIIで例外を投げるため、
        # bytes に変換して比べる（合言葉の違いを500エラーで返さない）。
        def _clean(s):
            return (s or "").strip().lstrip("﻿").strip()

        expected = _clean(os.environ.get("INQUIRY_ADMIN_TOKEN", ""))
        if not expected:
            return {"error": "disabled",
                    "message": "INQUIRY_ADMIN_TOKEN が未設定のため無効です。"}, 503

        given = _clean(request.args.get("token")
                       or request.headers.get("X-Admin-Token"))
        if not hmac.compare_digest(given.encode("utf-8"), expected.encode("utf-8")):
            return {"error": "forbidden"}, 403

        # ?kind=spam で、遮断したぶんの中身を見る。
        # ⛔ 件数だけでは「本物を落としていないか」が分からない。
        #    誤判定は売上の損失なので、中身を読めるようにしておく。
        if request.args.get('kind') == 'spam':
            import json as _json
            import os as _os
            d = _os.environ.get('INQUIRY_LOG_DIR') or _os.path.join(
                _os.path.dirname(_os.path.abspath(__file__)), 'data')
            path = _os.path.join(d, 'spam.log')
            rows = []
            if _os.path.exists(path):
                for line in open(path, encoding='utf-8'):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rows.append(_json.loads(line))
                    except Exception:
                        rows.append({'_unparsed': line})
            rows.reverse()
            # 判定理由ごとの内訳も返す（どの防御が効いているかが分かる）
            by_reason = {}
            for r in rows:
                by_reason[r.get('reason', '?')] = by_reason.get(r.get('reason', '?'), 0) + 1
            return {"count": len(rows), "by_reason": by_reason, "blocked": rows[:200]}

        rows = read_inquiries()
        return {"count": len(rows), "inquiries": rows}

    @app.route("/api/solo-inquiry", methods=["POST"])
    def solo_inquiry():
        try:
            data = request.get_json(force=True)
        except Exception:
            return {"error": "invalid JSON"}, 400

        name = (data.get("name") or "").strip()
        email = (data.get("email") or "").strip()
        course = (data.get("course") or "").strip()
        message = (data.get("message") or "").strip()

        # スパム判定。⛔ 弾いたことをボットに教えない（成功と同じ形で返す）。
        #    保存もしない＝台帳がスパムで埋まらない。
        import antispam
        spam = antispam.check(request, data)
        if spam:
            app.logger.info('[solo-inquiry] スパムとして遮断: %s', spam)
            return {"ok": True, "mail_sent": "deferred"}

        if not name or not email:
            return {"error": "name and email are required"}, 400

        # 1) まず保存する。メールより先。
        #    メール送信が唯一の記録手段だと、鍵が無い・送信に失敗しただけで
        #    申込が痕跡ごと消え、何件失ったのかも数えられない（2026-07-30に実際に発生）。
        try:
            saved = save_inquiry("solo-ceo", {
                "name": name,
                "email": email,
                "course": course,
                "message": message,
            })
        except Exception:
            app.logger.exception("[solo-inquiry] 保存に失敗＝受付を成立させない")
            return {
                "error": "save_failed",
                "message": "受付処理に失敗しました。お手数ですが info@jgaia.org まで直接ご連絡ください。",
            }, 500

        # 2) そのうえでメールを送る。送れなくても受付自体は成立している（保存済み）。
        #    ただし「確認メールを送った」とは言わない。
        #    送信は自前のSMTP（さくら）が既定。外部APIの無料枠に依存しない。
        body_lines = [
            f"氏名: {name}",
            f"メール: {email}",
            f"関心コース: {course}" if course else None,
            f"ご質問・ご相談:\n{message}" if message else None,
        ]
        body_text = "\n".join(line for line in body_lines if line)
        notify_subject = f"【JGAIA AI経営講座】お問い合わせ: {name}様"
        reply_subject = "【JGAIA】一人会社AI経営講座 お問い合わせありがとうございます"
        reply_body = (
            f"{name} 様\n\n"
            "一般社団法人日本生成AI協会（JGAIA）の一人会社AI経営講座に"
            "ご関心をお寄せいただきありがとうございます。\n\n"
            "担当者より2営業日以内にご連絡いたします。\n\n"
            "---\n"
            "一般社団法人日本生成AI協会（JGAIA）\n"
            "〒104-0061 東京都中央区銀座1-22-11 銀座大竹ビジデンス2階\n"
            "info@jgaia.org\n"
            "https://www.jgaia.org/\n"
        )

        # ⛔ ここからSMTPで送ろうとしないこと。Railwayは外向きSMTPを遮断しており
        #    （2026-08-06実測: さくら587/465ともTimeout）、必ず失敗するうえに
        #    その30秒ぶん利用者のフォーム送信が固まる。
        #    サイトから送れるのはHTTPのAPI（Resend）だけ。
        #    送れなかったぶんは SoloOS（自宅PC）がさくら経由で拾って送る＝予備。
        api_key = os.environ.get("RESEND_API_KEY", "") or RESEND_API_KEY
        if not api_key:
            app.logger.error(
                "[solo-inquiry] 送信手段が未設定です（SMTP・外部APIとも）。"
                "申込は保存済みですが通知メールは送れていません: %s <%s>", name, email)
            LAST_MAIL_ERROR["at"] = _now_jst()
            LAST_MAIL_ERROR["kind"] = "NoMailer"
            return {"ok": True, "mail_sent": False}

        try:
            import resend
            resend.api_key = api_key
            resend.Emails.send({"from": FROM_EMAIL, "to": [NOTIFY_EMAIL],
                                "subject": notify_subject, "text": body_text})
            resend.Emails.send({"from": FROM_EMAIL, "to": [email],
                                "subject": reply_subject, "text": reply_body})
        except Exception as e:
            # 握り潰さない。保存は済んでいるので、予備の経路が拾って送る。
            app.logger.exception(
                "[solo-inquiry] メール送信に失敗。申込は保存済み: %s <%s>", name, email)
            LAST_MAIL_ERROR["at"] = _now_jst()
            LAST_MAIL_ERROR["kind"] = type(e).__name__
            return {"ok": True, "mail_sent": False}

        # 送れた印を残す。⛔これが無いと予備の経路が同じ人に二重に送る。
        try:
            mark_mailed(inquiry_key(saved))
        except Exception:
            app.logger.exception("[solo-inquiry] 送信済みの印を残せませんでした")

        LAST_MAIL_ERROR["at"] = None
        LAST_MAIL_ERROR["kind"] = None
        return {"ok": True, "mail_sent": True}
