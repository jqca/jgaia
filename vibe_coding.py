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
<meta property="og:image" content="https://jgaia-production.up.railway.app/static/img/hero.png">
<link rel="canonical" href="https://jgaia-production.up.railway.app/vibe-coding">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:ital,wght@0,300;0,400;0,500;1,300&family=Noto+Sans+JP:wght@300;400;500;700&display=swap" rel="stylesheet">

<script type="application/ld+json">
[
  {"@context":"https://schema.org","@type":"Course","name":"AIアプリ開発 入門","description":"3時間でAIを使ったアプリ開発を体験。プログラミング経験不要。","provider":{"@type":"Organization","name":"JGAIA 日本生成AI協会","url":"https://www.jgaia.org/"},"offers":{"@type":"Offer","price":"19800","priceCurrency":"JPY"}},
  {"@context":"https://schema.org","@type":"Course","name":"AIアプリ開発 実践","description":"6時間で業務アプリを企画から設計・実装・デプロイまで。","provider":{"@type":"Organization","name":"JGAIA 日本生成AI協会","url":"https://www.jgaia.org/"},"offers":{"@type":"Offer","price":"49800","priceCurrency":"JPY"}},
  {"@context":"https://schema.org","@type":"Course","name":"AIセキュリティ＆ガバナンス","description":"AI生成コードの脆弱性対策、プロンプトインジェクション防御、社内ガイドライン策定。","provider":{"@type":"Organization","name":"JGAIA 日本生成AI協会","url":"https://www.jgaia.org/"},"offers":{"@type":"Offer","price":"49800","priceCurrency":"JPY"}},
  {"@context":"https://schema.org","@type":"Course","name":"AIエンジニアリング マスター","description":"3日間でチーム導入戦略、マルチエージェント設計、CI/CD統合、ROI測定を習得。","provider":{"@type":"Organization","name":"JGAIA 日本生成AI協会","url":"https://www.jgaia.org/"},"offers":{"@type":"Offer","price":"128000","priceCurrency":"JPY"}}
]
</script>

<style>
:root{
  --ink:#09090b;--ink-s:#111118;--ink-m:#27272a;
  --text:#fafafa;--text-s:#a1a1aa;--text-m:#52525b;
  --accent:#6366f1;--accent-l:#818cf8;--accent-d:#4f46e5;
  --green:#10b981;--amber:#f59e0b;--purple:#8b5cf6;--red:#ef4444;
  --border:rgba(255,255,255,.07);--border-l:rgba(255,255,255,.12);
  --font-d:'Syne','Noto Sans JP',sans-serif;
  --font:'DM Sans','Noto Sans JP',sans-serif;
  --r:4px;--ease:cubic-bezier(.16,1,.3,1);
}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth;font-size:16px}
body{background:var(--ink);color:var(--text);font-family:var(--font);line-height:1.6;-webkit-font-smoothing:antialiased}
a{color:inherit;text-decoration:none}
img{display:block;max-width:100%}
button{cursor:pointer;border:none;background:none;font-family:inherit}

/* ── Header ── */
.hd{position:fixed;top:0;left:0;right:0;z-index:100;padding:0 48px;display:flex;align-items:center;height:72px;background:rgba(9,9,11,.88);backdrop-filter:blur(24px);border-bottom:1px solid var(--border)}
.hd-logo{display:flex;align-items:center;gap:11px;margin-right:48px;flex-shrink:0}
.hd-logo-mark{width:32px;height:32px;border-radius:6px;border:1px solid var(--border-l);display:flex;align-items:center;justify-content:center}
.hd-logo-mark svg{width:16px;height:16px;fill:none;stroke:#fff;stroke-width:1.5}
.hd-logo-text .en{font-family:var(--font-d);font-size:16px;font-weight:700;color:#fff;letter-spacing:.06em}
.hd-logo-text .ja{font-size:9px;color:var(--text-s);letter-spacing:.04em;margin-top:1px}
.hd-nav{display:flex;align-items:center;gap:2px;flex:1}
.hd-nav a{font-size:13.5px;font-weight:400;color:var(--text-s);padding:7px 14px;border-radius:var(--r);transition:color .15s,background .15s;white-space:nowrap}
.hd-nav a:hover{color:#fff;background:rgba(255,255,255,.06)}
.hd-nav a.active{color:#fff}
.hd-right{display:flex;align-items:center;gap:10px;margin-left:auto}
.btn-ghost-hd{font-size:13px;font-weight:500;color:var(--text-s);padding:8px 18px;border-radius:var(--r);border:1px solid var(--border-l);transition:all .15s}
.btn-ghost-hd:hover{color:#fff;border-color:rgba(255,255,255,.25);background:rgba(255,255,255,.05)}
.btn-solid{font-size:13px;font-weight:600;color:#fff;padding:9px 20px;border-radius:var(--r);background:var(--accent);transition:opacity .15s}
.btn-solid:hover{opacity:.85}

/* ── Section basics ── */
section{padding:120px 80px}
section+section{border-top:1px solid var(--border)}
.sec-label{display:inline-flex;align-items:center;gap:10px;font-size:10.5px;font-weight:600;letter-spacing:.2em;text-transform:uppercase;color:var(--accent-l);margin-bottom:20px}
.sec-label::before{content:'';width:16px;height:1px;background:var(--accent-l)}
.sec-title{font-family:var(--font-d);font-size:clamp(32px,4vw,52px);font-weight:800;color:#fff;line-height:1.1;letter-spacing:-.03em;margin-bottom:20px}
.sec-desc{font-size:15px;font-weight:300;color:var(--text-s);line-height:1.8;max-width:560px}

/* ── Hero ── */
.hero{position:relative;min-height:700px;display:flex;align-items:flex-end;overflow:hidden;padding:0;margin-top:72px}
.hero-bg{position:absolute;inset:0;background:var(--ink-s)}
.hero-bg::after{content:'';position:absolute;inset:0;background:linear-gradient(to top,rgba(9,9,11,1) 0%,rgba(9,9,11,.5) 40%,rgba(9,9,11,.15) 100%),linear-gradient(to right,rgba(9,9,11,.7) 0%,transparent 60%)}
.hero-content{position:relative;z-index:1;padding:0 80px 96px;max-width:900px}
.hero-eyebrow{display:inline-flex;align-items:center;gap:10px;font-size:11px;font-weight:600;letter-spacing:.2em;text-transform:uppercase;color:var(--accent-l);margin-bottom:28px}
.hero-eyebrow::before{content:'';width:24px;height:1px;background:var(--accent-l)}
.hero h1{font-family:var(--font-d);font-size:clamp(40px,5.5vw,72px);font-weight:800;line-height:1.08;color:#fff;letter-spacing:-.03em;margin-bottom:28px}
.hero h1 em{font-style:normal;color:transparent;-webkit-text-stroke:1px rgba(255,255,255,.5)}
.hero-sub{font-size:16px;font-weight:300;color:rgba(255,255,255,.65);line-height:1.8;max-width:520px;margin-bottom:44px}
.hero-actions{display:flex;align-items:center;gap:16px;flex-wrap:wrap}
.btn-primary{display:inline-flex;align-items:center;gap:10px;font-size:14px;font-weight:600;color:#fff;background:var(--accent);padding:14px 30px;border-radius:var(--r);transition:all .2s var(--ease)}
.btn-primary:hover{background:var(--accent-d);transform:translateY(-1px)}
.btn-ghost{display:inline-flex;align-items:center;gap:10px;font-size:14px;font-weight:400;color:rgba(255,255,255,.7);padding:14px 20px;border-radius:var(--r);border:1px solid rgba(255,255,255,.15);transition:all .2s}
.btn-ghost:hover{color:#fff;border-color:rgba(255,255,255,.35)}

/* ── Stats bar ── */
.stats-bar{border-top:1px solid var(--border);border-bottom:1px solid var(--border);padding:48px 80px;display:grid;grid-template-columns:repeat(4,1fr)}
.stat-item{padding:0 40px 0 0;border-right:1px solid var(--border)}
.stat-item:last-child{border-right:none;padding-right:0;padding-left:40px}
.stat-item:not(:first-child){padding-left:40px}
.stat-n{font-family:var(--font-d);font-size:48px;font-weight:800;color:#fff;line-height:1;margin-bottom:8px;letter-spacing:-.03em}
.stat-n sup{font-size:24px;vertical-align:super;font-weight:600}
.stat-lb{font-size:12px;color:var(--text-s);letter-spacing:.04em}
.stat-ds{font-size:11px;color:var(--text-m);margin-top:4px}

/* ── Problems ── */
.sec-header-2col{display:grid;grid-template-columns:1fr 1fr;gap:80px;align-items:end;margin-bottom:64px}
.problems-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:var(--border);border:1px solid var(--border)}
.problem-card{background:var(--ink-s);padding:36px 24px;transition:background .3s}
.problem-card:hover{background:rgba(99,102,241,.06)}
.problem-num{font-family:var(--font-d);font-size:11px;font-weight:700;letter-spacing:.2em;color:var(--accent-l);margin-bottom:16px}
.problem-icon{font-size:28px;margin-bottom:16px;filter:grayscale(.3)}
.problem-card h3{font-family:var(--font-d);font-size:15px;font-weight:700;color:#fff;margin-bottom:10px}
.problem-card p{font-size:12.5px;color:rgba(255,255,255,.55);line-height:1.7}

/* ── Steps ── */
.steps-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:1px;background:var(--border);border:1px solid var(--border);margin-top:64px}
.step-card{background:var(--ink-s);padding:48px 32px;text-align:center;transition:background .3s}
.step-card:hover{background:rgba(99,102,241,.06)}
.step-num-circle{display:inline-flex;align-items:center;justify-content:center;width:44px;height:44px;border-radius:50%;border:1px solid var(--border-l);font-family:var(--font-d);font-weight:800;font-size:18px;color:var(--accent-l);margin-bottom:20px}
.step-card h3{font-family:var(--font-d);font-size:17px;font-weight:700;color:#fff;margin-bottom:12px;line-height:1.4}
.step-card p{font-size:13px;color:var(--text-s);line-height:1.7}

/* ── Courses ── */
.courses-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:1px;background:var(--border);border:1px solid var(--border)}
.course-card{background:var(--ink-s);position:relative;transition:background .3s}
.course-card:hover{background:rgba(99,102,241,.04)}
.course-head{padding:28px 32px 0;display:flex;align-items:center;gap:12px}
.course-step-tag{font-family:var(--font-d);font-size:10px;font-weight:700;letter-spacing:.15em;color:#fff;padding:4px 12px;border-radius:2px;white-space:nowrap}
.c-a .course-step-tag{background:rgba(99,102,241,.6)}
.c-b .course-step-tag{background:rgba(16,185,129,.6)}
.c-c .course-step-tag{background:rgba(245,158,11,.6)}
.c-d .course-step-tag{background:rgba(139,92,246,.6)}
.course-card h3{font-family:var(--font-d);font-size:20px;font-weight:700;color:#fff}
.course-body{padding:20px 32px 32px}
.course-meta{display:flex;gap:16px;flex-wrap:wrap;margin-bottom:16px;font-size:12.5px;color:var(--text-s)}
.course-meta span{display:flex;align-items:center;gap:4px}
.course-desc{font-size:13.5px;color:rgba(255,255,255,.55);line-height:1.7;margin-bottom:20px}
.course-price{display:flex;align-items:baseline;gap:8px;margin-bottom:8px}
.price-main{font-family:var(--font-d);font-size:28px;font-weight:800;color:#fff;letter-spacing:-.02em}
.price-sub{font-size:12px;color:var(--text-s)}
.price-subsidy{font-size:12px;color:var(--green);font-weight:500;margin-bottom:20px}
.toggle-btn{font-size:13px;font-weight:500;color:var(--text-s);padding:10px 20px;border-radius:var(--r);border:1px solid var(--border-l);transition:all .2s;width:100%}
.toggle-btn:hover{color:#fff;border-color:rgba(255,255,255,.25);background:rgba(255,255,255,.05)}
.curriculum{display:none;margin-top:20px}
.curriculum.open{display:block}
.curriculum ul{list-style:none}
.curriculum li{font-size:13px;color:var(--text-s);padding:8px 0;border-bottom:1px solid var(--border);display:flex;align-items:flex-start;gap:8px}
.curriculum li::before{content:"✓";color:var(--green);font-weight:700;flex-shrink:0}
.apply-wrap{display:none;margin-top:20px}
.apply-wrap.open{display:block}

/* ── Quiz ── */
.quiz-wrap{margin-top:64px;padding:48px;background:var(--ink-s);border:1px solid var(--border)}
.quiz-wrap h3{font-family:var(--font-d);font-size:20px;font-weight:700;color:#fff;margin-bottom:8px}
.quiz-wrap>p{font-size:14px;color:var(--text-s);margin-bottom:32px}
.quiz-q{margin-bottom:24px}
.quiz-q label{font-size:14px;font-weight:600;color:#fff;display:block;margin-bottom:12px}
.quiz-opts{display:flex;gap:8px;flex-wrap:wrap}
.quiz-opt{background:var(--ink);border:1px solid var(--border-l);border-radius:var(--r);padding:10px 20px;font-size:13px;color:var(--text-s);cursor:pointer;transition:all .15s}
.quiz-opt:hover,.quiz-opt.sel{border-color:var(--accent);color:#fff;background:rgba(99,102,241,.1)}
.quiz-result{display:none;padding:24px;border-left:2px solid var(--accent);margin-top:20px}
.quiz-result.show{display:block}
.quiz-result h4{font-family:var(--font-d);font-size:16px;font-weight:700;color:var(--accent-l);margin-bottom:8px}
.quiz-result p{font-size:14px;color:var(--text-s);line-height:1.7}

/* ── Subsidy ── */
.subsidy-table{width:100%;border-collapse:collapse;margin-top:32px;font-size:14px}
.subsidy-table th,.subsidy-table td{padding:14px 20px;border-bottom:1px solid var(--border);text-align:left}
.subsidy-table th{font-size:11px;color:var(--text-m);font-weight:600;letter-spacing:.06em;text-transform:uppercase}
.subsidy-table .hi{color:var(--green);font-weight:600}

/* ── Corporate ── */
.corp-section{display:grid;grid-template-columns:1fr 1fr;gap:80px;align-items:center}
.corp-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:1px;background:var(--border);border:1px solid var(--border)}
.corp-item{background:var(--ink-s);padding:28px;transition:background .2s}
.corp-item:hover{background:rgba(99,102,241,.06)}
.corp-item-icon{font-size:24px;margin-bottom:12px}
.corp-item h4{font-family:var(--font-d);font-size:14px;font-weight:700;color:#fff;margin-bottom:6px}
.corp-item p{font-size:12px;color:var(--text-s);line-height:1.7}

/* ── Instructor ── */
.instructor-section{display:grid;grid-template-columns:1fr 1fr;gap:0;background:var(--ink-s);border-top:1px solid var(--border);border-bottom:1px solid var(--border);padding:0}
.instructor-photo-wrap{position:relative;overflow:hidden;min-height:500px}
.instructor-photo-wrap img{width:100%;height:100%;object-fit:cover;object-position:center top;filter:grayscale(20%)}
.instructor-photo-wrap::after{content:'';position:absolute;inset:0;background:linear-gradient(to right,transparent 70%,var(--ink-s) 100%)}
.instructor-text{padding:80px;display:flex;flex-direction:column;justify-content:center}
.instructor-text blockquote{font-family:var(--font-d);font-size:clamp(20px,2.2vw,28px);font-weight:700;color:#fff;line-height:1.4;letter-spacing:-.02em;margin-bottom:32px;border-left:2px solid var(--accent);padding-left:24px}
.instructor-body{font-size:14px;font-weight:300;color:var(--text-s);line-height:1.9;margin-bottom:32px}
.instructor-sig{display:flex;align-items:center;gap:20px;padding-top:28px;border-top:1px solid var(--border)}
.instructor-sig-avatar{width:48px;height:48px;border-radius:50%;background:var(--ink-m);border:1px solid var(--border-l);overflow:hidden;flex-shrink:0}
.instructor-sig-avatar img{width:100%;height:100%;object-fit:cover}
.instructor-sig-name{font-family:var(--font-d);font-size:15px;font-weight:700;color:#fff}
.instructor-sig-role{font-size:11.5px;color:var(--text-m);margin-top:2px}

/* ── FAQ ── */
.faq-item{border-bottom:1px solid var(--border);padding:20px 0}
.faq-q{font-size:14px;font-weight:500;color:#fff;cursor:pointer;display:flex;justify-content:space-between;align-items:center;transition:color .15s}
.faq-q:hover{color:var(--accent-l)}
.faq-q::after{content:"+";font-family:var(--font-d);font-size:20px;color:var(--text-m);transition:transform .2s;flex-shrink:0;margin-left:16px}
.faq-q.open::after{transform:rotate(45deg)}
.faq-a{max-height:0;overflow:hidden;transition:max-height .4s var(--ease);font-size:13.5px;color:var(--text-s);line-height:1.8}
.faq-a.open{max-height:500px;padding-top:12px}

/* ── Form ── */
.form-group{margin-bottom:16px}
.form-group label{display:block;font-size:12px;font-weight:600;color:var(--text-s);letter-spacing:.04em;margin-bottom:6px}
.form-group input,.form-group select,.form-group textarea{width:100%;padding:12px 16px;font-size:14px;background:var(--ink);border:1px solid var(--border-l);border-radius:var(--r);color:var(--text);font-family:var(--font);transition:border-color .15s}
.form-group input:focus,.form-group select:focus,.form-group textarea:focus{outline:none;border-color:var(--accent)}
.form-group textarea{min-height:100px;resize:vertical}
.form-status{font-size:13px;margin-top:10px;min-height:20px}
.form-status.ok{color:var(--green)}
.form-status.err{color:var(--red)}

/* ── CTA ── */
.cta-section{padding:120px 80px;background:var(--ink-s);border-top:1px solid var(--border);display:grid;grid-template-columns:1fr 1fr;gap:80px;align-items:center}
.cta-right{display:grid;grid-template-columns:1fr 1fr;gap:1px;background:var(--border);border:1px solid var(--border)}
.cta-item{background:var(--ink-s);padding:32px;transition:background .2s}
.cta-item:hover{background:rgba(99,102,241,.06)}
.cta-item-num{font-family:var(--font-d);font-size:11px;font-weight:700;letter-spacing:.2em;color:var(--accent-l);margin-bottom:16px}
.cta-item h4{font-family:var(--font-d);font-size:16px;font-weight:700;color:#fff;margin-bottom:8px}
.cta-item p{font-size:12.5px;color:var(--text-s);line-height:1.7}

/* ── Footer ── */
.footer{padding:72px 80px 40px;border-top:1px solid var(--border)}
.footer-top{display:grid;grid-template-columns:1.6fr 1fr 1fr 1fr;gap:48px;margin-bottom:64px}
.footer-brand-name{font-family:var(--font-d);font-size:15px;font-weight:700;color:#fff;margin-bottom:6px}
.footer-brand-ja{font-size:11px;color:var(--text-m);margin-bottom:20px;letter-spacing:.04em}
.footer-brand-desc{font-size:13px;color:var(--text-m);line-height:1.75}
.footer-col h5{font-size:10.5px;font-weight:700;letter-spacing:.15em;text-transform:uppercase;color:var(--text-m);margin-bottom:18px}
.footer-col ul{list-style:none}
.footer-col li+li{margin-top:12px}
.footer-col a{font-size:13.5px;color:var(--text-s);transition:color .15s}
.footer-col a:hover{color:#fff}
.footer-bottom{display:flex;align-items:center;justify-content:space-between;padding-top:28px;border-top:1px solid var(--border)}
.footer-bottom p{font-size:12px;color:var(--text-m)}
.footer-bottom-links{display:flex;gap:24px}
.footer-bottom-links a{font-size:12px;color:var(--text-m);transition:color .15s}
.footer-bottom-links a:hover{color:var(--text-s)}

/* ── Mobile CTA ── */
.mobile-cta{display:none;position:fixed;bottom:0;left:0;right:0;background:rgba(9,9,11,.95);backdrop-filter:blur(10px);padding:12px 24px;z-index:100;border-top:1px solid var(--border)}
.mobile-cta a{display:block;text-align:center;font-size:14px;font-weight:600;color:#fff;background:var(--accent);padding:14px;border-radius:var(--r)}

/* ── Responsive ── */
@media(max-width:1024px){
  section{padding:80px 40px}
  .hd{padding:0 24px}
  .hero-content{padding:0 40px 72px}
  .stats-bar{padding:40px}
  .sec-header-2col,.corp-section{grid-template-columns:1fr;gap:32px}
  .problems-grid{grid-template-columns:repeat(2,1fr)}
  .courses-grid{grid-template-columns:1fr}
  .instructor-section{grid-template-columns:1fr}
  .cta-section{grid-template-columns:1fr;padding:80px 40px}
  .footer{padding:64px 40px 32px}
  .footer-top{grid-template-columns:1fr 1fr;gap:32px}
}
@media(max-width:768px){
  .hd-nav,.hd-right .btn-ghost-hd{display:none}
  section{padding:64px 24px}
  .hero h1{font-size:32px}
  .hero{min-height:500px}
  .hero-content{padding:0 24px 56px}
  .stats-bar{grid-template-columns:repeat(2,1fr);padding:32px 24px;gap:0}
  .stat-item:nth-child(2){border-right:none}
  .stat-item:nth-child(3){border-top:1px solid var(--border);border-right:1px solid var(--border)}
  .problems-grid,.steps-grid{grid-template-columns:1fr}
  .quiz-wrap{padding:32px 24px}
  .instructor-photo-wrap{min-height:320px}
  .instructor-text{padding:40px 24px}
  .cta-right{grid-template-columns:1fr}
  .footer-top{grid-template-columns:1fr}
  .mobile-cta{display:block}
}
</style>
</head>
<body>

<!-- Header -->
<header class="hd">
  <a href="/" class="hd-logo">
    <div class="hd-logo-mark"><svg viewBox="0 0 24 24"><polygon points="12,2 22,8 22,16 12,22 2,16 2,8"/><line x1="12" y1="2" x2="12" y2="22"/><line x1="2" y1="8" x2="22" y2="8"/><line x1="2" y1="16" x2="22" y2="16"/></svg></div>
    <div class="hd-logo-text"><div class="en">JGAIA</div><div class="ja">一般社団法人 日本生成AI協会</div></div>
  </a>
  <nav class="hd-nav">
    <a href="/">ホーム</a>
    <a href="/#">協会情報</a>
    <a href="/vibe-coding" class="active">資格・講座</a>
    <a href="/#">協会員一覧</a>
    <a href="/#">協会員募集</a>
    <a href="#inquiry-section">お問い合わせ</a>
  </nav>
  <div class="hd-right">
    <a href="#" class="btn-ghost-hd">ログイン</a>
    <a href="#inquiry-section" class="btn-solid">お問い合わせ</a>
  </div>
</header>

<!-- Hero -->
<section class="hero">
  <div class="hero-bg"></div>
  <div class="hero-content">
    <div class="hero-eyebrow">JGAIA CERTIFIED COURSE</div>
    <h1>コードを書かない<br>時代の、<br><em>アプリ開発。</em></h1>
    <p class="hero-sub">AIに指示するだけで、あなたのアイデアが動き出す。<br>プログラミング経験ゼロから、3時間で最初のアプリを。</p>
    <div class="hero-actions">
      <a href="#courses" class="btn-primary">講座ラインナップ <span>→</span></a>
      <a href="#quiz" class="btn-ghost">おすすめコース診断</a>
    </div>
  </div>
</section>

<!-- Stats bar -->
<div class="stats-bar">
  <div class="stat-item"><div class="stat-n">40<sup>%</sup></div><div class="stat-lb">バイブコーディング</div><div class="stat-ds">2028年の本番ソフト — Gartner予測</div></div>
  <div class="stat-item"><div class="stat-n">75<sup>%</sup></div><div class="stat-lb">AIツール採用率</div><div class="stat-ds">2028年の開発者 — Gartner予測</div></div>
  <div class="stat-item"><div class="stat-n">79<sup>万人</sup></div><div class="stat-lb">IT人材不足</div><div class="stat-ds">2030年 — 経産省推計</div></div>
  <div class="stat-item"><div class="stat-n">1/10</div><div class="stat-lb">開発コスト</div><div class="stat-ds">従来比削減 — 当協会実績</div></div>
</div>

<!-- Problems -->
<section>
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
</section>

<!-- What is Vibe Coding -->
<section>
  <div class="sec-label">WHAT IS VIBE CODING</div>
  <h2 class="sec-title">バイブコーディングとは？</h2>
  <p class="sec-desc" style="margin-bottom:0">2025年にAI研究者 Andrej Karpathy が提唱した新しい開発スタイル。AIコーディングエージェントに実装を任せ、人間はアイデアと設計に集中します。</p>
  <div class="steps-grid">
    <div class="step-card"><div class="step-num-circle">1</div><h3>作りたいものを<br>言葉で伝える</h3><p>「顧客管理アプリを作って」「グラフで売上を可視化して」— 日本語で指示するだけ。</p></div>
    <div class="step-card"><div class="step-num-circle">2</div><h3>AIが<br>コードを書く</h3><p>Cursor、Claude Code 等のAIツールが、あなたの指示を元にアプリのコードを自動生成。</p></div>
    <div class="step-card"><div class="step-num-circle">3</div><h3>動くアプリが<br>完成する</h3><p>数時間で実際に動くアプリが完成。修正も「ここを変えて」と言うだけ。</p></div>
  </div>
</section>

<!-- Courses -->
<section id="courses">
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
</section>

<!-- Subsidy -->
<section id="subsidy">
  <div class="sec-label">SUBSIDY</div>
  <h2 class="sec-title">助成金で、<br>実質半額以下に</h2>
  <p class="sec-desc">東京しごと財団「事業外スキルアップ助成金」を利用すると、受講料の最大2/3が助成されます。</p>
  <table class="subsidy-table">
    <thead><tr><th>コース</th><th>受講料</th><th>小規模企業（2/3助成）</th><th>中小企業（1/2助成）</th></tr></thead>
    <tbody>
      <tr><td>A: 入門（3h）</td><td>¥19,800</td><td class="hi">実質 ¥6,600</td><td class="hi">実質 ¥9,900</td></tr>
      <tr><td>B: 実践（6h）</td><td>¥49,800</td><td class="hi">実質 ¥24,800</td><td class="hi">実質 ¥24,800</td></tr>
      <tr><td>C: セキュリティ（6h）</td><td>¥49,800</td><td class="hi">実質 ¥24,800</td><td class="hi">実質 ¥24,800</td></tr>
      <tr><td>D: マスター（3日間）</td><td>¥128,000</td><td colspan="2" style="color:var(--text-s)">助成上限¥25,000 → 実質 ¥103,000</td></tr>
    </tbody>
  </table>
  <p style="margin-top:20px;font-size:13px;color:var(--text-m);line-height:1.8">※ 東京しごと財団 令和8年度事業外スキルアップ助成金。都内本社の中小企業が対象。<br>※ 助成上限: 1人1研修あたり¥25,000。Jグランツで1ヶ月前の事前申請が必要です。<br>※ 申請手続きのサポートも行っております。お気軽にご相談ください。</p>
</section>

<!-- Corporate -->
<section>
  <div class="corp-section">
    <div>
      <div class="sec-label">CORPORATE</div>
      <h2 class="sec-title">法人研修<br>カスタマイズ</h2>
      <p class="sec-desc" style="margin-bottom:36px">御社の業種・課題・既存システムに合わせて、コース内容をカスタマイズいたします。演習テーマを御社の業務に差し替え、研修後すぐに実務で活用できる構成に。</p>
      <a href="#inquiry-section" class="btn-primary">法人研修のご相談 →</a>
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
</section>

<!-- Instructor -->
<div class="instructor-section">
  <div class="instructor-photo-wrap">
    <img src="/static/img/representative.png" alt="高野秀隆" onerror="this.parentElement.style.background='var(--ink-m)'">
  </div>
  <div class="instructor-text">
    <div class="sec-label">INSTRUCTOR</div>
    <blockquote>「技術を事業に変える。<br>非エンジニアこそ、<br>AIの主役になれる。」</blockquote>
    <p class="instructor-body">AI×量子コンピューティングの両分野で国家プロジェクト（SIP・NEDO）を推進。JQCA（日本量子コンピューティング協会）では会員1,030名・資格取得者450名の実績。<br><br>「技術を事業に変える」実践者として、非エンジニアでもAIを使いこなせる教育プログラムを設計。バイブコーディング講座では、受講者が3時間で実際に動くアプリを完成させることを重視しています。</p>
    <div class="instructor-sig">
      <div class="instructor-sig-avatar"><img src="/static/img/representative.png" alt="" onerror="this.style.display='none'"></div>
      <div><div class="instructor-sig-name">高野 秀隆</div><div class="instructor-sig-role">一般社団法人 日本生成AI協会 代表理事</div></div>
    </div>
  </div>
</div>

<!-- FAQ -->
<section>
  <div class="sec-label">FAQ</div>
  <h2 class="sec-title">よくある質問</h2>
  <div style="margin-top:40px">
    <div class="faq-item"><div class="faq-q" onclick="toggleFaq(this)">プログラミング経験がなくても大丈夫ですか？</div><div class="faq-a">はい、コースAは完全未経験者向けに設計されています。パソコンの基本操作（文字入力・ブラウザ操作）ができれば十分です。</div></div>
    <div class="faq-item"><div class="faq-q" onclick="toggleFaq(this)">どのコースから始めればいいですか？</div><div class="faq-a">未経験の方はコースA（入門）から。プログラミング経験がある方やコースA修了者はコースB（実践）から始められます。上の「おすすめコース診断」もご活用ください。</div></div>
    <div class="faq-item"><div class="faq-q" onclick="toggleFaq(this)">オンラインでも受講できますか？</div><div class="faq-a">コースA〜Cは会場受講とオンライン受講をお選びいただけます。コースD（マスター）は対面でのワークショップが中心のため会場受講のみです。</div></div>
    <div class="faq-item"><div class="faq-q" onclick="toggleFaq(this)">使用するAIツールは何ですか？</div><div class="faq-a">主にCursor（AIコードエディタ）を使用します。Claude、ChatGPT等の生成AIも適宜活用します。特定のベンダーに依存しない、ツール横断的なスキルが身につきます。</div></div>
    <div class="faq-item"><div class="faq-q" onclick="toggleFaq(this)">助成金の申請は難しいですか？</div><div class="faq-a">東京しごと財団への申請はJグランツ（電子申請）で行います。必要書類の準備から申請まで、JGAIAがサポートいたします。受講の1ヶ月前までに事前申請が必要です。</div></div>
    <div class="faq-item"><div class="faq-q" onclick="toggleFaq(this)">受講後のサポートはありますか？</div><div class="faq-a">修了者向けのオンラインコミュニティ（Slack）をご用意しています。講師への質問、受講者同士の情報交換、最新ツール情報の共有にご活用いただけます。</div></div>
    <div class="faq-item"><div class="faq-q" onclick="toggleFaq(this)">修了証は発行されますか？</div><div class="faq-a">はい、各コース修了時にJGAIA認定の修了証を発行します。法人研修では受講者リストと受講証明書もお渡しします。</div></div>
    <div class="faq-item"><div class="faq-q" onclick="toggleFaq(this)">JQCAとJGAIAの講座の違いは？</div><div class="faq-a">JQCAは「AI×量子コンピューティング」に特化した講座です。JGAIAは量子要素を含まず「生成AI」に特化しており、ビジネスパーソン全般を対象としています。まずは生成AIから始めたい方はJGAIAがおすすめです。</div></div>
  </div>
</section>

<!-- Contact + CTA -->
<div class="cta-section" id="inquiry-section">
  <div>
    <div class="sec-label">CONTACT</div>
    <h2 class="sec-title" style="margin-bottom:16px">お問い合わせ・<br>お申し込み</h2>
    <p style="font-size:15px;font-weight:300;color:var(--text-s);line-height:1.8;margin-bottom:32px">ご質問・お申し込み・法人研修のご相談など、お気軽にどうぞ。2営業日以内にご連絡いたします。</p>
    <form id="main-form" onsubmit="return submitForm(event, this)">
      <div class="form-group"><label>お名前 *</label><input type="text" name="name" required></div>
      <div class="form-group"><label>メールアドレス *</label><input type="email" name="email" required></div>
      <div class="form-group"><label>会社名（法人の方）</label><input type="text" name="company"></div>
      <div class="form-group"><label>ご興味のあるコース</label><select name="course"><option value="">選択してください</option><option>A: AIアプリ開発 入門（¥19,800）</option><option>B: AIアプリ開発 実践（¥49,800）</option><option>C: AIセキュリティ＆ガバナンス（¥49,800）</option><option>D: AIエンジニアリング マスター（¥128,000）</option><option>法人カスタマイズ研修</option></select></div>
      <div class="form-group"><label>お問い合わせ内容</label><textarea name="message" placeholder="ご質問やご要望をお書きください"></textarea></div>
      <button type="submit" class="btn-primary" style="width:100%;justify-content:center">送信する →</button>
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

<!-- Footer -->
<footer class="footer">
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
</footer>

<!-- Mobile CTA -->
<div class="mobile-cta"><a href="#inquiry-section">¥19,800〜 お問い合わせ・お申し込み →</a></div>

<script>
function toggleCurriculum(btn){var c=btn.nextElementSibling;c.classList.toggle('open');btn.textContent=c.classList.contains('open')?'カリキュラムを閉じる ×':'カリキュラムを見る →'}
function toggleApply(btn){var w=btn.nextElementSibling;if(w.classList.contains('open')){w.classList.remove('open');return}w.classList.add('open');if(w.querySelector('form'))return;var c=w.dataset.course;w.innerHTML='<form onsubmit="return submitForm(event,this)"><div class="form-group"><label>お名前 *</label><input type="text" name="name" required></div><div class="form-group"><label>メールアドレス *</label><input type="email" name="email" required></div><div class="form-group"><label>会社名</label><input type="text" name="company"></div><input type="hidden" name="course" value="'+c+'"><div class="form-group"><label>備考</label><textarea name="message" placeholder="ご質問があればお書きください"></textarea></div><button type="submit" class="btn-primary" style="width:100%;justify-content:center">申し込む →</button><div class="form-status"></div></form>'}
async function submitForm(e,form){e.preventDefault();var st=form.querySelector('.form-status'),btn=form.querySelector('button[type="submit"]'),d=Object.fromEntries(new FormData(form));btn.disabled=true;btn.textContent='送信中...';st.className='form-status';st.textContent='';try{var r=await fetch('/api/inquiry',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)});var j=await r.json();if(r.ok){st.className='form-status ok';st.textContent='送信しました。2営業日以内にご連絡いたします。';form.reset()}else throw new Error(j.error||'エラーが発生しました')}catch(err){st.className='form-status err';st.textContent=err.message}btn.disabled=false;btn.textContent=form.querySelector('[name="course"][type="hidden"]')?'申し込む →':'送信する →';return false}
function toggleFaq(el){el.classList.toggle('open');el.nextElementSibling.classList.toggle('open')}
var qs={};
function quizAnswer(q,v,el){qs['q'+q]=v;el.parentElement.querySelectorAll('.quiz-opt').forEach(function(o){o.classList.remove('sel')});el.classList.add('sel');if(q===1)document.getElementById('q2').style.display='';if(q===2)document.getElementById('q3').style.display='';if(q===3)showQuizResult()}
function showQuizResult(){var rec,desc;if(qs.q2==='team'){rec='コースD: AIエンジニアリング マスター';desc='組織導入をお考えなら、チーム戦略とROI測定まで学べるマスターコースが最適です。'}else if(qs.q3==='high'){rec='コースC: AIセキュリティ＆ガバナンス';desc='セキュリティ・ガバナンスへの関心が高い方に。社内ガイドライン策定まで実践します。'}else if(qs.q1==='none'||qs.q2==='try'){rec='コースA: AIアプリ開発 入門';desc='まずは3時間で「自分にもできる」を体験。¥19,800、助成金で実質¥6,600から。'}else{rec='コースB: AIアプリ開発 実践';desc='経験をお持ちの方に。6時間で業務アプリを企画→実装→デプロイまで完成させます。'}var el=document.getElementById('quiz-result');el.innerHTML='<h4>おすすめ: '+rec+'</h4><p>'+desc+'</p>';el.classList.add('show')}
var io=new IntersectionObserver(function(entries){entries.forEach(function(e){if(e.isIntersecting){e.target.style.opacity='1';e.target.style.transform='none';io.unobserve(e.target)}})},{threshold:.12,rootMargin:'0px 0px -40px 0px'});
document.querySelectorAll('.problem-card,.step-card,.course-card,.corp-item,.cta-item,.faq-item').forEach(function(el,i){el.style.cssText+='opacity:0;transform:translateY(24px);transition:opacity .6s '+i*.06+'s cubic-bezier(.16,1,.3,1),transform .6s '+i*.06+'s cubic-bezier(.16,1,.3,1);';io.observe(el)});
</script>
</body>
</html>"""
