"""
JGAIA バイブコーディング講座 業種特化型コース
Routes:
  GET  /vibe-coding/manufacturing  — 製造業特化型
  GET  /vibe-coding/healthcare     — 医療・ヘルスケア特化型
  GET  /vibe-coding/finance        — 金融特化型
  GET  /vibe-coding/logistics      — 物流特化型
  GET  /vibe-coding/construction   — 建設特化型
  POST /api/industry-inquiry       — お問い合わせ送信
"""
import os
from flask import Response, request, jsonify
import sendgrid
from sendgrid.helpers.mail import Mail, Email, To, Content

SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY', '')

# ─────────────────────────────────────────────────────────────
#  業界別設定データ
# ─────────────────────────────────────────────────────────────
INDUSTRIES = {
    # ─────────────────── 製造業 ───────────────────
    "manufacturing": {
        "slug": "manufacturing",
        "name": "製造業",
        "name_en": "MANUFACTURING",
        "badge": "製造特化型 | JGAIA認定",
        "title_html": "生産管理・品質検査・設備保全を、<br><em>生成AIで革新する。</em>",
        "hero_subtitle": "生産管理・品質検査・設備保全をAIで革新",
        "lead": "生成AIを活用した外観検査・需要予測・生産スケジューリングなど、製造業の現場課題を解決するアプリを自ら開発できる。工場・製造現場のDX担当者向け実戦型カリキュラム。",
        "stats": [
            {"num": "¥49,800〜", "label": "受講料（税込）"},
            {"num": "GM-A〜C", "label": "3段階コース体制"},
            {"num": "4業界", "label": "作れるアプリ例"},
            {"num": "生成AI", "label": "最先端カリキュラム"},
        ],
        "accent": "#00897b",
        "accent_rgb": "0,137,123",
        "hero_grad": "linear-gradient(160deg,#09090b 0%,#0a1a17 40%,#09090b 100%)",
        "courses": [
            {
                "code": "GM-A",
                "name": "製造業AI入門",
                "sub": "半日集中コース（4時間）",
                "concept": "AI外観検査、需要予測、生産スケジューリングの基礎",
                "target": "製造業の経営者・管理職・DX推進担当者",
                "format": "会場 + オンライン同時配信",
                "duration": "4時間（半日）",
                "capacity": "20名",
                "price": "¥49,800",
                "price_unit": "/名（税込）",
                "features": [
                    "バイブコーディング基礎・AIツール操作",
                    "AI外観検査アプリ体験＆カスタマイズ",
                    "需要予測ダッシュボードのデモ実装",
                    "生成AIプロンプト特典8種プレゼント",
                    "JGAIA認定修了証 発行",
                    "製造業×生成AIロードマップ資料付き",
                ],
                "btn_label": "GM-Aコースに申し込む",
            },
            {
                "code": "GM-B",
                "name": "製造業AIマスター",
                "sub": "3日間マスターコース",
                "concept": "設備予知保全、品質管理SPC、工程最適化の実装",
                "target": "製造業のDX推進担当・エンジニア",
                "format": "会場（少人数制）",
                "duration": "3日間（各7時間）",
                "capacity": "15名",
                "price": "¥128,000",
                "price_unit": "/名（税込）",
                "features": [
                    "主要AIコーディングツール 完全習得",
                    "設備予知保全AIアプリの開発",
                    "品質管理SPC自動化ダッシュボード構築",
                    "工程最適化エンジンの実装",
                    "生成AIプロンプト特典8種プレゼント",
                    "JGAIA認定修了証 発行",
                ],
                "btn_label": "GM-Bコースに申し込む",
            },
            {
                "code": "GM-C",
                "name": "製造業AIアーキテクト",
                "sub": "5日間エキスパートコース",
                "concept": "デジタルツイン、IoTセンサー連携、AI生産管理システム構築",
                "target": "製造業SIer・スタートアップ・社内DX推進チーム",
                "format": "会場（少人数制）",
                "duration": "5日間（各7時間）",
                "capacity": "10名",
                "price": "¥228,000",
                "price_unit": "/名（税込）",
                "features": [
                    "デジタルツイン設計・構築実践",
                    "IoTセンサーデータ×生成AI連携",
                    "AI生産管理システム設計・アーキテクチャ",
                    "本番デプロイ・運用保守体制構築",
                    "生成AIプロンプト特典8種プレゼント",
                    "JGAIA認定エキスパート修了証 発行",
                ],
                "btn_label": "GM-Cコースに申し込む",
            },
        ],
        "challenges": [
            {"icon": "🔍", "title": "品質検査の属人化", "desc": "熟練検査員の目視検査に依存。AI外観検査で24時間均一品質を実現します。"},
            {"icon": "📉", "title": "需要予測の精度不足", "desc": "勘と経験に頼る在庫計画。生成AIで過去データから高精度な需要予測モデルを構築。"},
            {"icon": "⚙️", "title": "突発的な設備故障", "desc": "計画外停止による損失。センサーデータ×AIで故障を事前予測し予防保全を実現。"},
            {"icon": "📋", "title": "生産計画の非効率", "desc": "手作業のスケジューリング。AIが制約条件を考慮し最適な生産計画を自動立案。"},
        ],
        "use_cases": [
            {"icon": "🔍", "name": "外観検査AI", "desc": "画像1枚で不良品を瞬時に検出するAI検査アプリ"},
            {"icon": "📊", "name": "需要予測ダッシュボード", "desc": "SKU別・地域別の需要変動をリアルタイム可視化"},
            {"icon": "🔧", "name": "設備故障予知システム", "desc": "センサーデータからAIが故障兆候を事前検出"},
            {"icon": "📋", "name": "生産計画最適化", "desc": "制約条件を考慮しAIが最適な工程順序を算出"},
        ],
        "prompts": [
            "AI外観検査アプリ構築プロンプト",
            "需要予測ダッシュボード生成プロンプト",
            "設備予知保全システム構築プロンプト",
            "生産スケジューリング最適化プロンプト",
            "品質管理SPC自動化プロンプト",
            "在庫最適化AIダッシュボードプロンプト",
            "IoTセンサーデータ分析プロンプト",
            "デジタルツイン設計プロンプト",
        ],
        "faqs": [
            {"q": "プログラミング経験がなくても受講できますか？",
             "a": "はい、GM-Aコースはプログラミング未経験の方向けに設計しています。AIに日本語で指示するだけでコードが生成されるバイブコーディングの仕組みから丁寧に解説します。"},
            {"q": "受講するのに必要な機材を教えてください。",
             "a": "インターネット接続可能なPC（Windows/Mac）をお持ちください。必要なソフトウェアはすべてブラウザ上で動作し、インストール不要です。"},
            {"q": "製造業以外の業種でも参加できますか？",
             "a": "本コースは製造業に特化したカリキュラムです。他業種の方は医療・金融・物流・建設分野のコースもご用意しています。"},
            {"q": "法人での複数名受講は可能ですか？",
             "a": "法人での複数名受講・出張研修も承っています。5名以上の場合はお問い合わせフォームにてご相談ください。グループ割引もご用意しています。"},
            {"q": "JGAIA認定修了証とはどのような資格ですか？",
             "a": "一般社団法人日本生成AI協会（JGAIA）が発行する修了証です。生成AIアプリ開発スキルの民間認定証明として、名刺・LinkedInへの記載に活用いただけます。"},
        ],
        "inquiry_industry": "manufacturing",
        "course_options": [
            "GM-A：製造業AI入門（半日・¥49,800）",
            "GM-B：製造業AIマスター（3日間・¥128,000）",
            "GM-C：製造業AIアーキテクト（5日間・¥228,000）",
            "出張研修（5名以上）",
            "まず話を聞きたい",
        ],
    },

    # ─────────────────── 医療・ヘルスケア ───────────────────
    "healthcare": {
        "slug": "healthcare",
        "name": "医療・ヘルスケア",
        "name_en": "HEALTHCARE",
        "badge": "医療特化型 | JGAIA認定",
        "title_html": "医療現場の業務効率化を、<br><em>生成AIで推進する。</em>",
        "hero_subtitle": "医療現場の業務効率化とAI活用を推進",
        "lead": "生成AIを活用した医療文書作成支援・患者説明資料の自動生成・診療データ分析など、医療現場の課題を解決するアプリを自ら開発できる。医療機関・製薬企業のDX担当者向け実戦型カリキュラム。",
        "stats": [
            {"num": "¥49,800〜", "label": "受講料（税込）"},
            {"num": "GH-A〜C", "label": "3段階コース体制"},
            {"num": "4業界", "label": "作れるアプリ例"},
            {"num": "生成AI", "label": "最先端カリキュラム"},
        ],
        "accent": "#e53935",
        "accent_rgb": "229,57,53",
        "hero_grad": "linear-gradient(160deg,#09090b 0%,#1a0a0a 40%,#09090b 100%)",
        "courses": [
            {
                "code": "GH-A",
                "name": "医療AI入門",
                "sub": "半日集中コース（4時間）",
                "concept": "医療文書作成支援、患者説明資料の自動生成、診療データ分析",
                "target": "医療機関の管理職・DX推進担当者",
                "format": "会場 + オンライン同時配信",
                "duration": "4時間（半日）",
                "capacity": "20名",
                "price": "¥49,800",
                "price_unit": "/名（税込）",
                "features": [
                    "バイブコーディング基礎・AIツール操作",
                    "医療文書作成AI体験＆カスタマイズ",
                    "患者説明資料の自動生成デモ",
                    "生成AIプロンプト特典8種プレゼント",
                    "JGAIA認定修了証 発行",
                    "医療×生成AIロードマップ資料付き",
                ],
                "btn_label": "GH-Aコースに申し込む",
            },
            {
                "code": "GH-B",
                "name": "ヘルスケアAIマスター",
                "sub": "3日間マスターコース",
                "concept": "電子カルテ連携、医療画像AI基礎、患者コミュニケーション最適化",
                "target": "医療機関のIT部門・医療情報技師",
                "format": "会場（少人数制）",
                "duration": "3日間（各7時間）",
                "capacity": "15名",
                "price": "¥128,000",
                "price_unit": "/名（税込）",
                "features": [
                    "主要AIコーディングツール 完全習得",
                    "電子カルテ連携AIアプリ開発",
                    "医療画像AI基礎・診断支援ツール構築",
                    "患者コミュニケーション最適化AI実装",
                    "生成AIプロンプト特典8種プレゼント",
                    "JGAIA認定修了証 発行",
                ],
                "btn_label": "GH-Bコースに申し込む",
            },
            {
                "code": "GH-C",
                "name": "ヘルスケアAIアーキテクト",
                "sub": "5日間エキスパートコース",
                "concept": "病院DXシステム設計、リモート患者モニタリング、医薬品管理AI",
                "target": "医療DX推進部門・ヘルステック・医療系SIer",
                "format": "会場（少人数制）",
                "duration": "5日間（各7時間）",
                "capacity": "10名",
                "price": "¥228,000",
                "price_unit": "/名（税込）",
                "features": [
                    "病院DXシステム設計・アーキテクチャ",
                    "リモート患者モニタリングAI構築",
                    "医薬品管理AI・在庫最適化実装",
                    "本番デプロイ・運用保守体制構築",
                    "生成AIプロンプト特典8種プレゼント",
                    "JGAIA認定エキスパート修了証 発行",
                ],
                "btn_label": "GH-Cコースに申し込む",
            },
        ],
        "challenges": [
            {"icon": "📝", "title": "文書作成の負担", "desc": "診断書・紹介状・サマリー作成に膨大な時間。生成AIで文書作成を大幅に効率化。"},
            {"icon": "🗣️", "title": "患者説明の属人化", "desc": "説明の質がドクターにより異なる。AIが患者向けにわかりやすい説明資料を自動生成。"},
            {"icon": "📅", "title": "予約管理の非効率", "desc": "キャンセル・待ち時間の問題。AIが最適な予約スケジュールを自動提案。"},
            {"icon": "💊", "title": "医薬品管理の煩雑さ", "desc": "在庫・期限・発注の手動管理。AIで医薬品在庫を最適化し廃棄ロスを削減。"},
        ],
        "use_cases": [
            {"icon": "📝", "name": "医療文書自動作成", "desc": "診断書・紹介状・退院サマリーをAIが下書き生成"},
            {"icon": "🗣️", "name": "患者説明用AI資料", "desc": "症状・治療法をわかりやすく図解した説明資料を自動作成"},
            {"icon": "📅", "name": "診療予約最適化", "desc": "AIが患者動線と診察時間を分析し最適なスケジュールを提案"},
            {"icon": "📊", "name": "健康データダッシュボード", "desc": "バイタル・検査結果をリアルタイムで可視化・トレンド分析"},
        ],
        "prompts": [
            "医療文書自動作成AIプロンプト",
            "患者説明資料生成プロンプト",
            "診療予約最適化プロンプト",
            "健康データダッシュボード構築プロンプト",
            "電子カルテ連携AIプロンプト",
            "医療画像AI分析基礎プロンプト",
            "医薬品在庫管理AI最適化プロンプト",
            "リモート患者モニタリング構築プロンプト",
        ],
        "faqs": [
            {"q": "プログラミング経験がなくても受講できますか？",
             "a": "はい、GH-Aコースはプログラミング未経験の方向けに設計しています。AIに日本語で指示するだけでアプリが作れる体験から丁寧にスタートします。"},
            {"q": "医療データのセキュリティは大丈夫ですか？",
             "a": "講座ではサンプルデータを使用し、実際の患者データは使用しません。法人出張研修では、院内セキュリティポリシーに準拠した環境構築もご支援します。"},
            {"q": "医療機関以外でも参加できますか？",
             "a": "製薬企業・医療機器メーカー・ヘルステックスタートアップの方にもご受講いただけます。他業種向けコースもご用意しています。"},
            {"q": "法人での複数名受講は可能ですか？",
             "a": "法人での複数名受講・出張研修も承っています。5名以上の場合はグループ割引もご用意しています。"},
            {"q": "JGAIA認定修了証とはどのような資格ですか？",
             "a": "一般社団法人日本生成AI協会（JGAIA）が発行する修了証です。生成AIアプリ開発スキルの民間認定証明として活用いただけます。"},
        ],
        "inquiry_industry": "healthcare",
        "course_options": [
            "GH-A：医療AI入門（半日・¥49,800）",
            "GH-B：ヘルスケアAIマスター（3日間・¥128,000）",
            "GH-C：ヘルスケアAIアーキテクト（5日間・¥228,000）",
            "法人・医療機関向け出張研修（5名以上）",
            "まず話を聞きたい",
        ],
    },

    # ─────────────────── 金融 ───────────────────
    "finance": {
        "slug": "finance",
        "name": "金融",
        "name_en": "FINANCE",
        "badge": "金融特化型 | JGAIA認定",
        "title_html": "リスク管理・レポート自動化を、<br><em>生成AIで進化させる。</em>",
        "hero_subtitle": "リスク管理・レポート自動化・顧客対応をAIで進化",
        "lead": "生成AIを活用した市場レポート自動生成・顧客対応チャットボット・コンプライアンスチェックなど、金融業界の課題を解決するアプリを自ら開発できる。証券・銀行・保険のDX担当者向け実戦型カリキュラム。",
        "stats": [
            {"num": "¥49,800〜", "label": "受講料（税込）"},
            {"num": "GF-A〜C", "label": "3段階コース体制"},
            {"num": "4業界", "label": "作れるアプリ例"},
            {"num": "生成AI", "label": "最先端カリキュラム"},
        ],
        "accent": "#1565c0",
        "accent_rgb": "21,101,192",
        "hero_grad": "linear-gradient(160deg,#09090b 0%,#090e1a 40%,#09090b 100%)",
        "courses": [
            {
                "code": "GF-A",
                "name": "金融AI入門",
                "sub": "半日集中コース（4時間）",
                "concept": "市場レポート自動生成、顧客対応チャットボット、コンプライアンスチェック",
                "target": "金融機関のDX推進担当・経営企画",
                "format": "会場 + オンライン同時配信",
                "duration": "4時間（半日）",
                "capacity": "20名",
                "price": "¥49,800",
                "price_unit": "/名（税込）",
                "features": [
                    "バイブコーディング基礎・AIツール操作",
                    "市場レポート自動生成アプリ体験",
                    "コンプライアンスチェックAIのデモ実装",
                    "生成AIプロンプト特典8種プレゼント",
                    "JGAIA認定修了証 発行",
                    "金融×生成AIロードマップ資料付き",
                ],
                "btn_label": "GF-Aコースに申し込む",
            },
            {
                "code": "GF-B",
                "name": "金融AIマスター",
                "sub": "3日間マスターコース",
                "concept": "リスク分析ダッシュボード、不正検知、審査自動化",
                "target": "証券・銀行・保険のシステム部門",
                "format": "会場（少人数制）",
                "duration": "3日間（各7時間）",
                "capacity": "15名",
                "price": "¥128,000",
                "price_unit": "/名（税込）",
                "features": [
                    "主要AIコーディングツール 完全習得",
                    "リスク分析ダッシュボード開発",
                    "不正検知AIモデルの構築・実装",
                    "審査自動化ワークフロー構築",
                    "生成AIプロンプト特典8種プレゼント",
                    "JGAIA認定修了証 発行",
                ],
                "btn_label": "GF-Bコースに申し込む",
            },
            {
                "code": "GF-C",
                "name": "金融AIアーキテクト",
                "sub": "5日間エキスパートコース",
                "concept": "ALM最適化、信用スコアリング、規制対応AI",
                "target": "フィンテック・資産運用会社・金融系SIer",
                "format": "会場（少人数制）",
                "duration": "5日間（各7時間）",
                "capacity": "10名",
                "price": "¥228,000",
                "price_unit": "/名（税込）",
                "features": [
                    "ALM最適化システム設計",
                    "信用スコアリングAIモデル構築",
                    "規制対応AIチェックシステム実装",
                    "本番デプロイ・運用保守体制構築",
                    "生成AIプロンプト特典8種プレゼント",
                    "JGAIA認定エキスパート修了証 発行",
                ],
                "btn_label": "GF-Cコースに申し込む",
            },
        ],
        "challenges": [
            {"icon": "📊", "title": "レポート作成の負担", "desc": "日次・週次の市場レポート作成に多大な工数。生成AIで自動生成し分析に集中。"},
            {"icon": "🛡️", "title": "コンプライアンス対応", "desc": "規制変更への追従が困難。AIが規制文書を解析し対応状況を自動チェック。"},
            {"icon": "🔍", "title": "不正取引の検出", "desc": "膨大なトランザクションから異常を検出。AIリアルタイム監視で不正を即座に発見。"},
            {"icon": "🤝", "title": "顧客対応の品質", "desc": "問い合わせ対応の標準化が課題。AIチャットボットで24時間均一品質の対応を実現。"},
        ],
        "use_cases": [
            {"icon": "📊", "name": "市場分析レポート自動生成", "desc": "市場データからAIが分析レポートを自動作成"},
            {"icon": "🤖", "name": "顧客対応AI", "desc": "FAQチャットボット・問い合わせ分類を自動化"},
            {"icon": "🔍", "name": "不正取引検知", "desc": "異常トランザクションをリアルタイムで検出・アラート"},
            {"icon": "✅", "name": "コンプライアンス自動チェック", "desc": "規制文書をAIが解析し対応状況を自動判定"},
        ],
        "prompts": [
            "市場分析レポート自動生成プロンプト",
            "顧客対応AIチャットボット構築プロンプト",
            "不正取引検知AIシステムプロンプト",
            "コンプライアンスチェック自動化プロンプト",
            "リスク分析ダッシュボード構築プロンプト",
            "審査自動化ワークフロープロンプト",
            "信用スコアリングモデル開発プロンプト",
            "ALM最適化システム設計プロンプト",
        ],
        "faqs": [
            {"q": "金融・プログラミングの専門知識がなくても受講できますか？",
             "a": "GF-Aコースはプログラミング・金融工学の知識不要で設計しています。AIに日本語で指示するだけで金融AIアプリが体験できます。"},
            {"q": "法令・コンプライアンス上の懸念はありますか？",
             "a": "本コースは金融商品の販売・投資勧誘を行うものではなく、あくまでアプリ開発技術の習得を目的としています。実業務への適用は各社のコンプライアンス審査のもとで行ってください。"},
            {"q": "機密情報を扱うワークショップはありますか？",
             "a": "法人向け出張研修ではNDA締結のうえ、自社データを用いたカスタマイズワークショップを提供可能です。"},
            {"q": "法人での複数名受講は可能ですか？",
             "a": "法人での複数名受講・出張研修も承っています。5名以上の場合はグループ割引もご用意しています。"},
            {"q": "JGAIA認定修了証とはどのような資格ですか？",
             "a": "一般社団法人日本生成AI協会（JGAIA）が発行する修了証です。生成AIアプリ開発スキルの民間認定証明として活用いただけます。"},
        ],
        "inquiry_industry": "finance",
        "course_options": [
            "GF-A：金融AI入門（半日・¥49,800）",
            "GF-B：金融AIマスター（3日間・¥128,000）",
            "GF-C：金融AIアーキテクト（5日間・¥228,000）",
            "法人・金融機関向け出張研修（5名以上）",
            "まず話を聞きたい",
        ],
    },

    # ─────────────────── 物流 ───────────────────
    "logistics": {
        "slug": "logistics",
        "name": "物流",
        "name_en": "LOGISTICS",
        "badge": "物流特化型 | JGAIA認定",
        "title_html": "配送最適化・倉庫管理を、<br><em>生成AIで効率化する。</em>",
        "hero_subtitle": "配送最適化・倉庫管理・需要予測をAIで効率化",
        "lead": "生成AIを活用した配送ルート最適化・在庫管理AI・需要予測など、物流業界の課題を解決するアプリを自ら開発できる。物流企業・EC・サプライチェーン担当者向け実戦型カリキュラム。",
        "stats": [
            {"num": "¥49,800〜", "label": "受講料（税込）"},
            {"num": "GL-A〜C", "label": "3段階コース体制"},
            {"num": "4業界", "label": "作れるアプリ例"},
            {"num": "生成AI", "label": "最先端カリキュラム"},
        ],
        "accent": "#ef6c00",
        "accent_rgb": "239,108,0",
        "hero_grad": "linear-gradient(160deg,#09090b 0%,#1a1005 40%,#09090b 100%)",
        "courses": [
            {
                "code": "GL-A",
                "name": "物流AI入門",
                "sub": "半日集中コース（4時間）",
                "concept": "配送ルート最適化、在庫管理AI、需要予測基礎",
                "target": "物流企業・EC・SCM担当者",
                "format": "会場 + オンライン同時配信",
                "duration": "4時間（半日）",
                "capacity": "20名",
                "price": "¥49,800",
                "price_unit": "/名（税込）",
                "features": [
                    "バイブコーディング基礎・AIツール操作",
                    "配送ルート最適化AIアプリ体験",
                    "在庫管理AIダッシュボードのデモ",
                    "生成AIプロンプト特典8種プレゼント",
                    "JGAIA認定修了証 発行",
                    "物流×生成AIロードマップ資料付き",
                ],
                "btn_label": "GL-Aコースに申し込む",
            },
            {
                "code": "GL-B",
                "name": "物流AIマスター",
                "sub": "3日間マスターコース",
                "concept": "倉庫自動化設計、サプライチェーン可視化、ラストワンマイル最適化",
                "target": "物流IT部門・EC事業者・3PL企業",
                "format": "会場（少人数制）",
                "duration": "3日間（各7時間）",
                "capacity": "15名",
                "price": "¥128,000",
                "price_unit": "/名（税込）",
                "features": [
                    "主要AIコーディングツール 完全習得",
                    "倉庫自動化AIシステム設計",
                    "サプライチェーン可視化ダッシュボード構築",
                    "ラストワンマイル最適化エンジン実装",
                    "生成AIプロンプト特典8種プレゼント",
                    "JGAIA認定修了証 発行",
                ],
                "btn_label": "GL-Bコースに申し込む",
            },
            {
                "code": "GL-C",
                "name": "物流AIアーキテクト",
                "sub": "5日間エキスパートコース",
                "concept": "物流DXプラットフォーム設計、IoT×AI統合管理",
                "target": "物流スタートアップ・SIer・SCMコンサルタント",
                "format": "会場（少人数制）",
                "duration": "5日間（各7時間）",
                "capacity": "10名",
                "price": "¥228,000",
                "price_unit": "/名（税込）",
                "features": [
                    "物流DXプラットフォーム設計・アーキテクチャ",
                    "IoTセンサー×AI統合管理システム構築",
                    "リアルタイム配送ダッシュボードAPI開発",
                    "本番デプロイ・SaaS商用化",
                    "生成AIプロンプト特典8種プレゼント",
                    "JGAIA認定エキスパート修了証 発行",
                ],
                "btn_label": "GL-Cコースに申し込む",
            },
        ],
        "challenges": [
            {"icon": "🚛", "title": "配送効率の低下", "desc": "非効率なルート設計で燃料費・人件費が増大。AIが最適な配送ルートを自動算出。"},
            {"icon": "📦", "title": "在庫管理の課題", "desc": "過剰在庫と欠品の同時発生。AIが需要予測し適正在庫を維持。"},
            {"icon": "🏭", "title": "倉庫作業の非効率", "desc": "ピッキング動線の無駄。AIがレイアウトと動線を最適化し生産性向上。"},
            {"icon": "⏱️", "title": "ラストワンマイル問題", "desc": "時間帯指定と交通状況への対応。AIが動的にルートを再計算。"},
        ],
        "use_cases": [
            {"icon": "🗺️", "name": "配送ルート最適化", "desc": "AIが交通情報・時間帯指定を考慮し最適ルートを算出"},
            {"icon": "📊", "name": "需要予測ダッシュボード", "desc": "SKU別・地域別の需要変動をリアルタイム可視化"},
            {"icon": "📦", "name": "倉庫在庫AI管理", "desc": "入出荷・在庫回転率をAIが分析し適正在庫を維持"},
            {"icon": "🚚", "name": "配車計画自動化", "desc": "車両×荷量×時間帯をAIが考慮し最適な配車を自動立案"},
        ],
        "prompts": [
            "配送ルート最適化AIプロンプト",
            "需要予測ダッシュボード構築プロンプト",
            "倉庫在庫管理AI最適化プロンプト",
            "配車計画自動化プロンプト",
            "サプライチェーン可視化プロンプト",
            "ラストワンマイル動的ルーティングプロンプト",
            "倉庫レイアウト最適化AIプロンプト",
            "IoT×AI統合物流管理プロンプト",
        ],
        "faqs": [
            {"q": "プログラミング経験がなくても受講できますか？",
             "a": "GL-Aコースはプログラミング未経験でも受講可能です。AIに日本語で指示するだけでアプリが動く体験から始めます。"},
            {"q": "自社の配送データを使ってワークショップできますか？",
             "a": "法人向け出張研修ではNDA締結のうえ、自社の配送データ・拠点情報を使ったカスタムワークショップを提供できます。"},
            {"q": "EC（通販）企業でも活用できますか？",
             "a": "EC企業向けの在庫最適化・ラストワンマイル最適化の内容も含まれています。物流子会社・3PLの方にも最適です。"},
            {"q": "法人での複数名受講は可能ですか？",
             "a": "法人での複数名受講・出張研修も承っています。5名以上の場合はグループ割引もご用意しています。"},
            {"q": "JGAIA認定修了証とはどのような資格ですか？",
             "a": "一般社団法人日本生成AI協会（JGAIA）が発行する修了証です。生成AIアプリ開発スキルの民間認定証明として活用いただけます。"},
        ],
        "inquiry_industry": "logistics",
        "course_options": [
            "GL-A：物流AI入門（半日・¥49,800）",
            "GL-B：物流AIマスター（3日間・¥128,000）",
            "GL-C：物流AIアーキテクト（5日間・¥228,000）",
            "法人・物流企業向け出張研修（5名以上）",
            "まず話を聞きたい",
        ],
    },

    # ─────────────────── 建設 ───────────────────
    "construction": {
        "slug": "construction",
        "name": "建設",
        "name_en": "CONSTRUCTION",
        "badge": "建設特化型 | JGAIA認定",
        "title_html": "施工管理・安全管理・積算を、<br><em>生成AIで革新する。</em>",
        "hero_subtitle": "施工管理・安全管理・積算をAIで革新",
        "lead": "生成AIを活用した日報自動化・安全パトロールAI・積算支援など、建設業界の課題を解決するアプリを自ら開発できる。ゼネコン・サブコン・設計事務所のDX担当者向け実戦型カリキュラム。",
        "stats": [
            {"num": "¥49,800〜", "label": "受講料（税込）"},
            {"num": "GN-A〜C", "label": "3段階コース体制"},
            {"num": "4業界", "label": "作れるアプリ例"},
            {"num": "生成AI", "label": "最先端カリキュラム"},
        ],
        "accent": "#5d4037",
        "accent_rgb": "93,64,55",
        "hero_grad": "linear-gradient(160deg,#09090b 0%,#140e0b 40%,#09090b 100%)",
        "courses": [
            {
                "code": "GN-A",
                "name": "建設AI入門",
                "sub": "半日集中コース（4時間）",
                "concept": "日報自動化、安全パトロールAI、積算支援",
                "target": "建設業の経営者・現場監督・DX推進担当者",
                "format": "会場 + オンライン同時配信",
                "duration": "4時間（半日）",
                "capacity": "20名",
                "price": "¥49,800",
                "price_unit": "/名（税込）",
                "features": [
                    "バイブコーディング基礎・AIツール操作",
                    "施工日報AI自動化アプリ体験",
                    "安全パトロールAIカメラのデモ",
                    "生成AIプロンプト特典8種プレゼント",
                    "JGAIA認定修了証 発行",
                    "建設×生成AIロードマップ資料付き",
                ],
                "btn_label": "GN-Aコースに申し込む",
            },
            {
                "code": "GN-B",
                "name": "建設AIマスター",
                "sub": "3日間マスターコース",
                "concept": "BIM×AI連携、工程管理AI、品質検査自動化",
                "target": "建設業のIT部門・BIM担当者・施工管理技士",
                "format": "会場（少人数制）",
                "duration": "3日間（各7時間）",
                "capacity": "15名",
                "price": "¥128,000",
                "price_unit": "/名（税込）",
                "features": [
                    "主要AIコーディングツール 完全習得",
                    "BIM×AI連携アプリ開発",
                    "工程管理AIダッシュボード構築",
                    "品質検査自動化システム実装",
                    "生成AIプロンプト特典8種プレゼント",
                    "JGAIA認定修了証 発行",
                ],
                "btn_label": "GN-Bコースに申し込む",
            },
            {
                "code": "GN-C",
                "name": "建設AIアーキテクト",
                "sub": "5日間エキスパートコース",
                "concept": "建設DX統合プラットフォーム、ドローン×AI検査、i-Construction対応",
                "target": "ゼネコンDX推進部門・建設テック・設計事務所",
                "format": "会場（少人数制）",
                "duration": "5日間（各7時間）",
                "capacity": "10名",
                "price": "¥228,000",
                "price_unit": "/名（税込）",
                "features": [
                    "建設DX統合プラットフォーム設計",
                    "ドローン×AI検査システム構築",
                    "i-Construction対応AI実装",
                    "本番デプロイ・運用保守体制構築",
                    "生成AIプロンプト特典8種プレゼント",
                    "JGAIA認定エキスパート修了証 発行",
                ],
                "btn_label": "GN-Cコースに申し込む",
            },
        ],
        "challenges": [
            {"icon": "📋", "title": "日報・書類作成の負担", "desc": "毎日の施工日報、安全書類の作成に多大な時間。AIで自動化し現場業務に集中。"},
            {"icon": "⚠️", "title": "安全管理の限界", "desc": "広大な現場の安全確認は人手に限界。AIカメラが危険行動・不備を即座に検知。"},
            {"icon": "💰", "title": "積算の属人化", "desc": "経験者しかできない積算業務。AIが図面から数量を自動算出し精度と速度を向上。"},
            {"icon": "📅", "title": "工程遅延リスク", "desc": "天候・資材・人員の変動への対応。AIが工程を動的に再計算し遅延を最小化。"},
        ],
        "use_cases": [
            {"icon": "📋", "name": "施工日報AI自動化", "desc": "写真・音声メモからAIが施工日報を自動生成"},
            {"icon": "📷", "name": "安全管理AIカメラ", "desc": "現場映像からAIが危険行動・保護具未着用を即座に検知"},
            {"icon": "💰", "name": "積算AI支援", "desc": "図面データからAIが数量を自動算出し見積精度を向上"},
            {"icon": "📊", "name": "工程管理ダッシュボード", "desc": "リアルタイムで工程進捗を可視化・遅延リスクを予測"},
        ],
        "prompts": [
            "施工日報AI自動生成プロンプト",
            "安全管理AIカメラシステム構築プロンプト",
            "積算AI支援システムプロンプト",
            "工程管理ダッシュボード構築プロンプト",
            "BIM×AI連携アプリ開発プロンプト",
            "品質検査自動化AIプロンプト",
            "ドローン×AI検査システムプロンプト",
            "i-Construction対応AI実装プロンプト",
        ],
        "faqs": [
            {"q": "プログラミング経験がなくても受講できますか？",
             "a": "はい、GN-Aコースはプログラミング未経験の方向けに設計しています。AIに日本語で指示するだけでアプリが作れる体験からスタートします。"},
            {"q": "現場で使えるアプリが本当に作れますか？",
             "a": "はい、講座内でスマホ対応の施工日報アプリや安全チェックアプリを実際に作成し、クラウドにデプロイして持ち帰れます。"},
            {"q": "建設業以外の業種でも参加できますか？",
             "a": "本コースは建設業に特化したカリキュラムです。他業種の方は製造業・医療・金融・物流分野のコースもご用意しています。"},
            {"q": "法人での複数名受講は可能ですか？",
             "a": "法人での複数名受講・出張研修も承っています。5名以上の場合はグループ割引もご用意しています。"},
            {"q": "JGAIA認定修了証とはどのような資格ですか？",
             "a": "一般社団法人日本生成AI協会（JGAIA）が発行する修了証です。生成AIアプリ開発スキルの民間認定証明として活用いただけます。"},
        ],
        "inquiry_industry": "construction",
        "course_options": [
            "GN-A：建設AI入門（半日・¥49,800）",
            "GN-B：建設AIマスター（3日間・¥128,000）",
            "GN-C：建設AIアーキテクト（5日間・¥228,000）",
            "法人・建設企業向け出張研修（5名以上）",
            "まず話を聞きたい",
        ],
    },
}


# ─────────────────────────────────────────────────────────────
#  HTML テンプレート（共通）
# ─────────────────────────────────────────────────────────────
def _render_industry_page(ind):
    c = ind
    accent = c["accent"]
    accent_rgb = c["accent_rgb"]
    # JGAIA brand indigo
    brand = "#6366f1"
    brand_rgb = "99,102,241"
    brand_light = "#818cf8"

    # コースカード3色パレット
    palette = [
        {"accent": accent, "rgb": accent_rgb,
         "grad": f"linear-gradient(135deg,{accent}18,{brand}18)",
         "border": f"rgba({accent_rgb},0.25)",
         "check": accent,
         "btn_grad": f"linear-gradient(135deg,{accent},{brand})"},
        {"accent": brand, "rgb": brand_rgb,
         "grad": f"linear-gradient(135deg,{brand}18,{accent}18)",
         "border": f"rgba({brand_rgb},0.25)",
         "check": brand,
         "btn_grad": f"linear-gradient(135deg,{brand},{accent})"},
        {"accent": brand_light, "rgb": "129,140,248",
         "grad": "linear-gradient(135deg,#6366f118,#818cf818)",
         "border": "rgba(129,140,248,0.25)",
         "check": brand_light,
         "btn_grad": f"linear-gradient(135deg,{brand},{brand_light})"},
    ]

    # ---------- コースカード HTML ----------
    course_cards_html = ""
    for i, course in enumerate(c["courses"]):
        p = palette[i]
        # Aコース（4時間）のみ事業外スキルアップ助成金対象
        subsidy_badge_html = ""
        if i == 0:
            subsidy_badge_html = (
                '<div style="margin:0 0 14px;background:rgba(16,185,129,0.12);border:1px solid rgba(16,185,129,0.35);'
                'border-radius:10px;padding:10px 14px;font-size:0.82rem;font-weight:700;color:#10b981;">'
                '&#10003; 東京しごと財団 助成金対象（4時間）'
                '<br><span style="font-weight:500;font-size:0.78rem;color:rgba(255,255,255,0.7);">'
                '実質 &#165;24,800&#12316; / 人（助成金利用時）</span></div>'
            )
        feat_items = "".join(
            f'<li style="border-bottom:1px solid rgba(255,255,255,0.06);padding:7px 0;display:flex;'
            f'align-items:center;gap:8px;font-size:0.88rem;color:rgba(255,255,255,0.8);">'
            f'<span style="color:{p["check"]};font-weight:900;flex-shrink:0;">&#10003;</span>{f}</li>'
            for f in course["features"]
        )
        meta_items = f"""
          <div style="background:rgba(255,255,255,0.05);border-radius:10px;padding:10px 12px;">
            <div style="font-size:0.7rem;color:rgba(255,255,255,0.45);margin-bottom:2px;">対象</div>
            <div style="font-size:0.82rem;font-weight:700;color:#fff;">{course["target"]}</div>
          </div>
          <div style="background:rgba(255,255,255,0.05);border-radius:10px;padding:10px 12px;">
            <div style="font-size:0.7rem;color:rgba(255,255,255,0.45);margin-bottom:2px;">形式</div>
            <div style="font-size:0.82rem;font-weight:700;color:#fff;">{course["format"]}</div>
          </div>
          <div style="background:rgba(255,255,255,0.05);border-radius:10px;padding:10px 12px;">
            <div style="font-size:0.7rem;color:rgba(255,255,255,0.45);margin-bottom:2px;">期間</div>
            <div style="font-size:0.82rem;font-weight:700;color:#fff;">{course["duration"]}</div>
          </div>
          <div style="background:rgba(255,255,255,0.05);border-radius:10px;padding:10px 12px;">
            <div style="font-size:0.7rem;color:rgba(255,255,255,0.45);margin-bottom:2px;">定員</div>
            <div style="font-size:0.82rem;font-weight:700;color:#fff;">{course["capacity"]}</div>
          </div>
        """
        course_cards_html += f"""
        <div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);border-radius:24px;
          overflow:hidden;transition:transform 0.3s,box-shadow 0.3s;display:flex;flex-direction:column;"
          onmouseenter="this.style.transform='translateY(-6px)';this.style.boxShadow='0 24px 48px rgba(0,0,0,0.4)'"
          onmouseleave="this.style.transform='';this.style.boxShadow=''">
          <div style="height:5px;background:{p['btn_grad']};"></div>
          <div style="padding:24px 24px 14px;background:{p['grad']};border-bottom:1px solid {p['border']};">
            <div style="font-size:0.72rem;font-weight:800;letter-spacing:0.15em;color:{p['accent']};margin-bottom:6px;">
              {course["code"]}</div>
            <h3 style="font-size:1.3rem;font-weight:900;line-height:1.3;margin-bottom:4px;color:#fff;">
              {course["name"]}</h3>
            <div style="font-size:0.82rem;color:rgba(255,255,255,0.6);margin-bottom:8px;">{course["sub"]}</div>
            <div style="font-size:0.8rem;color:rgba(255,255,255,0.5);font-style:italic;">{course["concept"]}</div>
          </div>
          <div style="padding:20px 24px 28px;flex:1;display:flex;flex-direction:column;">
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:18px;">
              {meta_items}</div>
            {subsidy_badge_html}
            <div style="font-size:2rem;font-weight:900;color:{p['accent']};margin-bottom:4px;">
              {course["price"]}<span style="font-size:0.8rem;font-weight:400;color:rgba(255,255,255,0.5);">
              {course["price_unit"]}</span></div>
            <ul style="list-style:none;margin:0 0 20px;padding:0;flex:1;">{feat_items}</ul>
            <a href="#inquiry" style="display:block;text-align:center;padding:14px;border-radius:14px;
              font-weight:800;font-size:0.92rem;text-decoration:none;color:#fff;background:{p['btn_grad']};
              transition:opacity 0.2s;" onmouseenter="this.style.opacity='0.85'"
              onmouseleave="this.style.opacity='1'">{course["btn_label"]}</a>
          </div>
        </div>
        """

    # ---------- 業界課題 HTML ----------
    challenge_cards_html = ""
    for ch in c["challenges"]:
        challenge_cards_html += (
            f'<div style="background:rgba(255,255,255,0.04);border:1px solid rgba({accent_rgb},0.18);'
            f'border-radius:20px;padding:32px 28px;transition:border-color 0.3s,transform 0.3s;"'
            f' onmouseenter="this.style.borderColor=\'rgba({accent_rgb},0.4)\';this.style.transform=\'translateY(-4px)\'"'
            f' onmouseleave="this.style.borderColor=\'rgba({accent_rgb},0.18)\';this.style.transform=\'\'">'
            f'<div style="font-size:2.4rem;margin-bottom:14px;">{ch["icon"]}</div>'
            f'<h3 style="font-size:1.05rem;font-weight:800;margin-bottom:8px;color:#fff;">{ch["title"]}</h3>'
            f'<p style="font-size:0.88rem;color:rgba(255,255,255,0.6);line-height:1.8;">{ch["desc"]}</p>'
            f'</div>'
        )

    # ---------- ユースケースカード HTML ----------
    use_case_cards_html = ""
    for uc in c["use_cases"]:
        use_case_cards_html += (
            f'<div style="background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);'
            f'border-radius:16px;padding:22px 18px;text-align:center;transition:border-color 0.3s;"'
            f' onmouseenter="this.style.borderColor=\'rgba({accent_rgb},0.35)\'"'
            f' onmouseleave="this.style.borderColor=\'rgba(255,255,255,0.08)\'">'
            f'<div style="font-size:2.4rem;margin-bottom:12px;">{uc["icon"]}</div>'
            f'<h4 style="font-size:0.9rem;font-weight:800;margin-bottom:6px;color:#fff;">{uc["name"]}</h4>'
            f'<p style="font-size:0.8rem;color:rgba(255,255,255,0.55);line-height:1.6;">{uc["desc"]}</p>'
            f'</div>'
        )

    # ---------- プロンプト特典 HTML ----------
    prompt_items_html = ""
    for i, pr in enumerate(c["prompts"]):
        prompt_items_html += (
            f'<div style="background:rgba(255,255,255,0.04);border:1px solid rgba({accent_rgb},0.18);'
            f'border-radius:14px;padding:16px 20px;display:flex;align-items:center;gap:14px;">'
            f'<div style="width:32px;height:32px;border-radius:50%;'
            f'background:linear-gradient(135deg,{accent},{brand});display:flex;align-items:center;'
            f'justify-content:center;font-size:0.8rem;font-weight:900;flex-shrink:0;color:#fff;">'
            f'{i+1:02d}</div>'
            f'<span style="font-size:0.9rem;color:rgba(255,255,255,0.85);">{pr}</span>'
            f'</div>'
        )

    # ---------- FAQ HTML ----------
    faq_items_html = ""
    for faq in c["faqs"]:
        faq_items_html += f"""
        <div class="faq-item" style="border-bottom:1px solid rgba(255,255,255,0.08);">
          <button class="faq-q" onclick="toggleFaq(this)"
            style="width:100%;background:none;border:none;color:#fff;text-align:left;padding:22px 0;
            font-size:0.98rem;font-weight:700;cursor:pointer;display:flex;justify-content:space-between;
            align-items:center;gap:16px;font-family:inherit;">
            <span>{faq["q"]}</span>
            <span class="faq-icon" style="font-size:1.4rem;color:{accent};flex-shrink:0;
              transition:transform 0.3s;">+</span>
          </button>
          <div class="faq-a" style="display:none;padding:0 0 20px;font-size:0.9rem;
            color:rgba(255,255,255,0.65);line-height:1.85;">{faq["a"]}</div>
        </div>
        """

    # ---------- コース選択 options ----------
    course_opts_html = "".join(
        f'<option value="{o}">{o}</option>' for o in c["course_options"]
    )

    # ---------- スタッツ HTML ----------
    stats_html = "".join(
        f'<div style="text-align:center;">'
        f'<div style="font-size:1.8rem;font-weight:900;color:{accent};line-height:1;">{s["num"]}</div>'
        f'<div style="font-size:0.75rem;color:rgba(255,255,255,0.6);margin-top:4px;">{s["label"]}</div>'
        f'</div>'
        for s in c["stats"]
    )

    # ---------- TRUST セクション ----------
    ind_name = c["name"]
    trust_items = [
        ("&#9889;", "生成AI活用の実績に基づくカリキュラム",
         f"JGAIAが企業向けに提供してきた生成AI活用の知見を凝縮。{ind_name}分野の実務課題に直結するカリキュラムです。"),
        ("&#127942;", "JGAIA認定修了証 発行",
         f"一般社団法人日本生成AI協会が発行するJGAIA認定修了証。LinkedInや名刺に記載でき、{ind_name}×生成AIスキルの証明になります。"),
        ("&#127873;", "生成AIプロンプト特典8種",
         f"{ind_name}分野特化の生成AI＆アプリ構築プロンプトを特典として提供。他講座では手に入らないJGAIA独自コンテンツです。"),
        ("&#128105;&#8205;&#127979;", "少人数制・現役実務家が指導",
         "最大20名の少人数制。生成AI専門家とAIエンジニアが丁寧に指導します。"),
        ("&#128640;", "当日中に本番デプロイ",
         "作ったアプリをクラウドで即日デプロイ。「作っておしまい」ではなく、実際に動くサービスとして持ち帰れます。"),
        ("&#127970;", "法人・出張研修対応",
         "5名以上の場合は社内出張研修（NDA対応可）も承ります。自社データを使ったカスタム版カリキュラムも設計します。"),
    ]
    trust_html = ""
    for t_icon, t_title, t_desc in trust_items:
        trust_html += (
            f'<div style="display:flex;gap:16px;align-items:flex-start;background:rgba(255,255,255,0.03);'
            f'border:1px solid rgba(255,255,255,0.08);border-radius:18px;padding:26px 22px;">'
            f'<div style="font-size:1.8rem;flex-shrink:0;width:48px;height:48px;display:flex;align-items:center;'
            f'justify-content:center;border-radius:13px;background:rgba({accent_rgb},0.12);">{t_icon}</div>'
            f'<div><h4 style="font-size:0.95rem;font-weight:800;margin-bottom:6px;color:#fff;">{t_title}</h4>'
            f'<p style="font-size:0.84rem;color:rgba(255,255,255,0.6);line-height:1.75;">{t_desc}</p>'
            f'</div></div>'
        )

    # ---------- 他業界リンク ----------
    all_industries = [
        ("manufacturing",  "&#127981;", "製造業",         "生産管理・品質検査・設備保全"),
        ("healthcare",     "&#127973;", "医療・ヘルスケア", "医療文書・患者説明・診療データ"),
        ("finance",        "&#128200;", "金融",           "リスク管理・レポート・コンプライアンス"),
        ("logistics",      "&#128666;", "物流",           "配送最適化・倉庫管理・需要予測"),
        ("construction",   "&#127959;", "建設",           "施工管理・安全管理・積算"),
    ]
    other_ind_html = ""
    for o_slug, o_icon, o_name, o_sub in all_industries:
        if o_slug == c["slug"]:
            continue
        other_ind_html += (
            f'<a href="/vibe-coding/{o_slug}" style="display:block;background:rgba(255,255,255,0.04);'
            f'border:1px solid rgba(255,255,255,0.1);border-radius:16px;padding:22px 18px;text-align:center;'
            f'text-decoration:none;color:#fff;transition:border-color 0.3s,transform 0.3s;"'
            f' onmouseenter="this.style.borderColor=\'rgba(255,255,255,0.3)\';this.style.transform=\'translateY(-3px)\'"'
            f' onmouseleave="this.style.borderColor=\'rgba(255,255,255,0.1)\';this.style.transform=\'\'">'
            f'<div style="font-size:2.2rem;margin-bottom:10px;">{o_icon}</div>'
            f'<div style="font-weight:800;font-size:0.95rem;margin-bottom:4px;">{o_name}</div>'
            f'<div style="font-size:0.78rem;color:rgba(255,255,255,0.5);">{o_sub}</div>'
            f'</a>'
        )
    other_ind_html += (
        '<a href="/vibe-coding" style="display:block;background:rgba(255,255,255,0.04);'
        'border:1px solid rgba(255,255,255,0.1);border-radius:16px;padding:22px 18px;text-align:center;'
        'text-decoration:none;color:#fff;transition:border-color 0.3s,transform 0.3s;"'
        ' onmouseenter="this.style.borderColor=\'rgba(255,255,255,0.3)\';this.style.transform=\'translateY(-3px)\'"'
        ' onmouseleave="this.style.borderColor=\'rgba(255,255,255,0.1)\';this.style.transform=\'\'">'
        '<div style="font-size:2.2rem;margin-bottom:10px;">&#128203;</div>'
        '<div style="font-weight:800;font-size:0.95rem;margin-bottom:4px;">全コース一覧</div>'
        '<div style="font-size:0.78rem;color:rgba(255,255,255,0.5);">汎用コースも含む</div>'
        '</a>'
    )

    # ---------- 完成HTML ----------
    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{c["name"]}特化型バイブコーディング認定講座 | JGAIA認定 生成AI開発スキル</title>
<meta name="description" content="{c["name"]}分野の生成AIアプリ開発スキルをゼロから習得。JGAIA認定修了証発行。プロンプト特典付き。">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=DM+Sans:wght@400;500;700&family=Noto+Sans+JP:wght@400;500;700;900&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  html {{ scroll-behavior: smooth; }}
  body {{ font-family: 'DM Sans', 'Noto Sans JP', sans-serif; background: #09090b; color: #fff; line-height: 1.7; }}
  h1, h2, h3 {{ font-family: 'Syne', 'Noto Sans JP', sans-serif; }}

  /* ─── Nav ─── */
  nav {{ position: fixed; top: 0; left: 0; right: 0; z-index: 100;
    background: rgba(9,9,11,0.92); backdrop-filter: blur(16px);
    border-bottom: 1px solid rgba(255,255,255,0.06); padding: 0 32px;
    height: 64px; display: flex; align-items: center; justify-content: space-between; }}
  .nav-logo {{ display: flex; align-items: center; gap: 10px; text-decoration: none; }}
  .nav-logo span {{ font-size: 0.9rem; font-weight: 700; color: #fff;
    font-family: 'Syne', sans-serif; }}
  .nav-links {{ display: flex; gap: 24px; list-style: none; }}
  .nav-links a {{ color: rgba(255,255,255,0.6); text-decoration: none;
    font-size: 0.88rem; transition: color 0.2s; }}
  .nav-links a:hover {{ color: #fff; }}
  .nav-cta {{ background: linear-gradient(135deg, {brand}, {accent});
    color: #fff; padding: 8px 20px; border-radius: 24px; text-decoration: none;
    font-size: 0.85rem; font-weight: 700; transition: opacity 0.2s; }}
  .nav-cta:hover {{ opacity: 0.85; }}

  /* ─── Sections ─── */
  section {{ padding: 88px 24px; }}
  .section-inner {{ max-width: 1100px; margin: 0 auto; }}
  .section-label {{ display: inline-block; font-size: 0.72rem; font-weight: 800;
    letter-spacing: 0.15em; padding: 5px 14px; border-radius: 20px; margin-bottom: 14px;
    background: rgba({accent_rgb},0.15); color: {accent};
    font-family: 'Syne', sans-serif; }}
  .section-title {{ font-size: clamp(1.7rem, 3.5vw, 2.4rem); font-weight: 900;
    line-height: 1.25; letter-spacing: -0.02em; margin-bottom: 14px; }}
  .section-lead {{ color: rgba(255,255,255,0.65); font-size: 1rem;
    line-height: 1.85; max-width: 600px; }}
  .text-center {{ text-align: center; }}
  .text-center .section-lead {{ margin: 0 auto; }}

  /* ─── Footer ─── */
  footer {{ background: #050506; padding: 48px 24px; text-align: center;
    border-top: 1px solid rgba(255,255,255,0.06); }}
  footer p {{ font-size: 0.8rem; color: rgba(255,255,255,0.35); margin-top: 8px; }}
  footer a {{ color: rgba(255,255,255,0.5); text-decoration: none; }}
  footer a:hover {{ color: #fff; }}

  /* ─── Form ─── */
  .form-group {{ margin-bottom: 20px; }}
  .form-group label {{ display: block; font-size: 0.85rem; font-weight: 700;
    color: rgba(255,255,255,0.8); margin-bottom: 8px; }}
  .form-group label span {{ color: #818cf8; margin-left: 4px; }}
  .form-group input, .form-group select, .form-group textarea {{
    width: 100%; background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.1); border-radius: 10px;
    padding: 12px 16px; color: #fff; font-size: 0.92rem;
    font-family: inherit; outline: none; transition: border-color 0.2s; }}
  .form-group input:focus, .form-group select:focus, .form-group textarea:focus {{
    border-color: rgba({accent_rgb},0.5); }}
  .form-group textarea {{ height: 100px; resize: vertical; }}
  .form-group select option {{ background: #18181b; }}

  /* ─── Responsive ─── */
  @media (max-width: 1024px) {{
    .course-grid {{ grid-template-columns: 1fr !important; }}
    .trust-grid {{ grid-template-columns: repeat(2,1fr) !important; }}
    .challenge-grid {{ grid-template-columns: repeat(2,1fr) !important; }}
  }}
  @media (max-width: 768px) {{
    .course-grid {{ grid-template-columns: 1fr !important; }}
    .uc-grid {{ grid-template-columns: repeat(2,1fr) !important; }}
    .trust-grid {{ grid-template-columns: 1fr !important; }}
    .challenge-grid {{ grid-template-columns: 1fr !important; }}
    .prompt-grid {{ grid-template-columns: 1fr !important; }}
    .other-grid {{ grid-template-columns: repeat(2,1fr) !important; }}
    .nav-links {{ display: none; }}
    .stats-row {{ gap: 20px !important; flex-wrap: wrap; }}
    .subsidy-cols {{ grid-template-columns: 1fr !important; }}
  }}
</style>
</head>
<body>

<!-- ═══════════ NAV ═══════════ -->
<nav>
  <a class="nav-logo" href="/vibe-coding">
    <span style="font-size:1.1rem;font-weight:900;background:linear-gradient(135deg,{brand},{brand_light});
      -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;">JGAIA</span>
    <span>{c["name"]}特化型 バイブコーディング</span>
  </a>
  <ul class="nav-links">
    <li><a href="#courses">コース</a></li>
    <li><a href="#prompts">プロンプト特典</a></li>
    <li><a href="#faq">FAQ</a></li>
    <li><a href="/vibe-coding">全コース一覧</a></li>
  </ul>
  <a href="#inquiry" class="nav-cta">無料相談する</a>
</nav>

<!-- ═══════════ HERO ═══════════ -->
<section style="position:relative;min-height:100vh;display:flex;align-items:center;justify-content:center;
  text-align:center;overflow:hidden;padding:100px 24px 80px;background:#09090b;">
  <div style="position:absolute;inset:0;background:{c["hero_grad"]};"></div>
  <!-- Grid overlay -->
  <div style="position:absolute;inset:0;
    background-image:linear-gradient(rgba({accent_rgb},0.04) 1px,transparent 1px),
    linear-gradient(90deg,rgba({accent_rgb},0.04) 1px,transparent 1px);
    background-size:60px 60px;pointer-events:none;"></div>
  <!-- Particle canvas -->
  <canvas id="particles" style="position:absolute;inset:0;pointer-events:none;opacity:0.35;"></canvas>
  <!-- Glow orbs -->
  <div style="position:absolute;top:18%;left:12%;width:420px;height:420px;
    background:radial-gradient(circle,rgba({accent_rgb},0.12) 0%,transparent 70%);
    pointer-events:none;border-radius:50%;"></div>
  <div style="position:absolute;bottom:12%;right:8%;width:380px;height:380px;
    background:radial-gradient(circle,rgba({brand_rgb},0.10) 0%,transparent 70%);
    pointer-events:none;border-radius:50%;"></div>

  <div style="position:relative;z-index:1;max-width:860px;margin:0 auto;">
    <div style="display:inline-flex;align-items:center;gap:8px;
      background:rgba({accent_rgb},0.12);border:1px solid rgba({accent_rgb},0.3);
      color:{accent};padding:6px 18px;border-radius:24px;font-size:0.8rem;font-weight:700;
      letter-spacing:0.08em;margin-bottom:28px;font-family:'Syne',sans-serif;">
      JGAIA INDUSTRY PROGRAM
    </div>
    <h1 style="font-size:clamp(2.2rem,6vw,4rem);font-weight:900;line-height:1.2;
      letter-spacing:-0.02em;margin-bottom:24px;">
      {c["title_html"].replace("<em>", f'<em style="font-style:normal;background:linear-gradient(135deg,{accent},{brand});-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;">')}
    </h1>
    <p style="font-size:clamp(1rem,2vw,1.15rem);color:rgba(255,255,255,0.75);
      max-width:640px;margin:0 auto 40px;line-height:1.85;">{c["lead"]}</p>
    <div style="display:flex;gap:16px;justify-content:center;flex-wrap:wrap;margin-bottom:56px;">
      <a href="#courses" style="background:linear-gradient(135deg,{accent},{brand});color:#fff;
        padding:16px 36px;border-radius:40px;text-decoration:none;font-weight:800;font-size:1.05rem;
        box-shadow:0 8px 32px rgba({accent_rgb},0.30);transition:transform 0.2s,box-shadow 0.2s;"
        onmouseenter="this.style.transform='translateY(-2px)';this.style.boxShadow='0 12px 40px rgba({accent_rgb},0.4)'"
        onmouseleave="this.style.transform='';this.style.boxShadow='0 8px 32px rgba({accent_rgb},0.30)'">
        コースを見る</a>
      <a href="#inquiry" style="background:rgba(255,255,255,0.08);border:1px solid rgba(255,255,255,0.2);
        color:#fff;padding:16px 36px;border-radius:40px;text-decoration:none;font-weight:700;
        font-size:1.05rem;transition:background 0.2s;"
        onmouseenter="this.style.background='rgba(255,255,255,0.14)'"
        onmouseleave="this.style.background='rgba(255,255,255,0.08)'">
        無料相談はこちら</a>
    </div>
    <div class="stats-row" style="display:flex;gap:32px;justify-content:center;flex-wrap:wrap;
      padding-top:40px;border-top:1px solid rgba(255,255,255,0.1);">
      {stats_html}
    </div>
  </div>
</section>

<!-- ═══════════ INDUSTRY CHALLENGES ═══════════ -->
<section style="background:linear-gradient(180deg,#09090b 0%,#0f0f14 100%);padding:88px 24px;">
  <div class="section-inner">
    <div class="text-center">
      <span class="section-label">{c["name_en"]} CHALLENGES</span>
      <h2 class="section-title">{c["name"]}が抱える課題をAIで解決</h2>
      <p class="section-lead">{c["name"]}業界の現場が直面する課題に、生成AIアプリ開発で挑みます。</p>
    </div>
    <div class="challenge-grid" style="display:grid;grid-template-columns:repeat(4,1fr);gap:24px;margin-top:56px;">
      {challenge_cards_html}
    </div>
  </div>
</section>

<!-- ═══════════ USE CASES ═══════════ -->
<section style="background:#09090b;padding:88px 24px;">
  <div class="section-inner">
    <div class="text-center">
      <span class="section-label">USE CASES</span>
      <h2 class="section-title">こんな{c["name"]}AIアプリが作れる</h2>
      <p class="section-lead">受講後に開発できるアプリの例です。すべて生成AIを活用した実用的なプロダクトです。</p>
    </div>
    <div class="uc-grid" style="display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-top:48px;">
      {use_case_cards_html}
    </div>
  </div>
</section>

<!-- ═══════════ COURSES ═══════════ -->
<section id="courses" style="background:linear-gradient(180deg,#0c0c10 0%,#09090b 100%);padding:88px 24px;">
  <div class="section-inner">
    <div class="text-center">
      <span class="section-label">COURSES</span>
      <h2 class="section-title">{c["name"]}特化型 3段階コース</h2>
      <p class="section-lead">入門から本格システム構築まで。{c["name"]}業界の実務課題に特化したカリキュラムで、着実にスキルを積み上げます。</p>
    </div>
    <div class="course-grid" style="display:grid;grid-template-columns:repeat(3,1fr);gap:28px;margin-top:56px;">
      {course_cards_html}
    </div>

    <!-- 特典ノート -->
    <div style="margin-top:40px;background:rgba({accent_rgb},0.08);border:1px solid rgba({accent_rgb},0.2);
      border-radius:18px;padding:28px 32px;display:flex;align-items:flex-start;gap:18px;">
      <div style="font-size:2rem;flex-shrink:0;">&#127873;</div>
      <div>
        <h3 style="font-size:1.05rem;font-weight:800;color:{accent};margin-bottom:6px;">
          全コース共通：生成AIプロンプト特典8種付き</h3>
        <p style="font-size:0.9rem;color:rgba(255,255,255,0.72);line-height:1.8;">
          {c["name"]}分野に特化した生成AI＆アプリ構築プロンプトを8種セットでプレゼント。
          講座終了後もすぐに実務へ応用できます。他のバイブコーディング講座では手に入らないJGAIA独自の差別化特典です。</p>
      </div>
    </div>

    <!-- 助成金バナー -->
    <div style="margin-top:28px;background:rgba(16,185,129,0.06);border:2px solid rgba(16,185,129,0.22);
      border-radius:18px;padding:28px 32px;">
      <div style="display:flex;align-items:flex-start;gap:18px;margin-bottom:20px;">
        <div style="font-size:1.8rem;flex-shrink:0;">&#128180;</div>
        <div>
          <div style="font-size:0.72rem;font-weight:800;letter-spacing:0.12em;color:#10b981;margin-bottom:6px;">
            東京しごと財団「事業外スキルアップ助成金」対象講座</div>
          <h3 style="font-size:1.05rem;font-weight:900;color:#fff;margin-bottom:6px;">
            {c["name"]}入門コース（{c["courses"][0]["code"]}）の受講料が最大2/3助成されます</h3>
          <p style="font-size:0.87rem;color:rgba(255,255,255,0.65);line-height:1.8;">
            都内中小企業（本社所在地）の従業員が対象。会社が受講料を全額負担し業務命令として実施する場合に適用。
            Jグランツで受講開始の1ヶ月前までに事前申請が必要です。
            B・Cコースは受講時間が10時間以上のため本助成金の対象外となります。</p>
        </div>
      </div>
      <div class="subsidy-cols" style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;margin-bottom:20px;">
        <div style="background:rgba(16,185,129,0.12);border-radius:12px;padding:16px 14px;text-align:center;">
          <div style="font-size:0.7rem;font-weight:700;color:#10b981;letter-spacing:0.08em;margin-bottom:6px;">
            小規模企業（2/3助成）</div>
          <div style="font-size:1.6rem;font-weight:900;color:#10b981;line-height:1;">
            &#165;24,800<span style="font-size:0.75rem;font-weight:400;">&#12316;</span></div>
          <div style="font-size:0.7rem;color:rgba(255,255,255,0.45);margin-top:4px;">
            &#165;25,000助成 → 実質&#165;24,800</div>
        </div>
        <div style="background:rgba(16,185,129,0.08);border-radius:12px;padding:16px 14px;text-align:center;">
          <div style="font-size:0.7rem;font-weight:700;color:#34d399;letter-spacing:0.08em;margin-bottom:6px;">
            中小企業（1/2助成）</div>
          <div style="font-size:1.6rem;font-weight:900;color:#34d399;line-height:1;">
            &#165;24,800<span style="font-size:0.75rem;font-weight:400;">&#12316;</span></div>
          <div style="font-size:0.7rem;color:rgba(255,255,255,0.45);margin-top:4px;">
            &#165;24,900助成 → 実質&#165;24,800</div>
        </div>
        <div style="background:rgba(255,255,255,0.04);border-radius:12px;padding:16px 14px;text-align:center;">
          <div style="font-size:0.7rem;font-weight:700;color:rgba(255,255,255,0.4);letter-spacing:0.08em;margin-bottom:6px;">
            B・Cコース</div>
          <div style="font-size:1rem;font-weight:800;color:rgba(255,255,255,0.4);line-height:1.4;">
            &#10060; 対象外</div>
          <div style="font-size:0.7rem;color:rgba(255,255,255,0.35);margin-top:4px;">
            受講10時間以上のため</div>
        </div>
      </div>
      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;">
        <div style="font-size:0.8rem;color:rgba(255,255,255,0.5);">
          &#128197; 令和8年度受付期間：2026年3月1日&#12316;2027年2月28日　上限&#165;25,000/人</div>
        <a href="https://www.koyokankyo.shigotozaidan.or.jp/jigyo/skillup/skill-R8jigyogai.html"
          target="_blank" style="font-size:0.82rem;color:#10b981;text-decoration:none;
          border-bottom:1px solid rgba(16,185,129,0.4);padding-bottom:2px;white-space:nowrap;">
          東京しごと財団 公式サイトで詳細を確認 →</a>
      </div>
    </div>
  </div>
</section>

<!-- ═══════════ PROMPT BONUS ═══════════ -->
<section id="prompts" style="background:linear-gradient(135deg,#0c0a14,#09090b,#0a100e);padding:88px 24px;">
  <div class="section-inner">
    <div class="text-center">
      <span class="section-label">EXCLUSIVE BONUS</span>
      <h2 class="section-title">生成AIプロンプト特典 8種セット</h2>
      <p class="section-lead">{c["name"]}分野特化の生成AI＆アプリ構築プロンプトを全コース共通でプレゼント。受講後すぐに実務・商品化に活用できます。</p>
    </div>
    <div class="prompt-grid" style="display:grid;grid-template-columns:repeat(2,1fr);gap:16px;margin-top:48px;">
      {prompt_items_html}
    </div>
    <div style="text-align:center;margin-top:32px;padding:22px;
      background:rgba({accent_rgb},0.08);border:1px solid rgba({accent_rgb},0.2);border-radius:14px;">
      <p style="font-size:0.92rem;color:rgba(255,255,255,0.75);">
        このプロンプト特典は <strong style="color:{accent};">JGAIA認定講座のみ</strong> で提供しています。</p>
    </div>
  </div>
</section>

<!-- ═══════════ TRUST ═══════════ -->
<section style="background:linear-gradient(180deg,#09090b 0%,#0c0c10 100%);padding:88px 24px;">
  <div class="section-inner">
    <div class="text-center">
      <span class="section-label">WHY JGAIA</span>
      <h2 class="section-title">JGAIAが選ばれる6つの理由</h2>
    </div>
    <div class="trust-grid" style="display:grid;grid-template-columns:repeat(3,1fr);gap:24px;margin-top:56px;">
      {trust_html}
    </div>
  </div>
</section>

<!-- ═══════════ FAQ ═══════════ -->
<section id="faq" style="background:#0c0c10;padding:88px 24px;">
  <div class="section-inner">
    <div class="text-center">
      <span class="section-label">FAQ</span>
      <h2 class="section-title">よくある質問</h2>
    </div>
    <div style="max-width:720px;margin:48px auto 0;">
      {faq_items_html}
    </div>
  </div>
</section>

<!-- ═══════════ INQUIRY FORM ═══════════ -->
<section id="inquiry" style="background:linear-gradient(135deg,#0c0a14,#09090b);padding:88px 24px;">
  <div class="section-inner">
    <div class="text-center">
      <span class="section-label">INQUIRY</span>
      <h2 class="section-title">無料相談・お申し込み</h2>
      <p class="section-lead">コース選択・法人研修・日程等、お気軽にお問い合わせください。通常2営業日以内にご返信します。</p>
    </div>
    <div style="max-width:600px;margin:48px auto 0;background:rgba(255,255,255,0.03);
      border:1px solid rgba(255,255,255,0.08);border-radius:24px;padding:40px;">
      <form id="inquiry-form" onsubmit="return false;">
        <input type="hidden" id="fi-industry" value="{c["inquiry_industry"]}">
        <div class="form-group">
          <label>お名前<span>*</span></label>
          <input type="text" id="fi-name" placeholder="山田 太郎" required>
        </div>
        <div class="form-group">
          <label>メールアドレス<span>*</span></label>
          <input type="email" id="fi-email" placeholder="yamada@company.com" required>
        </div>
        <div class="form-group">
          <label>会社名・所属</label>
          <input type="text" id="fi-company" placeholder="株式会社〇〇">
        </div>
        <div class="form-group">
          <label>電話番号</label>
          <input type="tel" id="fi-phone" placeholder="03-0000-0000">
        </div>
        <div class="form-group">
          <label>お問い合わせコース<span>*</span></label>
          <select id="fi-course">
            <option value="">選択してください</option>
            {course_opts_html}
          </select>
        </div>
        <div class="form-group">
          <label>受講人数</label>
          <select id="fi-count">
            <option value="1名">1名</option>
            <option value="2&#12316;4名">2&#12316;4名</option>
            <option value="5&#12316;9名（法人割引あり）">5&#12316;9名（法人割引あり）</option>
            <option value="10名以上（出張研修）">10名以上（出張研修）</option>
          </select>
        </div>
        <div class="form-group">
          <label>ご質問・ご要望</label>
          <textarea id="fi-message" placeholder="ご質問やご要望があればご記入ください"></textarea>
        </div>
        <button onclick="submitInquiry()" type="button"
          style="width:100%;background:linear-gradient(135deg,{accent},{brand});color:#fff;border:none;
          padding:16px;border-radius:14px;font-size:1rem;font-weight:800;cursor:pointer;
          transition:opacity 0.2s;margin-top:8px;font-family:inherit;" id="fi-btn">送信する</button>
        <div id="fi-msg" style="text-align:center;margin-top:16px;font-size:0.9rem;min-height:20px;"></div>
      </form>
    </div>
  </div>
</section>

<!-- ═══════════ OTHER INDUSTRIES ═══════════ -->
<section style="background:#09090b;padding:64px 24px;">
  <div class="section-inner">
    <div class="text-center">
      <span class="section-label">OTHER COURSES</span>
      <h2 class="section-title" style="font-size:1.8rem;">他の分野特化型コースも見る</h2>
    </div>
    <div class="other-grid" style="display:grid;grid-template-columns:repeat(5,1fr);gap:16px;margin-top:40px;">
      {other_ind_html}
    </div>
  </div>
</section>

<!-- ═══════════ FOOTER ═══════════ -->
<footer>
  <div style="display:flex;align-items:center;justify-content:center;gap:10px;margin-bottom:12px;">
    <span style="font-size:1.2rem;font-weight:900;font-family:'Syne',sans-serif;
      background:linear-gradient(135deg,{brand},{brand_light});
      -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;">JGAIA</span>
  </div>
  <p>&copy; 2026 一般社団法人日本生成AI協会（JGAIA）</p>
  <p style="margin-top:8px;font-size:0.75rem;">
    <a href="/vibe-coding">バイブコーディング講座トップ</a> ｜
    <a href="https://www.jgaia.org" target="_blank">JGAIA公式</a></p>
</footer>

<script>
// ─── Particles ───
(function(){{
  var c=document.getElementById('particles');
  if(!c)return;
  var ctx=c.getContext('2d');
  var W=c.width=window.innerWidth,H=c.height=window.innerHeight;
  var pts=Array.from({{length:50}},function(){{
    return {{x:Math.random()*W,y:Math.random()*H,r:Math.random()*2+0.5,
      dx:(Math.random()-0.5)*0.3,dy:(Math.random()-0.5)*0.3}};
  }});
  function draw(){{
    ctx.clearRect(0,0,W,H);
    pts.forEach(function(p){{
      p.x+=p.dx;p.y+=p.dy;
      if(p.x<0)p.x=W;if(p.x>W)p.x=0;
      if(p.y<0)p.y=H;if(p.y>H)p.y=0;
      ctx.beginPath();ctx.arc(p.x,p.y,p.r,0,Math.PI*2);
      ctx.fillStyle='rgba({accent_rgb},0.5)';ctx.fill();
    }});
    requestAnimationFrame(draw);
  }}
  draw();
  window.addEventListener('resize',function(){{W=c.width=window.innerWidth;H=c.height=window.innerHeight;}});
}})();

// ─── FAQ Toggle ───
function toggleFaq(btn){{
  var item=btn.parentElement;
  var a=item.querySelector('.faq-a');
  var icon=btn.querySelector('.faq-icon');
  var open=a.style.display==='block';
  a.style.display=open?'none':'block';
  icon.textContent=open?'+':'\\u2212';
  icon.style.transform=open?'':'rotate(45deg)';
}}

// ─── Inquiry Form Submit ───
async function submitInquiry(){{
  var name=document.getElementById('fi-name').value.trim();
  var email=document.getElementById('fi-email').value.trim();
  var course=document.getElementById('fi-course').value;
  var msg=document.getElementById('fi-msg');
  if(!name||!email||!course){{
    msg.style.color='#f87171';
    msg.textContent='お名前・メールアドレス・コースは必須です。';
    return;
  }}
  var btn=document.getElementById('fi-btn');
  btn.disabled=true;btn.textContent='送信中...';
  try{{
    var res=await fetch('/api/industry-inquiry',{{
      method:'POST',
      headers:{{'Content-Type':'application/json'}},
      body:JSON.stringify({{
        name:name,
        email:email,
        company:document.getElementById('fi-company').value,
        phone:document.getElementById('fi-phone').value,
        course:course,
        count:document.getElementById('fi-count').value,
        message:document.getElementById('fi-message').value,
        industry:document.getElementById('fi-industry').value
      }})
    }});
    var data=await res.json();
    if(data.ok){{
      msg.style.color='#4ade80';
      msg.textContent='送信しました。2営業日以内にご返信します。';
      btn.textContent='送信完了';
    }}else{{
      throw new Error(data.error||'error');
    }}
  }}catch(e){{
    msg.style.color='#f87171';
    msg.textContent='送信エラーが発生しました。info@jgaia.org へ直接ご連絡ください。';
    btn.disabled=false;btn.textContent='送信する';
  }}
}}
</script>

</body>
</html>"""
    return html


# ─────────────────────────────────────────────────────────────
#  お問い合わせメール送信
# ─────────────────────────────────────────────────────────────
def _send_industry_inquiry(data):
    if not SENDGRID_API_KEY:
        return False
    industry_names = {
        "manufacturing": "製造業",
        "healthcare": "医療・ヘルスケア",
        "finance": "金融",
        "logistics": "物流",
        "construction": "建設",
    }
    ind_name = industry_names.get(data.get("industry", ""), "業界特化型")
    subject = f"【{ind_name}バイブコーディング講座】お問い合わせ：{data.get('name', '')}様"
    body_staff = f"""
{ind_name}特化型バイブコーディング講座にお問い合わせがありました。

■ お名前: {data.get('name', '')}
■ メール: {data.get('email', '')}
■ 電話: {data.get('phone', '')}
■ 会社名: {data.get('company', '')}
■ 希望コース: {data.get('course', '')}
■ 受講人数: {data.get('count', '')}
■ ご質問: {data.get('message', '')}
"""
    body_user = f"""
{data.get('name', '')} 様

{ind_name}特化型バイブコーディング認定講座へのお問い合わせありがとうございます。
内容を確認のうえ、通常2営業日以内にご返信いたします。

■ ご希望コース: {data.get('course', '')}
■ 受講人数: {data.get('count', '')}

一般社団法人日本生成AI協会（JGAIA）
メール: info@jgaia.org
Web: https://www.jgaia.org
"""
    try:
        sg = sendgrid.SendGridAPIClient(SENDGRID_API_KEY)
        # スタッフ宛
        sg.send(Mail(
            from_email=Email("info@jgaia.org"),
            to_emails=To("takano.hidetaka@gmail.com"),
            subject=subject,
            plain_text_content=Content("text/plain", body_staff)
        ))
        # 申込者宛自動返信
        sg.send(Mail(
            from_email=Email("info@jgaia.org"),
            to_emails=To(data.get("email")),
            subject=f"【受付完了】{ind_name}特化型バイブコーディング講座のお問い合わせ",
            plain_text_content=Content("text/plain", body_user)
        ))
        return True
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────
#  Flask ルート登録
# ─────────────────────────────────────────────────────────────
def register_vibe_coding_industry_routes(app):

    @app.route("/vibe-coding/manufacturing")
    def vibe_manufacturing():
        return Response(_render_industry_page(INDUSTRIES["manufacturing"]), mimetype="text/html")

    @app.route("/vibe-coding/healthcare")
    def vibe_healthcare():
        return Response(_render_industry_page(INDUSTRIES["healthcare"]), mimetype="text/html")

    @app.route("/vibe-coding/finance")
    def vibe_finance():
        return Response(_render_industry_page(INDUSTRIES["finance"]), mimetype="text/html")

    @app.route("/vibe-coding/logistics")
    def vibe_logistics():
        return Response(_render_industry_page(INDUSTRIES["logistics"]), mimetype="text/html")

    @app.route("/vibe-coding/construction")
    def vibe_construction():
        return Response(_render_industry_page(INDUSTRIES["construction"]), mimetype="text/html")

    @app.route("/api/industry-inquiry", methods=["POST"])
    def api_industry_inquiry():
        data = request.get_json(silent=True) or {}
        if not data.get("name") or not data.get("email") or not data.get("course"):
            return jsonify({"ok": False, "error": "required fields missing"}), 400
        _send_industry_inquiry(data)
        return jsonify({"ok": True})
