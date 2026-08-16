"""JGAIA サイト GA4 KPI自動取得スクリプト

毎週月曜に実行し、以下のKPIを取得:
- 週間PV / ユーザー数 / セッション数
- ページ別PVランキング
- 流入元別セッション数
- 問い合わせフォーム送信数（イベント）

取得結果は marketing.md の JGAIA セクションに追記する。

前提:
1. Google Cloud Console で GA4 Data API を有効化済み
2. GA4 プロパティにサービスアカウントを閲覧者として追加済み
3. サービスアカウントJSONが line-notify/service_account.json にある
"""
import json
import os
import sys
from datetime import datetime, timedelta

SA_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    '..', 'line-notify', 'service_account.json'
)
# GA4プロパティID（APIが有効化された後、_find_property_id.pyで特定して設定）
GA4_PROPERTY_ID = os.environ.get('JGAIA_GA4_PROPERTY_ID', '')

MARKETING_MD = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    '..', '..', 'cockpit-kb', 'marketing.md'
)


def get_client():
    from google.oauth2 import service_account
    from google.analytics.data_v1beta import BetaAnalyticsDataClient

    sa_info = json.load(open(SA_PATH))
    creds = service_account.Credentials.from_service_account_info(
        sa_info,
        scopes=['https://www.googleapis.com/auth/analytics.readonly']
    )
    return BetaAnalyticsDataClient(credentials=creds)


def run_report(client, property_id, dimensions, metrics, start_date, end_date, limit=10):
    from google.analytics.data_v1beta.types import (
        RunReportRequest, DateRange, Dimension, Metric
    )
    request = RunReportRequest(
        property=f'properties/{property_id}',
        dimensions=[Dimension(name=d) for d in dimensions],
        metrics=[Metric(name=m) for m in metrics],
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
        limit=limit,
    )
    return client.run_report(request)


def fetch_weekly_kpi():
    if not GA4_PROPERTY_ID:
        print('ERROR: JGAIA_GA4_PROPERTY_ID が未設定です')
        print('_find_property_id.py を実行してプロパティIDを特定し、')
        print('このファイルの GA4_PROPERTY_ID を更新してください。')
        sys.exit(1)

    client = get_client()
    today = datetime.now()
    last_week_start = (today - timedelta(days=7)).strftime('%Y-%m-%d')
    last_week_end = (today - timedelta(days=1)).strftime('%Y-%m-%d')
    prev_week_start = (today - timedelta(days=14)).strftime('%Y-%m-%d')
    prev_week_end = (today - timedelta(days=8)).strftime('%Y-%m-%d')

    results = {}

    # 1. 全体サマリー（今週）
    summary = run_report(
        client, GA4_PROPERTY_ID,
        dimensions=[],
        metrics=['screenPageViews', 'totalUsers', 'sessions', 'averageSessionDuration'],
        start_date=last_week_start, end_date=last_week_end
    )
    if summary.rows:
        row = summary.rows[0]
        results['pv'] = int(row.metric_values[0].value)
        results['users'] = int(row.metric_values[1].value)
        results['sessions'] = int(row.metric_values[2].value)
        results['avg_duration'] = float(row.metric_values[3].value)

    # 1b. 全体サマリー（前週 - 比較用）
    prev_summary = run_report(
        client, GA4_PROPERTY_ID,
        dimensions=[],
        metrics=['screenPageViews', 'totalUsers', 'sessions'],
        start_date=prev_week_start, end_date=prev_week_end
    )
    if prev_summary.rows:
        row = prev_summary.rows[0]
        results['prev_pv'] = int(row.metric_values[0].value)
        results['prev_users'] = int(row.metric_values[1].value)
        results['prev_sessions'] = int(row.metric_values[2].value)

    # 2. ページ別PV TOP10
    pages = run_report(
        client, GA4_PROPERTY_ID,
        dimensions=['pagePath'],
        metrics=['screenPageViews'],
        start_date=last_week_start, end_date=last_week_end,
        limit=10
    )
    results['top_pages'] = []
    for row in pages.rows:
        results['top_pages'].append({
            'path': row.dimension_values[0].value,
            'pv': int(row.metric_values[0].value)
        })

    # 3. 流入元別
    sources = run_report(
        client, GA4_PROPERTY_ID,
        dimensions=['sessionSource'],
        metrics=['sessions'],
        start_date=last_week_start, end_date=last_week_end,
        limit=10
    )
    results['top_sources'] = []
    for row in sources.rows:
        results['top_sources'].append({
            'source': row.dimension_values[0].value,
            'sessions': int(row.metric_values[0].value)
        })

    # 4. デバイス別
    devices = run_report(
        client, GA4_PROPERTY_ID,
        dimensions=['deviceCategory'],
        metrics=['sessions'],
        start_date=last_week_start, end_date=last_week_end
    )
    results['devices'] = []
    for row in devices.rows:
        results['devices'].append({
            'device': row.dimension_values[0].value,
            'sessions': int(row.metric_values[0].value)
        })

    return results, last_week_start, last_week_end


def format_change(current, previous):
    if previous == 0:
        return 'N/A'
    pct = ((current - previous) / previous) * 100
    sign = '+' if pct >= 0 else ''
    return f'{sign}{pct:.0f}%'


def format_report(results, start_date, end_date):
    lines = []
    lines.append(f'\n### JGAIA KPI ({start_date} 〜 {end_date})')

    pv = results.get('pv', 0)
    users = results.get('users', 0)
    sessions = results.get('sessions', 0)
    avg_dur = results.get('avg_duration', 0)
    prev_pv = results.get('prev_pv', 0)
    prev_users = results.get('prev_users', 0)
    prev_sessions = results.get('prev_sessions', 0)

    lines.append(f'| 指標 | 今週 | 前週比 |')
    lines.append(f'|------|------|--------|')
    lines.append(f'| PV | {pv:,} | {format_change(pv, prev_pv)} |')
    lines.append(f'| ユーザー | {users:,} | {format_change(users, prev_users)} |')
    lines.append(f'| セッション | {sessions:,} | {format_change(sessions, prev_sessions)} |')
    lines.append(f'| 平均滞在(秒) | {avg_dur:.0f} | - |')

    if results.get('top_pages'):
        lines.append('\n**ページ別PV TOP10**')
        for p in results['top_pages']:
            lines.append(f'- `{p["path"]}` — {p["pv"]:,} PV')

    if results.get('top_sources'):
        lines.append('\n**流入元TOP10**')
        for s in results['top_sources']:
            lines.append(f'- {s["source"]} — {s["sessions"]:,} sessions')

    if results.get('devices'):
        lines.append('\n**デバイス別**')
        for d in results['devices']:
            lines.append(f'- {d["device"]} — {d["sessions"]:,} sessions')

    return '\n'.join(lines)


def main():
    print('JGAIA GA4 KPI 取得中...')
    results, start_date, end_date = fetch_weekly_kpi()
    report = format_report(results, start_date, end_date)
    print(report)

    # marketing.md に追記（存在する場合）
    if os.path.exists(MARKETING_MD):
        with open(MARKETING_MD, 'a', encoding='utf-8') as f:
            f.write('\n' + report + '\n')
        print(f'\n→ {MARKETING_MD} に追記しました')
    else:
        print(f'\n→ {MARKETING_MD} が見つかりません。手動でコピーしてください。')


if __name__ == '__main__':
    main()
