# -*- coding: utf-8 -*-
"""申込・問い合わせを「消えない場所」に必ず残すための最小の受け皿。

なぜ必要か（2026-07-30に判明）:
    問い合わせAPIは、メール送信に失敗しても・メールの設定が無くても、
    利用者には「送信完了しました。確認メールをお送りしました」と返していた。
    申込内容はどこにも保存していなかったため、メールが出なければ
    その申込は痕跡ごと消える。何件失ったのかを数えることすらできない。

方針:
    1. まずファイルに追記する（メールより先。ここが失敗したらエラーを返す）
    2. そのあとメールを送る
    3. メールが送れなくても、受付自体は成立している（保存済み）と扱う
       ただし「確認メールを送った」とは言わない

保存先は環境変数 INQUIRY_LOG_DIR（既定 ./data）。Railwayの再デプロイで
消える可能性があるため、これは最後の砦であって台帳の代わりではない。
恒久的にはDB保存へ寄せる。
"""
import json
import os
import threading
from datetime import datetime, timezone, timedelta

_LOCK = threading.Lock()
JST = timezone(timedelta(hours=9))


def _log_path():
    d = os.environ.get('INQUIRY_LOG_DIR', os.path.join(os.path.dirname(
        os.path.abspath(__file__)), 'data'))
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, 'inquiries.jsonl')


def save_inquiry(kind, payload):
    """問い合わせを1件追記する。失敗したら例外を上げる（握り潰さない）。"""
    record = {
        'received_at': datetime.now(JST).strftime('%Y-%m-%d %H:%M:%S'),
        'kind': kind,
        **{k: v for k, v in payload.items()},
    }
    line = json.dumps(record, ensure_ascii=False)
    with _LOCK:
        with open(_log_path(), 'a', encoding='utf-8') as f:
            f.write(line + '\n')
            f.flush()
            os.fsync(f.fileno())
    return record


def count_inquiries():
    """保存済み件数。/healthz から見えるようにして、0のまま増えない異常に気づく。"""
    path = _log_path()
    if not os.path.exists(path):
        return 0
    with open(path, encoding='utf-8') as f:
        return sum(1 for line in f if line.strip())


def _mailed_path():
    return os.path.join(os.path.dirname(_log_path()), 'mailed.jsonl')


def inquiry_key(record):
    """1件を見分ける鍵。受付時刻＋メール（原本側にIDが無いため）。"""
    return f"{record.get('received_at', '')}|{record.get('email', '')}"


def mark_mailed(key):
    """確認メールを送れた申込に印を付ける。

    サイト（Railway）から送れたぶんを、予備の経路（SoloOS）が
    二重に送らないようにするための印。追記だけで、消さない。
    """
    path = _mailed_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with _LOCK:
        with open(path, 'a', encoding='utf-8') as f:
            f.write(json.dumps({'key': key}, ensure_ascii=False) + '\n')
            f.flush()
            os.fsync(f.fileno())


def _mailed_keys():
    path = _mailed_path()
    if not os.path.exists(path):
        return set()
    keys = set()
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                keys.add(json.loads(line).get('key'))
            except Exception:
                continue
    return keys


def read_inquiries(limit=200):
    """保存済みの申込を新しい順に返す。

    メールが送れないときの唯一の受け取り口になる。メール送信は外部サービスの
    日次上限で落ちることがあり（2026-08-04に実際に発生）、そのとき保存だけが
    残る。取り出せなければ保存している意味がない。
    """
    path = _log_path()
    if not os.path.exists(path):
        return []
    mailed = _mailed_keys()
    rows = []
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                # 予備の経路が二重に送らないよう、送信済みかどうかを添える
                rec['mail_sent'] = inquiry_key(rec) in mailed
                rows.append(rec)
            except Exception:
                # 壊れた行があっても残りは読めるようにする（黙って全件失わない）
                rows.append({'_unparsed': line})
    rows.reverse()
    return rows[:limit]
