# -*- coding: utf-8 -*-
"""全26講座の 料金／開催場所／想定支出／想定利益 の一覧を、実データから作る。

⛔ 数字を手で書かない。料金・定員・日数は booking.COURSES、開催形式は
   掲載ページのモジュール（solo_ceo / vibe_coding_courses /
   vibe_coding_industry / vibe_coding_kids）から引く。
⛔ 会場費は「不明」であって0ではない。会場が1つも決まっていないので
   金額を作れない。0円と書くと、決まった瞬間に嘘になる。
"""
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('INQUIRY_LOG_DIR',
                      os.path.join(os.environ['TEMP'], 'jgaia-pl'))

import booking                      # noqa: E402
import solo_ceo                     # noqa: E402
import vibe_coding_courses as vc    # noqa: E402
import vibe_coding_industry as vi   # noqa: E402

STRIPE = 0.036          # カード決済手数料

# ── 掲載ページの「開催形式」を、講座コードに結びつける
fmt = {}
for key, c in solo_ceo.COURSES.items():
    fmt[key.upper().replace('SP', 'SP-')] = c.get('format', '')
for key, c in vc.COURSES.items():
    fmt[key.upper()] = c.get('format', '')
for slug, ind in vi.INDUSTRIES.items():
    for c in ind.get('courses', []):
        code = (c.get('code') or c.get('id') or '').upper()
        if code:
            fmt[code] = c.get('format', '')
# 子ども向けはモジュールに format が無いので掲載ページの記載に合わせる
for k in ('GK1', 'GK2', 'GK3'):
    fmt.setdefault(k, '会場開催')


def short(f):
    if not f:
        return '（未記載）'
    if 'オンライン' in f and '会場' not in f:
        return 'オンラインのみ'
    if '会場' in f and 'オンライン' in f:
        return '会場＋オンライン'
    return '会場のみ'


rows = []
for c in booking.COURSES:
    code, price = c['code'], c['price']
    days = booking.course_days(code)
    cap = c['capacity']
    fee = booking.instructor_fee(code)          # 1開催あたりの定額
    f = fmt.get(code, '')
    # 1名のとき / 定員のとき
    def profit(n):
        return int(round(price * n * (1 - STRIPE))) - fee
    rows.append(dict(code=code, name=c['name'], group=c.get('group', ''),
                     price=price, days=days, cap=cap, fee=fee,
                     fmt=short(f), raw=f,
                     p1=profit(1), pcap=profit(cap),
                     s1=int(round(price * 1 * STRIPE)),
                     scap=int(round(price * cap * STRIPE))))

W = io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         'course_pl.md'), 'w', encoding='utf-8')


def out(s=''):
    print(s)
    W.write(s + '\n')


out('| コード | 講座 | 料金(税込) | 日数 | 定員 | 開催場所 | 講師料(定額) '
    '| 決済手数料(1名) | **1名の利益** | 定員時の利益 |')
out('|---|---|---:|---:|---:|---|---:|---:|---:|---:|')
for r in rows:
    out('| {code} | {name} | ¥{price:,} | {days} | {cap} | {fmt} '
        '| ¥{fee:,} | ¥{s1:,} | **¥{p1:,}** | ¥{pcap:,} |'.format(**r))

out()
out('■ 形式ごとの内訳')
agg = {}
for r in rows:
    agg.setdefault(r['fmt'], []).append(r['code'])
for k, v in sorted(agg.items(), key=lambda x: -len(x[1])):
    out(f'  {k}: {len(v)}講座  {" ".join(v)}')

out()
out('■ 会場費が出た場合に、1名開催が赤字になる分岐点（1日あたり）')
for r in sorted(rows, key=lambda r: r['p1'] / max(1, r['days'])):
    if r['fmt'] != 'オンラインのみ':
        out('  {code:6} {fmt:14} 1日あたり ¥{v:,} を超えると1名開催は赤字'
            .format(code=r['code'], fmt=r['fmt'],
                    v=int(r['p1'] / max(1, r['days']))))

out()
out('■ 合計（全26講座を1回ずつ、1名で開催した場合）')
out('  売上 ¥{:,} / 講師料 ¥{:,} / 決済手数料 ¥{:,} / 利益 ¥{:,}'.format(
    sum(r['price'] for r in rows), sum(r['fee'] for r in rows),
    sum(r['s1'] for r in rows), sum(r['p1'] for r in rows)))
out('■ 合計（全26講座を1回ずつ、定員まで埋めた場合）')
out('  売上 ¥{:,} / 講師料 ¥{:,} / 決済手数料 ¥{:,} / 利益 ¥{:,}'.format(
    sum(r['price'] * r['cap'] for r in rows), sum(r['fee'] for r in rows),
    sum(r['scap'] for r in rows), sum(r['pcap'] for r in rows)))
W.close()
