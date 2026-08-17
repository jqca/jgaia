# -*- coding: utf-8 -*-
r"""全講座を「受講者が予約できる」状態にして、目視確認できるようにする道具。

社長ご指示 2026-08-17「GAしか講師の講義可能な日付登録がないせいか、他の講座に
ついて受講生が予約登録できるか目視確認できません。全講座で予約登録可能か目視
確認できるようにして」。

やること: 動作確認用の講師（ダミー）に**全講座**を担当として登録し、運営が決めた
開催日（毎週水＋第2・第4土）のうち LEAD_DAYS より先の日を一括で登録する。
これで全講座の紹介ページに「申し込む」が出て、予約ページで日が選べるようになる。

⛔ 本物の講師を勝手に作らないこと。触るのは下の DEMO_EMAIL の1行だけ。
⛔ 確認が済んだら --remove で見送りに戻すこと。戻すと全講座が「調整中」に戻る。
   （ダミーのまま放置すると、本物の受講者が架空の講師の枠に申し込める）
⛔ 開催日の決まりをここに書き写して"正"にしないこと。ここで計算するのは候補で、
   受け付けるかどうかを決めるのは本番の set_day_courses（拒否された日は表に出す）。

使い方（PowerShell・F:\company\development\jgaia から）:
    C:\Python314\python.exe tools\demo_availability.py --check
    C:\Python314\python.exe tools\demo_availability.py --apply --token <合言葉>
    C:\Python314\python.exe tools\demo_availability.py --remove --token <合言葉>
合言葉は Railway の INQUIRY_ADMIN_TOKEN（環境変数 JGAIA_ADMIN_TOKEN でも可）。
"""
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta

BASE = 'https://www.jgaia.org'
# 動作確認用の講師。⛔ 本物の講師のアドレスをここに書かないこと
DEMO_EMAIL = 'takano.hidetaka+dummy-instructor@gmail.com'
UA = 'jgaia-demo-availability/1.0'


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """302 を「保存できた」の合図として受け取るため、追いかけない。"""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_OPENER = urllib.request.build_opener(_NoRedirect)


def _req(url, data=None, token=None, json_body=None):
    """(ステータス, 本文) を返す。例外にしない（302も本文なしの正常系）。"""
    body, headers = None, {'User-Agent': UA}
    if json_body is not None:
        body = json.dumps(json_body).encode()
        headers['Content-Type'] = 'application/json'
    elif data is not None:
        body = urllib.parse.urlencode(data, doseq=True).encode()
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
    if token:
        headers['X-Admin-Token'] = token
    req = urllib.request.Request(url, data=body, headers=headers,
                                 method='POST' if body is not None else 'GET')
    try:
        with _OPENER.open(req, timeout=60) as r:
            return r.status, r.read().decode('utf-8', 'replace')
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8', 'replace')


def _instructors(token):
    st, body = _req(BASE + '/api/instructors', token=token)
    if st != 200:
        raise SystemExit('講師の一覧が読めません（%s）: %s' % (st, body[:200]))
    return json.loads(body)


def _candidate_days(span_days=135, lead=15):
    """開催日の候補（毎週水＋第2・第4土）。

    ⛔ ここを"正"にしないこと。実際に受け付けるかは本番が決める。
    lead は LEAD_DAYS(14) より1日多く取る（今日の申込を締切ぎりぎりにしない）。
    span は3か月（予約画面が出す範囲）＋全5回ぶんの余白。
    """
    out, d0 = [], date.today()
    for i in range(lead, span_days):
        d = d0 + timedelta(days=i)
        nth = (d.day - 1) // 7 + 1
        if d.weekday() == 2 or (d.weekday() == 5 and nth in (2, 4)):
            out.append(d.isoformat())
    return out


def check():
    """受講者に見えている画面をそのまま読む（予約できる日が何日あるか）。"""
    st, body = _req(BASE + '/api/instructors',
                    token=os.environ.get('JGAIA_ADMIN_TOKEN'))
    codes = []
    if st == 200:
        codes = [c['code'] for c in json.loads(body).get('courses', [])]
    if not codes:
        raise SystemExit('講座の一覧が取れません。--token をご指定ください')

    # ⛔ 紹介ページの対応表をここに書き写さないこと（アプリ側の1か所を読む）
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from booking_check import INTRO

    print('%-7s %-7s %s' % ('講座', '予約可', '紹介ページに「申し込む」が出るか'))
    ng, no_link = [], []
    intro_cache = {}
    for code in codes:
        _s, page = _req('%s/book/%s' % (BASE, code))
        days = len(re.findall(r'data-day="', page))
        path = INTRO.get(code)
        if path and path not in intro_cache:
            intro_cache[path] = _req(BASE + path)[1]
        linked = bool(path) and ('/book/%s' % code) in intro_cache.get(path, '')
        print('%-7s %5d日  %s  %s' % (code, days, '出ています' if linked
                                      else '出ていません', path or '(未設定)'))
        if not days:
            ng.append(code)
        if not linked:
            no_link.append(code)
    print('\n予約できる講座 %d / %d' % (len(codes) - len(ng), len(codes)))
    if ng:
        print('予約できない: %s' % ', '.join(ng))
    if no_link:
        print('紹介ページに導線が出ていない: %s' % ', '.join(no_link))
    return ng


def apply_demo(token, dry=True):
    data = _instructors(token)
    codes = [c['code'] for c in data['courses']]
    row = next((r for r in data['rows']
                if (r.get('連絡先') or '').lower() == DEMO_EMAIL), None)
    if not row:
        raise SystemExit(
            '動作確認用の講師（%s）が見つかりません。\n'
            '%s/instructor/register から登録してください。' % (DEMO_EMAIL, BASE))
    tok = row['鍵']
    days = _candidate_days()
    print('対象: %s（%s）' % (row.get('氏名'), DEMO_EMAIL))
    print('担当講座: %d件 → %d件' % (len(row.get('対応コース') or []), len(codes)))
    print('登録する日: %d日（%s 〜 %s）' % (len(days), days[0], days[-1]))
    if dry:
        print('\n※ 下見です。実行するには --apply を付けてください')
        return

    st, body = _req('%s/instructor/schedule/%s/courses' % (BASE, tok),
                    data={'courses': codes})
    if st not in (200, 302):
        raise SystemExit('担当講座を更新できません（%s）' % st)
    st, body = _req(BASE + '/api/instructor/decide', token=token,
                    json_body={'id': row['id'], 'state': '承認'})
    if st != 200:
        raise SystemExit('承認できません（%s）: %s' % (st, body[:200]))
    print('担当講座を%d件にして承認しました' % len(codes))

    ok = 0
    for iso in days:
        st, body = _req('%s/instructor/schedule/%s/day/%s' % (BASE, tok, iso),
                        data={'courses': codes, 'confirm': '1'})
        if st == 302:
            ok += 1
        else:
            # ⛔ 断られた日を黙って飛ばさないこと（予約が入っている日など）
            m = re.search(r'class="err[^"]*">([^<]{5,120})', body)
            print('  %s を登録できませんでした: %s'
                  % (iso, (m.group(1).strip() if m else 'HTTP %s' % st)))
    print('開催日を %d/%d 日ぶん登録しました' % (ok, len(days)))


def remove_demo(token, dry=True):
    data = _instructors(token)
    row = next((r for r in data['rows']
                if (r.get('連絡先') or '').lower() == DEMO_EMAIL), None)
    if not row:
        print('動作確認用の講師は登録されていません')
        return
    print('見送りに戻す: %s（%s）' % (row.get('氏名'), DEMO_EMAIL))
    if dry:
        print('※ 下見です。実行するには --remove --apply を付けてください')
        return
    st, body = _req(BASE + '/api/instructor/decide', token=token,
                    json_body={'id': row['id'], 'state': '見送り'})
    if st != 200:
        raise SystemExit('戻せません（%s）: %s' % (st, body[:200]))
    print('戻しました（全講座が「調整中」に戻ります）')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true', help='いまの状態を数える')
    ap.add_argument('--apply', action='store_true', help='実際に書き込む')
    ap.add_argument('--remove', action='store_true', help='ダミーを見送りに戻す')
    ap.add_argument('--token', default=os.environ.get('JGAIA_ADMIN_TOKEN'))
    a = ap.parse_args()
    if a.token:
        os.environ['JGAIA_ADMIN_TOKEN'] = a.token

    if a.remove:
        remove_demo(a.token, dry=not a.apply)
    elif a.apply:
        apply_demo(a.token, dry=False)
    elif a.check or not a.token:
        check()
    else:
        apply_demo(a.token, dry=True)
    if a.apply:
        print()
        check()


if __name__ == '__main__':
    sys.exit(main())
