"""JGAIA バイブコーディング講座 子ども向けコース（GK1/GK2/GK3）"""
import os
from flask import Response, request, jsonify

RESEND_API_KEY = os.getenv('RESEND_API_KEY', '')


def register_vibe_coding_kids_routes(app):
    @app.route('/vibe-coding/kids')
    def vibe_coding_kids():
        return Response(KIDS_HTML, mimetype='text/html')

    @app.route('/api/kids-inquiry', methods=['POST'])
    def kids_inquiry_api():
        data = request.get_json() or {}
        parent_name = data.get('parent_name', '')
        child_age = data.get('child_age', '')
        email = data.get('email', '')
        phone = data.get('phone', '')
        course = data.get('course', '')
        message = data.get('message', '')

        if not all([parent_name, child_age, email, course]):
            return jsonify({'success': False, 'error': 'missing fields'})

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
            resend.Emails.send({
                "from": "JGAIA キッズ講座 <info@jgaia.org>",
                "to": ["info@jgaia.org"],
                "subject": f"【キッズ講座】お問い合わせ: {parent_name}様",
                "text": admin_body,
            })

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


KIDS_HTML = r"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>キッズ・バイブコーディング | JGAIA 子ども向け生成AI講座</title>
<meta name="description" content="AIに話しかけるだけでアプリが作れる。小学生・中学生向けバイブコーディング体験講座。JGAIA認定修了証発行。プログラミング経験不要。">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=Noto+Sans+JP:wght@300;400;500;700&family=DM+Sans:ital,wght@0,300;0,400;0,500;0,600;0,700;1,300&display=swap" rel="stylesheet">
<style>
  :root {
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
  }
  *,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
  html{scroll-behavior:smooth;font-size:16px}
  body{
    background:var(--ink);color:var(--text);
    font-family:var(--font);line-height:1.6;
    -webkit-font-smoothing:antialiased;
  }
  a{color:inherit;text-decoration:none}
  img{display:block;max-width:100%}
  button{cursor:pointer;border:none;background:none;font-family:inherit}

  /* ── NAV ── */
  .hd{
    position:fixed;top:0;left:0;right:0;z-index:100;
    padding:0 48px;height:72px;
    display:flex;align-items:center;
    background:rgba(9,9,11,0.88);
    backdrop-filter:blur(24px);
    border-bottom:1px solid var(--border);
  }
  .hd-logo{
    display:flex;align-items:center;gap:11px;
    margin-right:48px;flex-shrink:0;
  }
  .hd-logo-mark{
    width:32px;height:32px;border-radius:6px;
    border:1px solid var(--border-l);
    display:flex;align-items:center;justify-content:center;
  }
  .hd-logo-mark svg{width:16px;height:16px;fill:none;stroke:#fff;stroke-width:1.5}
  .hd-logo-text .en{
    font-family:var(--font-d);font-size:16px;font-weight:700;
    color:#fff;letter-spacing:.06em;
  }
  .hd-logo-text .ja{font-size:9px;color:var(--text-s);letter-spacing:.04em;margin-top:1px}
  .hd-nav{display:flex;align-items:center;gap:2px;flex:1}
  .hd-nav a{
    font-size:13.5px;font-weight:400;color:var(--text-s);
    padding:7px 14px;border-radius:var(--r);
    transition:color .15s,background .15s;white-space:nowrap;
  }
  .hd-nav a:hover{color:#fff;background:rgba(255,255,255,0.06)}
  .hd-right{display:flex;align-items:center;gap:10px;margin-left:auto}
  .btn-ghost{
    font-size:13px;font-weight:500;color:var(--text-s);
    padding:8px 18px;border-radius:var(--r);
    border:1px solid var(--border-l);transition:all .15s;
  }
  .btn-ghost:hover{color:#fff;border-color:rgba(255,255,255,0.25);background:rgba(255,255,255,0.05)}
  .btn-solid{
    font-size:13px;font-weight:600;color:#fff;
    padding:9px 20px;border-radius:var(--r);
    background:var(--accent);transition:opacity .15s;
  }
  .btn-solid:hover{opacity:.85}

  /* ── HERO ── */
  .hero{
    position:relative;min-height:100vh;
    display:flex;align-items:center;justify-content:center;
    text-align:center;overflow:hidden;
    padding:120px 24px 80px;
  }
  .hero::before{
    content:'';position:absolute;inset:0;
    background:
      radial-gradient(ellipse 80% 60% at 30% 20%, rgba(99,102,241,0.12) 0%, transparent 70%),
      radial-gradient(ellipse 60% 50% at 70% 80%, rgba(236,72,153,0.08) 0%, transparent 70%),
      radial-gradient(ellipse 40% 40% at 50% 50%, rgba(34,211,238,0.06) 0%, transparent 70%);
    pointer-events:none;
  }
  .hero-inner{position:relative;z-index:1;max-width:800px;margin:0 auto}
  .hero-eyebrow{
    display:inline-flex;align-items:center;gap:10px;
    font-size:11px;font-weight:600;letter-spacing:.2em;
    text-transform:uppercase;color:var(--accent-l);
    margin-bottom:28px;
  }
  .hero-eyebrow::before{content:'';width:24px;height:1px;background:var(--accent-l)}
  .hero h1{
    font-family:var(--font-d);
    font-size:clamp(2.2rem,5.5vw,3.6rem);
    font-weight:800;line-height:1.15;
    color:#fff;letter-spacing:-.02em;
    margin-bottom:24px;
  }
  .hero h1 .grad{
    background:linear-gradient(135deg,#818cf8,#22d3ee,#ec4899);
    -webkit-background-clip:text;-webkit-text-fill-color:transparent;
    background-clip:text;
  }
  .hero-lead{
    font-size:16px;font-weight:300;
    color:rgba(255,255,255,0.65);
    line-height:1.85;max-width:560px;
    margin:0 auto 40px;
  }
  .hero-actions{display:flex;gap:16px;justify-content:center;flex-wrap:wrap;margin-bottom:56px}
  .btn-hero-primary{
    display:inline-flex;align-items:center;gap:10px;
    font-size:14px;font-weight:600;color:#fff;
    background:var(--accent);
    padding:14px 30px;border-radius:var(--r);
    transition:all .2s var(--ease);letter-spacing:.01em;
  }
  .btn-hero-primary:hover{background:#4f46e5;transform:translateY(-1px)}
  .btn-hero-ghost{
    display:inline-flex;align-items:center;gap:10px;
    font-size:14px;font-weight:400;
    color:rgba(255,255,255,0.7);
    padding:14px 20px;border-radius:var(--r);
    border:1px solid rgba(255,255,255,0.15);transition:all .2s;
  }
  .btn-hero-ghost:hover{color:#fff;border-color:rgba(255,255,255,0.35)}
  .hero-stats{
    display:flex;gap:40px;justify-content:center;flex-wrap:wrap;
    padding-top:40px;border-top:1px solid var(--border);
  }
  .hero-stat .num{
    font-family:var(--font-d);font-size:1.6rem;font-weight:800;
    color:var(--accent-l);line-height:1;
  }
  .hero-stat .label{font-size:11px;color:var(--text-s);margin-top:6px;letter-spacing:.04em}

  /* ── SECTION BASE ── */
  section{padding:100px 24px}
  .sec-inner{max-width:1100px;margin:0 auto}
  .sec-label{
    display:inline-flex;align-items:center;gap:10px;
    font-size:10.5px;font-weight:600;letter-spacing:.2em;
    text-transform:uppercase;color:var(--accent-l);
    margin-bottom:20px;
  }
  .sec-label::before{content:'';width:16px;height:1px;background:var(--accent-l)}
  .sec-title{
    font-family:var(--font-d);
    font-size:clamp(1.6rem,3.5vw,2.4rem);
    font-weight:800;color:#fff;line-height:1.15;
    letter-spacing:-.02em;margin-bottom:16px;
  }
  .sec-desc{
    font-size:15px;font-weight:300;color:var(--text-s);
    line-height:1.85;max-width:560px;
  }
  .text-center{text-align:center}
  .text-center .sec-desc{margin:0 auto}

  /* ── WHAT KIDS CAN MAKE ── */
  .make{background:var(--ink)}
  .make-grid{
    display:grid;grid-template-columns:repeat(3,1fr);
    gap:20px;margin-top:56px;
  }
  .make-card{
    background:var(--ink-s);
    border:1px solid var(--border-l);
    border-radius:16px;padding:36px 28px;
    text-align:center;
    transition:border-color .3s,transform .3s var(--ease);
  }
  .make-card:hover{border-color:rgba(99,102,241,0.35);transform:translateY(-4px)}
  .make-icon{font-size:2.8rem;margin-bottom:20px}
  .make-card h3{
    font-family:var(--font-d);font-size:1.05rem;font-weight:700;
    color:#fff;margin-bottom:10px;
  }
  .make-card p{font-size:0.88rem;color:var(--text-s);line-height:1.8}

  /* ── COURSE CARDS ── */
  .courses{background:var(--ink-s)}
  .course-cards{
    display:grid;grid-template-columns:repeat(3,1fr);
    gap:24px;margin-top:56px;
  }
  .course-card{
    background:var(--ink);
    border:1px solid var(--border-l);
    border-radius:16px;overflow:hidden;
    transition:transform .3s var(--ease),box-shadow .3s;
  }
  .course-card:hover{transform:translateY(-6px);box-shadow:0 24px 48px rgba(0,0,0,0.5)}
  .course-header{
    padding:28px 24px 24px;
    position:relative;
  }
  .course-header::before{
    content:'';position:absolute;top:0;left:0;right:0;height:3px;
  }
  .cc-gk1 .course-header::before{background:linear-gradient(90deg,#f97316,#fb923c)}
  .cc-gk2 .course-header::before{background:linear-gradient(90deg,#06b6d4,#22d3ee)}
  .cc-gk3 .course-header::before{background:linear-gradient(90deg,#ec4899,#f472b6)}
  .course-code{
    font-family:var(--font-d);font-size:11px;font-weight:700;
    letter-spacing:.15em;margin-bottom:10px;
  }
  .cc-gk1 .course-code{color:#fb923c}
  .cc-gk2 .course-code{color:#22d3ee}
  .cc-gk3 .course-code{color:#f472b6}
  .course-card h3{
    font-family:var(--font-d);font-size:1.2rem;font-weight:800;
    color:#fff;line-height:1.3;margin-bottom:8px;
  }
  .course-concept{font-size:0.82rem;color:var(--text-m);line-height:1.65}
  .course-body{padding:0 24px 28px}
  .course-meta{
    display:grid;grid-template-columns:1fr 1fr;gap:8px;
    margin:16px 0;
  }
  .meta-item{
    background:rgba(255,255,255,0.04);
    border-radius:8px;padding:10px 12px;
  }
  .meta-label{font-size:10px;color:var(--text-m);margin-bottom:2px;letter-spacing:.04em}
  .meta-value{font-size:0.88rem;font-weight:600;color:#fff}
  .course-price{
    font-family:var(--font-d);font-size:1.6rem;font-weight:800;
    margin:18px 0 16px;
  }
  .course-price span{font-size:0.78rem;font-weight:400;color:var(--text-m)}
  .cc-gk1 .course-price{color:#fb923c}
  .cc-gk2 .course-price{color:#22d3ee}
  .cc-gk3 .course-price{color:#f472b6}
  .course-features{list-style:none;margin-bottom:24px}
  .course-features li{
    font-size:0.88rem;color:rgba(255,255,255,0.72);
    padding:7px 0;border-bottom:1px solid var(--border);
    display:flex;align-items:center;gap:10px;
  }
  .course-features li::before{
    content:'';width:6px;height:6px;border-radius:50%;flex-shrink:0;
  }
  .cc-gk1 .course-features li::before{background:#fb923c}
  .cc-gk2 .course-features li::before{background:#22d3ee}
  .cc-gk3 .course-features li::before{background:#f472b6}
  .btn-course{
    display:block;text-align:center;padding:13px;
    border-radius:var(--r);font-size:13px;font-weight:600;
    color:#fff;transition:opacity .15s;
  }
  .btn-course:hover{opacity:.85}
  .cc-gk1 .btn-course{background:linear-gradient(135deg,#f97316,#fb923c)}
  .cc-gk2 .btn-course{background:linear-gradient(135deg,#06b6d4,#22d3ee)}
  .cc-gk3 .btn-course{background:linear-gradient(135deg,#ec4899,#f472b6)}

  /* ── SAFETY ── */
  .safety{background:var(--ink)}
  .safety-grid{
    display:grid;grid-template-columns:repeat(2,1fr);
    gap:16px;margin-top:56px;
  }
  .safety-card{
    display:flex;gap:18px;align-items:flex-start;
    background:var(--ink-s);border:1px solid var(--border-l);
    border-radius:16px;padding:28px 24px;
  }
  .safety-icon{
    flex-shrink:0;width:48px;height:48px;
    border-radius:10px;
    display:flex;align-items:center;justify-content:center;
    font-size:1.4rem;
    background:rgba(99,102,241,0.1);
    border:1px solid rgba(99,102,241,0.15);
  }
  .safety-card h4{
    font-size:0.95rem;font-weight:700;color:#fff;margin-bottom:6px;
  }
  .safety-card p{font-size:0.84rem;color:var(--text-s);line-height:1.8}

  /* ── VOICES ── */
  .voices{background:var(--ink-s)}
  .voice-grid{
    display:grid;grid-template-columns:repeat(3,1fr);
    gap:20px;margin-top:56px;
  }
  .voice-card{
    background:var(--ink);border:1px solid var(--border-l);
    border-radius:16px;padding:32px 24px;
    position:relative;
  }
  .voice-card::before{
    content:'\201C';position:absolute;top:16px;left:20px;
    font-family:var(--font-d);font-size:3rem;line-height:1;
    color:rgba(99,102,241,0.2);
  }
  .voice-quote{
    font-size:0.92rem;color:rgba(255,255,255,0.8);
    line-height:1.85;margin-bottom:20px;
    padding-top:16px;
  }
  .voice-author{
    font-size:0.8rem;font-weight:600;color:var(--accent-l);
  }
  .voice-role{
    font-size:0.75rem;color:var(--text-m);margin-top:2px;
  }

  /* ── FAQ ── */
  .faq{background:var(--ink)}
  .faq-list{max-width:720px;margin:48px auto 0}
  .faq-item{border-bottom:1px solid var(--border)}
  .faq-q{
    width:100%;background:none;border:none;
    color:#fff;text-align:left;
    padding:22px 0;font-size:0.95rem;font-weight:600;
    display:flex;justify-content:space-between;align-items:center;gap:16px;
    font-family:var(--font);
  }
  .faq-q::after{
    content:'+';font-family:var(--font-d);font-size:1.3rem;
    color:var(--accent-l);flex-shrink:0;
    transition:transform .3s var(--ease);
  }
  .faq-item.open .faq-q::after{transform:rotate(45deg)}
  .faq-a{
    display:none;padding:0 0 22px;
    font-size:0.88rem;color:var(--text-s);line-height:1.85;
  }
  .faq-item.open .faq-a{display:block}

  /* ── INQUIRY ── */
  .inquiry{background:var(--ink-s)}
  .form-wrap{
    max-width:600px;margin:48px auto 0;
    background:var(--ink);border:1px solid var(--border-l);
    border-radius:16px;padding:40px;
  }
  .form-group{margin-bottom:20px}
  .form-group label{
    display:block;font-size:0.84rem;font-weight:600;
    color:rgba(255,255,255,0.8);margin-bottom:8px;
  }
  .form-group label .req{color:#f472b6;margin-left:4px}
  .form-group input,.form-group select,.form-group textarea{
    width:100%;background:rgba(255,255,255,0.05);
    border:1px solid var(--border-l);border-radius:var(--r);
    padding:12px 16px;color:#fff;font-size:0.92rem;
    font-family:var(--font);outline:none;transition:border-color .2s;
  }
  .form-group input:focus,.form-group select:focus,.form-group textarea:focus{
    border-color:rgba(99,102,241,0.5);
  }
  .form-group textarea{height:100px;resize:vertical}
  .form-group select option{background:var(--ink-s)}
  .form-submit{
    width:100%;background:var(--accent);color:#fff;
    border:none;padding:14px;border-radius:var(--r);
    font-size:14px;font-weight:600;cursor:pointer;
    transition:opacity .15s;margin-top:8px;
  }
  .form-submit:hover{opacity:.85}
  .form-submit:disabled{opacity:0.4;cursor:not-allowed}
  #form-msg{text-align:center;margin-top:16px;font-size:0.88rem;min-height:20px}

  /* ── FOOTER ── */
  footer{
    background:var(--ink);padding:48px 24px;
    text-align:center;border-top:1px solid var(--border);
  }
  .ft-logo{
    display:inline-flex;align-items:center;gap:10px;
    margin-bottom:16px;
  }
  .ft-logo-mark{
    width:28px;height:28px;border-radius:5px;
    border:1px solid var(--border-l);
    display:flex;align-items:center;justify-content:center;
  }
  .ft-logo-mark svg{width:14px;height:14px;fill:none;stroke:#fff;stroke-width:1.5}
  .ft-logo-text{font-family:var(--font-d);font-size:14px;font-weight:700;color:#fff;letter-spacing:.06em}
  footer p{font-size:0.78rem;color:var(--text-m);margin-top:8px}
  footer a{color:var(--text-s);transition:color .15s}
  footer a:hover{color:#fff}

  /* ── RESPONSIVE ── */
  @media(max-width:900px){
    .hd{padding:0 20px}
    .hd-nav{display:none}
    .make-grid,.course-cards,.voice-grid{grid-template-columns:1fr}
    .safety-grid{grid-template-columns:1fr}
    section{padding:72px 20px}
    .hero{padding:100px 20px 64px}
  }
  @media(max-width:560px){
    .course-meta{grid-template-columns:1fr}
    .hero-stats{gap:24px}
  }
</style>
</head>
<body>

<!-- NAV -->
<header class="hd">
  <a class="hd-logo" href="/">
    <div class="hd-logo-mark">
      <svg viewBox="0 0 24 24"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg>
    </div>
    <div class="hd-logo-text">
      <div class="en">JGAIA</div>
      <div class="ja">日本生成AI協会</div>
    </div>
  </a>
  <nav class="hd-nav">
    <a href="#courses">コース</a>
    <a href="#safety">安心ポイント</a>
    <a href="#faq">よくある質問</a>
    <a href="/vibe-coding">大人向け講座</a>
  </nav>
  <div class="hd-right">
    <a href="#inquiry" class="btn-solid">無料相談</a>
  </div>
</header>

<!-- HERO -->
<section class="hero">
  <div class="hero-inner">
    <div class="hero-eyebrow">JGAIA Kids Vibe Coding</div>
    <h1>AIで、<span class="grad">つくる楽しさ</span>を<br>子どもたちへ</h1>
    <p class="hero-lead">小学3年生から参加OK。プログラミング経験は不要です。<br>AIに日本語で話しかけるだけで、自分だけのアプリが作れる体験を。</p>
    <div class="hero-actions">
      <a href="#courses" class="btn-hero-primary">コースを見る</a>
      <a href="#inquiry" class="btn-hero-ghost">無料相談はこちら</a>
    </div>
    <div class="hero-stats">
      <div class="hero-stat"><div class="num">小3〜</div><div class="label">対象学年</div></div>
      <div class="hero-stat"><div class="num">&yen;9,800〜</div><div class="label">受講料（税込）</div></div>
      <div class="hero-stat"><div class="num">JGAIA</div><div class="label">認定修了証 発行</div></div>
      <div class="hero-stat"><div class="num">0行</div><div class="label">コード記述不要</div></div>
    </div>
  </div>
</section>

<!-- WHAT KIDS CAN MAKE -->
<section class="make">
  <div class="sec-inner">
    <div class="text-center">
      <div class="sec-label">What Kids Can Make</div>
      <h2 class="sec-title">AIでこんなものが作れます</h2>
      <p class="sec-desc">AIに「こんなの作って」と話すだけ。プログラミングの知識がなくても、当日中にアプリが完成します。</p>
    </div>
    <div class="make-grid">
      <div class="make-card">
        <div class="make-icon">🎮</div>
        <h3>オリジナルゲーム</h3>
        <p>自分でルールを考えたゲームを、AIがコードに変換。友達にシェアして遊べる本格的なブラウザゲーム。</p>
      </div>
      <div class="make-card">
        <div class="make-icon">🎨</div>
        <h3>AI画像でマンガ制作</h3>
        <p>キャラクターやシーンをAI画像生成で作成。セリフを入れてオリジナルのデジタルマンガを完成させます。</p>
      </div>
      <div class="make-card">
        <div class="make-icon">🤖</div>
        <h3>自分だけのチャットボット</h3>
        <p>好きなキャラクターの性格をAIに設定して、自分だけのAIアシスタントを作ることができます。</p>
      </div>
    </div>
  </div>
</section>

<!-- COURSES -->
<section class="courses" id="courses">
  <div class="sec-inner">
    <div class="text-center">
      <div class="sec-label">Course Lineup</div>
      <h2 class="sec-title">3つのコース</h2>
      <p class="sec-desc">お子さまの年齢・目標に合わせてお選びください。</p>
    </div>
    <div class="course-cards">

      <!-- GK1 -->
      <div class="course-card cc-gk1">
        <div class="course-header">
          <div class="course-code">COURSE GK1</div>
          <h3>キッズ体験コース<br>（半日）</h3>
          <p class="course-concept">はじめてのAIアプリ作り。親子で一緒に感動を体験</p>
        </div>
        <div class="course-body">
          <div class="course-meta">
            <div class="meta-item"><div class="meta-label">対象</div><div class="meta-value">小学3〜6年生</div></div>
            <div class="meta-item"><div class="meta-label">時間</div><div class="meta-value">3時間</div></div>
            <div class="meta-item"><div class="meta-label">形式</div><div class="meta-value">会場・親子参加</div></div>
            <div class="meta-item"><div class="meta-label">条件</div><div class="meta-value">保護者同伴必須</div></div>
          </div>
          <div class="course-price">&yen;9,800 <span>（税込・1組）</span></div>
          <ul class="course-features">
            <li>AIってなに？（対話型レクチャー 15分）</li>
            <li>AIに絵を描いてもらおう（画像生成体験 30分）</li>
            <li>AIとおしゃべりしよう（チャットAI体験 30分）</li>
            <li>AIでミニゲームを作ろう（バイブコーディング 60分）</li>
            <li>作品発表タイム（15分）</li>
            <li>ふりかえり＋JGAIA認定修了証授与</li>
          </ul>
          <a href="#inquiry" class="btn-course">詳細・お申し込み</a>
        </div>
      </div>

      <!-- GK2 -->
      <div class="course-card cc-gk2">
        <div class="course-header">
          <div class="course-code">COURSE GK2</div>
          <h3>ジュニア入門コース<br>（1日）</h3>
          <p class="course-concept">本物のAIツールで、本格的なアプリ開発に挑戦</p>
        </div>
        <div class="course-body">
          <div class="course-meta">
            <div class="meta-item"><div class="meta-label">対象</div><div class="meta-value">中学生</div></div>
            <div class="meta-item"><div class="meta-label">時間</div><div class="meta-value">6時間</div></div>
            <div class="meta-item"><div class="meta-label">形式</div><div class="meta-value">会場開催</div></div>
            <div class="meta-item"><div class="meta-label">参加</div><div class="meta-value">単独参加OK</div></div>
          </div>
          <div class="course-price">&yen;29,800 <span>（税込）</span></div>
          <ul class="course-features">
            <li>生成AIの仕組み（ニューラルネットワークの基礎）</li>
            <li>プロンプトの書き方（効果的な指示の出し方）</li>
            <li>バイブコーディングでWebアプリを作る</li>
            <li>AI画像生成でオリジナルキャラクターを作る</li>
            <li>自分だけのAIアプリ制作（企画 → 開発 → テスト）</li>
            <li>作品プレゼンテーション＋JGAIA認定修了証授与</li>
          </ul>
          <a href="#inquiry" class="btn-course">詳細・お申し込み</a>
        </div>
      </div>

      <!-- GK3 -->
      <div class="course-card cc-gk3">
        <div class="course-header">
          <div class="course-code">COURSE GK3</div>
          <h3>親子ペアコース<br>（1日）</h3>
          <p class="course-concept">親子で同じ目線で学ぶ。共に作り上げる特別な1日</p>
        </div>
        <div class="course-body">
          <div class="course-meta">
            <div class="meta-item"><div class="meta-label">対象</div><div class="meta-value">小3〜中3＋保護者</div></div>
            <div class="meta-item"><div class="meta-label">時間</div><div class="meta-value">6時間</div></div>
            <div class="meta-item"><div class="meta-label">形式</div><div class="meta-value">会場・ペア参加</div></div>
            <div class="meta-item"><div class="meta-label">特典</div><div class="meta-value">修了証2枚発行</div></div>
          </div>
          <div class="course-price">&yen;49,800 <span>（税込・1組）</span></div>
          <ul class="course-features">
            <li>親子でAI基礎を学ぶ（世代間の理解ギャップを埋める）</li>
            <li>親子で役割分担してアプリを企画</li>
            <li>親がプロンプトを書き、子どもがデザイン担当（or逆）</li>
            <li>親子で1つのアプリを完成させる</li>
            <li>家庭でのAI活用ルール作りワークショップ</li>
            <li>成果発表＋親子写真＋JGAIA認定修了証授与（2枚）</li>
          </ul>
          <a href="#inquiry" class="btn-course">詳細・お申し込み</a>
        </div>
      </div>

    </div>
  </div>
</section>

<!-- SAFETY -->
<section class="safety" id="safety">
  <div class="sec-inner">
    <div class="text-center">
      <div class="sec-label">Safety &amp; Trust</div>
      <h2 class="sec-title">安心・安全への取り組み</h2>
      <p class="sec-desc">お子さまが安心して学べる環境を整えています。</p>
    </div>
    <div class="safety-grid">
      <div class="safety-card">
        <div class="safety-icon">👨‍👩‍👦</div>
        <div>
          <h4>保護者同伴（GK1/GK3）</h4>
          <p>GK1とGK3コースは保護者同伴が必須。お子さまの学びを保護者の方も間近で見守り、一緒に体験できます。GK2は中学生対象で単独参加が可能です。</p>
        </div>
      </div>
      <div class="safety-card">
        <div class="safety-icon">🛡️</div>
        <div>
          <h4>フィルタリング済みAI環境</h4>
          <p>子ども向けに設定された安全なAI環境を使用。有害なコンテンツの生成やアクセスができないよう、フィルタリングと制限を適用しています。</p>
        </div>
      </div>
      <div class="safety-card">
        <div class="safety-icon">🔒</div>
        <div>
          <h4>個人情報の取り扱い指導</h4>
          <p>AIに個人情報を入力しないルールを講座内で指導。デジタルリテラシーの基礎を実践的に学べます。</p>
        </div>
      </div>
      <div class="safety-card">
        <div class="safety-icon">🎓</div>
        <div>
          <h4>JGAIA認定講師が担当</h4>
          <p>一般社団法人日本生成AI協会が認定した講師が指導を担当。生成AI教育の専門知識を持つスタッフが、一人ひとりのペースに合わせてサポートします。</p>
        </div>
      </div>
    </div>
  </div>
</section>

<!-- VOICES -->
<section class="voices" id="voices">
  <div class="sec-inner">
    <div class="text-center">
      <div class="sec-label">Voices</div>
      <h2 class="sec-title">参加者の声</h2>
    </div>
    <div class="voice-grid">
      <div class="voice-card">
        <p class="voice-quote">AIに「シューティングゲーム作って」って言ったら、本当に動くゲームができてすごかった！プログラミングって難しいと思ってたけど、AIがあれば自分のアイデアがすぐ形になる。</p>
        <div class="voice-author">小5 男子</div>
        <div class="voice-role">GK1 キッズ体験コース受講</div>
      </div>
      <div class="voice-card">
        <p class="voice-quote">プログラミングは難しいと思ってたけど、AIに日本語で頼むだけでWebアプリが作れた。自分で作ったアプリを友達に見せたら「すごい！」って言われて嬉しかった。</p>
        <div class="voice-author">中2 女子</div>
        <div class="voice-role">GK2 ジュニア入門コース受講</div>
      </div>
      <div class="voice-card">
        <p class="voice-quote">子どもの方がAIの使い方を覚えるのが早くて驚きました。講座の後、家でも一緒にアプリを作るようになって、親子の新しいコミュニケーションが生まれました。</p>
        <div class="voice-author">保護者</div>
        <div class="voice-role">GK3 親子ペアコース受講</div>
      </div>
    </div>
  </div>
</section>

<!-- FAQ -->
<section class="faq" id="faq">
  <div class="sec-inner">
    <div class="text-center">
      <div class="sec-label">FAQ</div>
      <h2 class="sec-title">よくある質問</h2>
    </div>
    <div class="faq-list">
      <div class="faq-item">
        <button class="faq-q">プログラミング経験がなくても大丈夫ですか？</button>
        <div class="faq-a">はい、完全未経験者向けの講座です。バイブコーディングは日本語でAIに話しかけるだけでアプリが作れる技術です。コードを書く必要は一切ありません。小学3年生から参加できます。</div>
      </div>
      <div class="faq-item">
        <button class="faq-q">PCは必要ですか？</button>
        <div class="faq-a">会場にてPCの貸出を行っています（無料）。ご自身のPC（Windows/Mac）を持ち込んでいただくことも可能です。事前にご連絡ください。</div>
      </div>
      <div class="faq-item">
        <button class="faq-q">兄弟で参加できますか？</button>
        <div class="faq-a">GK1・GK3コースは1組追加5,000円で兄弟の追加参加が可能です。お申し込み時にメッセージ欄にてお知らせください。</div>
      </div>
      <div class="faq-item">
        <button class="faq-q">助成金は使えますか？</button>
        <div class="faq-a">子ども向けコースは東京しごと財団「事業外スキルアップ助成金」等の助成金の対象外です。企業の従業員向け助成金制度のため、子ども（非従業員）は対象となりません。</div>
      </div>
      <div class="faq-item">
        <button class="faq-q">受講後も自分でアプリを作り続けられますか？</button>
        <div class="faq-a">はい。受講時に使用するAIツールは無料プランでも継続利用できます。受講後はJGAIAのオンラインコミュニティで質問・交流できる環境もご用意しています。</div>
      </div>
      <div class="faq-item">
        <button class="faq-q">次回の開催日程はいつですか？</button>
        <div class="faq-a">開催日程は随時更新しています。お問い合わせフォームからご登録いただくと、最新の開催情報をいち早くお届けします。お気軽にご相談ください。</div>
      </div>
    </div>
  </div>
</section>

<!-- INQUIRY -->
<section class="inquiry" id="inquiry">
  <div class="sec-inner">
    <div class="text-center">
      <div class="sec-label">Contact</div>
      <h2 class="sec-title">無料相談・お申し込み</h2>
      <p class="sec-desc">ご不明な点はお気軽にご相談ください。担当者が丁寧にご案内します。</p>
    </div>
    <div class="form-wrap">
      <div class="form-group">
        <label>保護者名<span class="req">*</span></label>
        <input type="text" id="parent-name" placeholder="例：高野 秀隆">
      </div>
      <div class="form-group">
        <label>お子さまの年齢<span class="req">*</span></label>
        <select id="child-age">
          <option value="">選択してください</option>
          <option>8歳（小学3年生）</option>
          <option>9歳（小学4年生）</option>
          <option>10歳（小学5年生）</option>
          <option>11歳（小学6年生）</option>
          <option>12歳（中学1年生）</option>
          <option>13歳（中学2年生）</option>
          <option>14歳（中学3年生）</option>
        </select>
      </div>
      <div class="form-group">
        <label>メールアドレス<span class="req">*</span></label>
        <input type="email" id="email" placeholder="例：example@email.com">
      </div>
      <div class="form-group">
        <label>電話番号</label>
        <input type="tel" id="phone" placeholder="例：090-1234-5678">
      </div>
      <div class="form-group">
        <label>希望コース<span class="req">*</span></label>
        <select id="course">
          <option value="">選択してください</option>
          <option>GK1：キッズ体験（半日・3時間）¥9,800/組</option>
          <option>GK2：ジュニア入門（1日・6時間）¥29,800</option>
          <option>GK3：親子ペアコース（1日・6時間）¥49,800/組</option>
          <option>まだ決めていない・相談したい</option>
        </select>
      </div>
      <div class="form-group">
        <label>メッセージ</label>
        <textarea id="message" placeholder="ご質問・ご要望などお気軽にどうぞ（兄弟参加・日程のご希望など）"></textarea>
      </div>
      <button class="form-submit" id="submit-btn" onclick="submitKidsInquiry()">送信する</button>
      <div id="form-msg"></div>
    </div>
  </div>
</section>

<!-- FOOTER -->
<footer>
  <div class="ft-logo">
    <div class="ft-logo-mark">
      <svg viewBox="0 0 24 24"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg>
    </div>
    <span class="ft-logo-text">JGAIA</span>
  </div>
  <p>一般社団法人 日本生成AI協会<br>〒104-0061 東京都中央区銀座1-22-11 銀座大竹ビジデンス2階</p>
  <p style="margin-top:16px;"><a href="/vibe-coding">大人向け講座はこちら</a> ｜ <a href="https://www.jgaia.org">JGAIA公式サイト</a> ｜ <a href="mailto:info@jgaia.org">info@jgaia.org</a></p>
  <p style="margin-top:16px;">&copy; 2026 一般社団法人日本生成AI協会</p>
</footer>

<script>
// FAQ accordion
document.querySelectorAll('.faq-q').forEach(function(btn){
  btn.addEventListener('click',function(){
    var item=btn.parentElement;
    var isOpen=item.classList.contains('open');
    document.querySelectorAll('.faq-item').forEach(function(i){i.classList.remove('open')});
    if(!isOpen) item.classList.add('open');
  });
});

// Inquiry form
async function submitKidsInquiry(){
  var btn=document.getElementById('submit-btn');
  var msg=document.getElementById('form-msg');
  var parentName=document.getElementById('parent-name').value.trim();
  var childAge=document.getElementById('child-age').value;
  var email=document.getElementById('email').value.trim();
  var phone=document.getElementById('phone').value.trim();
  var course=document.getElementById('course').value;
  var message=document.getElementById('message').value.trim();

  if(!parentName||!childAge||!email||!course){
    msg.style.color='#f87171';
    msg.textContent='必須項目をすべて入力してください。';
    return;
  }
  btn.disabled=true;
  btn.textContent='送信中...';
  msg.textContent='';

  try{
    var res=await fetch('/api/kids-inquiry',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({parent_name:parentName,child_age:childAge,email:email,phone:phone,course:course,message:message})
    });
    var data=await res.json();
    if(data.success){
      msg.style.color='#34d399';
      msg.textContent='お問い合わせを受け付けました。確認メールをお送りしましたのでご確認ください。';
      document.getElementById('parent-name').value='';
      document.getElementById('child-age').selectedIndex=0;
      document.getElementById('email').value='';
      document.getElementById('phone').value='';
      document.getElementById('course').selectedIndex=0;
      document.getElementById('message').value='';
    }else{
      msg.style.color='#f87171';
      msg.textContent='送信に失敗しました。info@jgaia.org までご連絡ください。';
    }
  }catch(e){
    msg.style.color='#f87171';
    msg.textContent='通信エラーが発生しました。しばらくしてから再度お試しください。';
  }
  btn.disabled=false;
  btn.textContent='送信する';
}
</script>
</body>
</html>"""
