"""JGAIA バイブコーディング講座 各コース詳細ページ（GA/GB/GC/GD/GE）"""
import os
from flask import Response, request
import json

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "info@jgaia.org")

# ─────────────────────────────────────────
# コースデータ
# ─────────────────────────────────────────
COURSES = {
    "ga": {
        "id": "ga",
        "code": "GA",
        "title": "生成AI入門1日",
        "subtitle": "ChatGPT・Claude・Gemini の違いと使い分けから業務活用まで",
        "gradient": "linear-gradient(135deg, #1565c0, #0288d1)",
        "accent": "#0288d1",
        "accent_light": "#4fc3f7",
        "duration": "1日（6時間）",
        "price": "49,800",
        "price_num": 49800,
        "target": "生成AI未経験者・経営者・管理職",
        "format": "会場＋オンライン同時開催",
        "capacity": "20名",
        "schedule": "10:00〜17:00（昼休憩1時間）",
        "subsidy": True,
        "subsidy_text": "東京しごと財団 助成金対象（実質 ¥24,800〜）",
        "curriculum": [
            ("生成AIの基礎知識", "ChatGPT / Claude / Gemini の違いと使い分け。大規模言語モデル（LLM）の仕組みを直感的に理解します。"),
            ("プロンプトエンジニアリング入門", "効果的な指示の書き方。ゼロショット・Few-shot・Chain of Thought の3パターンを実践的に習得します。"),
            ("業務での活用事例", "文書作成・要約・翻訳・データ分析。実際の業務シーンを想定したライブデモで即戦力を身につけます。"),
            ("AIツールの比較と選定", "用途別おすすめツール。コスト・精度・セキュリティの観点から自社に最適なAIを選ぶ判断軸を学びます。"),
            ("セキュリティ・倫理の基礎", "機密情報の取り扱い。ハルシネーション・著作権・個人情報保護の3大リスクと対策を押さえます。"),
            ("ハンズオン：業務改善プロンプトを作成", "自分の業務課題をAIで解決するプロンプトを設計・実行。講師フィードバック付きで完成度を高めます。"),
        ],
        "outcomes": [
            ("主要AI 3ツールを使いこなせる", "ChatGPT・Claude・Gemini それぞれの得意分野を理解し、業務に合ったツールを選べるようになります。"),
            ("業務を30%効率化するプロンプトが書ける", "報告書作成・議事録要約・データ整理など、日常業務に即座に適用できるプロンプトを持ち帰れます。"),
            ("AIリスクを正しく理解できる", "機密情報漏洩・ハルシネーション・著作権侵害のリスクを理解し、安全なAI活用ルールを策定できます。"),
        ],
        "faq": [
            ("プログラミング経験がなくても大丈夫ですか？", "はい、プログラミング経験は一切不要です。パソコンの基本操作（ブラウザでの文字入力）ができれば問題ありません。"),
            ("会社のPCから受講できますか？", "はい、ChromeまたはEdgeブラウザがあればオンラインで受講可能です。社内セキュリティポリシーでAIツールへのアクセスが制限されている場合は、事前にご相談ください。"),
            ("受講後のサポートはありますか？", "受講後30日間、メールでの質問サポートを無料で提供しています。また、修了者限定のSlackコミュニティにご招待します。"),
            ("助成金を利用する場合の手続きは？", "東京しごと財団「事業外スキルアップ助成金」の対象です。Jグランツで1ヶ月前に事前申請が必要です。詳しい手続きは申込時にご案内します。"),
        ],
    },
    "gb": {
        "id": "gb",
        "code": "GB",
        "title": "バイブコーディング実践1日",
        "subtitle": "AIに「こんなアプリ作って」と伝えるだけ。コード不要のアプリ開発体験",
        "gradient": "linear-gradient(135deg, #4527a0, #7b1fa2)",
        "accent": "#7b1fa2",
        "accent_light": "#ce93d8",
        "duration": "1日（6時間）",
        "price": "49,800",
        "price_num": 49800,
        "target": "業務アプリを自作したいビジネスパーソン",
        "format": "会場＋オンライン同時開催",
        "capacity": "15名",
        "schedule": "10:00〜17:00（昼休憩1時間）",
        "subsidy": True,
        "subsidy_text": "東京しごと財団 助成金対象（実質 ¥24,800〜）",
        "curriculum": [
            ("バイブコーディングとは", "AIに「こんなアプリ作って」と伝える開発手法。Andrej Karpathy 氏が提唱した最新のソフトウェア開発パラダイムを解説します。"),
            ("開発環境セットアップ", "Claude Code / Cursor / Bolt.new の3ツールを実際にセットアップ。アカウント作成から初回実行までを丁寧にガイドします。"),
            ("プロンプトで業務アプリを作る", "日報管理・在庫管理・顧客リストなど、実務で使えるアプリを自然言語の指示だけで構築する体験をします。"),
            ("デザインとUI/UXの基本", "見やすいダッシュボードの作り方。色・レイアウト・フォントの3要素をAIに的確に伝えるテクニックを学びます。"),
            ("デプロイ入門", "作ったアプリを公開する方法。Railway / Vercel / Render を使った無料デプロイの手順を実践します。"),
            ("成果発表＋フィードバック", "受講者が作成したアプリを発表。講師と参加者からフィードバックを受け、改善ポイントを明確にします。"),
        ],
        "outcomes": [
            ("コード不要で業務アプリが作れる", "プログラミング経験ゼロでも、AIへの指示だけで実用的なWebアプリを構築できるスキルを習得します。"),
            ("3つの開発ツールを使い分けられる", "Claude Code・Cursor・Bolt.new それぞれの特徴を理解し、用途に応じて最適なツールを選択できます。"),
            ("作ったアプリを世界に公開できる", "デプロイの基本を習得し、自分が作ったアプリをURLで共有・公開できるようになります。"),
        ],
        "faq": [
            ("コースGAを先に受講する必要がありますか？", "必須ではありませんが、生成AIの基礎知識があるとスムーズです。AIツールを初めて使う方はコースGAの先行受講をおすすめします。"),
            ("どんなアプリが作れますか？", "日報管理、在庫管理、顧客リスト、タスク管理、アンケートフォーム、ダッシュボードなど、Webブラウザで動くアプリ全般が対象です。"),
            ("自分のPCが必要ですか？", "はい、ノートPCをご持参ください。Windows / Mac どちらでも問題ありません。事前セットアップ手順は申込後にメールでお送りします。"),
            ("受講後もアプリを使い続けられますか？", "はい、受講中に作成したアプリはすべてご自身のものです。デプロイしたアプリは受講後も無料で運用を継続できます。"),
        ],
    },
    "gc": {
        "id": "gc",
        "code": "GC",
        "title": "AI業務自動化マスター",
        "subtitle": "全5回の夜間集中コース。RAG・AIエージェント・ワークフロー自動化を体系的に習得",
        "gradient": "linear-gradient(135deg, #00695c, #00897b)",
        "accent": "#00897b",
        "accent_light": "#80cbc4",
        "duration": "全5回（各2.5時間）計12.5時間",
        "price": "68,000",
        "price_num": 68000,
        "target": "働きながらAI自動化スキルを身につけたい社会人",
        "format": "オンライン（毎週水曜19:00〜21:30）",
        "capacity": "30名",
        "schedule": "毎週水曜 19:00〜21:30（全5回）",
        "subsidy": False,
        "subsidy_text": "",
        "curriculum": [
            ("Week 1: プロンプト設計の深化", "システムプロンプト・Few-shot・Chain of Thought の3手法を深掘り。複雑なタスクを分解して高精度な出力を得るテクニックを習得します。"),
            ("Week 2: RAG（検索拡張生成）でナレッジベース構築", "社内文書をベクトル化してAIに読ませる技術。自社専用のAIアシスタントを構築する実践ワークショップです。"),
            ("Week 3: AIエージェント入門", "複数ツールの連携自動化。AIが自律的にWeb検索・データ取得・レポート作成を行うエージェントの設計パターンを学びます。"),
            ("Week 4: ワークフロー自動化", "Make / Zapier とAIを組み合わせた業務自動化。メール→要約→Slack通知など、ノーコードで構築する自動化パイプラインを実践します。"),
            ("Week 5: 卒業制作＋発表会", "自社業務の自動化プロトタイプを制作。講師・参加者からのフィードバックを受け、実運用に向けた改善計画を策定します。"),
        ],
        "outcomes": [
            ("社内ナレッジをAIで活用できる", "RAG技術を使って、社内マニュアル・FAQ・議事録をAIが参照できるナレッジベースを構築するスキルを身につけます。"),
            ("業務フローを自動化できる", "Make / Zapier とAIを組み合わせて、手作業で行っていた定型業務を自動化するワークフローを設計・構築できます。"),
            ("AIエージェントを設計できる", "複数ツールを連携させて自律的にタスクを実行するAIエージェントの基本設計パターンを習得します。"),
            ("卒業制作で実績を作れる", "自社業務の自動化プロトタイプを完成させ、社内提案や転職ポートフォリオとして活用できます。"),
        ],
        "faq": [
            ("途中の回を欠席した場合はどうなりますか？", "各回の録画アーカイブを翌日までに共有します。欠席された回は録画で学習し、次回までにキャッチアップいただけます。"),
            ("コースGA・GBの受講は前提ですか？", "前提ではありませんが、生成AIの基本操作（プロンプト入力・ツールの使い分け）ができることが望ましいです。"),
            ("会社の業務データを使っても大丈夫ですか？", "RAGのハンズオンではサンプルデータを用意しています。自社データを使用する場合は、社内の情報セキュリティポリシーをご確認の上、自己責任でお願いします。"),
            ("10時間超のため助成金は使えませんか？", "はい、東京しごと財団の助成金は10時間未満の講座が対象のため、本コース（12.5時間）は対象外です。法人研修としての請求書払いには対応しています。"),
        ],
    },
    "gd": {
        "id": "gd",
        "code": "GD",
        "title": "AIセキュリティ・ガバナンス",
        "subtitle": "AI利活用のリスクを正しく理解し、社内ガイドライン策定まで実践する1日集中コース",
        "gradient": "linear-gradient(135deg, #b71c1c, #d84315)",
        "accent": "#d84315",
        "accent_light": "#ff8a65",
        "duration": "1日（6時間）",
        "price": "49,800",
        "price_num": 49800,
        "target": "AI利用ルール策定担当者・情報セキュリティ担当",
        "format": "会場＋オンライン同時開催",
        "capacity": "15名",
        "schedule": "10:00〜17:00（昼休憩1時間）",
        "subsidy": True,
        "subsidy_text": "東京しごと財団 助成金対象（実質 ¥24,800〜）",
        "curriculum": [
            ("生成AIのリスク全体像", "ハルシネーション・情報漏洩・著作権侵害の3大リスクを、国内外の実際のインシデント事例とともに体系的に解説します。"),
            ("社内AIガイドライン策定ワークショップ", "自社の業種・規模・リスク許容度に合わせたAI利用ルールをグループワーク形式で策定。テンプレートを持ち帰れます。"),
            ("プロンプトインジェクション攻撃と対策", "悪意あるプロンプトでAIの挙動を乗っ取る攻撃手法と、入力検証・出力フィルタリング等の防御策を実演します。"),
            ("個人情報保護法・AI事業者ガイドラインへの対応", "2024年改正個人情報保護法・経産省AI事業者ガイドラインの要点を整理。法務部門との連携ポイントを解説します。"),
            ("セキュアなAI活用アーキテクチャ設計", "オンプレミス / プライベートクラウド / API経由の3パターンで、機密データを守りながらAIを活用する構成を設計します。"),
            ("インシデント対応演習", "AI起因のセキュリティインシデント（情報漏洩・誤情報公開等）を模擬体験。初動対応から再発防止策までをチームで実践します。"),
        ],
        "outcomes": [
            ("社内AIガイドラインを策定できる", "自社の業種・規模に合ったAI利用ルールのテンプレートを完成させ、経営層への提案資料として活用できます。"),
            ("AIセキュリティリスクを評価できる", "プロンプトインジェクション・データ漏洩・ハルシネーション等のリスクを体系的に評価し、対策優先度を判断できます。"),
            ("インシデント対応力が身につく", "AI起因のセキュリティ事故が発生した際の初動対応・報告フロー・再発防止策を実践的に習得します。"),
        ],
        "faq": [
            ("技術者でなくても理解できますか？", "はい、技術的な内容は平易な言葉で解説します。情報セキュリティ担当・法務・経営企画など、非技術者の方にもわかりやすい内容です。"),
            ("策定したガイドラインはそのまま使えますか？", "ワークショップで作成するガイドラインはテンプレートベースです。自社の就業規則・情報セキュリティポリシーとの整合性を確認の上、適宜カスタマイズしてご利用ください。"),
            ("コースGAの受講は必要ですか？", "必須ではありませんが、生成AIの基本的な操作経験があると理解がスムーズです。ChatGPT等を業務で使ったことがあれば十分です。"),
            ("法務部門のメンバーも参加できますか？", "むしろ推奨します。ガイドライン策定ワークショップは法務・IT・経営企画の複数部門から参加いただくと、より実効性の高いルールを策定できます。"),
        ],
    },
    "ge": {
        "id": "ge",
        "code": "GE",
        "title": "AIクリエイティブデザイン",
        "subtitle": "AI画像・動画・音声生成の最前線。ブランドアセットをAIで制作するスキルを1日で習得",
        "gradient": "linear-gradient(135deg, #283593, #3949ab)",
        "accent": "#3949ab",
        "accent_light": "#7986cb",
        "duration": "1日（6時間）",
        "price": "49,800",
        "price_num": 49800,
        "target": "デザイン・マーケティング・広報担当者",
        "format": "会場＋オンライン同時開催",
        "capacity": "15名",
        "schedule": "10:00〜17:00（昼休憩1時間）",
        "subsidy": True,
        "subsidy_text": "東京しごと財団 助成金対象（実質 ¥24,800〜）",
        "curriculum": [
            ("AI画像生成の基礎", "GPT-Image / Midjourney / Stable Diffusion の3ツールを比較。それぞれの得意分野・画風・料金体系を整理します。"),
            ("プロンプトで思い通りの画像を作る", "構図・スタイル・色彩をプロンプトで制御するテクニック。ネガティブプロンプト・シード値・ControlNet の活用法を実践します。"),
            ("AI動画生成", "Sora / Runway / Veo の最新動画生成AIを体験。テキストから動画、画像から動画、動画の編集・拡張までを実演します。"),
            ("AI音声・ナレーション生成", "ElevenLabs / VOICEVOX を使った高品質音声生成。多言語ナレーション・感情制御・音声クローニングの可能性を探ります。"),
            ("ブランドアセット制作ワークショップ", "ロゴ・バナー・SNS素材をAIで制作。ブランドガイドラインに沿った一貫性のあるビジュアルアイデンティティを構築します。"),
            ("著作権・商用利用の注意点", "AI生成コンテンツの著作権・商用利用ルールを解説。文化庁ガイドライン・各ツールの利用規約を整理し、安全な運用方法を学びます。"),
        ],
        "outcomes": [
            ("AIで高品質なビジュアルを制作できる", "画像・動画・音声の3領域でAI生成ツールを使いこなし、プロレベルのクリエイティブ素材を短時間で制作できます。"),
            ("ブランド一貫性を保ったデザインが作れる", "ブランドガイドラインに沿って、ロゴ・バナー・SNS素材をAIで効率的に量産するワークフローを構築できます。"),
            ("著作権リスクを回避できる", "AI生成コンテンツの著作権・商用利用の法的リスクを理解し、安全にビジネス活用するための判断基準を持てます。"),
        ],
        "faq": [
            ("デザインの専門知識は必要ですか？", "不要です。AIツールが画像・動画・音声を生成するため、デザインスキルがなくてもプロンプト（指示文）が書ければ参加できます。"),
            ("生成した画像を商用利用できますか？", "ツールによって利用規約が異なります。講座内で各ツールの商用利用条件を詳しく解説し、安全な運用方法をお伝えします。"),
            ("動画編集ソフトは必要ですか？", "不要です。講座ではブラウザベースのAI動画生成ツールを使用します。ローカルソフトのインストールは必要ありません。"),
            ("制作したアセットは持ち帰れますか？", "はい、ワークショップで制作したすべてのクリエイティブ素材（画像・動画・音声）はダウンロードしてお持ち帰りいただけます。"),
        ],
    },
}


# ─────────────────────────────────────────
# ルート登録
# ─────────────────────────────────────────
def register_vibe_coding_course_routes(app):
    """Flask appにコース詳細ルートを登録"""

    @app.route("/vibe-coding/course-ga")
    def course_ga():
        return Response(_render_course_page("ga"), mimetype="text/html")

    @app.route("/vibe-coding/course-gb")
    def course_gb():
        return Response(_render_course_page("gb"), mimetype="text/html")

    @app.route("/vibe-coding/course-gc")
    def course_gc():
        return Response(_render_course_page("gc"), mimetype="text/html")

    @app.route("/vibe-coding/course-gd")
    def course_gd():
        return Response(_render_course_page("gd"), mimetype="text/html")

    @app.route("/vibe-coding/course-ge")
    def course_ge():
        return Response(_render_course_page("ge"), mimetype="text/html")

    @app.post("/api/course-inquiry")
    def course_inquiry():
        data = request.form
        name = data.get("name", "")
        email = data.get("email", "")
        company = data.get("company", "")
        phone = data.get("phone", "")
        course = data.get("course", "")
        message = data.get("message", "")

        sg_key = os.environ.get("SENDGRID_API_KEY", SENDGRID_API_KEY)
        if sg_key:
            try:
                import sendgrid
                from sendgrid.helpers.mail import Mail
                sg = sendgrid.SendGridAPIClient(api_key=sg_key)
                body = (
                    f"コース: {course}\n"
                    f"お名前: {name}\n"
                    f"メール: {email}\n"
                    f"会社名: {company}\n"
                    f"電話: {phone}\n\n"
                    f"メッセージ:\n{message}"
                )
                mail = Mail(
                    from_email=SENDER_EMAIL,
                    to_emails="takano.hidetaka@gmail.com",
                    subject=f"【JGAIA講座問い合わせ】{course} - {company or name}",
                    plain_text_content=body,
                )
                sg.send(mail)

                # 自動返信
                auto_body = (
                    f"{name} 様\n\n"
                    f"お問い合わせありがとうございます。\n"
                    f"以下の内容で受け付けました。\n\n"
                    f"コース: {course}\n\n"
                    f"担当者より2営業日以内にご連絡いたします。\n\n"
                    f"一般社団法人日本生成AI協会（JGAIA）"
                )
                auto_mail = Mail(
                    from_email=SENDER_EMAIL,
                    to_emails=email,
                    subject="【JGAIA】お問い合わせありがとうございます",
                    plain_text_content=auto_body,
                )
                sg.send(auto_mail)
            except Exception:
                pass

        return Response(_render_thank_you_page(course, name), mimetype="text/html")


# ─────────────────────────────────────────
# ページレンダリング
# ─────────────────────────────────────────
def _render_course_page(course_id):
    """コース詳細ページのHTML全体を生成"""
    c = COURSES[course_id]

    # カリキュラム行
    curriculum_html = ""
    for i, (title, desc) in enumerate(c["curriculum"], 1):
        curriculum_html += f'''
        <div class="cur-item">
          <div class="cur-num" style="background:{c['accent']}">{i:02d}</div>
          <div class="cur-body">
            <h4 class="cur-title">{title}</h4>
            <p class="cur-desc">{desc}</p>
          </div>
        </div>'''

    # 習得スキルカード
    outcomes_html = ""
    for title, desc in c["outcomes"]:
        outcomes_html += f'''
        <div class="out-card">
          <div class="out-icon" style="color:{c['accent_light']}">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
              <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
          </div>
          <h4 class="out-title">{title}</h4>
          <p class="out-desc">{desc}</p>
        </div>'''

    # FAQ
    faq_html = ""
    for q, a in c["faq"]:
        faq_html += f'''
        <div class="faq-item">
          <button class="faq-q" onclick="this.parentElement.classList.toggle('open')">
            <span>{q}</span>
            <svg class="faq-chevron" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"></polyline></svg>
          </button>
          <div class="faq-a"><p>{a}</p></div>
        </div>'''

    # 助成金セクション
    subsidy_html = ""
    if c["subsidy"]:
        subsidy_html = f'''
    <section class="sec subsidy-sec">
      <div class="sec-inner">
        <div class="sec-eyebrow"><span class="sec-eyebrow-line"></span>SUBSIDY</div>
        <h2 class="sec-heading">助成金で実質 <span style="color:{c['accent_light']}">¥24,800</span> から受講可能</h2>
        <p class="sec-sub">東京しごと財団「事業外スキルアップ助成金」の対象講座です。</p>
        <div class="subsidy-grid">
          <div class="subsidy-card">
            <div class="subsidy-label">小規模企業（従業員20人以下）</div>
            <div class="subsidy-rate">受講料の <strong>2/3</strong> 助成</div>
            <div class="subsidy-result">実質負担 <strong>¥24,800</strong>〜 / 人</div>
          </div>
          <div class="subsidy-card">
            <div class="subsidy-label">中小企業（従業員21人以上）</div>
            <div class="subsidy-rate">受講料の <strong>1/2</strong> 助成</div>
            <div class="subsidy-result">実質負担 <strong>¥24,900</strong>〜 / 人</div>
          </div>
        </div>
        <div class="subsidy-note">
          <p>対象: 都内中小企業の従業員（代表者除く）。Jグランツにて受講開始1ヶ月前までに事前申請が必要です。</p>
          <p>令和8年度受付: 2026年3月1日〜2027年2月28日 ｜ <a href="https://www.koyokankyo.shigotozaidan.or.jp/jigyo/skillup/skill-R8jigyogai.html" target="_blank" rel="noopener" style="color:{c['accent_light']}">公式サイト →</a></p>
        </div>
      </div>
    </section>'''

    return f'''<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{c["title"]} | JGAIA バイブコーディング講座</title>
<meta name="description" content="{c['subtitle']}。受講料¥{c['price']}（税込）。{c['target']}向け。">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=Noto+Sans+JP:wght@300;400;500;700&family=DM+Sans:ital,wght@0,300;0,400;0,500;1,300&display=swap" rel="stylesheet">
<style>
:root {{
  --ink:      #09090b;
  --ink-s:    #111118;
  --ink-m:    #27272a;
  --text:     #fafafa;
  --text-s:   #a1a1aa;
  --text-m:   #52525b;
  --accent:   #6366f1;
  --accent-l: #818cf8;
  --border:   rgba(255,255,255,0.07);
  --border-l: rgba(255,255,255,0.12);
  --font-d:   'Syne','Noto Sans JP',sans-serif;
  --font:     'DM Sans','Noto Sans JP',sans-serif;
  --r:        4px;
  --ease:     cubic-bezier(0.16, 1, 0.3, 1);
}}
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
html{{scroll-behavior:smooth;font-size:16px}}
body{{
  background:var(--ink);color:var(--text);
  font-family:var(--font);line-height:1.6;
  -webkit-font-smoothing:antialiased;
}}
a{{color:inherit;text-decoration:none}}
img{{display:block;max-width:100%}}
button{{cursor:pointer;border:none;background:none;font-family:inherit}}

/* ── ヘッダー ── */
.hd {{
  position:fixed;top:0;left:0;right:0;z-index:100;
  padding:0 48px;height:72px;
  display:flex;align-items:center;
  background:rgba(9,9,11,0.92);
  backdrop-filter:blur(24px);
  border-bottom:1px solid var(--border);
}}
.hd-logo {{
  display:flex;align-items:center;gap:11px;
  margin-right:48px;flex-shrink:0;
}}
.hd-logo-mark {{
  width:32px;height:32px;border-radius:6px;
  border:1px solid var(--border-l);
  display:flex;align-items:center;justify-content:center;
}}
.hd-logo-mark svg{{width:16px;height:16px;fill:none;stroke:#fff;stroke-width:1.5}}
.hd-logo-text .en{{
  font-family:var(--font-d);font-size:16px;font-weight:700;
  color:#fff;letter-spacing:.06em;
}}
.hd-logo-text .ja{{font-size:9px;color:var(--text-s);letter-spacing:.04em;margin-top:1px}}
.hd-nav{{display:flex;align-items:center;gap:2px;flex:1}}
.hd-nav a{{
  font-size:13.5px;font-weight:400;color:var(--text-s);
  padding:7px 14px;border-radius:var(--r);
  transition:color .15s,background .15s;
  white-space:nowrap;
}}
.hd-nav a:hover{{color:#fff;background:rgba(255,255,255,0.06)}}
.hd-right{{display:flex;align-items:center;gap:10px;margin-left:auto}}
.btn-ghost{{
  font-size:13px;font-weight:500;color:var(--text-s);
  padding:8px 18px;border-radius:var(--r);
  border:1px solid var(--border-l);
  transition:all .15s;
}}
.btn-ghost:hover{{color:#fff;border-color:rgba(255,255,255,0.25);background:rgba(255,255,255,0.05)}}
.btn-solid{{
  font-size:13px;font-weight:600;color:#fff;
  padding:9px 20px;border-radius:var(--r);
  background:var(--accent);
  transition:opacity .15s;
}}
.btn-solid:hover{{opacity:.85}}

/* ── ヒーロー ── */
.hero {{
  position:relative;
  padding:140px 80px 80px;
  overflow:hidden;
  min-height:480px;
  display:flex;align-items:flex-end;
}}
.hero-bg {{
  position:absolute;inset:0;
  {c['gradient']};
  opacity:0.25;
}}
.hero-bg::after {{
  content:'';position:absolute;inset:0;
  background:
    linear-gradient(to top, var(--ink) 0%, rgba(9,9,11,0.6) 50%, rgba(9,9,11,0.3) 100%),
    linear-gradient(to right, var(--ink) 0%, transparent 60%);
}}
.hero-grid {{
  position:absolute;inset:0;
  background-image:
    linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px);
  background-size:64px 64px;
}}
.hero-content {{
  position:relative;z-index:1;
  max-width:800px;
}}
.hero-badge {{
  display:inline-flex;align-items:center;gap:8px;
  font-size:11px;font-weight:700;letter-spacing:.18em;
  text-transform:uppercase;
  padding:6px 16px;border-radius:var(--r);
  {c['gradient']};
  color:#fff;margin-bottom:20px;
}}
.hero h1 {{
  font-family:var(--font-d);
  font-size:clamp(36px,5vw,60px);
  font-weight:800;line-height:1.1;
  color:#fff;letter-spacing:-.03em;
  margin-bottom:16px;
}}
.hero-sub {{
  font-size:16px;font-weight:300;
  color:rgba(255,255,255,0.7);
  line-height:1.8;max-width:600px;
  margin-bottom:32px;
}}
.hero-meta {{
  display:flex;flex-wrap:wrap;gap:12px;
}}
.hero-tag {{
  font-size:12px;font-weight:500;
  padding:6px 14px;border-radius:var(--r);
  background:rgba(255,255,255,0.08);
  border:1px solid rgba(255,255,255,0.12);
  color:rgba(255,255,255,0.8);
}}
.hero-price {{
  font-family:var(--font-d);
  font-size:clamp(28px,4vw,42px);
  font-weight:800;color:#fff;
  margin-top:24px;
}}
.hero-price small {{
  font-size:14px;font-weight:400;
  color:var(--text-s);margin-left:8px;
}}

/* ── セクション共通 ── */
.sec {{
  padding:100px 80px;
  border-top:1px solid var(--border);
}}
.sec-inner {{
  max-width:900px;margin:0 auto;
}}
.sec-eyebrow {{
  display:inline-flex;align-items:center;gap:10px;
  font-size:10.5px;font-weight:600;letter-spacing:.2em;
  text-transform:uppercase;color:{c['accent_light']};
  margin-bottom:20px;
}}
.sec-eyebrow-line {{
  display:inline-block;width:16px;height:1px;
  background:{c['accent_light']};
}}
.sec-heading {{
  font-family:var(--font-d);
  font-size:clamp(28px,3.5vw,44px);
  font-weight:800;color:#fff;
  line-height:1.15;letter-spacing:-.02em;
  margin-bottom:16px;
}}
.sec-sub {{
  font-size:15px;font-weight:300;
  color:var(--text-s);line-height:1.8;
  margin-bottom:48px;max-width:600px;
}}

/* ── 概要グリッド ── */
.overview-grid {{
  display:grid;
  grid-template-columns:repeat(auto-fit,minmax(200px,1fr));
  gap:2px;margin-bottom:0;
}}
.ov-card {{
  background:var(--ink-s);
  padding:28px 24px;
  transition:background .2s;
}}
.ov-card:hover {{background:var(--ink-m)}}
.ov-label {{
  font-size:10px;font-weight:600;letter-spacing:.15em;
  text-transform:uppercase;
  color:var(--text-m);margin-bottom:8px;
}}
.ov-val {{
  font-size:15px;font-weight:600;color:#fff;line-height:1.5;
}}
.ov-val .sub {{
  display:block;font-size:12px;font-weight:400;
  color:{c['accent_light']};margin-top:4px;
}}

/* ── カリキュラム ── */
.cur-list {{
  display:flex;flex-direction:column;gap:2px;
}}
.cur-item {{
  display:flex;gap:20px;align-items:flex-start;
  background:var(--ink-s);
  padding:28px 28px;
  transition:background .2s;
}}
.cur-item:hover {{background:var(--ink-m)}}
.cur-num {{
  flex-shrink:0;
  width:40px;height:40px;
  border-radius:8px;
  display:flex;align-items:center;justify-content:center;
  font-family:var(--font-d);font-size:13px;font-weight:700;
  color:#fff;letter-spacing:.05em;
}}
.cur-body {{flex:1;min-width:0}}
.cur-title {{
  font-size:15px;font-weight:700;color:#fff;
  margin-bottom:6px;line-height:1.4;
}}
.cur-desc {{
  font-size:13.5px;font-weight:300;
  color:var(--text-s);line-height:1.7;
}}

/* ── 習得スキル ── */
.out-grid {{
  display:grid;
  grid-template-columns:repeat(auto-fit,minmax(260px,1fr));
  gap:2px;
}}
.out-card {{
  background:var(--ink-s);
  padding:32px 28px;
  transition:background .2s;
}}
.out-card:hover {{background:var(--ink-m)}}
.out-icon {{
  margin-bottom:16px;
}}
.out-title {{
  font-size:15px;font-weight:700;color:#fff;
  margin-bottom:8px;line-height:1.4;
}}
.out-desc {{
  font-size:13px;font-weight:300;
  color:var(--text-s);line-height:1.7;
}}

/* ── 講師 ── */
.instructor-card {{
  display:flex;gap:32px;align-items:center;
  background:var(--ink-s);
  padding:40px;
}}
.instructor-avatar {{
  flex-shrink:0;
  width:100px;height:100px;
  border-radius:50%;
  {c['gradient']};
  display:flex;align-items:center;justify-content:center;
  font-family:var(--font-d);font-size:32px;font-weight:800;color:#fff;
}}
.instructor-info {{flex:1;min-width:0}}
.instructor-name {{
  font-family:var(--font-d);
  font-size:22px;font-weight:800;color:#fff;
  margin-bottom:4px;
}}
.instructor-role {{
  font-size:13px;color:{c['accent_light']};
  font-weight:500;margin-bottom:12px;
}}
.instructor-bio {{
  font-size:13.5px;font-weight:300;
  color:var(--text-s);line-height:1.8;
}}

/* ── 助成金 ── */
.subsidy-sec {{
  background:var(--ink-s);
}}
.subsidy-grid {{
  display:grid;
  grid-template-columns:repeat(auto-fit,minmax(280px,1fr));
  gap:2px;margin-bottom:24px;
}}
.subsidy-card {{
  background:var(--ink);
  padding:28px 24px;
}}
.subsidy-label {{
  font-size:12px;font-weight:600;
  color:var(--text-s);margin-bottom:12px;
}}
.subsidy-rate {{
  font-size:14px;color:var(--text-s);
  margin-bottom:8px;
}}
.subsidy-rate strong {{color:#fff}}
.subsidy-result {{
  font-family:var(--font-d);
  font-size:22px;font-weight:800;color:#fff;
}}
.subsidy-result strong {{
  color:{c['accent_light']};
}}
.subsidy-note {{
  font-size:12px;color:var(--text-m);line-height:1.8;
}}
.subsidy-note a {{
  text-decoration:underline;text-underline-offset:3px;
}}

/* ── FAQ ── */
.faq-list {{
  display:flex;flex-direction:column;gap:2px;
}}
.faq-item {{
  background:var(--ink-s);overflow:hidden;
}}
.faq-q {{
  width:100%;
  display:flex;justify-content:space-between;align-items:center;gap:16px;
  padding:22px 28px;
  font-size:14px;font-weight:600;color:#fff;
  text-align:left;
  transition:background .15s;
}}
.faq-q:hover {{background:var(--ink-m)}}
.faq-chevron {{
  flex-shrink:0;
  transition:transform .25s var(--ease);
  color:var(--text-m);
}}
.faq-item.open .faq-chevron {{transform:rotate(180deg)}}
.faq-a {{
  max-height:0;overflow:hidden;
  transition:max-height .35s var(--ease),padding .35s;
  padding:0 28px;
}}
.faq-item.open .faq-a {{
  max-height:300px;
  padding:0 28px 24px;
}}
.faq-a p {{
  font-size:13.5px;font-weight:300;
  color:var(--text-s);line-height:1.8;
  border-top:1px solid var(--border);
  padding-top:16px;
}}

/* ── お問い合わせフォーム ── */
.form-sec {{
  background:var(--ink-s);
}}
.form-wrap {{
  display:grid;
  grid-template-columns:1fr 1fr;
  gap:16px;
}}
.form-group {{
  display:flex;flex-direction:column;gap:6px;
}}
.form-group.full {{grid-column:1/-1}}
.form-label {{
  font-size:12px;font-weight:600;
  color:var(--text-s);letter-spacing:.04em;
}}
.form-label .req {{
  color:#ef4444;margin-left:4px;font-size:10px;
}}
.form-input,.form-select,.form-textarea {{
  width:100%;padding:12px 14px;
  border-radius:var(--r);
  border:1px solid var(--border-l);
  background:var(--ink);
  color:#fff;font-size:14px;
  font-family:var(--font);
  outline:none;transition:border .2s;
}}
.form-input::placeholder,.form-textarea::placeholder {{
  color:var(--text-m);
}}
.form-input:focus,.form-select:focus,.form-textarea:focus {{
  border-color:rgba(255,255,255,0.35);
}}
.form-select {{
  appearance:none;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='8' viewBox='0 0 12 8'%3E%3Cpath fill='%23a1a1aa' d='M6 8L0 0h12z'/%3E%3C/svg%3E");
  background-repeat:no-repeat;background-position:right 14px center;
  padding-right:36px;
}}
.form-select option {{color:var(--ink);background:#fff}}
.form-textarea {{resize:vertical;min-height:100px}}
.btn-submit {{
  width:100%;padding:14px;
  {c['gradient']};
  color:#fff;font-size:14px;font-weight:700;
  border:none;border-radius:var(--r);
  cursor:pointer;letter-spacing:.03em;
  transition:opacity .15s,transform .1s;
  margin-top:8px;
}}
.btn-submit:hover {{opacity:.85;transform:translateY(-1px)}}
.btn-submit:disabled {{opacity:.5;cursor:not-allowed;transform:none}}
.form-note {{
  font-size:11px;color:var(--text-m);
  text-align:center;margin-top:12px;line-height:1.8;
}}
#form-msg {{
  margin-top:16px;padding:14px;
  border-radius:var(--r);text-align:center;
  font-weight:600;font-size:13px;display:none;
}}
.msg-ok {{background:rgba(34,197,94,0.15);color:#4ade80;border:1px solid rgba(34,197,94,0.2)}}
.msg-err {{background:rgba(239,68,68,0.15);color:#f87171;border:1px solid rgba(239,68,68,0.2)}}

/* ── フッター ── */
.footer {{
  border-top:1px solid var(--border);
  padding:48px 80px;
  display:flex;justify-content:space-between;align-items:center;
  flex-wrap:wrap;gap:24px;
}}
.footer-brand {{
  font-family:var(--font-d);font-size:14px;font-weight:700;
  color:#fff;letter-spacing:.06em;
}}
.footer-brand .ja {{
  display:block;font-size:10px;font-weight:400;
  color:var(--text-m);margin-top:4px;font-family:var(--font);
  letter-spacing:0;
}}
.footer-links {{
  display:flex;gap:24px;flex-wrap:wrap;
}}
.footer-links a {{
  font-size:12px;color:var(--text-m);
  transition:color .15s;
}}
.footer-links a:hover {{color:#fff}}
.footer-copy {{
  width:100%;font-size:11px;color:var(--text-m);
  border-top:1px solid var(--border);
  padding-top:24px;margin-top:8px;
}}

/* ── レスポンシブ ── */
@media(max-width:768px){{
  .hd {{padding:0 20px}}
  .hd-nav {{display:none}}
  .hd-right {{display:none}}
  .hero {{padding:120px 24px 48px;min-height:auto}}
  .hero h1 {{font-size:32px}}
  .sec {{padding:64px 24px}}
  .overview-grid {{grid-template-columns:1fr}}
  .cur-item {{padding:20px;gap:14px}}
  .cur-num {{width:32px;height:32px;font-size:11px}}
  .out-grid {{grid-template-columns:1fr}}
  .instructor-card {{flex-direction:column;text-align:center;padding:28px 24px}}
  .subsidy-grid {{grid-template-columns:1fr}}
  .form-wrap {{grid-template-columns:1fr}}
  .form-group.full {{grid-column:1}}
  .footer {{padding:32px 24px;flex-direction:column;align-items:flex-start}}
}}
</style>
</head>
<body>

<!-- ヘッダー -->
<header class="hd">
  <a href="/" class="hd-logo">
    <div class="hd-logo-mark">
      <svg viewBox="0 0 24 24"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>
    </div>
    <div class="hd-logo-text">
      <div class="en">JGAIA</div>
      <div class="ja">日本生成AI協会</div>
    </div>
  </a>
  <nav class="hd-nav">
    <a href="/">JGAIAトップ</a>
    <a href="/vibe-coding">講座概要</a>
    <a href="/vibe-coding/kids">子ども向け</a>
    <a href="/vibe-coding/industry">業種別</a>
    <a href="#inquiry">お問い合わせ</a>
  </nav>
  <div class="hd-right">
    <a href="/vibe-coding" class="btn-ghost">全コース一覧</a>
    <a href="#inquiry" class="btn-solid">お問い合わせ</a>
  </div>
</header>

<!-- ヒーロー -->
<section class="hero">
  <div class="hero-bg"></div>
  <div class="hero-grid"></div>
  <div class="hero-content">
    <div class="hero-badge">COURSE {c['code']}</div>
    <h1>{c['title']}</h1>
    <p class="hero-sub">{c['subtitle']}</p>
    <div class="hero-meta">
      <span class="hero-tag">{c['duration']}</span>
      <span class="hero-tag">{c['format']}</span>
      <span class="hero-tag">定員 {c['capacity']}</span>
      <span class="hero-tag">{c['target']}</span>
    </div>
    <div class="hero-price">
      &yen;{c['price']}<small>（税込）</small>
    </div>
    {f'<p style="margin-top:10px;font-size:13px;color:{c["accent_light"]};font-weight:500">{c["subsidy_text"]}</p>' if c["subsidy"] else ""}
  </div>
</section>

<!-- 概要 -->
<div class="overview-grid">
  <div class="ov-card">
    <div class="ov-label">DURATION</div>
    <div class="ov-val">{c['duration']}</div>
  </div>
  <div class="ov-card">
    <div class="ov-label">SCHEDULE</div>
    <div class="ov-val">{c['schedule']}</div>
  </div>
  <div class="ov-card">
    <div class="ov-label">FORMAT</div>
    <div class="ov-val">{c['format']}</div>
  </div>
  <div class="ov-card">
    <div class="ov-label">PRICE</div>
    <div class="ov-val">&yen;{c['price']}<span class="sub">{"助成金利用で実質 ¥24,800〜" if c["subsidy"] else "法人請求書払い可"}</span></div>
  </div>
</div>

<!-- カリキュラム -->
<section class="sec">
  <div class="sec-inner">
    <div class="sec-eyebrow"><span class="sec-eyebrow-line"></span>CURRICULUM</div>
    <h2 class="sec-heading">カリキュラム</h2>
    <p class="sec-sub">{c['duration']}で体系的に学ぶ実践プログラム。座学とハンズオンを交互に配置し、確実にスキルを定着させます。</p>
    <div class="cur-list">
      {curriculum_html}
    </div>
  </div>
</section>

<!-- 習得スキル -->
<section class="sec">
  <div class="sec-inner">
    <div class="sec-eyebrow"><span class="sec-eyebrow-line"></span>WHAT YOU WILL LEARN</div>
    <h2 class="sec-heading">修了後に身につくスキル</h2>
    <p class="sec-sub">本コースを修了することで、以下のスキルを即座に業務で活用できるようになります。</p>
    <div class="out-grid">
      {outcomes_html}
    </div>
  </div>
</section>

<!-- 講師 -->
<section class="sec">
  <div class="sec-inner">
    <div class="sec-eyebrow"><span class="sec-eyebrow-line"></span>INSTRUCTOR</div>
    <h2 class="sec-heading">講師紹介</h2>
    <p class="sec-sub">AI・量子コンピューティング分野の第一人者が直接指導します。</p>
    <div class="instructor-card">
      <div class="instructor-avatar">HT</div>
      <div class="instructor-info">
        <div class="instructor-name">高野 秀隆</div>
        <div class="instructor-role">一般社団法人日本生成AI協会（JGAIA）代表理事</div>
        <p class="instructor-bio">
          一般社団法人日本生成AI協会（JGAIA）代表理事。一般社団法人日本量子コンピューティング協会（JQCA）代表理事。
          株式会社長大 クオンタム推進部 部長。国家プロジェクト（SIP・NEDO）の研究開発を推進する傍ら、
          全国でAI・量子コンピューティングの人材育成に取り組む。バイブコーディングを活用した40業界対応の
          AIアプリケーション開発実績を持ち、実務に直結する講座を提供。
        </p>
      </div>
    </div>
  </div>
</section>

<!-- 助成金 -->
{subsidy_html}

<!-- FAQ -->
<section class="sec">
  <div class="sec-inner">
    <div class="sec-eyebrow"><span class="sec-eyebrow-line"></span>FAQ</div>
    <h2 class="sec-heading">よくあるご質問</h2>
    <p class="sec-sub">受講に関するよくあるご質問をまとめました。</p>
    <div class="faq-list">
      {faq_html}
    </div>
  </div>
</section>

<!-- お問い合わせフォーム -->
<section class="sec form-sec" id="inquiry">
  <div class="sec-inner">
    <div class="sec-eyebrow"><span class="sec-eyebrow-line"></span>INQUIRY</div>
    <h2 class="sec-heading">お問い合わせ・お申し込み</h2>
    <p class="sec-sub">下記フォームよりお気軽にお問い合わせください。担当者より2営業日以内にご連絡いたします。</p>
    <form id="inquiry-form" action="/api/course-inquiry" method="POST">
      <input type="hidden" name="course" value="JGAIA {c['code']}：{c['title']}">
      <div class="form-wrap">
        <div class="form-group">
          <label class="form-label">お名前<span class="req">*</span></label>
          <input class="form-input" type="text" name="name" placeholder="山田 太郎" required>
        </div>
        <div class="form-group">
          <label class="form-label">メールアドレス<span class="req">*</span></label>
          <input class="form-input" type="email" name="email" placeholder="taro@example.com" required>
        </div>
        <div class="form-group">
          <label class="form-label">会社名・団体名</label>
          <input class="form-input" type="text" name="company" placeholder="株式会社〇〇">
        </div>
        <div class="form-group">
          <label class="form-label">電話番号</label>
          <input class="form-input" type="tel" name="phone" placeholder="03-1234-5678">
        </div>
        <div class="form-group full">
          <label class="form-label">お問い合わせ内容</label>
          <textarea class="form-textarea" name="message" placeholder="ご質問・ご要望をご記入ください。受講希望日程がある場合もお知らせください。"></textarea>
        </div>
      </div>
      <button class="btn-submit" type="submit" id="submit-btn">送信する</button>
      <p class="form-note">送信後、ご入力いただいたメールアドレスに自動確認メールをお送りします。</p>
      <div id="form-msg"></div>
    </form>
  </div>
</section>

<!-- フッター -->
<footer class="footer">
  <div class="footer-brand">
    JGAIA
    <span class="ja">一般社団法人 日本生成AI協会</span>
  </div>
  <div class="footer-links">
    <a href="/">JGAIAトップ</a>
    <a href="/vibe-coding">講座概要</a>
    <a href="/vibe-coding/kids">子ども向け</a>
    <a href="/vibe-coding/industry">業種別</a>
    <a href="https://www.jgaia.org/" target="_blank">JGAIA公式サイト</a>
    <a href="mailto:info@jgaia.org">info@jgaia.org</a>
  </div>
  <div class="footer-copy">&copy; 2026 JGAIA &mdash; 一般社団法人 日本生成AI協会. All rights reserved.</div>
</footer>

<script>
document.getElementById('inquiry-form').addEventListener('submit', async function(e) {{
  e.preventDefault();
  const btn = document.getElementById('submit-btn');
  const msg = document.getElementById('form-msg');
  btn.disabled = true;
  btn.textContent = '送信中...';
  msg.style.display = 'none';

  try {{
    const formData = new FormData(this);
    const res = await fetch('/api/course-inquiry', {{
      method: 'POST',
      body: formData
    }});
    if (res.ok) {{
      msg.className = 'msg-ok';
      msg.textContent = '送信完了しました。確認メールをお送りしましたのでご確認ください。';
      msg.style.display = 'block';
      this.reset();
    }} else {{
      throw new Error('送信に失敗しました');
    }}
  }} catch (err) {{
    msg.className = 'msg-err';
    msg.textContent = '送信に失敗しました。お手数ですが info@jgaia.org まで直接ご連絡ください。';
    msg.style.display = 'block';
  }} finally {{
    btn.disabled = false;
    btn.textContent = '送信する';
  }}
}});
</script>
</body>
</html>'''


def _render_thank_you_page(course, name):
    """送信完了ページ"""
    return f'''<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>送信完了 | JGAIA バイブコーディング講座</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=Noto+Sans+JP:wght@300;400;500;700&family=DM+Sans:ital,wght@0,300;0,400;0,500;1,300&display=swap" rel="stylesheet">
<style>
:root {{
  --ink:#09090b;--text:#fafafa;--text-s:#a1a1aa;--text-m:#52525b;
  --accent:#6366f1;--accent-l:#818cf8;
  --border:rgba(255,255,255,0.07);--border-l:rgba(255,255,255,0.12);
  --font-d:'Syne','Noto Sans JP',sans-serif;
  --font:'DM Sans','Noto Sans JP',sans-serif;
  --r:4px;
}}
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
html{{font-size:16px}}
body{{
  background:var(--ink);color:var(--text);
  font-family:var(--font);
  display:flex;align-items:center;justify-content:center;
  min-height:100vh;padding:24px;
}}
.ty-card {{
  max-width:520px;width:100%;text-align:center;
  background:#111118;border:1px solid var(--border-l);
  padding:64px 48px;border-radius:8px;
}}
.ty-icon {{
  width:64px;height:64px;margin:0 auto 24px;
  border-radius:50%;
  background:rgba(34,197,94,0.15);
  display:flex;align-items:center;justify-content:center;
}}
.ty-icon svg {{color:#4ade80}}
.ty-card h1 {{
  font-family:var(--font-d);font-size:28px;font-weight:800;
  color:#fff;margin-bottom:12px;
}}
.ty-card p {{
  font-size:14px;color:var(--text-s);line-height:1.8;
  margin-bottom:8px;
}}
.ty-course {{
  display:inline-block;margin:16px 0;
  padding:8px 20px;border-radius:var(--r);
  background:rgba(99,102,241,0.15);
  color:var(--accent-l);font-size:13px;font-weight:600;
}}
.ty-actions {{
  display:flex;gap:12px;justify-content:center;margin-top:32px;
}}
.ty-actions a {{
  font-size:13px;font-weight:500;color:var(--text-s);
  padding:10px 24px;border-radius:var(--r);
  border:1px solid var(--border-l);
  transition:all .15s;
}}
.ty-actions a:hover {{color:#fff;border-color:rgba(255,255,255,0.25)}}
</style>
</head>
<body>
<div class="ty-card">
  <div class="ty-icon">
    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
      <polyline points="20 6 9 17 4 12"></polyline>
    </svg>
  </div>
  <h1>送信完了</h1>
  <p>{name} 様、お問い合わせありがとうございます。</p>
  <div class="ty-course">{course}</div>
  <p>確認メールをお送りしました。<br>担当者より2営業日以内にご連絡いたします。</p>
  <div class="ty-actions">
    <a href="/vibe-coding">講座一覧に戻る</a>
    <a href="/">JGAIAトップ</a>
  </div>
</div>
</body>
</html>'''
