# -*- coding: utf-8 -*-
"""同じメールアドレスで重複している講師の行を1人1行に寄せる（既定は下見）。

なぜ要るか（2026-08-14 社長ご指摘）:
    register_instructor に重複チェックが1行も無く、同じアドレスでも毎回
    新しい行を append していた。本番の台帳は12件すべてが同一アドレスで、
    1人が12人として並んでいた。実装は直したが、既に入っている行は
    残るのでここで寄せる。

⛔ 既定は下見（--apply を付けるまで1バイトも書かない）。
⛔ 書く前に必ず控えを取ること（instructors.json.bak-<日時>）。
⛔ 残す行は「メール確認済み → 担当講座が多い → 新しい」の順で選ぶ。
   鍵は残す行のものが生きるので、消える鍵＝死ぬリンクを必ず表に出す。
⛔ 予約が入っている講師の行を消さないこと（予約は 担当講師id で紐づく）。

使い方（PowerShell・絶対パス1行）:
    C:\\Python314\\python.exe F:\\company\\development\\jgaia\\tools\\merge_duplicate_instructors.py
    C:\\Python314\\python.exe F:\\company\\development\\jgaia\\tools\\merge_duplicate_instructors.py --apply
"""
import argparse
import collections
import json
import os
import shutil
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding='utf-8')

import booking  # noqa: E402


def _rank(r, booked_ids):
    """残す1行を選ぶ順番。大きいほど残す。

    ⛔ 予約が入っている行を最優先で残すこと（消すと申込と講師が切れる）。
    """
    return (
        1 if str(r.get('id')) in booked_ids else 0,
        1 if r.get('メール確認済み') else 0,
        len(r.get('対応コース') or []),
        len(booking.registered_days(r) or {}),
        r.get('登録日時') or '',
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true', help='実際に書き換える')
    args = ap.parse_args()

    rows = booking.instructors()
    booked_ids = {str(b.get('担当講師id')) for b in booking.bookings()
                  if b.get('担当講師id')}

    groups = collections.OrderedDict()
    for r in rows:
        groups.setdefault(booking._norm_email(r.get('連絡先')), []).append(r)

    dups = {k: v for k, v in groups.items() if len(v) > 1}
    print(f'講師の行数: {len(rows)} / アドレスの種類: {len(groups)} / '
          f'重複しているアドレス: {len(dups)}')
    if not dups:
        print('重複はありません。書き換えるものはありません。')
        return 0

    keep_ids, drop = set(), []
    for mail, rs in dups.items():
        best = max(rs, key=lambda r: _rank(r, booked_ids))
        keep_ids.add(str(best.get('id')))
        print(f'\n■ {mail}（{len(rs)}行 → 1行）')
        for r in sorted(rs, key=lambda r: r.get('登録日時') or ''):
            keep = str(r.get('id')) == str(best.get('id'))
            days = len(booking.registered_days(r) or {})
            print(f'  {"残す" if keep else "消す"} {r.get("登録日時")} '
                  f'{r.get("状態")} メール確認={"済" if r.get("メール確認済み") else "未"} '
                  f'講座{len(r.get("対応コース") or [])}件 日程{days}日 '
                  f'予約={"あり" if str(r.get("id")) in booked_ids else "なし"} '
                  f'id={r.get("id")}')
            if not keep:
                drop.append(r)
        if len(rs) > 1:
            print(f'  ⚠ 消す{len(rs) - 1}行ぶんの専用リンク（鍵）は使えなくなります。'
                  f'該当の方へお送りしたメールのリンクが開かなくなるため、'
                  f'必要なら残る行の鍵を改めてご案内ください。')

    if not args.apply:
        print(f'\n下見です。{len(drop)}行を消すと {len(rows) - len(drop)}行になります。'
              f'\n実行するには --apply を付けてください。')
        return 0

    # ⛔ 控えを取ってから書く
    src = booking._path('instructors.json')
    bak = f'{src}.bak-{datetime.now().strftime("%Y%m%d-%H%M%S")}'
    shutil.copy2(src, bak)
    print(f'\n控え: {bak}')

    drop_ids = {str(r.get('id')) for r in drop}
    kept = [r for r in rows if str(r.get('id')) not in drop_ids]
    booking._save('instructors.json', kept)

    after = booking.instructors()
    print(f'書き換えました: {len(rows)}行 → {len(after)}行')
    left = [m for m, v in collections.Counter(
        booking._norm_email(r.get('連絡先')) for r in after).items() if v > 1]
    if left:
        print(f'⚠ まだ重複が残っています: {left}')
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
