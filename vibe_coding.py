"""JGAIA バイブコーディング講座紹介ページ（汎用コースGA/GB/GC/GD/GE）"""
from flask import Response


def register_vibe_coding_routes(app):
    @app.route("/vibe-coding")
    def vibe_coding():
        return Response(VIBE_CODING_HTML, mimetype="text/html")


VIBE_CODING_HTML = r"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>バイブコーディング認定講座 | JGAIA 日本生成AI協会</title>
  <meta name="description" content="JGAIAが認定するバイブコーディング講座。生成AI（ChatGPT・Claude・Gemini等）を活用して、コーディング知識ゼロからビジネスアプリを作れる全15コースを提供。助成金対象・修了証発行。">
  <meta property="og:title" content="バイブコーディング認定講座 | JGAIA 日本生成AI協会">
  <meta property="og:description" content="生成AIで、誰でもアプリが作れる時代へ。JGAIA認定バイブコーディング講座で、生成AIを使ったアプリ開発スキルを身につけましょう。">
  <meta property="og:type" content="website">
  <meta property="og:url" content="https://jgaia-production.up.railway.app/vibe-coding">
  <link rel="icon" href="https://www.jgaia.org/favicon.ico">
  <link href="https://fonts.googleapis.com/css2?family=Syne:wght@600;700;800&family=DM+Sans:wght@400;500;700&family=Noto+Sans+JP:wght@400;500;700;900&display=swap" rel="stylesheet">
  <style>
    :root {
      --ink: #09090b;
      --ink-light: #111118;
      --accent: #6366f1;
      --accent-l: #818cf8;
      --accent-d: #4f46e5;
      --text: #fafafa;
      --text-s: #a1a1aa;
      --text-m: #d4d4d8;
      --border: rgba(255,255,255,0.07);
      --border-l: rgba(255,255,255,0.12);
      --glass: rgba(255,255,255,0.03);
      --glass-l: rgba(255,255,255,0.06);
      --radius: 16px;
      --radius-s: 10px;
      --radius-xs: 6px;
    }

    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    html { scroll-behavior: smooth; }
    body {
      font-family: 'Noto Sans JP', 'DM Sans', sans-serif;
      background: var(--ink);
      color: var(--text);
      line-height: 1.7;
      font-size: 15px;
      -webkit-font-smoothing: antialiased;
    }
    a { text-decoration: none; color: inherit; }
    img { max-width: 100%; height: auto; }
    .syne { font-family: 'Syne', 'Noto Sans JP', sans-serif; }

    /* ── HEADER ── */
    .site-header {
      background: rgba(9,9,11,0.85);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      border-bottom: 1px solid var(--border);
      position: sticky;
      top: 0;
      z-index: 200;
    }
    .header-inner {
      max-width: 1200px;
      margin: 0 auto;
      padding: 0 24px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      height: 64px;
    }
    .site-logo {
      font-family: 'Syne', sans-serif;
      font-weight: 800;
      font-size: 1.2rem;
      color: var(--text);
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .site-logo .logo-accent { color: var(--accent-l); }
    .site-nav { display: flex; align-items: center; gap: 2px; }
    .site-nav a {
      padding: 8px 14px;
      border-radius: var(--radius-xs);
      font-size: 0.82rem;
      font-weight: 500;
      color: var(--text-s);
      transition: background 0.2s, color 0.2s;
      white-space: nowrap;
    }
    .site-nav a:hover { background: var(--glass-l); color: var(--text); }
    .site-nav a.active { background: rgba(99,102,241,0.12); color: var(--accent-l); font-weight: 700; }
    .nav-cta {
      background: var(--accent) !important;
      color: #fff !important;
      padding: 8px 20px !important;
      border-radius: 20px !important;
      font-weight: 700 !important;
    }
    .nav-cta:hover { background: var(--accent-d) !important; }
    .hamburger { display: none; cursor: pointer; flex-direction: column; gap: 5px; padding: 8px; }
    .hamburger span { display: block; width: 22px; height: 2px; background: var(--text-s); border-radius: 2px; transition: 0.3s; }

    /* ── HERO ── */
    .hero {
      background: linear-gradient(160deg, #09090b 0%, #111128 30%, #1e1b4b 60%, #312e81 100%);
      color: var(--text);
      padding: 100px 24px 110px;
      text-align: center;
      position: relative;
      overflow: hidden;
    }
    .hero::before {
      content: '';
      position: absolute;
      top: -200px;
      right: -200px;
      width: 600px;
      height: 600px;
      background: radial-gradient(circle, rgba(99,102,241,0.15), transparent 70%);
      pointer-events: none;
    }
    .hero::after {
      content: '';
      position: absolute;
      bottom: -100px;
      left: -100px;
      width: 400px;
      height: 400px;
      background: radial-gradient(circle, rgba(129,140,248,0.1), transparent 70%);
      pointer-events: none;
    }
    .hero > * { position: relative; z-index: 1; }
    .hero-badge {
      display: inline-block;
      background: rgba(99,102,241,0.15);
      border: 1px solid rgba(99,102,241,0.35);
      color: var(--accent-l);
      font-family: 'Syne', sans-serif;
      font-size: 0.72rem;
      font-weight: 700;
      letter-spacing: 0.16em;
      padding: 6px 20px;
      border-radius: 20px;
      margin-bottom: 28px;
    }
    .hero h1 {
      font-family: 'Noto Sans JP', sans-serif;
      font-size: clamp(2rem, 5vw, 3.4rem);
      font-weight: 900;
      line-height: 1.25;
      margin-bottom: 22px;
      letter-spacing: -0.02em;
    }
    .hero h1 .hl { color: var(--accent-l); }
    .hero-lead {
      font-size: clamp(0.95rem, 1.8vw, 1.1rem);
      color: var(--text-s);
      max-width: 640px;
      margin: 0 auto 44px;
      line-height: 1.9;
    }
    .hero-actions {
      display: flex;
      gap: 14px;
      justify-content: center;
      flex-wrap: wrap;
      margin-bottom: 60px;
    }
    .btn {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 14px 34px;
      border-radius: 30px;
      font-size: 0.92rem;
      font-weight: 700;
      transition: all 0.25s;
      cursor: pointer;
      border: none;
    }
    .btn-primary { background: var(--accent); color: #fff; }
    .btn-primary:hover { background: var(--accent-d); transform: translateY(-2px); box-shadow: 0 8px 28px rgba(99,102,241,0.4); }
    .btn-outline { background: transparent; color: var(--text); border: 1.5px solid rgba(255,255,255,0.25); }
    .btn-outline:hover { background: rgba(255,255,255,0.06); border-color: rgba(255,255,255,0.5); }
    .hero-stats {
      display: flex;
      gap: 48px;
      justify-content: center;
      flex-wrap: wrap;
      padding-top: 44px;
      border-top: 1px solid var(--border-l);
    }
    .hero-stat { text-align: center; }
    .hero-stat .num {
      font-family: 'Syne', sans-serif;
      font-size: 1.6rem;
      font-weight: 800;
      color: var(--accent-l);
      line-height: 1;
    }
    .hero-stat .label { font-size: 0.75rem; color: var(--text-s); margin-top: 6px; }

    /* ── SECTIONS COMMON ── */
    section { padding: 90px 24px; }
    .section-inner { max-width: 1100px; margin: 0 auto; }
    .section-label {
      display: inline-block;
      background: rgba(99,102,241,0.1);
      color: var(--accent-l);
      font-family: 'Syne', sans-serif;
      font-size: 0.7rem;
      font-weight: 700;
      letter-spacing: 0.14em;
      padding: 5px 16px;
      border-radius: 20px;
      margin-bottom: 16px;
    }
    .section-title {
      font-size: clamp(1.5rem, 3vw, 2.1rem);
      font-weight: 900;
      line-height: 1.3;
      margin-bottom: 14px;
      letter-spacing: -0.02em;
      color: var(--text);
    }
    .section-lead {
      color: var(--text-s);
      font-size: 0.95rem;
      max-width: 600px;
      line-height: 1.85;
      margin-bottom: 48px;
    }
    .text-center { text-align: center; }
    .text-center .section-lead { margin-left: auto; margin-right: auto; }

    /* ── WHAT IS VIBE CODING ── */
    .what-is { background: var(--ink-light); }
    .what-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 48px;
      align-items: start;
    }
    .what-visual {
      background: linear-gradient(160deg, #1e1b4b, #312e81);
      border: 1px solid var(--border-l);
      border-radius: var(--radius);
      padding: 40px;
      position: relative;
      overflow: hidden;
    }
    .what-visual::before {
      content: '';
      position: absolute;
      top: -40px;
      right: -40px;
      width: 180px;
      height: 180px;
      background: radial-gradient(circle, rgba(129,140,248,0.25), transparent);
      border-radius: 50%;
    }
    .what-visual .flow-steps {
      display: flex;
      flex-direction: column;
      gap: 20px;
      position: relative;
      z-index: 1;
    }
    .flow-step {
      display: flex;
      align-items: center;
      gap: 16px;
    }
    .flow-icon {
      width: 48px;
      height: 48px;
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 1.4rem;
      flex-shrink: 0;
    }
    .flow-icon-1 { background: rgba(99,102,241,0.2); }
    .flow-icon-2 { background: rgba(129,140,248,0.2); }
    .flow-icon-3 { background: rgba(167,139,250,0.2); }
    .flow-text h4 { font-size: 0.92rem; font-weight: 700; margin-bottom: 2px; }
    .flow-text p { font-size: 0.8rem; color: var(--text-s); line-height: 1.6; }
    .flow-arrow {
      margin-left: 22px;
      color: var(--accent-l);
      font-size: 1.2rem;
      opacity: 0.5;
    }

    .compare-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.85rem;
      border: 1px solid var(--border);
      border-radius: var(--radius-s);
      overflow: hidden;
    }
    .compare-table th {
      background: rgba(99,102,241,0.1);
      color: var(--accent-l);
      padding: 12px 16px;
      text-align: left;
      font-weight: 700;
      font-size: 0.8rem;
    }
    .compare-table td {
      padding: 12px 16px;
      border-bottom: 1px solid var(--border);
      color: var(--text-m);
      vertical-align: top;
    }
    .compare-table tr:last-child td { border-bottom: none; }
    .compare-table .col-old { color: #ef4444; }
    .compare-table .col-new { color: #34d399; font-weight: 600; }

    /* ── APP EXAMPLES ── */
    .app-examples { background: var(--ink); }
    .app-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 24px;
    }
    .app-card {
      background: var(--glass);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      overflow: hidden;
      transition: transform 0.3s, box-shadow 0.3s, border-color 0.3s;
    }
    .app-card:hover {
      transform: translateY(-6px);
      box-shadow: 0 16px 48px rgba(99,102,241,0.12);
      border-color: var(--border-l);
    }
    .app-card-visual {
      height: 180px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 3.5rem;
      position: relative;
    }
    .app-card-visual::after {
      content: '';
      position: absolute;
      inset: 0;
      background: linear-gradient(to bottom, transparent 50%, var(--ink) 100%);
      pointer-events: none;
    }
    .app-v1 { background: linear-gradient(135deg, #1e1b4b, #312e81); }
    .app-v2 { background: linear-gradient(135deg, #134e4a, #115e59); }
    .app-v3 { background: linear-gradient(135deg, #1e1b4b, #4c1d95); }
    .app-card-body { padding: 20px 24px 24px; }
    .app-tag {
      display: inline-block;
      background: rgba(99,102,241,0.12);
      color: var(--accent-l);
      font-family: 'Syne', sans-serif;
      font-size: 0.65rem;
      font-weight: 700;
      letter-spacing: 0.1em;
      padding: 3px 10px;
      border-radius: 10px;
      margin-bottom: 10px;
    }
    .app-card-body h4 { font-size: 1rem; font-weight: 800; margin-bottom: 6px; }
    .app-card-body p { font-size: 0.82rem; color: var(--text-s); line-height: 1.7; }

    /* ── COURSE CARDS ── */
    .courses { background: var(--ink-light); }
    .course-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 24px;
    }
    .course-card {
      background: var(--glass);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      overflow: hidden;
      transition: transform 0.3s, box-shadow 0.3s;
      display: flex;
      flex-direction: column;
    }
    .course-card:hover {
      transform: translateY(-6px);
      box-shadow: 0 16px 48px rgba(0,0,0,0.3);
    }
    .course-card-head {
      padding: 28px 28px 22px;
      position: relative;
      overflow: hidden;
    }
    .course-card-head::before {
      content: '';
      position: absolute;
      top: -30px;
      right: -30px;
      width: 120px;
      height: 120px;
      background: rgba(255,255,255,0.06);
      border-radius: 50%;
    }
    .cc-ga { background: linear-gradient(135deg, #1565c0, #0288d1); }
    .cc-gb { background: linear-gradient(135deg, #4527a0, #7b1fa2); }
    .cc-gc { background: linear-gradient(135deg, #00695c, #00897b); }
    .cc-gd { background: linear-gradient(135deg, #b71c1c, #d84315); }
    .cc-ge { background: linear-gradient(135deg, #283593, #3949ab); }

    .course-badge {
      display: inline-block;
      background: rgba(255,255,255,0.2);
      color: #fff;
      font-family: 'Syne', sans-serif;
      font-size: 0.68rem;
      font-weight: 700;
      letter-spacing: 0.1em;
      padding: 3px 12px;
      border-radius: 10px;
      margin-bottom: 14px;
    }
    .course-card-head h3 {
      color: #fff;
      font-size: 1.15rem;
      font-weight: 800;
      line-height: 1.35;
      margin-bottom: 8px;
    }
    .course-concept {
      color: rgba(255,255,255,0.8);
      font-size: 0.78rem;
      line-height: 1.65;
    }
    .course-card-body {
      padding: 24px 28px;
      flex: 1;
      display: flex;
      flex-direction: column;
    }
    .course-meta {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
      margin-bottom: 20px;
    }
    .meta-label { font-size: 0.7rem; color: var(--text-s); font-weight: 500; margin-bottom: 2px; }
    .meta-value { font-size: 0.88rem; font-weight: 700; color: var(--text); }
    .course-price {
      font-family: 'Syne', sans-serif;
      font-size: 1.5rem;
      font-weight: 800;
      color: var(--accent-l);
      margin-bottom: 4px;
    }
    .course-price span { font-size: 0.78rem; font-weight: 400; color: var(--text-s); }
    .course-features {
      list-style: none;
      margin-bottom: 24px;
      flex: 1;
    }
    .course-features li {
      padding: 7px 0;
      padding-left: 24px;
      position: relative;
      font-size: 0.82rem;
      color: var(--text-m);
      border-bottom: 1px solid var(--border);
    }
    .course-features li:last-child { border-bottom: none; }
    .course-features li::before {
      content: '\2713';
      position: absolute;
      left: 0;
      color: var(--accent-l);
      font-weight: 700;
    }
    .btn-course {
      display: block;
      text-align: center;
      padding: 12px;
      border-radius: var(--radius-xs);
      font-size: 0.88rem;
      font-weight: 700;
      transition: all 0.25s;
      border: 1px solid var(--border-l);
      color: var(--text);
      background: var(--glass-l);
    }
    .btn-course:hover {
      background: var(--accent);
      border-color: var(--accent);
      color: #fff;
    }

    /* ── KIDS SECTION ── */
    .kids-section { background: var(--ink); }
    .kids-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 20px;
    }
    .kids-card {
      background: var(--glass);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 28px;
      text-align: center;
      transition: transform 0.3s, border-color 0.3s;
    }
    .kids-card:hover { transform: translateY(-4px); border-color: var(--border-l); }
    .kids-icon { font-size: 2.4rem; margin-bottom: 14px; display: block; }
    .kids-card h4 { font-size: 0.95rem; font-weight: 800; margin-bottom: 6px; }
    .kids-card .kids-target { font-size: 0.78rem; color: var(--accent-l); margin-bottom: 8px; font-weight: 600; }
    .kids-card p { font-size: 0.8rem; color: var(--text-s); line-height: 1.6; margin-bottom: 14px; }
    .kids-price { font-family: 'Syne', sans-serif; font-size: 1.2rem; font-weight: 800; color: var(--accent-l); }
    .kids-price span { font-size: 0.75rem; font-weight: 400; color: var(--text-s); }
    .kids-link-wrap {
      text-align: center;
      margin-top: 36px;
    }

    /* ── INDUSTRY SECTION ── */
    .industry-section { background: var(--ink-light); }
    .industry-grid {
      display: grid;
      grid-template-columns: repeat(5, 1fr);
      gap: 16px;
    }
    .industry-card {
      background: var(--glass);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 28px 20px;
      text-align: center;
      transition: transform 0.3s, border-color 0.3s, box-shadow 0.3s;
      display: block;
    }
    .industry-card:hover {
      transform: translateY(-4px);
      border-color: rgba(99,102,241,0.3);
      box-shadow: 0 8px 32px rgba(99,102,241,0.1);
    }
    .industry-icon { font-size: 2.2rem; margin-bottom: 12px; display: block; }
    .industry-card h4 { font-size: 0.88rem; font-weight: 800; margin-bottom: 4px; }
    .industry-card p { font-size: 0.72rem; color: var(--text-s); line-height: 1.5; }
    .industry-arrow {
      display: inline-block;
      margin-top: 12px;
      font-size: 0.75rem;
      color: var(--accent-l);
      font-weight: 600;
    }

    /* ── SUBSIDY ── */
    .subsidy-section { background: var(--ink); }
    .subsidy-banner {
      background: linear-gradient(135deg, rgba(99,102,241,0.08), rgba(129,140,248,0.04));
      border: 1px solid rgba(99,102,241,0.2);
      border-radius: var(--radius);
      padding: 40px;
      margin-bottom: 32px;
    }
    .subsidy-banner h3 {
      font-size: 1.1rem;
      font-weight: 800;
      margin-bottom: 8px;
      color: var(--text);
    }
    .subsidy-banner p { font-size: 0.88rem; color: var(--text-s); line-height: 1.8; }
    .subsidy-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 24px;
      margin-bottom: 32px;
    }
    .subsidy-card {
      background: var(--glass);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 28px;
    }
    .subsidy-card h4 {
      font-size: 0.92rem;
      font-weight: 800;
      margin-bottom: 6px;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .subsidy-badge-ok {
      display: inline-block;
      background: rgba(52,211,153,0.15);
      color: #34d399;
      font-size: 0.65rem;
      font-weight: 700;
      padding: 2px 8px;
      border-radius: 8px;
    }
    .subsidy-badge-ng {
      display: inline-block;
      background: rgba(239,68,68,0.12);
      color: #ef4444;
      font-size: 0.65rem;
      font-weight: 700;
      padding: 2px 8px;
      border-radius: 8px;
    }
    .subsidy-card p { font-size: 0.82rem; color: var(--text-s); line-height: 1.7; }
    .subsidy-card .price-highlight {
      font-family: 'Syne', sans-serif;
      font-size: 1.6rem;
      font-weight: 800;
      color: #34d399;
      margin: 12px 0 4px;
    }
    .subsidy-card .price-highlight span { font-size: 0.8rem; color: var(--text-s); font-weight: 400; }
    .subsidy-eligible {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
      gap: 8px;
      margin-top: 16px;
    }
    .eligible-tag {
      text-align: center;
      padding: 8px;
      border-radius: var(--radius-xs);
      font-size: 0.75rem;
      font-weight: 700;
    }
    .eligible-yes { background: rgba(52,211,153,0.1); color: #34d399; border: 1px solid rgba(52,211,153,0.2); }
    .eligible-no { background: rgba(239,68,68,0.06); color: #ef4444; border: 1px solid rgba(239,68,68,0.12); }
    .subsidy-note {
      background: var(--glass);
      border: 1px solid var(--border);
      border-radius: var(--radius-s);
      padding: 20px 24px;
      font-size: 0.8rem;
      color: var(--text-s);
      line-height: 1.8;
    }
    .subsidy-note a { color: var(--accent-l); text-decoration: underline; }

    /* ── FAQ ── */
    .faq { background: var(--ink-light); }
    .faq-list { max-width: 760px; margin: 0 auto; }
    .faq-item {
      border-bottom: 1px solid var(--border);
      padding: 22px 0;
    }
    .faq-item:last-child { border-bottom: none; }
    .faq-q {
      font-size: 0.95rem;
      font-weight: 700;
      color: var(--text);
      margin-bottom: 10px;
      padding-left: 30px;
      position: relative;
    }
    .faq-q::before {
      content: 'Q';
      position: absolute;
      left: 0;
      color: var(--accent-l);
      font-family: 'Syne', sans-serif;
      font-weight: 800;
    }
    .faq-a {
      font-size: 0.85rem;
      color: var(--text-s);
      line-height: 1.85;
      padding-left: 30px;
      position: relative;
    }
    .faq-a::before {
      content: 'A';
      position: absolute;
      left: 0;
      color: #34d399;
      font-family: 'Syne', sans-serif;
      font-weight: 800;
    }

    /* ── CTA ── */
    .cta-section {
      background: linear-gradient(160deg, #1e1b4b, #312e81, #3730a3);
      color: var(--text);
      text-align: center;
      padding: 90px 24px;
      position: relative;
      overflow: hidden;
    }
    .cta-section::before {
      content: '';
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      width: 600px;
      height: 600px;
      background: radial-gradient(circle, rgba(99,102,241,0.12), transparent 70%);
      pointer-events: none;
    }
    .cta-section > * { position: relative; z-index: 1; }
    .cta-section h2 {
      font-size: clamp(1.5rem, 3vw, 2.2rem);
      font-weight: 900;
      margin-bottom: 16px;
    }
    .cta-section p {
      color: var(--text-s);
      font-size: 1rem;
      margin-bottom: 40px;
      max-width: 540px;
      margin-left: auto;
      margin-right: auto;
      line-height: 1.8;
    }
    .cta-buttons {
      display: flex;
      gap: 16px;
      justify-content: center;
      flex-wrap: wrap;
    }
    .cta-contact-info {
      margin-top: 40px;
      font-size: 0.82rem;
      color: var(--text-s);
      line-height: 1.8;
    }
    .cta-contact-info a { color: var(--accent-l); }

    /* ── FOOTER ── */
    .site-footer {
      background: #050507;
      color: var(--text-s);
      padding: 48px 24px 24px;
      border-top: 1px solid var(--border);
    }
    .footer-inner { max-width: 1100px; margin: 0 auto; }
    .footer-grid {
      display: grid;
      grid-template-columns: 2fr 1fr 1fr 1fr;
      gap: 40px;
      margin-bottom: 40px;
    }
    .footer-brand .footer-logo {
      font-family: 'Syne', sans-serif;
      font-weight: 800;
      font-size: 1.1rem;
      color: var(--text);
      margin-bottom: 12px;
    }
    .footer-brand .footer-logo .logo-accent { color: var(--accent-l); }
    .footer-brand p { font-size: 0.78rem; line-height: 1.8; }
    .footer-col h4 {
      color: var(--text);
      font-size: 0.8rem;
      font-weight: 700;
      margin-bottom: 14px;
      letter-spacing: 0.05em;
    }
    .footer-col ul { list-style: none; }
    .footer-col ul li { margin-bottom: 8px; }
    .footer-col ul li a {
      font-size: 0.78rem;
      color: var(--text-s);
      transition: color 0.2s;
    }
    .footer-col ul li a:hover { color: var(--accent-l); }
    .footer-bottom {
      border-top: 1px solid var(--border);
      padding-top: 20px;
      text-align: center;
      font-size: 0.72rem;
      color: rgba(255,255,255,0.3);
    }

    /* ── MOBILE STICKY CTA ── */
    .mobile-sticky-cta { display: none; }

    /* ── RESPONSIVE ── */
    @media (max-width: 1024px) {
      .industry-grid { grid-template-columns: repeat(3, 1fr); }
      .footer-grid { grid-template-columns: 1fr 1fr; gap: 28px; }
    }

    @media (max-width: 768px) {
      .site-nav { display: none; }
      .hamburger { display: flex; }
      section { padding: 56px 16px; }
      .hero { padding: 60px 16px 70px; }
      .cta-section { padding: 60px 16px; }

      .what-grid { grid-template-columns: 1fr; gap: 28px; }
      .app-grid { grid-template-columns: 1fr; }
      .course-grid { grid-template-columns: 1fr; }
      .kids-grid { grid-template-columns: 1fr; }
      .industry-grid { grid-template-columns: repeat(2, 1fr); }
      .subsidy-grid { grid-template-columns: 1fr; }

      .hero-stats { gap: 24px; }
      .hero-stat .num { font-size: 1.3rem; }
      .footer-grid { grid-template-columns: 1fr; gap: 24px; }

      .mobile-sticky-cta {
        display: block;
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background: rgba(9,9,11,0.95);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border-top: 1px solid var(--border);
        padding: 12px 16px;
        z-index: 300;
        text-align: center;
      }
      .mobile-sticky-cta a {
        display: block;
        background: var(--accent);
        color: #fff;
        padding: 14px;
        border-radius: 12px;
        font-size: 0.9rem;
        font-weight: 700;
      }
    }
  </style>
</head>
<body>

<!-- ======================= HEADER ======================= -->
<header class="site-header">
  <div class="header-inner">
    <a href="/" class="site-logo">
      <span class="logo-accent">JGAIA</span> | Vibe Coding
    </a>
    <nav class="site-nav">
      <a href="/">JGAIAトップ</a>
      <a href="/vibe-coding" class="active">講座概要</a>
      <a href="/vibe-coding/kids">子ども向け</a>
      <a href="/vibe-coding/manufacturing">業種別</a>
      <a href="#contact" class="nav-cta">お問い合わせ</a>
    </nav>
    <div class="hamburger" onclick="document.querySelector('.site-nav').classList.toggle('show')">
      <span></span><span></span><span></span>
    </div>
  </div>
</header>

<!-- ======================= HERO ======================= -->
<section class="hero">
  <div class="hero-badge syne">JGAIA CERTIFIED PROGRAM</div>
  <h1>生成AIで、誰でも<br><span class="hl">アプリが作れる</span>時代へ</h1>
  <p class="hero-lead">
    ChatGPT・Claude・Geminiなどの生成AIに「こんなアプリが欲しい」と伝えるだけで、
    ビジネスアプリが完成。コーディング経験ゼロから始められるJGAIA認定プログラムです。
  </p>
  <div class="hero-actions">
    <a href="#courses" class="btn btn-primary">コース一覧を見る</a>
    <a href="#contact" class="btn btn-outline">無料相談を申し込む</a>
  </div>
  <div class="hero-stats">
    <div class="hero-stat">
      <div class="num syne">15</div>
      <div class="label">全コース</div>
    </div>
    <div class="hero-stat">
      <div class="num syne">OK</div>
      <div class="label">助成金対象</div>
    </div>
    <div class="hero-stat">
      <div class="num syne">CERT</div>
      <div class="label">修了証発行</div>
    </div>
    <div class="hero-stat">
      <div class="num syne">98%</div>
      <div class="label">満足度</div>
    </div>
  </div>
</section>

<!-- ======================= WHAT IS ======================= -->
<section class="what-is" id="about">
  <div class="section-inner">
    <div class="section-label syne">WHAT IS VIBE CODING</div>
    <h2 class="section-title">バイブコーディングとは？</h2>
    <p class="section-lead">
      「こんなアプリが欲しい」という自然な言葉をAIに伝えるだけで、
      プログラムが自動生成される新しいアプリ開発手法です。
    </p>
    <div class="what-grid">
      <div class="what-visual">
        <div class="flow-steps">
          <div class="flow-step">
            <div class="flow-icon flow-icon-1">&#x1f4ac;</div>
            <div class="flow-text">
              <h4>1. 自然言語で指示</h4>
              <p>「売上管理ダッシュボードを作って」<br>と日本語でAIに伝える</p>
            </div>
          </div>
          <div class="flow-arrow">&#x2193;</div>
          <div class="flow-step">
            <div class="flow-icon flow-icon-2">&#x2728;</div>
            <div class="flow-text">
              <h4>2. AIがコードを自動生成</h4>
              <p>ChatGPT・Claude・Geminiなどの<br>生成AIが即座にコードを書く</p>
            </div>
          </div>
          <div class="flow-arrow">&#x2193;</div>
          <div class="flow-step">
            <div class="flow-icon flow-icon-3">&#x1f680;</div>
            <div class="flow-text">
              <h4>3. アプリが完成</h4>
              <p>動作するアプリをその場で確認。<br>修正も言葉で指示するだけ</p>
            </div>
          </div>
        </div>
      </div>
      <div>
        <h3 style="font-size:1.05rem;font-weight:800;margin-bottom:20px;">従来の開発 vs バイブコーディング</h3>
        <table class="compare-table">
          <tr>
            <th style="width:30%">比較項目</th>
            <th>従来の開発</th>
            <th>バイブコーディング</th>
          </tr>
          <tr>
            <td>必要スキル</td>
            <td class="col-old">プログラミング言語の習得</td>
            <td class="col-new">日本語で指示できればOK</td>
          </tr>
          <tr>
            <td>開発期間</td>
            <td class="col-old">数週間〜数ヶ月</td>
            <td class="col-new">数分〜数時間</td>
          </tr>
          <tr>
            <td>開発コスト</td>
            <td class="col-old">数十万〜数百万円</td>
            <td class="col-new">ほぼゼロ（AI利用料のみ）</td>
          </tr>
          <tr>
            <td>修正対応</td>
            <td class="col-old">仕様変更で追加費用</td>
            <td class="col-new">AIに追加指示するだけ</td>
          </tr>
          <tr>
            <td>学習コスト</td>
            <td class="col-old">6ヶ月〜数年</td>
            <td class="col-new">1日で基礎を習得</td>
          </tr>
        </table>
      </div>
    </div>
  </div>
</section>

<!-- ======================= APP EXAMPLES ======================= -->
<section class="app-examples">
  <div class="section-inner text-center">
    <div class="section-label syne">EXAMPLES</div>
    <h2 class="section-title">こんなアプリが作れます</h2>
    <p class="section-lead">
      受講者が実際に講座内で制作したアプリの一例。
      すべてコーディング未経験者がAIを使って作成しました。
    </p>
    <div class="app-grid">
      <div class="app-card">
        <div class="app-card-visual app-v1">&#x1f4cb;</div>
        <div class="app-card-body">
          <div class="app-tag syne">BUSINESS APP</div>
          <h4>業務日報自動化アプリ</h4>
          <p>社員がスマホで入力するだけで日報が自動集計。上司へのメール送信やグラフ化も自動で完了します。</p>
        </div>
      </div>
      <div class="app-card">
        <div class="app-card-visual app-v2">&#x1f4ca;</div>
        <div class="app-card-body">
          <div class="app-tag syne">CRM</div>
          <h4>顧客管理CRMダッシュボード</h4>
          <p>顧客情報の一元管理、商談進捗の可視化、売上予測グラフをリアルタイムで確認できるWebアプリです。</p>
        </div>
      </div>
      <div class="app-card">
        <div class="app-card-visual app-v3">&#x1f916;</div>
        <div class="app-card-body">
          <div class="app-tag syne">AI CHATBOT</div>
          <h4>社内FAQ AIチャットボット</h4>
          <p>社内マニュアルやFAQを学習させたAIチャットボット。新入社員の質問に24時間自動で回答します。</p>
        </div>
      </div>
    </div>
  </div>
</section>

<!-- ======================= COURSES ======================= -->
<section class="courses" id="courses">
  <div class="section-inner text-center">
    <div class="section-label syne">COURSES</div>
    <h2 class="section-title">コースラインナップ</h2>
    <p class="section-lead">
      目的・レベル・ライフスタイルに合わせて選べる5つのコース。
      すべてJGAIA認定修了証を発行します。
    </p>
    <div class="course-grid">

      <!-- GA -->
      <div class="course-card">
        <div class="course-card-head cc-ga">
          <div class="course-badge syne">COURSE GA</div>
          <h3>生成AI入門1日</h3>
          <p class="course-concept">生成AIの基礎から実際のアプリ作成まで、1日で体験する入門コース</p>
        </div>
        <div class="course-card-body">
          <div class="course-meta">
            <div><div class="meta-label">受講時間</div><div class="meta-value">6時間（1日）</div></div>
            <div><div class="meta-label">対象者</div><div class="meta-value">未経験者・経営者</div></div>
          </div>
          <div class="course-price">&yen;49,800 <span>（税込）</span></div>
          <ul class="course-features">
            <li>ChatGPT / Claude / Gemini の使い分け</li>
            <li>プロンプトエンジニアリング基礎</li>
            <li>ハンズオン：業務アプリを1つ作成</li>
            <li>AI活用の業務効率化戦略</li>
            <li>JGAIA認定修了証を発行</li>
          </ul>
          <a href="/vibe-coding/course-ga" class="btn-course">詳細を見る &rarr;</a>
        </div>
      </div>

      <!-- GB -->
      <div class="course-card">
        <div class="course-card-head cc-gb">
          <div class="course-badge syne">COURSE GB</div>
          <h3>バイブコーディング実践1日</h3>
          <p class="course-concept">AIを使ったアプリ開発のプロセスを1日で体系的に学ぶ実践コース</p>
        </div>
        <div class="course-card-body">
          <div class="course-meta">
            <div><div class="meta-label">受講時間</div><div class="meta-value">6時間（1日）</div></div>
            <div><div class="meta-label">対象者</div><div class="meta-value">実務活用したい方</div></div>
          </div>
          <div class="course-price">&yen;49,800 <span>（税込）</span></div>
          <ul class="course-features">
            <li>Claude Code / Cursor の実践操作</li>
            <li>要件定義からデプロイまでの全工程</li>
            <li>データベース連携アプリの構築</li>
            <li>APIとの連携（外部サービス接続）</li>
            <li>JGAIA認定修了証を発行</li>
          </ul>
          <a href="/vibe-coding/course-gb" class="btn-course">詳細を見る &rarr;</a>
        </div>
      </div>

      <!-- GC -->
      <div class="course-card">
        <div class="course-card-head cc-gc">
          <div class="course-badge syne">COURSE GC</div>
          <h3>AI業務自動化マスター<br>全5回夜間</h3>
          <p class="course-concept">働きながら学べる夜間コース。AI業務自動化を5週間で体系的にマスター</p>
        </div>
        <div class="course-card-body">
          <div class="course-meta">
            <div><div class="meta-label">受講時間</div><div class="meta-value">12.5h（全5回）</div></div>
            <div><div class="meta-label">対象者</div><div class="meta-value">働く社会人</div></div>
          </div>
          <div class="course-price">&yen;68,000 <span>（税込）</span></div>
          <ul class="course-features">
            <li>毎週水曜 19:00〜21:30（オンライン）</li>
            <li>AI × RPA による業務プロセス自動化</li>
            <li>社内ツール・ダッシュボード構築</li>
            <li>チーム向けAI活用提案書の作成</li>
            <li>JGAIA認定修了証を発行</li>
          </ul>
          <a href="/vibe-coding/course-gc" class="btn-course">詳細を見る &rarr;</a>
        </div>
      </div>

      <!-- GD -->
      <div class="course-card">
        <div class="course-card-head cc-gd">
          <div class="course-badge syne">COURSE GD</div>
          <h3>AIセキュリティ・ガバナンス</h3>
          <p class="course-concept">AI生成コードの脆弱性対策とガバナンス体制の構築を1日で学ぶ</p>
        </div>
        <div class="course-card-body">
          <div class="course-meta">
            <div><div class="meta-label">受講時間</div><div class="meta-value">6時間（1日）</div></div>
            <div><div class="meta-label">対象者</div><div class="meta-value">GA/GB受講者</div></div>
          </div>
          <div class="course-price">&yen;49,800 <span>（税込）</span></div>
          <ul class="course-features">
            <li>AI生成コードのセキュリティリスク</li>
            <li>OWASP Top 10 for LLM Applications</li>
            <li>プロンプトインジェクション対策</li>
            <li>社内AIガバナンス規程の策定</li>
            <li>JGAIA認定修了証を発行</li>
          </ul>
          <a href="/vibe-coding/course-gd" class="btn-course">詳細を見る &rarr;</a>
        </div>
      </div>

      <!-- GE -->
      <div class="course-card">
        <div class="course-card-head cc-ge">
          <div class="course-badge syne">COURSE GE</div>
          <h3>AIクリエイティブデザイン</h3>
          <p class="course-concept">画像・動画・資料をAIで自動生成。ビジュアルコンテンツ制作を効率化</p>
        </div>
        <div class="course-card-body">
          <div class="course-meta">
            <div><div class="meta-label">受講時間</div><div class="meta-value">6時間（1日）</div></div>
            <div><div class="meta-label">対象者</div><div class="meta-value">マーケ・広報担当</div></div>
          </div>
          <div class="course-price">&yen;49,800 <span>（税込）</span></div>
          <ul class="course-features">
            <li>AI画像生成（DALL-E / Midjourney）</li>
            <li>AI動画生成（Sora / Runway）</li>
            <li>プレゼン資料の自動デザイン</li>
            <li>ブランドガイドラインに沿ったAI活用</li>
            <li>JGAIA認定修了証を発行</li>
          </ul>
          <a href="/vibe-coding/course-ge" class="btn-course">詳細を見る &rarr;</a>
        </div>
      </div>

    </div>
  </div>
</section>

<!-- ======================= KIDS SECTION ======================= -->
<section class="kids-section" id="kids">
  <div class="section-inner text-center">
    <div class="section-label syne">KIDS COURSES</div>
    <h2 class="section-title">子ども向けコース</h2>
    <p class="section-lead">
      小学3年生から中学3年生まで対応。
      AIを使ったアプリ作りを通じて「つくる喜び」を体験します。
    </p>
    <div class="kids-grid">
      <div class="kids-card">
        <span class="kids-icon">&#x1f9d2;</span>
        <h4>GK1：キッズ体験（半日）</h4>
        <div class="kids-target">小学3〜6年生 + 保護者</div>
        <p>親子で一緒にAIアプリを作る半日の体験コース。ゲームやクイズアプリを制作します。</p>
        <div class="kids-price">&yen;9,800 <span>/1組</span></div>
      </div>
      <div class="kids-card">
        <span class="kids-icon">&#x1f393;</span>
        <h4>GK2：ジュニア入門（1日）</h4>
        <div class="kids-target">中学生（単独参加OK）</div>
        <p>AIを使って本格的なWebアプリを1つ完成させる1日集中コース。</p>
        <div class="kids-price">&yen;29,800 <span></span></div>
      </div>
      <div class="kids-card">
        <span class="kids-icon">&#x1f46a;</span>
        <h4>GK3：親子ペアコース（1日）</h4>
        <div class="kids-target">小3〜中3 + 保護者</div>
        <p>親子で協力してAIアプリ開発に挑戦。家族のコミュニケーションツールも作れます。</p>
        <div class="kids-price">&yen;49,800 <span>/1組</span></div>
      </div>
    </div>
    <div class="kids-link-wrap">
      <a href="/vibe-coding/kids" class="btn btn-outline" style="margin-top:12px;">子ども向けコースの詳細を見る &rarr;</a>
    </div>
  </div>
</section>

<!-- ======================= INDUSTRY ======================= -->
<section class="industry-section" id="industry">
  <div class="section-inner text-center">
    <div class="section-label syne">INDUSTRY COURSES</div>
    <h2 class="section-title">業種別特化コース</h2>
    <p class="section-lead">
      各業界の実務課題に直結したカリキュラム。
      業界固有のアプリをAIで構築するスキルを習得します。
    </p>
    <div class="industry-grid">
      <a href="/vibe-coding/manufacturing" class="industry-card">
        <span class="industry-icon">&#x1f3ed;</span>
        <h4>製造業</h4>
        <p>生産管理・品質検査・予知保全</p>
        <span class="industry-arrow">詳細 &rarr;</span>
      </a>
      <a href="/vibe-coding/healthcare" class="industry-card">
        <span class="industry-icon">&#x1f3e5;</span>
        <h4>医療・ヘルスケア</h4>
        <p>電子カルテ・患者管理・診療支援</p>
        <span class="industry-arrow">詳細 &rarr;</span>
      </a>
      <a href="/vibe-coding/finance" class="industry-card">
        <span class="industry-icon">&#x1f3e6;</span>
        <h4>金融</h4>
        <p>リスク分析・コンプライアンス・顧客管理</p>
        <span class="industry-arrow">詳細 &rarr;</span>
      </a>
      <a href="/vibe-coding/logistics" class="industry-card">
        <span class="industry-icon">&#x1f69a;</span>
        <h4>物流</h4>
        <p>配送最適化・在庫管理・倉庫自動化</p>
        <span class="industry-arrow">詳細 &rarr;</span>
      </a>
      <a href="/vibe-coding/construction" class="industry-card">
        <span class="industry-icon">&#x1f3d7;</span>
        <h4>建設</h4>
        <p>工程管理・安全管理・BIM連携</p>
        <span class="industry-arrow">詳細 &rarr;</span>
      </a>
    </div>
  </div>
</section>

<!-- ======================= SUBSIDY ======================= -->
<section class="subsidy-section" id="subsidy">
  <div class="section-inner">
    <div class="section-label syne">SUBSIDY</div>
    <h2 class="section-title">助成金のご案内</h2>
    <p class="section-lead">
      東京しごと財団「事業外スキルアップ助成金」をご活用いただけます。
      対象コースは実質2万円台から受講可能です。
    </p>
    <div class="subsidy-banner">
      <h3>東京しごと財団「事業外スキルアップ助成金」（令和8年度）</h3>
      <p>
        都内中小企業の従業員が業務命令で受講する場合に、受講料の一部が助成されます。
        対象は3時間以上10時間未満のコースです。事前にJグランツで申請が必要です（受講1ヶ月前まで）。
      </p>
    </div>

    <div class="subsidy-grid">
      <div class="subsidy-card">
        <h4>小規模企業 <span class="subsidy-badge-ok">2/3助成</span></h4>
        <p>受講料の2/3を助成（上限25,000円/人）</p>
        <div class="price-highlight">&yen;24,800〜 <span>/人（実質負担）</span></div>
        <p>例：GA（&yen;49,800）&rarr; 助成&yen;25,000 &rarr; 実質&yen;24,800</p>
      </div>
      <div class="subsidy-card">
        <h4>中小企業 <span class="subsidy-badge-ok">1/2助成</span></h4>
        <p>受講料の1/2を助成（上限25,000円/人）</p>
        <div class="price-highlight">&yen;24,800〜 <span>/人（実質負担）</span></div>
        <p>例：GA（&yen;49,800）&rarr; 助成&yen;24,900 &rarr; 実質&yen;24,900</p>
      </div>
    </div>

    <h4 style="font-size:0.9rem;font-weight:700;margin-bottom:16px;color:var(--text);">コース別 助成金対象</h4>
    <div class="subsidy-eligible" style="max-width:600px;margin-bottom:28px;">
      <div class="eligible-tag eligible-yes">GA（6h）対象</div>
      <div class="eligible-tag eligible-yes">GB（6h）対象</div>
      <div class="eligible-tag eligible-no">GC（12.5h）対象外</div>
      <div class="eligible-tag eligible-yes">GD（6h）対象</div>
      <div class="eligible-tag eligible-yes">GE（6h）対象</div>
    </div>

    <div class="subsidy-note">
      <strong style="color:var(--text);">申請要件</strong><br>
      ・都内に本社または事業所がある中小企業の従業員（代表者は対象外）<br>
      ・会社が全額負担し、業務命令として受講すること<br>
      ・受講1ヶ月前までに<a href="https://www.jgrants-portal.go.jp/" target="_blank" rel="noopener">Jグランツ</a>で事前申請が必要<br>
      ・受付期間：2026年3月1日〜2027年2月28日<br>
      ・詳細：<a href="https://www.koyokankyo.shigotozaidan.or.jp/jigyo/skillup/skill-R8jigyogai.html" target="_blank" rel="noopener">東京しごと財団 公式サイト</a>
    </div>
  </div>
</section>

<!-- ======================= FAQ ======================= -->
<section class="faq" id="faq">
  <div class="section-inner text-center">
    <div class="section-label syne">FAQ</div>
    <h2 class="section-title">よくあるご質問</h2>
    <p class="section-lead">お問い合わせの多い質問をまとめました。</p>
    <div class="faq-list" style="text-align:left;">

      <div class="faq-item">
        <div class="faq-q">プログラミング経験がなくても受講できますか？</div>
        <div class="faq-a">はい、全く問題ありません。バイブコーディングは「日本語でAIに指示する」ことでアプリを作る手法です。GA（生成AI入門）コースは完全未経験の方を対象に設計されています。</div>
      </div>

      <div class="faq-item">
        <div class="faq-q">どのコースから始めればよいですか？</div>
        <div class="faq-a">まずはGA（生成AI入門1日）から始めることをお勧めします。生成AIの基礎と実際のアプリ作成を1日で体験できます。すでにChatGPT等を使い慣れている方はGBから直接受講いただくことも可能です。</div>
      </div>

      <div class="faq-item">
        <div class="faq-q">オンラインで受講できますか？</div>
        <div class="faq-a">GCコース（AI業務自動化マスター 全5回夜間）は完全オンラインです。GA・GB・GD・GEは会場受講＋オンライン配信のハイブリッド形式で実施しています。</div>
      </div>

      <div class="faq-item">
        <div class="faq-q">法人で複数名の申し込みは可能ですか？</div>
        <div class="faq-a">はい、法人でのまとめてのお申し込みも承っております。5名以上の団体割引や、貴社オフィスでの出張セミナーも対応可能です。お問い合わせフォームよりご相談ください。</div>
      </div>

      <div class="faq-item">
        <div class="faq-q">助成金はどのように申請すればよいですか？</div>
        <div class="faq-a">東京しごと財団の「事業外スキルアップ助成金」は、受講の1ヶ月前までにJグランツ（電子申請システム）から事前申請が必要です。GA・GB・GD・GEの各コース（6時間）が助成対象です。GC（12.5時間）は10時間を超えるため対象外となります。</div>
      </div>

      <div class="faq-item">
        <div class="faq-q">修了証はどのような場面で使えますか？</div>
        <div class="faq-a">JGAIA認定修了証は、生成AIを活用したアプリ開発スキルを持つことの公的な証明として、就職・転職活動、社内の昇進審査、クライアントへの提案時などにご活用いただけます。</div>
      </div>

      <div class="faq-item">
        <div class="faq-q">受講に必要なものは何ですか？</div>
        <div class="faq-a">ノートPC（Windows / Mac）とインターネット接続が必要です。ChatGPTやClaude等のアカウントの事前作成をお願いしています。具体的な準備手順は、お申し込み後にご案内します。</div>
      </div>

      <div class="faq-item">
        <div class="faq-q">JGAIAとJQCAの違いは何ですか？</div>
        <div class="faq-a">JGAIA（日本生成AI協会）は生成AI全般の普及・教育を目的とした団体です。JQCA（日本量子コンピューティング協会）は量子コンピューティング分野に特化した別の団体です。本講座はJGAIAが主催する生成AI特化のプログラムです。</div>
      </div>

    </div>
  </div>
</section>

<!-- ======================= CTA ======================= -->
<section class="cta-section" id="contact">
  <h2>まずは無料相談から</h2>
  <p>
    コース選びに迷ったら、お気軽にご相談ください。
    経験豊富なスタッフが最適なコースをご提案します。
  </p>
  <div class="cta-buttons">
    <a href="mailto:info@jgaia.org?subject=%E3%83%90%E3%82%A4%E3%83%96%E3%82%B3%E3%83%BC%E3%83%87%E3%82%A3%E3%83%B3%E3%82%B0%E8%AC%9B%E5%BA%A7%E3%81%AE%E3%81%94%E7%9B%B8%E8%AB%87" class="btn btn-primary">無料相談を申し込む</a>
    <a href="#courses" class="btn btn-outline">コース一覧に戻る</a>
  </div>
  <div class="cta-contact-info">
    一般社団法人日本生成AI協会（JGAIA）<br>
    <a href="mailto:info@jgaia.org">info@jgaia.org</a><br>
    〒104-0061 東京都中央区銀座1-22-11 銀座大竹ビジデンス2階
  </div>
</section>

<!-- ======================= FOOTER ======================= -->
<footer class="site-footer">
  <div class="footer-inner">
    <div class="footer-grid">
      <div class="footer-brand">
        <div class="footer-logo"><span class="logo-accent">JGAIA</span> | 日本生成AI協会</div>
        <p>生成AIの社会実装を推進し、すべての人がAIの恩恵を受けられる社会の実現を目指します。</p>
      </div>
      <div class="footer-col">
        <h4>講座</h4>
        <ul>
          <li><a href="/vibe-coding">講座概要</a></li>
          <li><a href="/vibe-coding/course-ga">GA：生成AI入門</a></li>
          <li><a href="/vibe-coding/course-gb">GB：バイブコーディング実践</a></li>
          <li><a href="/vibe-coding/course-gc">GC：AI業務自動化マスター</a></li>
          <li><a href="/vibe-coding/course-gd">GD：AIセキュリティ</a></li>
          <li><a href="/vibe-coding/course-ge">GE：AIクリエイティブ</a></li>
        </ul>
      </div>
      <div class="footer-col">
        <h4>特別講座</h4>
        <ul>
          <li><a href="/vibe-coding/kids">子ども向け</a></li>
          <li><a href="/vibe-coding/manufacturing">製造業特化</a></li>
          <li><a href="/vibe-coding/healthcare">医療・ヘルスケア特化</a></li>
          <li><a href="/vibe-coding/finance">金融特化</a></li>
          <li><a href="/vibe-coding/logistics">物流特化</a></li>
          <li><a href="/vibe-coding/construction">建設特化</a></li>
        </ul>
      </div>
      <div class="footer-col">
        <h4>協会情報</h4>
        <ul>
          <li><a href="https://www.jgaia.org/" target="_blank" rel="noopener">JGAIAトップ</a></li>
          <li><a href="mailto:info@jgaia.org">お問い合わせ</a></li>
          <li><a href="https://www.jgaia.org/privacy" target="_blank" rel="noopener">プライバシーポリシー</a></li>
          <li><a href="https://www.jgaia.org/terms" target="_blank" rel="noopener">利用規約</a></li>
        </ul>
      </div>
    </div>
    <div class="footer-bottom">
      &copy; 2026 一般社団法人日本生成AI協会（JGAIA）All rights reserved.
    </div>
  </div>
</footer>

<!-- モバイルスティッキーCTA -->
<div class="mobile-sticky-cta">
  <a href="#contact">無料相談を申し込む</a>
</div>

<script>
// ハンバーガーメニュー
document.querySelector('.hamburger').addEventListener('click', function() {
  const nav = document.querySelector('.site-nav');
  if (nav.style.display === 'flex') {
    nav.style.display = 'none';
  } else {
    nav.style.display = 'flex';
    nav.style.flexDirection = 'column';
    nav.style.position = 'absolute';
    nav.style.top = '64px';
    nav.style.left = '0';
    nav.style.right = '0';
    nav.style.background = 'rgba(9,9,11,0.97)';
    nav.style.backdropFilter = 'blur(16px)';
    nav.style.padding = '16px';
    nav.style.borderBottom = '1px solid rgba(255,255,255,0.07)';
    nav.style.zIndex = '300';
    nav.style.gap = '4px';
  }
});

// スムーススクロール
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
  anchor.addEventListener('click', function(e) {
    const target = document.querySelector(this.getAttribute('href'));
    if (target) {
      e.preventDefault();
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      // モバイルメニューを閉じる
      const nav = document.querySelector('.site-nav');
      if (window.innerWidth <= 768) nav.style.display = 'none';
    }
  });
});
</script>

</body>
</html>"""
