---
version: alpha
name: JGAIA 協会サイト
description: jgaia.org（日本生成AI協会）の公開サイトと講座予約システムの視覚的アイデンティティ。base.html が全ページ共通の紺の外枠を持ち、各ページは本文だけを白くする構造。
colors:
  # ── ブランド（協会サイトの外枠） ──
  primary: "#041F4E"
  primary-deep: "#0D1B3E"
  # ── 白い本文の地（.lp-body / .course-body / .kids-body） ──
  ink: "#FFFFFF"
  ink-subtle: "#F8FAFC"
  ink-muted: "#F0F4F8"
  # ── 白地の上の文字 ──
  text: "#1A1A2E"
  text-subtle: "#4A5568"
  text-muted: "#64748B"
  # ── 罫線 ──
  border: "#E2E8F0"
  border-light: "#D1D9E6"
  # ── 既定アクセント（コース固有色が無いとき） ──
  accent: "#3B82F6"
  accent-deep: "#1D4ED8"
  # ── 状態 ──
  success: "#10B981"
  success-deep: "#047857"
  success-bg: "#ECFDF5"
  warning-bg: "#FFFBEB"
  warning-border: "#FDE68A"
  warning-text: "#92400E"
  error: "#DC2626"
  error-bg: "#FEF2F2"
  error-border: "#FECACA"
  # ── 講座ごとのアクセント（DBから注入。値はコース単位で変わる） ──
  course-accent-sample-a: "#2563EB"
  course-accent-light-sample-a: "#93C5FD"
  course-accent-sample-b: "#4F46E5"
  course-accent-light-sample-b: "#A5B4FC"
  course-accent-sample-c: "#0D9488"
  course-accent-light-sample-c: "#5EEAD4"
typography:
  hero-display:
    fontFamily: Noto Sans JP
    fontSize: 48px
    fontWeight: 700
    lineHeight: 1.2
  headline-lg:
    fontFamily: Noto Sans JP
    fontSize: 32px
    fontWeight: 700
    lineHeight: 1.4
  headline-md:
    fontFamily: Noto Sans JP
    fontSize: 22px
    fontWeight: 800
    lineHeight: 1.4
  headline-sm:
    fontFamily: Noto Sans JP
    fontSize: 18px
    fontWeight: 700
    lineHeight: 1.5
  body-lg:
    fontFamily: Noto Sans JP
    fontSize: 16px
    fontWeight: 400
    lineHeight: 1.7
  body-md:
    fontFamily: Noto Sans JP
    fontSize: 15px
    fontWeight: 400
    lineHeight: 1.7
  body-sm:
    fontFamily: Noto Sans JP
    fontSize: 14px
    fontWeight: 400
    lineHeight: 1.7
  label-md:
    fontFamily: Noto Sans JP
    fontSize: 13px
    fontWeight: 600
    lineHeight: 1.5
  label-sm:
    fontFamily: Noto Sans JP
    fontSize: 12px
    fontWeight: 600
    lineHeight: 1.5
  section-label:
    fontFamily: Noto Sans JP
    fontSize: 12px
    fontWeight: 600
    lineHeight: 1.4
    letterSpacing: 0.12em
  base:
    fontFamily: Noto Sans
    fontSize: 16px
    fontWeight: 400
    lineHeight: 1.4
rounded:
  base: 4px
  sm: 6px
  md: 8px
  lg: 10px
  xl: 12px
  "2xl": 16px
  button: 0.8em
  pill: 2em
  full: 999px
spacing:
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 40px
  "2xl": 80px
  wrap-max: 1100px
  wrap-padding: 24px
  header-height: 8em
  hero-min-height: 420px
  button-padding: 14px 28px
components:
  link-button:
    textColor: "{colors.ink}"
    borderColor: "{colors.ink}"
    rounded: "{rounded.button}"
    padding: 0.6em 1em
  link-button-hover:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.primary}"
  link-button-white:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.primary}"
  body-wrapper:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.text}"
    typography: "{typography.body-lg}"
  wrap:
    width: "{spacing.wrap-max}"
    padding: "{spacing.wrap-padding}"
  stats-bar:
    backgroundColor: "{colors.ink-muted}"
    borderColor: "{colors.border}"
    padding: 40px 24px
  stat-divider:
    borderColor: "{colors.border-light}"
  section-label:
    textColor: "{colors.accent-deep}"
    typography: "{typography.section-label}"
  form-submit:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.ink}"
    rounded: "{rounded.base}"
    padding: 14px
    typography: "{typography.body-sm}"
  card:
    backgroundColor: "{colors.ink}"
    borderColor: "{colors.border}"
    textColor: "{colors.text}"
    rounded: "{rounded.md}"
  notice-warning:
    backgroundColor: "{colors.warning-bg}"
    borderColor: "{colors.warning-border}"
    textColor: "{colors.warning-text}"
    rounded: "{rounded.md}"
  notice-error:
    backgroundColor: "{colors.error-bg}"
    borderColor: "{colors.error-border}"
    textColor: "{colors.error}"
    rounded: "{rounded.md}"
---

# DESIGN.md — JGAIA 協会サイト

## Overview

jgaia.org（日本生成AI協会）の公開サイトと講座予約システム。Flask + Jinja2 テンプレートで、`templates/base.html` が全ページの外枠を持つ。

**この製品の構造を先に理解すること。** 協会サイトは「紺の外枠の中に、白い本文が浮いている」という一枚の作りになっている。

- `base.html` が**透明のヘッダー**・**紺の粒子背景**（`.particles-background` / `.polygon-background`）・**フッター**を提供する
- 各ページはその上に、**本文だけを白くするラッパー**を1枚敷く — `.lp-body`（/vibe-coding）・`.course-body`（講座詳細）・`.kids-body`（キッズ）はすべて同じ作り
- ヒーローだけは紺の上にそのまま置き、文字は白のまま。ヒーローに背景色を敷かない

**新しいページを作るときも、この3層（base.html の外枠 → 白い本文ラッパー → ヒーローは紺のまま）を必ず踏襲する。** 過去にこの構造を破って本番の文字が消えた事故が複数回起きている（下の Do's and Don'ts に日付つきで記録）。

性格は **「協会の顔」**。落ち着いた紺を基調に、講座ごとの色を1点だけ効かせる。公開サイトなので情報密度より読みやすさを優先し、行間は 1.7 を基本にゆったり取る。

## Colors

ブランドは **濃紺（`#041F4E`）** の一色で、そこに講座ごとのアクセントが乗る。

- **Primary（`#041F4E` 協会の紺）** — ブランドの色。白ボタンの文字色、白地の上の見出し、反転ボタンの地色
- **Primary Deep（`#0D1B3E`）** — 管理画面と一部の見出しで使う、さらに沈んだ紺
- **本文の地は3段**：`ink` `#FFFFFF`（本文の地）→ `ink-subtle` `#F8FAFC`（薄い区画）→ `ink-muted` `#F0F4F8`（統計バーなどの帯）
- **白地の上の文字は3段**：`text` `#1A1A2E`（本文）→ `text-subtle` `#4A5568`（補足）→ `text-muted` `#64748B`（キャプション）
- **罫線は2段**：`border` `#E2E8F0`（通常）／ `border-light` `#D1D9E6`（区切りの縦罫）
- **既定アクセント**：`accent` `#3B82F6`（ボタンの地）／ `accent-deep` `#1D4ED8`（**白地の上の文字色**）。白地に `#3B82F6` の文字を置かない — 濃い方を使う

### 講座ごとのアクセント

講座詳細ページは、コースごとに **`accent` / `accent_light` / `gradient` の3点セット**をDBから受け取り、`--c-accent` `--c-accent-l` `--c-gradient` に注入する。例：`#2563EB`/`#93C5FD`、`#4F46E5`/`#A5B4FC`、`#0D9488`/`#5EEAD4`。

**使い分けは地の明るさで決まる。** `accent`（濃い方）は白地の上の文字とボタンの地に、`accent_light`（淡い方）は紺のヒーローの上の文字に使う。逆にすると読めなくなる。

## Typography

**書体は `'Noto Sans', 'Noto Sans JP', sans-serif` の一本だけ。** 変数は `--font-site` で、`--font-d`（見出し用）と `--font`（本文用）はどちらもその別名にしてある。

**`Syne` と `DM Sans` を使ってはならない**（社長ご指摘 2026-08-17・2度目）。どちらも欧文専用で和文の字形を持たないため、数字や英字が日本語に混ざるとその文字だけ別書体で描かれる。実測した割れ方：

- 「小3〜」＝ 小:Noto / 3:Syne / 〜:Noto
- 「0行」＝ 0:Syne / 行:Noto
- 「3つのコース」「（1日）」「10:00〜13:00」も同じ

1か所ずつ直しても新しい文言を足すたびに再発するため、**変数の側で断つ**。変数名 `--font-d` / `--font` は既存の参照が多いので残し、値だけ `--font-site` に揃える。

サイズは公開サイトらしく大きめに取る。基準は `base.html` の `16px/1.4`、本文ラッパーの中では **行間 1.7**。ヒーローの見出しは `clamp()` で流動させる（例：`clamp(2rem, 7vw, 5rem)`）。太さは 400 / 600 / 700 / 800。

## Layout

- 本文の横幅は `.wrap { max-width: 1100px; margin: 0 auto; padding: 0 24px; }`
- **ヒーローの高さは `calc(100vh - 8em)`。`100vh` にしない** — ヘッダーは `position: relative` で場所を取るため、`100vh` にすると1画面目がヘッダーのぶんだけはみ出す
- 講座詳細のヒーローは `min-height: 420px`、内側 `60px 80px 80px`
- 余白の刻みは 4 / 8 / 16 / 24 / 40 / 80px
- 統計バーなどの横並びは `grid-template-columns: repeat(4, 1fr)` に `border-left` の縦罫（`border-light`）

## Elevation & Depth

このサイトの奥行きは **影ではなく「紺の上に薄く色を重ねる」** ことで作る。

- 講座詳細のヒーローは、紺の粒子背景の上に `background: {{ c.gradient }}` を `opacity: 0.32` で重ねる
- **黒の重ね塗りを使わない。** 下地が白だった頃の名残で、しかも親の `opacity` が `::after` にも掛かって1/4しか効かず、「薄いグレーの上に白文字」＝見出しがほぼ読めない状態になっていた
- 白い本文の中では、影ではなく `1px solid #E2E8F0` の罫線とカードの地色で区切る

## Shapes

角丸の基準は **`--r: 4px`**。フォーム・ボタン・入力欄はこれ。

- **4px（`base`）** — フォーム、送信ボタン、入力欄。最も多い
- **6 / 8 / 10 / 12 / 16px** — カード、画像、パネル。大きい要素ほど大きく
- **`0.8em`（`button`）** — 協会サイト共通の `a.link-button`
- **`2em`（`pill`）／ `999px`（`full`）** — 丸ボタン、バッジ

## Components

### 共通ボタン（`a.link-button`）
`base.html` と `index.html` が持つ協会サイト共通のボタン。白の2px枠・白文字・角丸 `0.8em`。ホバーで**白地に紺文字（`#041F4E`）へ反転**する。`.btn-white` は最初から反転した状態で、ホバーで透明に戻る。`.btn-rounded` は角丸を `2em` にする。

### 本文ラッパー（`.lp-body` / `.course-body` / `.kids-body`）
紺の外枠の中に白い本文を作る唯一の方法。`background: #fff` ＋ `color: #1A1A2E` ＋ `font-family` ＋ `line-height: 1.7`。**新しいページもこの3つのどれかと同じ作りにする。**

リンクのリセットは **`.lp-body :where(a)` と書く**。`.lp-body a` と書いてはならない（理由は Do's and Don'ts）。

### 統計バー（`.stats-bar`）
地は `ink-muted` `#F0F4F8`、下に `border` の罫。4カラムのグリッドで、項目間は `border-left: 1px solid #D1D9E6`。

### 節ラベル（`.sec-label`）
`accent-deep` の色、12px/600、字間 0.12em、大文字。前に `16px × 1px` の短い横線を `::before` で置く。

### フォーム送信ボタン（`.form-submit`）
幅いっぱい、`accent` の地に白文字、角丸 4px、内側 14px、14px/600。

### 通知（警告・エラー）
警告は `#FFFBEB` の地に `#FDE68A` の枠と `#92400E` の文字。エラーは `#FEF2F2` の地に `#FECACA` の枠と `#DC2626` の文字。**必ず3点セットで指定する。**

## Do's and Don'ts

このサイトで実際に起きた事故の記録。すべて本番で文字や色が消えている。

- **Don't** `base.html` のヘッダー・フッター・背景を上書きしない（社長ご指摘 2026-08-16）。過去にキッズページが `:root` ごと白テーマに塗り替え・`body` を白で `!important`・紺の背景を `display:none` で全消し・透明ヘッダーを黒帯に置換していた結果、そのページだけ協会サイトと違う顔になり、さらに `h1`・リード文・「無料相談はこちら」が白地に白文字で本番から消えていた。**白くするのは本文ラッパーだけ**
- **Don't** `:root { color: #fff }` を白い地の上で継承させない。白背景に置く要素は**文字色を必ず明示する**（`.site-lede` が `color: #041F4E` を持つのはこのため）
- **Don't** `.lp-body a` のように**要素セレクタを混ぜたセレクタを書かない**（社長ご指摘 2026-08-17）。クラス1つ（`.btn-corp` など）より詳細度が高くなり、ボタンに書いた色が黙って捨てられる。実測で「法人研修のご相談」が `#1A1A2E` on `#0D1B3E` ＝ **コントラスト比 1.01（ほぼ不可視）**、コース詳細ボタン4つも青が消えていた。**リセットは `:where(a)` で書く**（詳細度ゼロなのでボタンの色に負ける）
- **Don't** `Syne` / `DM Sans` を読み込まない・効かせない（社長ご指摘 2026-08-17・2度目）。和文の字形を持たないため日本語に混ざった数字・英字だけ別書体で割れる
- **Don't** Jinja のグラデーション変数を裸で書かない。`{{ c.gradient }};` は「値」であって宣言ではないため、プロパティ名の無い不正な宣言としてブラウザが黙って1行捨てる。**必ず `background: {{ c.gradient }};` と書く。** 2026-08-16 まで4か所がこの書き方で、ヒーロー・COURSE GAバッジ・講師アイコン・「送信する」ボタンの色が全部消えていた（送信ボタンは灰色＝押せないように見えた）
- **Don't** ヒーローに背景色を敷かない。透明ヘッダーとの間に横一本の継ぎ目が出て、ヘッダーだけ別ページのように見える
- **Don't** ヒーロー（紺の上）に本文用の濃い色を使わない。`accent-deep` `#1D4ED8` や `text-subtle` `#4A5568` は白地専用で、紺の上では読めない。紺の上は `accent_light` 系と白
- **Do** ヒーローの高さは `calc(100vh - 8em)` にする。`100vh` は1画面目がヘッダーのぶんはみ出す
- **Do** 講座色は「濃い方＝白地の文字とボタン地」「淡い方＝紺の上の文字」で使い分ける
- **Do** 本文の横幅は `.wrap` の `max-width: 1100px` に揃える
- **Do** 色を書く前に、その要素の**背後にあるのが紺か白か**を確かめる。このサイトの事故はすべてこの取り違えから起きている
