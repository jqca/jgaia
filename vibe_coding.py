"""JGAIA バイブコーディング講座 — 1ページ完結型LP

4コース体系:
  A: AIアプリ開発 入門（3h / ¥19,800）
  B: AIアプリ開発 実践（6h / ¥49,800）
  C: AIセキュリティ＆ガバナンス（6h / ¥49,800）
  D: AIエンジニアリング マスター（3日間 / ¥128,000）
  + 法人カスタマイズ研修

問い合わせAPI:
  POST /api/inquiry — SendGrid経由でinfo@jgaia.orgへ通知＋自動返信
"""
import json
import os

from flask import Response, request


SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY", "")
FROM_EMAIL = "info@jgaia.org"
NOTIFY_EMAIL = "takano.hidetaka@gmail.com"


def register_vibe_coding_routes(app):
    @app.route("/vibe-coding")
    def vibe_coding():
        return Response(LP_HTML, mimetype="text/html")

    @app.route("/api/inquiry", methods=["POST"])
    def inquiry():
        try:
            data = request.get_json(force=True)
        except Exception:
            return {"error": "invalid JSON"}, 400

        name = (data.get("name") or "").strip()
        email = (data.get("email") or "").strip()
        company = (data.get("company") or "").strip()
        course = (data.get("course") or "").strip()
        message = (data.get("message") or "").strip()

        if not name or not email:
            return {"error": "name and email are required"}, 400

        if not SENDGRID_API_KEY:
            return {"ok": True, "note": "SendGrid未設定のためメール送信をスキップしました"}

        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail

            body_lines = [
                f"氏名: {name}",
                f"メール: {email}",
                f"会社名: {company}" if company else None,
                f"希望コース: {course}" if course else None,
                f"お問い合わせ内容:\n{message}" if message else None,
            ]
            body_text = "\n".join(line for line in body_lines if line)

            sg = SendGridAPIClient(SENDGRID_API_KEY)

            notify = Mail(
                from_email=FROM_EMAIL,
                to_emails=NOTIFY_EMAIL,
                subject=f"【JGAIA講座】お問い合わせ: {name}様",
                plain_text_content=body_text,
            )
            sg.send(notify)

            reply = Mail(
                from_email=FROM_EMAIL,
                to_emails=email,
                subject="【JGAIA】お問い合わせありがとうございます",
                plain_text_content=(
                    f"{name} 様\n\n"
                    "一般社団法人日本生成AI協会（JGAIA）のバイブコーディング講座に"
                    "ご関心をお寄せいただきありがとうございます。\n\n"
                    "担当者より2営業日以内にご連絡いたします。\n\n"
                    "---\n"
                    "一般社団法人日本生成AI協会（JGAIA）\n"
                    "〒104-0061 東京都中央区銀座1-22-11 銀座大竹ビジデンス2階\n"
                    "info@jgaia.org\n"
                    "https://www.jgaia.org/"
                ),
            )
            sg.send(reply)

            return {"ok": True}
        except Exception as e:
            return {"error": str(e)}, 500


LP_HTML = r"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>バイブコーディング講座 | JGAIA 日本生成AI協会</title>
<meta name="description" content="AIに指示するだけでアプリが作れる「バイブコーディング」を3時間¥19,800から。非エンジニア向け・助成金で実質半額以下。JGAIA認定講座。">
<meta property="og:title" content="バイブコーディング講座 | JGAIA 日本生成AI協会">
<meta property="og:description" content="コードを書かない時代の、アプリ開発。AIに指示するだけで、あなたのアイデアが動き出す。">
<meta property="og:type" content="website">
<meta property="og:url" content="https://jgaia-production.up.railway.app/vibe-coding">
<link rel="canonical" href="https://jgaia-production.up.railway.app/vibe-coding">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@300;400;500;700;900&display=swap" rel="stylesheet">

<script type="application/ld+json">
[
  {"@context":"https://schema.org","@type":"Course","name":"AIアプリ開発 入門","description":"3時間でAIを使ったアプリ開発を体験。プログラミング経験不要。","provider":{"@type":"Organization","name":"JGAIA 日本生成AI協会","url":"https://www.jgaia.org/"},"offers":{"@type":"Offer","price":"19800","priceCurrency":"JPY"}},
  {"@context":"https://schema.org","@type":"Course","name":"AIアプリ開発 実践","description":"6時間で業務アプリを企画から設計・実装・デプロイまで。","provider":{"@type":"Organization","name":"JGAIA 日本生成AI協会","url":"https://www.jgaia.org/"},"offers":{"@type":"Offer","price":"49800","priceCurrency":"JPY"}},
  {"@context":"https://schema.org","@type":"Course","name":"AIセキュリティ＆ガバナンス","description":"AI生成コードの脆弱性対策、プロンプトインジェクション防御、社内ガイドライン策定。","provider":{"@type":"Organization","name":"JGAIA 日本生成AI協会","url":"https://www.jgaia.org/"},"offers":{"@type":"Offer","price":"49800","priceCurrency":"JPY"}},
  {"@context":"https://schema.org","@type":"Course","name":"AIエンジニアリング マスター","description":"3日間でチーム導入戦略、マルチエージェント設計、CI/CD統合、ROI測定を習得。","provider":{"@type":"Organization","name":"JGAIA 日本生成AI協会","url":"https://www.jgaia.org/"},"offers":{"@type":"Offer","price":"128000","priceCurrency":"JPY"}}
]
</script>

<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth;font-size:16px}
body{background:#fff;color:#1a1a2e;font-family:'Noto Sans JP',sans-serif;line-height:1.7;-webkit-font-smoothing:antialiased}
a{color:inherit;text-decoration:none}
img{display:block;max-width:100%}
button{cursor:pointer;border:none;background:none;font-family:inherit}
.wrap{max-width:1100px;margin:0 auto;padding:0 24px}

/* ── Header (navy gradient + constellation dots) ── */
.site-header{background:linear-gradient(135deg,#0a1628 0%,#0d1b3e 40%,#162d5a 100%);position:relative;overflow:hidden}
.site-header::before{content:'';position:absolute;inset:0;background:radial-gradient(1.5px 1.5px at 10% 20%,rgba(255,255,255,.45),transparent),radial-gradient(1px 1px at 25% 60%,rgba(255,255,255,.3),transparent),radial-gradient(1.5px 1.5px at 45% 15%,rgba(255,255,255,.5),transparent),radial-gradient(1px 1px at 60% 45%,rgba(255,255,255,.25),transparent),radial-gradient(1.5px 1.5px at 75% 25%,rgba(255,255,255,.4),transparent),radial-gradient(1px 1px at 85% 55%,rgba(255,255,255,.35),transparent),radial-gradient(1.5px 1.5px at 30% 80%,rgba(255,255,255,.3),transparent),radial-gradient(1px 1px at 50% 70%,rgba(255,255,255,.2),transparent),radial-gradient(1.5px 1.5px at 90% 80%,rgba(255,255,255,.35),transparent),radial-gradient(1px 1px at 15% 45%,rgba(255,255,255,.25),transparent),radial-gradient(1.5px 1.5px at 70% 65%,rgba(255,255,255,.3),transparent),radial-gradient(1px 1px at 55% 90%,rgba(255,255,255,.2),transparent);pointer-events:none}
.site-header::after{content:'';position:absolute;inset:0;background:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='400' height='200'%3E%3Cline x1='40' y1='40' x2='120' y2='80' stroke='rgba(255,255,255,0.06)' stroke-width='1'/%3E%3Cline x1='120' y1='80' x2='200' y2='30' stroke='rgba(255,255,255,0.06)' stroke-width='1'/%3E%3Cline x1='200' y1='30' x2='300' y2='90' stroke='rgba(255,255,255,0.06)' stroke-width='1'/%3E%3Cline x1='300' y1='90' x2='370' y2='50' stroke='rgba(255,255,255,0.06)' stroke-width='1'/%3E%3Cline x1='60' y1='130' x2='160' y2='160' stroke='rgba(255,255,255,0.04)' stroke-width='1'/%3E%3Cline x1='160' y1='160' x2='260' y2='120' stroke='rgba(255,255,255,0.04)' stroke-width='1'/%3E%3Cline x1='260' y1='120' x2='350' y2='170' stroke='rgba(255,255,255,0.04)' stroke-width='1'/%3E%3C/svg%3E") repeat;pointer-events:none}

/* Top bar */
.hd-top{position:relative;z-index:2;display:flex;align-items:center;justify-content:space-between;padding:16px 48px;border-bottom:1px solid rgba(255,255,255,.1)}
.hd-logo{display:flex;align-items:center;gap:12px;color:#fff;font-weight:700;font-size:20px;letter-spacing:.08em}
.hd-logo svg{width:28px;height:28px}
.hd-logo .sub{font-size:10px;font-weight:400;color:rgba(255,255,255,.7);display:block;letter-spacing:.02em;margin-top:2px}
.hd-nav{display:flex;align-items:center;gap:4px}
.hd-nav a{color:rgba(255,255,255,.8);font-size:13px;font-weight:500;padding:8px 16px;border-radius:4px;transition:all .15s}
.hd-nav a:hover,.hd-nav a.active{color:#fff;background:rgba(255,255,255,.1)}
.btn-contact-hd{font-size:13px;font-weight:600;color:#0d1b3e;background:#fff;padding:9px 22px;border-radius:4px;transition:opacity .15s}
.btn-contact-hd:hover{opacity:.9}

/* Hero area inside header */
.hero{position:relative;z-index:2;text-align:center;padding:80px 24px 88px}
.hero-eyebrow{display:inline-block;font-size:12px;font-weight:500;letter-spacing:.15em;color:rgba(255,255,255,.7);border:1px solid rgba(255,255,255,.2);padding:6px 20px;border-radius:20px;margin-bottom:28px}
.hero h1{font-size:clamp(28px,4.5vw,48px);font-weight:900;color:#fff;line-height:1.3;margin-bottom:20px}
.hero h1 span{color:#64b5f6}
.hero-sub{font-size:16px;font-weight:300;color:rgba(255,255,255,.75);line-height:1.8;max-width:600px;margin:0 auto 40px}
.hero-actions{display:flex;justify-content:center;gap:16px;flex-wrap:wrap}
.btn-primary{display:inline-flex;align-items:center;gap:8px;font-size:15px;font-weight:700;color:#0d1b3e;background:#fff;padding:14px 32px;border-radius:4px;transition:all .2s;box-shadow:0 2px 8px rgba(0,0,0,.15)}
.btn-primary:hover{transform:translateY(-2px);box-shadow:0 4px 16px rgba(0,0,0,.2)}
.btn-outline{display:inline-flex;align-items:center;gap:8px;font-size:15px;font-weight:500;color:#fff;padding:14px 28px;border-radius:4px;border:1px solid rgba(255,255,255,.35);transition:all .2s}
.btn-outline:hover{background:rgba(255,255,255,.1);border-color:rgba(255,255,255,.6)}

/* ── Stats ── */
.stats-bar{background:#f0f4f8;border-bottom:1px solid #e2e8f0}
.stats-inner{display:grid;grid-template-columns:repeat(4,1fr);max-width:1100px;margin:0 auto;padding:40px 24px}
.stat-item{text-align:center;padding:0 16px}
.stat-item+.stat-item{border-left:1px solid #d1d9e6}
.stat-n{font-size:40px;font-weight:900;color:#0d1b3e;line-height:1;margin-bottom:6px}
.stat-n sup{font-size:20px;font-weight:700}
.stat-lb{font-size:12px;color:#4a5568;font-weight:500}
.stat-ds{font-size:11px;color:#718096;margin-top:3px}

/* ── Sections ── */
.sec{padding:80px 0}
.sec+.sec{border-top:1px solid #e2e8f0}
.sec-label{display:inline-block;font-size:11px;font-weight:700;letter-spacing:.2em;text-transform:uppercase;color:#3b82f6;margin-bottom:12px}
.sec-title{font-size:clamp(24px,3.5vw,36px);font-weight:900;color:#0d1b3e;line-height:1.3;margin-bottom:16px}
.sec-desc{font-size:15px;color:#4a5568;line-height:1.8;max-width:600px}
.sec-header-2col{display:grid;grid-template-columns:1fr 1fr;gap:48px;align-items:end;margin-bottom:48px}

/* ── Problems ── */
.problems-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:20px}
.problem-card{background:#fff;border:1px solid #e2e8f0;border-radius:8px;padding:28px 20px;transition:all .2s}
.problem-card:hover{border-color:#3b82f6;box-shadow:0 4px 16px rgba(59,130,246,.1);transform:translateY(-2px)}
.problem-num{font-size:11px;font-weight:700;letter-spacing:.15em;color:#3b82f6;margin-bottom:12px}
.problem-icon{font-size:28px;margin-bottom:12px}
.problem-card h3{font-size:15px;font-weight:700;color:#0d1b3e;margin-bottom:8px}
.problem-card p{font-size:13px;color:#64748b;line-height:1.7}

/* ── Steps ── */
.steps-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:24px;margin-top:48px}
.step-card{background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:36px 24px;text-align:center;transition:all .2s}
.step-card:hover{border-color:#3b82f6;background:#fff}
.step-num-circle{display:inline-flex;align-items:center;justify-content:center;width:44px;height:44px;border-radius:50%;background:#0d1b3e;color:#fff;font-weight:900;font-size:18px;margin-bottom:16px}
.step-card h3{font-size:16px;font-weight:700;color:#0d1b3e;margin-bottom:10px;line-height:1.4}
.step-card p{font-size:13px;color:#64748b;line-height:1.7}

/* ── Courses ── */
.courses-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:24px}
.course-card{background:#fff;border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;transition:all .2s}
.course-card:hover{border-color:#3b82f6;box-shadow:0 4px 20px rgba(59,130,246,.08)}
.course-head{padding:24px 28px 0;display:flex;align-items:center;gap:12px}
.course-step-tag{font-size:10px;font-weight:700;letter-spacing:.12em;color:#fff;padding:4px 12px;border-radius:3px;white-space:nowrap}
.c-a .course-step-tag{background:#3b82f6}
.c-b .course-step-tag{background:#10b981}
.c-c .course-step-tag{background:#f59e0b}
.c-d .course-step-tag{background:#8b5cf6}
.course-card h3{font-size:18px;font-weight:700;color:#0d1b3e}
.course-body{padding:16px 28px 28px}
.course-meta{display:flex;gap:14px;flex-wrap:wrap;margin-bottom:14px;font-size:12.5px;color:#64748b}
.course-meta span{display:flex;align-items:center;gap:4px}
.course-desc{font-size:13.5px;color:#4a5568;line-height:1.7;margin-bottom:16px}
.course-price{display:flex;align-items:baseline;gap:8px;margin-bottom:6px}
.price-main{font-size:28px;font-weight:900;color:#0d1b3e;letter-spacing:-.02em}
.price-sub{font-size:12px;color:#64748b}
.price-subsidy{font-size:12px;color:#10b981;font-weight:600;margin-bottom:16px}
.toggle-btn{font-size:13px;font-weight:500;color:#3b82f6;padding:10px 20px;border-radius:4px;border:1px solid #3b82f6;transition:all .15s;width:100%;background:#fff}
.toggle-btn:hover{background:#eff6ff;color:#1d4ed8}
.curriculum{display:none;margin-top:16px}
.curriculum.open{display:block}
.curriculum ul{list-style:none}
.curriculum li{font-size:13px;color:#4a5568;padding:8px 0;border-bottom:1px solid #f1f5f9;display:flex;align-items:flex-start;gap:8px}
.curriculum li::before{content:"\2713";color:#10b981;font-weight:700;flex-shrink:0}
.apply-wrap{display:none;margin-top:16px}
.apply-wrap.open{display:block}

/* ── Quiz ── */
.quiz-wrap{margin-top:48px;padding:40px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px}
.quiz-wrap h3{font-size:20px;font-weight:700;color:#0d1b3e;margin-bottom:8px}
.quiz-wrap>p{font-size:14px;color:#64748b;margin-bottom:28px}
.quiz-q{margin-bottom:20px}
.quiz-q label{font-size:14px;font-weight:600;color:#0d1b3e;display:block;margin-bottom:10px}
.quiz-opts{display:flex;gap:8px;flex-wrap:wrap}
.quiz-opt{background:#fff;border:1px solid #e2e8f0;border-radius:4px;padding:10px 20px;font-size:13px;color:#4a5568;cursor:pointer;transition:all .15s}
.quiz-opt:hover,.quiz-opt.sel{border-color:#3b82f6;color:#1d4ed8;background:#eff6ff}
.quiz-result{display:none;padding:20px;border-left:3px solid #3b82f6;background:#eff6ff;border-radius:0 4px 4px 0;margin-top:16px}
.quiz-result.show{display:block}
.quiz-result h4{font-size:16px;font-weight:700;color:#1d4ed8;margin-bottom:6px}
.quiz-result p{font-size:14px;color:#4a5568;line-height:1.7}

/* ── Subsidy ── */
.subsidy-table{width:100%;border-collapse:collapse;margin-top:28px;font-size:14px}
.subsidy-table th,.subsidy-table td{padding:14px 16px;border-bottom:1px solid #e2e8f0;text-align:left}
.subsidy-table th{font-size:11px;color:#64748b;font-weight:700;letter-spacing:.05em;text-transform:uppercase;background:#f8fafc}
.subsidy-table .hi{color:#10b981;font-weight:700}

/* ── Corporate ── */
.corp-section{display:grid;grid-template-columns:1fr 1fr;gap:60px;align-items:center}
.corp-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:16px}
.corp-item{background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:24px;transition:all .2s}
.corp-item:hover{border-color:#3b82f6;background:#fff}
.corp-item-icon{font-size:24px;margin-bottom:8px}
.corp-item h4{font-size:14px;font-weight:700;color:#0d1b3e;margin-bottom:4px}
.corp-item p{font-size:12px;color:#64748b;line-height:1.7}

/* ── FAQ ── */
.faq-item{border-bottom:1px solid #e2e8f0;padding:18px 0}
.faq-q{font-size:14px;font-weight:600;color:#0d1b3e;cursor:pointer;display:flex;justify-content:space-between;align-items:center;transition:color .15s}
.faq-q:hover{color:#3b82f6}
.faq-q::after{content:"+";font-size:20px;color:#94a3b8;transition:transform .2s;flex-shrink:0;margin-left:16px}
.faq-q.open::after{transform:rotate(45deg)}
.faq-a{max-height:0;overflow:hidden;transition:max-height .4s ease;font-size:13.5px;color:#4a5568;line-height:1.8}
.faq-a.open{max-height:500px;padding-top:10px}

/* ── Contact / CTA ── */
.cta-section{padding:80px 0}
.cta-inner{display:grid;grid-template-columns:1fr 1fr;gap:60px;align-items:start}
.cta-right{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.cta-item{background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:28px;transition:all .2s}
.cta-item:hover{border-color:#3b82f6;background:#fff}
.cta-item-num{font-size:11px;font-weight:700;letter-spacing:.15em;color:#3b82f6;margin-bottom:12px}
.cta-item h4{font-size:15px;font-weight:700;color:#0d1b3e;margin-bottom:6px}
.cta-item p{font-size:12.5px;color:#64748b;line-height:1.7}

/* ── Form ── */
.form-group{margin-bottom:14px}
.form-group label{display:block;font-size:12px;font-weight:600;color:#4a5568;letter-spacing:.03em;margin-bottom:5px}
.form-group input,.form-group select,.form-group textarea{width:100%;padding:11px 14px;font-size:14px;background:#fff;border:1px solid #d1d5db;border-radius:4px;color:#1a1a2e;font-family:inherit;transition:border-color .15s}
.form-group input:focus,.form-group select:focus,.form-group textarea:focus{outline:none;border-color:#3b82f6;box-shadow:0 0 0 3px rgba(59,130,246,.1)}
.form-group textarea{min-height:100px;resize:vertical}
.form-status{font-size:13px;margin-top:8px;min-height:20px}
.form-status.ok{color:#10b981}
.form-status.err{color:#ef4444}
.btn-submit{display:inline-flex;align-items:center;justify-content:center;gap:8px;font-size:15px;font-weight:700;color:#fff;background:#0d1b3e;padding:14px 32px;border-radius:4px;width:100%;transition:all .15s;border:none;cursor:pointer}
.btn-submit:hover{background:#162d5a}
.btn-corp{display:inline-flex;align-items:center;gap:8px;font-size:15px;font-weight:700;color:#fff;background:#0d1b3e;padding:14px 32px;border-radius:4px;transition:all .15s}
.btn-corp:hover{background:#162d5a}

/* ── Footer ── */
.footer{background:#0d1b3e;color:rgba(255,255,255,.8);padding:60px 0 32px;position:relative;overflow:hidden}
.footer::before{content:'';position:absolute;inset:0;background:radial-gradient(1px 1px at 20% 30%,rgba(255,255,255,.2),transparent),radial-gradient(1px 1px at 60% 60%,rgba(255,255,255,.15),transparent),radial-gradient(1px 1px at 80% 20%,rgba(255,255,255,.2),transparent);pointer-events:none}
.footer-inner{position:relative;z-index:1;max-width:1100px;margin:0 auto;padding:0 24px}
.footer-top{display:grid;grid-template-columns:1.6fr 1fr 1fr 1fr;gap:40px;margin-bottom:48px}
.footer-brand-name{font-size:18px;font-weight:700;color:#fff;margin-bottom:4px;letter-spacing:.06em}
.footer-brand-ja{font-size:11px;color:rgba(255,255,255,.5);margin-bottom:16px}
.footer-brand-desc{font-size:13px;color:rgba(255,255,255,.5);line-height:1.75}
.footer-col h5{font-size:11px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:rgba(255,255,255,.4);margin-bottom:14px}
.footer-col ul{list-style:none}
.footer-col li+li{margin-top:10px}
.footer-col a{font-size:13px;color:rgba(255,255,255,.7);transition:color .15s}
.footer-col a:hover{color:#fff}
.footer-bottom{display:flex;align-items:center;justify-content:space-between;padding-top:24px;border-top:1px solid rgba(255,255,255,.1)}
.footer-bottom p{font-size:12px;color:rgba(255,255,255,.4)}
.footer-bottom-links{display:flex;gap:20px}
.footer-bottom-links a{font-size:12px;color:rgba(255,255,255,.4);transition:color .15s}
.footer-bottom-links a:hover{color:rgba(255,255,255,.7)}

/* ── Mobile CTA ── */
.mobile-cta{display:none;position:fixed;bottom:0;left:0;right:0;background:rgba(13,27,62,.97);backdrop-filter:blur(10px);padding:12px 24px;z-index:100;border-top:1px solid rgba(255,255,255,.15)}
.mobile-cta a{display:block;text-align:center;font-size:14px;font-weight:700;color:#0d1b3e;background:#fff;padding:14px;border-radius:4px}

/* ── Responsive ── */
@media(max-width:1024px){
  .hd-top{padding:14px 24px}
  .sec{padding:60px 0}
  .sec-header-2col,.corp-section{grid-template-columns:1fr;gap:24px}
  .problems-grid{grid-template-columns:repeat(2,1fr)}
  .courses-grid{grid-template-columns:1fr}
  .cta-inner{grid-template-columns:1fr}
  .footer-top{grid-template-columns:1fr 1fr;gap:24px}
}
@media(max-width:768px){
  .hd-nav{display:none}
  .hero{padding:48px 24px 56px}
  .hero h1{font-size:26px}
  .stats-inner{grid-template-columns:repeat(2,1fr);gap:20px;padding:28px 24px}
  .stat-item+.stat-item{border-left:none}
  .stat-item:nth-child(odd)+.stat-item{border-left:1px solid #d1d9e6}
  .problems-grid,.steps-grid{grid-template-columns:1fr}
  .quiz-wrap{padding:24px 20px}
  .cta-right{grid-template-columns:1fr}
  .footer-top{grid-template-columns:1fr}
  .footer-bottom{flex-direction:column;gap:12px;text-align:center}
  .mobile-cta{display:block}
}
</style>
</head>
<body>

<!-- Header with constellation pattern -->
<header class="site-header">
  <div class="hd-top">
    <a href="/" class="hd-logo">
      <svg viewBox="0 0 28 28" fill="none"><polygon points="14,2 26,8 26,20 14,26 2,20 2,8" fill="none" stroke="#fff" stroke-width="1.5"/><circle cx="14" cy="14" r="3" fill="#64b5f6"/><line x1="14" y1="2" x2="14" y2="11" stroke="rgba(255,255,255,.4)" stroke-width="1"/><line x1="14" y1="17" x2="14" y2="26" stroke="rgba(255,255,255,.4)" stroke-width="1"/><line x1="2" y1="8" x2="11" y2="14" stroke="rgba(255,255,255,.4)" stroke-width="1"/><line x1="17" y1="14" x2="26" y2="8" stroke="rgba(255,255,255,.4)" stroke-width="1"/></svg>
      <div>JGAIA<span class="sub">一般社団法人 日本生成AI協会</span></div>
    </a>
    <nav class="hd-nav">
      <a href="/">ホーム</a>
      <a href="/#">協会情報</a>
      <a href="/vibe-coding" class="active">資格・講座</a>
      <a href="/#">協会員一覧</a>
      <a href="/#">協会員募集</a>
    </nav>
    <a href="#inquiry-section" class="btn-contact-hd">お問い合わせ</a>
  </div>

  <!-- Hero -->
  <div class="hero">
    <div class="hero-eyebrow">JGAIA CERTIFIED COURSE</div>
    <h1>コードを書かない時代の、<br><span>アプリ開発。</span></h1>
    <p class="hero-sub">AIに指示するだけで、あなたのアイデアが動き出す。<br>プログラミング経験ゼロから、3時間で最初のアプリを。</p>
    <div class="hero-actions">
      <a href="#courses" class="btn-primary">講座ラインナップ →</a>
      <a href="#quiz" class="btn-outline">おすすめコース診断</a>
    </div>
  </div>
</header>

<!-- Stats bar -->
<div class="stats-bar">
  <div class="stats-inner">
    <div class="stat-item"><div class="stat-n">40<sup>%</sup></div><div class="stat-lb">バイブコーディング</div><div class="stat-ds">2028年の本番ソフト — Gartner予測</div></div>
    <div class="stat-item"><div class="stat-n">75<sup>%</sup></div><div class="stat-lb">AIツール採用率</div><div class="stat-ds">2028年の開発者 — Gartner予測</div></div>
    <div class="stat-item"><div class="stat-n">79<sup>万人</sup></div><div class="stat-lb">IT人材不足</div><div class="stat-ds">2030年 — 経産省推計</div></div>
    <div class="stat-item"><div class="stat-n">1/10</div><div class="stat-lb">開発コスト</div><div class="stat-ds">従来比削減 — 当協会実績</div></div>
  </div>
</div>

<!-- Problems -->
<section class="sec">
  <div class="wrap">
    <div class="sec-header-2col">
      <div><div class="sec-label">PROBLEM</div><h2 class="sec-title">こんな課題、<br>ありませんか？</h2></div>
      <p class="sec-desc">エンジニア不足・外注コスト・セキュリティ不安。企業のDX推進を阻む壁に、バイブコーディングという新しい解を。</p>
    </div>
    <div class="problems-grid">
      <div class="problem-card"><div class="problem-num">01</div><div class="problem-icon">💸</div><h3>外注すると数百万</h3><p>ちょっとした社内ツールを作りたいだけなのに、見積もりを見て断念した経験はありませんか。</p></div>
      <div class="problem-card"><div class="problem-num">02</div><div class="problem-icon">👤</div><h3>エンジニアが採れない</h3><p>IT人材は2030年に79万人不足。中小企業では技術者の確保がますます困難に。</p></div>
      <div class="problem-card"><div class="problem-num">03</div><div class="problem-icon">📚</div><h3>情報が散らばっている</h3><p>YouTube、ブログ、SNS…断片的な情報はあるけれど、体系的に学べる場所がない。</p></div>
      <div class="problem-card"><div class="problem-num">04</div><div class="problem-icon">🔒</div><h3>セキュリティが不安</h3><p>AIが書いたコードは安全なのか。社内利用のガバナンスと脆弱性対策の知識が必要。</p></div>
    </div>
  </div>
</section>

<!-- What is Vibe Coding -->
<section class="sec">
  <div class="wrap">
    <div class="sec-label">WHAT IS VIBE CODING</div>
    <h2 class="sec-title">バイブコーディングとは？</h2>
    <p class="sec-desc">2025年にAI研究者 Andrej Karpathy が提唱した新しい開発スタイル。AIコーディングエージェントに実装を任せ、人間はアイデアと設計に集中します。</p>
    <div class="steps-grid">
      <div class="step-card"><div class="step-num-circle">1</div><h3>作りたいものを<br>言葉で伝える</h3><p>「顧客管理アプリを作って」「グラフで売上を可視化して」— 日本語で指示するだけ。</p></div>
      <div class="step-card"><div class="step-num-circle">2</div><h3>AIが<br>コードを書く</h3><p>Cursor、Claude Code 等のAIツールが、あなたの指示を元にアプリのコードを自動生成。</p></div>
      <div class="step-card"><div class="step-num-circle">3</div><h3>動くアプリが<br>完成する</h3><p>数時間で実際に動くアプリが完成。修正も「ここを変えて」と言うだけ。</p></div>
    </div>
  </div>
</section>

<!-- Courses -->
<section class="sec" id="courses">
  <div class="wrap">
    <div class="sec-header-2col">
      <div><div class="sec-label">COURSES</div><h2 class="sec-title">4ステップで、<br>確実に身につく</h2></div>
      <p class="sec-desc">「まず体験」から「組織を変える」まで。あなたのレベルに合わせて、次のステップが明確です。</p>
    </div>
    <div class="courses-grid">
      <!-- A -->
      <div class="course-card c-a" id="course-a">
        <div class="course-head"><span class="course-step-tag">STEP 1</span><h3>AIアプリ開発 入門</h3></div>
        <div class="course-body">
          <div class="course-meta"><span>🕐 3時間</span><span>👤 未経験者歓迎</span><span>💻 会場 or オンライン</span></div>
          <p class="course-desc">プログラミング経験ゼロでOK。3時間で実際に動くアプリを1つ完成させます。「自分にもできた」という成功体験がゴールです。</p>
          <div class="course-price"><span class="price-main">¥19,800</span><span class="price-sub">（税込）</span></div>
          <div class="price-subsidy">💰 助成金利用で実質 ¥6,600〜9,900</div>
          <button class="toggle-btn" onclick="toggleCurriculum(this)">カリキュラムを見る →</button>
          <div class="curriculum">
            <ul>
              <li>バイブコーディングとは — AIと一緒に作る新しい開発スタイル</li>
              <li>開発環境のセットアップ — Cursorのインストールと基本操作</li>
              <li>最初のアプリ制作 — 「やりたいこと」を言葉にして、AIに伝える</li>
              <li>UIの調整と改善 — 「もっとこうして」でデザインを磨く</li>
              <li>完成・共有 — 作ったアプリをURLで公開する方法</li>
            </ul>
            <button class="toggle-btn" onclick="toggleApply(this)">このコースに申し込む →</button>
            <div class="apply-wrap" data-course="A: AIアプリ開発 入門（¥19,800）"></div>
          </div>
        </div>
      </div>
      <!-- B -->
      <div class="course-card c-b" id="course-b">
        <div class="course-head"><span class="course-step-tag">STEP 2</span><h3>AIアプリ開発 実践</h3></div>
        <div class="course-body">
          <div class="course-meta"><span>🕐 6時間（1日）</span><span>👤 コースA修了者 or 経験者</span><span>💻 会場 or オンライン</span></div>
          <p class="course-desc">業務で使えるアプリを企画→設計→実装→デプロイまで。データベース連携、API接続、セキュリティの基礎も学びます。</p>
          <div class="course-price"><span class="price-main">¥49,800</span><span class="price-sub">（税込）</span></div>
          <div class="price-subsidy">💰 助成金利用で実質 ¥24,800〜33,200</div>
          <button class="toggle-btn" onclick="toggleCurriculum(this)">カリキュラムを見る →</button>
          <div class="curriculum">
            <ul>
              <li>業務課題の分析 — 何を自動化すべきか見極める</li>
              <li>アプリ設計 — 画面構成・データ構造・API連携の設計</li>
              <li>実装ワークショップ — AIと対話しながら本格アプリを構築</li>
              <li>データベース入門 — データの保存・検索・更新の仕組み</li>
              <li>外部サービス連携 — Google Sheets、メール、Slack等との接続</li>
              <li>デプロイと運用 — インターネットに公開して実務で使い始める</li>
            </ul>
            <button class="toggle-btn" onclick="toggleApply(this)">このコースに申し込む →</button>
            <div class="apply-wrap" data-course="B: AIアプリ開発 実践（¥49,800）"></div>
          </div>
        </div>
      </div>
      <!-- C -->
      <div class="course-card c-c" id="course-c">
        <div class="course-head"><span class="course-step-tag">STEP 3</span><h3>AIセキュリティ＆ガバナンス</h3></div>
        <div class="course-body">
          <div class="course-meta"><span>🕐 6時間（1日）</span><span>👤 コースB修了者 or IT管理者</span><span>💻 会場 or オンライン</span></div>
          <p class="course-desc">AI生成コードの脆弱性、プロンプトインジェクション対策、コードレビュー手法、社内ガイドライン策定を学びます。</p>
          <div class="course-price"><span class="price-main">¥49,800</span><span class="price-sub">（税込）</span></div>
          <div class="price-subsidy">💰 助成金利用で実質 ¥24,800〜33,200</div>
          <button class="toggle-btn" onclick="toggleCurriculum(this)">カリキュラムを見る →</button>
          <div class="curriculum">
            <ul>
              <li>AI生成コードのリスク全体像 — OWASP Top 10 for LLM Applications</li>
              <li>プロンプトインジェクション — 攻撃手法と防御パターン</li>
              <li>コードレビュー実践 — AI生成コードの安全性を人間が検証する方法</li>
              <li>認証・認可・データ保護 — 最低限守るべきセキュリティライン</li>
              <li>社内ガイドライン策定 — 「AIコーディング利用規程」テンプレート付き</li>
              <li>インシデント対応 — 問題が起きたときの初動と報告フロー</li>
            </ul>
            <button class="toggle-btn" onclick="toggleApply(this)">このコースに申し込む →</button>
            <div class="apply-wrap" data-course="C: AIセキュリティ＆ガバナンス（¥49,800）"></div>
          </div>
        </div>
      </div>
      <!-- D -->
      <div class="course-card c-d" id="course-d">
        <div class="course-head"><span class="course-step-tag">STEP 4</span><h3>AIエンジニアリング マスター</h3></div>
        <div class="course-body">
          <div class="course-meta"><span>🕐 3日間（18時間）</span><span>👤 DXリーダー・技術責任者</span><span>💻 会場</span></div>
          <p class="course-desc">バイブコーディングの先へ。マルチエージェント設計、CI/CD統合、チーム導入戦略、ROI測定、社内展開ロードマップを3日間で習得します。</p>
          <div class="course-price"><span class="price-main">¥128,000</span><span class="price-sub">（税込）</span></div>
          <div class="price-subsidy">🏢 法人一括申込割引あり — お問い合わせください</div>
          <button class="toggle-btn" onclick="toggleCurriculum(this)">カリキュラムを見る →</button>
          <div class="curriculum">
            <ul>
              <li>Day 1: AIエージェントアーキテクチャ — マルチエージェント設計と制御</li>
              <li>Day 1: 開発ワークフロー統合 — CI/CD、コードレビュー、テスト自動化</li>
              <li>Day 2: チーム導入戦略 — 段階的ロールアウトと変更管理</li>
              <li>Day 2: ROI測定フレームワーク — 投資対効果の定量化と経営報告</li>
              <li>Day 3: 社内展開ロードマップ作成 — 自社に合った3-6ヶ月計画</li>
              <li>Day 3: 最終プレゼンテーション — 経営層向け提案書の作成と発表</li>
            </ul>
            <button class="toggle-btn" onclick="toggleApply(this)">このコースに申し込む →</button>
            <div class="apply-wrap" data-course="D: AIエンジニアリング マスター（¥128,000）"></div>
          </div>
        </div>
      </div>
    </div>

    <!-- Quiz -->
    <div class="quiz-wrap" id="quiz">
      <h3>おすすめコース診断</h3>
      <p>3つの質問に答えるだけで、最適なコースをご提案します。</p>
      <div class="quiz-q" id="q1"><label>Q1. プログラミングの経験は？</label><div class="quiz-opts"><div class="quiz-opt" onclick="quizAnswer(1,'none',this)">全くない</div><div class="quiz-opt" onclick="quizAnswer(1,'little',this)">少しある / 講座で学んだ</div><div class="quiz-opt" onclick="quizAnswer(1,'pro',this)">業務で使っている</div></div></div>
      <div class="quiz-q" id="q2" style="display:none"><label>Q2. 主な目的は？</label><div class="quiz-opts"><div class="quiz-opt" onclick="quizAnswer(2,'try',this)">まず試してみたい</div><div class="quiz-opt" onclick="quizAnswer(2,'work',this)">業務で使いたい</div><div class="quiz-opt" onclick="quizAnswer(2,'team',this)">チーム・組織に導入したい</div></div></div>
      <div class="quiz-q" id="q3" style="display:none"><label>Q3. セキュリティ・ガバナンスへの関心は？</label><div class="quiz-opts"><div class="quiz-opt" onclick="quizAnswer(3,'low',this)">まだ考えていない</div><div class="quiz-opt" onclick="quizAnswer(3,'high',this)">重要だと思う / 担当している</div></div></div>
      <div class="quiz-result" id="quiz-result"></div>
    </div>
  </div>
</section>

<!-- Subsidy -->
<section class="sec" id="subsidy">
  <div class="wrap">
    <div class="sec-label">SUBSIDY</div>
    <h2 class="sec-title">助成金で、<br>実質半額以下に</h2>
    <p class="sec-desc">東京しごと財団「事業外スキルアップ助成金」を利用すると、受講料の最大2/3が助成されます。</p>
    <table class="subsidy-table">
      <thead><tr><th>コース</th><th>受講料</th><th>小規模企業（2/3助成）</th><th>中小企業（1/2助成）</th></tr></thead>
      <tbody>
        <tr><td>A: 入門（3h）</td><td>¥19,800</td><td class="hi">実質 ¥6,600</td><td class="hi">実質 ¥9,900</td></tr>
        <tr><td>B: 実践（6h）</td><td>¥49,800</td><td class="hi">実質 ¥24,800</td><td class="hi">実質 ¥24,800</td></tr>
        <tr><td>C: セキュリティ（6h）</td><td>¥49,800</td><td class="hi">実質 ¥24,800</td><td class="hi">実質 ¥24,800</td></tr>
        <tr><td>D: マスター（3日間）</td><td>¥128,000</td><td colspan="2" style="color:#64748b">助成上限¥25,000 → 実質 ¥103,000</td></tr>
      </tbody>
    </table>
    <p style="margin-top:20px;font-size:13px;color:#718096;line-height:1.8">※ 東京しごと財団 令和8年度事業外スキルアップ助成金。都内本社の中小企業が対象。<br>※ 助成上限: 1人1研修あたり¥25,000。Jグランツで1ヶ月前の事前申請が必要です。<br>※ 申請手続きのサポートも行っております。お気軽にご相談ください。</p>
  </div>
</section>

<!-- Corporate -->
<section class="sec">
  <div class="wrap">
    <div class="corp-section">
      <div>
        <div class="sec-label">CORPORATE</div>
        <h2 class="sec-title">法人研修<br>カスタマイズ</h2>
        <p class="sec-desc" style="margin-bottom:28px">御社の業種・課題・既存システムに合わせて、コース内容をカスタマイズいたします。演習テーマを御社の業務に差し替え、研修後すぐに実務で活用できる構成に。</p>
        <a href="#inquiry-section" class="btn-corp">法人研修のご相談 →</a>
      </div>
      <div class="corp-grid">
        <div class="corp-item"><div class="corp-item-icon">🏭</div><h4>製造業</h4><p>生産管理・品質検査の自動化</p></div>
        <div class="corp-item"><div class="corp-item-icon">🏦</div><h4>金融</h4><p>リスク分析・レポート自動化</p></div>
        <div class="corp-item"><div class="corp-item-icon">🏥</div><h4>医療</h4><p>データ管理・予約システム</p></div>
        <div class="corp-item"><div class="corp-item-icon">🏗️</div><h4>建設</h4><p>施工管理・安全報告の効率化</p></div>
        <div class="corp-item"><div class="corp-item-icon">🚚</div><h4>物流</h4><p>配送最適化・在庫管理</p></div>
        <div class="corp-item"><div class="corp-item-icon">🏛️</div><h4>自治体</h4><p>住民サービス・窓口DX</p></div>
      </div>
    </div>
  </div>
</section>

<!-- FAQ -->
<section class="sec">
  <div class="wrap">
    <div class="sec-label">FAQ</div>
    <h2 class="sec-title">よくある質問</h2>
    <div style="margin-top:32px">
      <div class="faq-item"><div class="faq-q" onclick="toggleFaq(this)">プログラミング経験がなくても大丈夫ですか？</div><div class="faq-a">はい、コースAは完全未経験者向けに設計されています。パソコンの基本操作（文字入力・ブラウザ操作）ができれば十分です。</div></div>
      <div class="faq-item"><div class="faq-q" onclick="toggleFaq(this)">どのコースから始めればいいですか？</div><div class="faq-a">未経験の方はコースA（入門）から。プログラミング経験がある方やコースA修了者はコースB（実践）から始められます。上の「おすすめコース診断」もご活用ください。</div></div>
      <div class="faq-item"><div class="faq-q" onclick="toggleFaq(this)">オンラインでも受講できますか？</div><div class="faq-a">コースA〜Cは会場受講とオンライン受講をお選びいただけます。コースD（マスター）は対面でのワークショップが中心のため会場受講のみです。</div></div>
      <div class="faq-item"><div class="faq-q" onclick="toggleFaq(this)">使用するAIツールは何ですか？</div><div class="faq-a">主にCursor（AIコードエディタ）を使用します。Claude、ChatGPT等の生成AIも適宜活用します。特定のベンダーに依存しない、ツール横断的なスキルが身につきます。</div></div>
      <div class="faq-item"><div class="faq-q" onclick="toggleFaq(this)">助成金の申請は難しいですか？</div><div class="faq-a">東京しごと財団への申請はJグランツ（電子申請）で行います。必要書類の準備から申請まで、JGAIAがサポートいたします。受講の1ヶ月前までに事前申請が必要です。</div></div>
      <div class="faq-item"><div class="faq-q" onclick="toggleFaq(this)">受講後のサポートはありますか？</div><div class="faq-a">修了者向けのオンラインコミュニティ（Slack）をご用意しています。講師への質問、受講者同士の情報交換、最新ツール情報の共有にご活用いただけます。</div></div>
      <div class="faq-item"><div class="faq-q" onclick="toggleFaq(this)">修了証は発行されますか？</div><div class="faq-a">はい、各コース修了時にJGAIA認定の修了証を発行します。法人研修では受講者リストと受講証明書もお渡しします。</div></div>
      <div class="faq-item"><div class="faq-q" onclick="toggleFaq(this)">JQCAとJGAIAの講座の違いは？</div><div class="faq-a">JQCAは「AI×量子コンピューティング」に特化した講座です。JGAIAは量子要素を含まず「生成AI」に特化しており、ビジネスパーソン全般を対象としています。まずは生成AIから始めたい方はJGAIAがおすすめです。</div></div>
    </div>
  </div>
</section>

<!-- Contact + CTA -->
<div class="cta-section" id="inquiry-section" style="border-top:1px solid #e2e8f0">
  <div class="wrap">
    <div class="cta-inner">
      <div>
        <div class="sec-label">CONTACT</div>
        <h2 class="sec-title" style="margin-bottom:12px">お問い合わせ・<br>お申し込み</h2>
        <p style="font-size:15px;color:#4a5568;line-height:1.8;margin-bottom:28px">ご質問・お申し込み・法人研修のご相談など、お気軽にどうぞ。2営業日以内にご連絡いたします。</p>
        <form id="main-form" onsubmit="return submitForm(event, this)">
          <div class="form-group"><label>お名前 *</label><input type="text" name="name" required></div>
          <div class="form-group"><label>メールアドレス *</label><input type="email" name="email" required></div>
          <div class="form-group"><label>会社名（法人の方）</label><input type="text" name="company"></div>
          <div class="form-group"><label>ご興味のあるコース</label><select name="course"><option value="">選択してください</option><option>A: AIアプリ開発 入門（¥19,800）</option><option>B: AIアプリ開発 実践（¥49,800）</option><option>C: AIセキュリティ＆ガバナンス（¥49,800）</option><option>D: AIエンジニアリング マスター（¥128,000）</option><option>法人カスタマイズ研修</option></select></div>
          <div class="form-group"><label>お問い合わせ内容</label><textarea name="message" placeholder="ご質問やご要望をお書きください"></textarea></div>
          <button type="submit" class="btn-submit">送信する →</button>
          <div class="form-status" id="form-status"></div>
        </form>
      </div>
      <div class="cta-right">
        <div class="cta-item"><div class="cta-item-num">01</div><h4>¥19,800から</h4><p>3時間の入門コースで「自分にもできる」を体験</p></div>
        <div class="cta-item"><div class="cta-item-num">02</div><h4>助成金で半額以下</h4><p>東京しごと財団の助成金で実質¥6,600から</p></div>
        <div class="cta-item"><div class="cta-item-num">03</div><h4>JGAIA認定修了証</h4><p>各コース修了時に認定証を発行</p></div>
        <div class="cta-item"><div class="cta-item-num">04</div><h4>法人カスタマイズ</h4><p>御社の業種・課題に合わせた研修設計</p></div>
      </div>
    </div>
  </div>
</div>

<!-- Footer -->
<footer class="footer">
  <div class="footer-inner">
    <div class="footer-top">
      <div><div class="footer-brand-name">JGAIA</div><div class="footer-brand-ja">一般社団法人 日本生成AI協会</div><p class="footer-brand-desc">生成AIの普及・教育・資格認定・産業連携を推進し、持続可能で豊かな社会の実現に貢献します。</p></div>
      <div class="footer-col"><h5>協会情報</h5><ul><li><a href="/">協会概要</a></li><li><a href="/">代表理事ご挨拶</a></li></ul></div>
      <div class="footer-col"><h5>資格・講座</h5><ul><li><a href="/vibe-coding">バイブコーディング講座</a></li></ul></div>
      <div class="footer-col"><h5>サポート</h5><ul><li><a href="#inquiry-section">お問い合わせ</a></li></ul></div>
    </div>
    <div class="footer-bottom">
      <p>&copy; 2026 JGAIA — 一般社団法人 日本生成AI協会. All rights reserved.</p>
      <div class="footer-bottom-links"><a href="#">プライバシーポリシー</a><a href="#">サイト利用規約</a></div>
    </div>
  </div>
</footer>

<!-- Mobile CTA -->
<div class="mobile-cta"><a href="#inquiry-section">¥19,800〜 お問い合わせ・お申し込み →</a></div>

<script>
function toggleCurriculum(btn){var c=btn.nextElementSibling;c.classList.toggle('open');btn.textContent=c.classList.contains('open')?'カリキュラムを閉じる ×':'カリキュラムを見る →'}
function toggleApply(btn){var w=btn.nextElementSibling;if(w.classList.contains('open')){w.classList.remove('open');return}w.classList.add('open');if(w.querySelector('form'))return;var c=w.dataset.course;w.innerHTML='<form onsubmit="return submitForm(event,this)"><div class="form-group"><label>お名前 *</label><input type="text" name="name" required></div><div class="form-group"><label>メールアドレス *</label><input type="email" name="email" required></div><div class="form-group"><label>会社名</label><input type="text" name="company"></div><input type="hidden" name="course" value="'+c+'"><div class="form-group"><label>備考</label><textarea name="message" placeholder="ご質問があればお書きください"></textarea></div><button type="submit" class="btn-submit">申し込む →</button><div class="form-status"></div></form>'}
async function submitForm(e,form){e.preventDefault();var st=form.querySelector('.form-status'),btn=form.querySelector('button[type="submit"]'),d=Object.fromEntries(new FormData(form));btn.disabled=true;btn.textContent='送信中...';st.className='form-status';st.textContent='';try{var r=await fetch('/api/inquiry',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)});var j=await r.json();if(r.ok){st.className='form-status ok';st.textContent='送信しました。2営業日以内にご連絡いたします。';form.reset()}else throw new Error(j.error||'エラーが発生しました')}catch(err){st.className='form-status err';st.textContent=err.message}btn.disabled=false;btn.textContent=form.querySelector('[name="course"][type="hidden"]')?'申し込む →':'送信する →';return false}
function toggleFaq(el){el.classList.toggle('open');el.nextElementSibling.classList.toggle('open')}
var qs={};
function quizAnswer(q,v,el){qs['q'+q]=v;el.parentElement.querySelectorAll('.quiz-opt').forEach(function(o){o.classList.remove('sel')});el.classList.add('sel');if(q===1)document.getElementById('q2').style.display='';if(q===2)document.getElementById('q3').style.display='';if(q===3)showQuizResult()}
function showQuizResult(){var rec,desc;if(qs.q2==='team'){rec='コースD: AIエンジニアリング マスター';desc='組織導入をお考えなら、チーム戦略とROI測定まで学べるマスターコースが最適です。'}else if(qs.q3==='high'){rec='コースC: AIセキュリティ＆ガバナンス';desc='セキュリティ・ガバナンスへの関心が高い方に。社内ガイドライン策定まで実践します。'}else if(qs.q1==='none'||qs.q2==='try'){rec='コースA: AIアプリ開発 入門';desc='まずは3時間で「自分にもできる」を体験。¥19,800、助成金で実質¥6,600から。'}else{rec='コースB: AIアプリ開発 実践';desc='経験をお持ちの方に。6時間で業務アプリを企画→実装→デプロイまで完成させます。'}var el=document.getElementById('quiz-result');el.innerHTML='<h4>おすすめ: '+rec+'</h4><p>'+desc+'</p>';el.classList.add('show')}
var io=new IntersectionObserver(function(entries){entries.forEach(function(e){if(e.isIntersecting){e.target.style.opacity='1';e.target.style.transform='none';io.unobserve(e.target)}})},{threshold:.12,rootMargin:'0px 0px -40px 0px'});
document.querySelectorAll('.problem-card,.step-card,.course-card,.corp-item,.cta-item,.faq-item').forEach(function(el,i){el.style.cssText+='opacity:0;transform:translateY(20px);transition:opacity .5s '+i*.05+'s ease,transform .5s '+i*.05+'s ease;';io.observe(el)});
</script>
</body>
</html>"""
