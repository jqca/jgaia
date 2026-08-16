"""base.html と同一のヘッダー HTML/CSS（白テーマ版）を返すユーティリティ。
Kids・Industry など base.html を継承しないスタンドアロンページで使用。"""


def get_header_css():
    """base.html のヘッダーを白テーマで表示するための CSS を返す"""
    return """
  /* ── 共通ヘッダー（base.html 準拠・白テーマ） ── */
  .header-nav {
    display:block;position:fixed;top:0;left:0;
    width:100vw;height:8em;padding:10px 4%;
    background:rgba(255,255,255,0.95) !important;
    backdrop-filter:blur(24px);
    border-bottom:1px solid #e2e8f0;
    z-index:100;
  }
  .header-nav nav {display:flex;align-items:center}
  .header-nav nav .nav-logo {
    height:clamp(1rem,7vw,9rem);width:clamp(1rem,15vw,18rem);
    padding-top:2%;position:relative;z-index:2;
  }
  .header-nav nav .nav-logo a {display:block;height:100%;text-decoration:none}
  .header-nav nav .nav-logo .logo-text {
    font-size:clamp(1.2rem,2vw,1.8rem);font-weight:900;
    color:#1a1a2e;letter-spacing:0.05em;line-height:1.2;
  }
  .header-nav nav .nav-logo .logo-sub {
    font-size:clamp(0.5rem,0.7vw,0.7rem);
    color:#4a5568;letter-spacing:0.04em;
  }
  .header-nav nav .nav-item {
    display:flex;gap:clamp(0.5rem,1.5vw,2rem);
    position:absolute;right:40px;top:53px;z-index:1;
  }
  .header-nav nav .nav-item .nav-menu-list {
    display:flex;gap:calc(100vw / 33);align-items:center;margin-left:20vw;
  }
  .nav-menu-list__item {display:list-item;margin:0;list-style:none;text-align:center}
  .nav-menu-list__item a {
    display:flex;gap:0.3rem;flex-wrap:wrap;flex-direction:column;
    justify-content:center;align-items:center;
    font-size:clamp(1rem,1.2vw,3rem);color:#1a1a2e;
    text-decoration:none;transition:opacity 0.2s;
  }
  .nav-menu-list__item a:hover {opacity:0.7}
  .nav-menu-list__item a strong {display:block;width:100%;white-space:nowrap}
  .nav-menu-list__item a span {
    display:block;overflow:hidden;font-size:0.8em;line-height:24px;
    text-align:center;white-space:nowrap;color:#64748b;
  }
  /* ドロップダウン */
  .nav-menu-list .dropdown {position:relative}
  .nav-menu-list .dropdown > a strong::after {content:" ▾";font-size:0.7em;opacity:0.75}
  .nav-menu-list .dropdown-menu {
    display:block;position:absolute;top:calc(100% + 12px);
    left:50%;transform:translateX(-50%) translateY(-6px);
    min-width:220px;list-style:none;margin:0;padding:8px;
    background:rgba(255,255,255,0.97);backdrop-filter:blur(12px);
    border:1px solid #e2e8f0;border-radius:12px;
    box-shadow:0 8px 24px rgba(0,0,0,0.1);
    opacity:0;visibility:hidden;
    transition:opacity 0.2s ease,transform 0.2s ease,visibility 0.2s;
    z-index:1000;
  }
  .nav-menu-list .dropdown-menu::before {
    content:"";display:block;position:absolute;top:-12px;left:0;right:0;height:12px;
  }
  .nav-menu-list .dropdown-menu::after {
    content:"";position:absolute;top:-6px;left:50%;
    transform:translateX(-50%) rotate(45deg);
    width:12px;height:12px;background:rgba(255,255,255,0.97);
    border-left:1px solid #e2e8f0;border-top:1px solid #e2e8f0;
  }
  .nav-menu-list .dropdown:hover .dropdown-menu,
  .nav-menu-list .dropdown:focus-within .dropdown-menu {
    opacity:1;visibility:visible;transform:translateX(-50%) translateY(0);
  }
  .nav-menu-list .dropdown-menu li {list-style:none;margin:0;padding:0;text-align:left}
  .nav-menu-list .dropdown-menu li::before {display:none}
  .nav-menu-list .dropdown-menu li + li {margin-top:2px}
  .nav-menu-list .dropdown-menu a {
    display:block;padding:10px 14px;
    font-size:0.95rem !important;font-weight:500;line-height:1.4;
    color:#1a1a2e;text-decoration:none;white-space:nowrap;
    border-radius:8px;transition:background 0.18s ease,color 0.18s ease;
  }
  .nav-menu-list .dropdown-menu a:hover {
    background:rgba(99,102,241,0.1);color:#6366f1;
  }
  .nav-profile {display:flex;gap:1rem;align-items:center}
  .nav-profile .nav-register {
    color:#fff !important;background:#6366f1 !important;border-color:#6366f1 !important;
    display:inline-block;padding:0.6em 1.5em;border-radius:6px;
    font-size:0.9rem;font-weight:600;text-decoration:none;transition:opacity 0.2s;
  }
  .nav-profile .nav-register:hover {opacity:0.85}
  .nav-profile .nav-login {
    color:#1a1a2e !important;background:transparent !important;
    border:1px solid #d1d9e6 !important;
    display:inline-block;padding:0.6em 1.5em;border-radius:6px;
    font-size:0.9rem;font-weight:500;text-decoration:none;transition:all 0.2s;
  }
  .nav-profile .nav-login:hover {color:#1a1a2e;border-color:rgba(0,0,0,0.15)}
  .hamburger {
    display:none;font-size:clamp(2rem,8vw,5rem);cursor:pointer;
    position:absolute;right:20px;top:20px;color:#1a1a2e;
  }
  /* モバイルメニュー */
  .mobile-menu {
    display:none;flex-direction:column;align-items:flex-start;
    width:100%;height:100vh;background-color:#001e5f;color:white;
    position:fixed;top:0;left:0;z-index:1000;
  }
  .mobile-menu.active {display:flex}
  .mobile-menu .mobile-menu-list {
    list-style:none;padding:80px 30px 30px;margin:0;
    display:flex;flex-direction:column;width:100%;
  }
  .mobile-menu .mobile-nav-item {
    font-size:20px;text-align:left;padding:15px 0;width:100%;
    border-bottom:1px solid white;
  }
  .mobile-menu .mobile-nav-item a {color:white;text-decoration:none}
  .mobile-menu .mobile-subitem {
    padding-left:1.2em;border-left:2px solid rgba(255,255,255,0.3);
  }
  .mobile-menu .mobile-subitem a {font-size:0.9em;opacity:0.85}
  .mobile-menu .mobile-subitem a span {opacity:0.7}
  .mobile-log-item {
    position:fixed;bottom:30px;font-size:clamp(1rem,3vw,1.5rem);
    left:50%;transform:translateX(-50%);width:90%;max-width:100%;text-align:center;
  }
  .close-btn {
    position:absolute;top:10px;right:10px;font-size:30px;cursor:pointer;color:white;
  }
  @media(max-width:768px){
    .header-nav {height:auto;padding:12px 16px}
    .header-nav nav .nav-item {display:none}
    .hamburger {display:block}
  }
"""


def get_header_html():
    """base.html と同一のヘッダー HTML を返す"""
    return """
<header class="header-nav">
    <div class="pc-menu" id="pcMenu">
        <nav>
            <div class="nav-logo">
                <a href="/">
                    <div class="logo-text">JGAIA</div>
                    <div class="logo-sub">一般社団法人日本生成AI協会</div>
                </a>
            </div>
            <div class="nav-item">
                <ul class="nav-menu-list">
                    <li class="nav-menu-list__item"><a href="/"><strong>Home</strong><span>ホーム</span></a></li>
                    <li class="nav-menu-list__item dropdown">
                        <a href="/company-info"><strong>About</strong><span>協会情報</span></a>
                        <ul class="dropdown-menu">
                            <li><a href="/company-info">協会概要</a></li>
                            <li><a href="/team-members">協会メンバー紹介</a></li>
                        </ul>
                    </li>
                    <li class="nav-menu-list__item dropdown">
                        <a href="/course"><strong>Qualifications</strong><span>資格／試験講座</span></a>
                        <ul class="dropdown-menu">
                            <li><a href="/course">資格・認定講座</a></li>
                            <li><a href="/vibe-coding">バイブコーディング講座</a></li>
                        </ul>
                    </li>
                    <li class="nav-menu-list__item"><a href="/gpu-guide"><strong>GPU Guide</strong><span>GPU・計算環境</span></a></li>
                    <li class="nav-menu-list__item"><a href="/member"><strong>Association Members</strong><span>協会員一覧</span></a></li>
                    <li class="nav-menu-list__item"><a href="/join-us"><strong>JoinUs</strong><span>協会員募集</span></a></li>
                    <li class="nav-menu-list__item"><a href="/contact"><strong>Contact</strong><span>お問い合わせ</span></a></li>
                </ul>
                <div class="nav-profile">
                    <a class="link-button nav-register" href="https://member.jgaia.org/auth/register">登録</a>
                    <a class="link-button btn-white nav-login" href="https://member.jgaia.org/auth/login">ログイン</a>
                </div>
            </div>
        </nav>
        <div class="hamburger" onclick="toggleMenu()">&#9776;</div>
    </div>
    <div class="mobile-menu" id="mobileMenu">
        <div class="close-btn" onclick="toggleMenu()">&#10005;</div>
        <ul class="mobile-menu-list">
            <li class="mobile-nav-item"><a href="/">ホーム <span>Home</span></a></li>
            <li class="mobile-nav-item"><a href="/company-info">協会情報 <span>About</span></a></li>
            <li class="mobile-nav-item mobile-subitem"><a href="/team-members">協会メンバー紹介 <span>Member Introductions</span></a></li>
            <li class="mobile-nav-item"><a href="/course">資格／試験講座 <span>Qualifications</span></a></li>
            <li class="mobile-nav-item mobile-subitem"><a href="/vibe-coding">バイブコーディング講座 <span>Vibe Coding</span></a></li>
            <li class="mobile-nav-item"><a href="/gpu-guide">GPU・計算環境 <span>GPU Guide</span></a></li>
            <li class="mobile-nav-item"><a href="/member">協会員一覧 <span>Association Members</span></a></li>
            <li class="mobile-nav-item"><a href="/join-us">協会員募集 <span>JoinUs</span></a></li>
            <li class="mobile-nav-item"><a href="/contact">お問い合わせ <span>Contact</span></a></li>
            <li class="mobile-log-item">
                <a class="link-button nav-register" href="https://member.jgaia.org/auth/register">登録</a>
                <a class="link-button btn-white nav-login" href="https://member.jgaia.org/auth/login">ログイン</a>
            </li>
        </ul>
    </div>
</header>
"""


def get_header_js():
    """モバイルメニューの toggleMenu 関数"""
    return """
function toggleMenu() {
    document.getElementById("mobileMenu").classList.toggle("active");
}
"""
