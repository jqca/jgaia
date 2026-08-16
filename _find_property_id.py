"""GA4プロパティIDを特定するスクリプト。

前提: Google Cloud Console で GA4 Admin API を有効化済み
      GA4 プロパティにサービスアカウントを閲覧者として追加済み

実行: python _find_property_id.py
"""
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

SA_PATH = r'F:\company\development\line-notify\service_account.json'
sa_info = json.load(open(SA_PATH))

creds = service_account.Credentials.from_service_account_info(
    sa_info,
    scopes=['https://www.googleapis.com/auth/analytics.readonly']
)

service = build('analyticsadmin', 'v1beta', credentials=creds)

result = service.accounts().list().execute()
for acc in result.get('accounts', []):
    print("Account:", acc['name'], "-", acc.get('displayName', ''))
    props = service.properties().list(filter="parent:" + acc['name']).execute()
    for p in props.get('properties', []):
        pid = p['name'].split('/')[-1]
        print("  Property:", pid, "-", p.get('displayName', ''))
        # Data Streams を取得して測定IDを確認
        try:
            streams = service.properties().dataStreams().list(
                parent=p['name']
            ).execute()
            for s in streams.get('dataStreams', []):
                mid = s.get('webStreamData', {}).get('measurementId', '')
                print("    Stream:", s.get('displayName', ''), "- MeasurementID:", mid)
                if mid == 'G-H7XQ25E8YN':
                    print("    >>> JGAIA FOUND! Property ID =", pid)
        except Exception as e:
            print("    Stream error:", e)

print("\nDone. ga4_kpi.py の GA4_PROPERTY_ID に上記IDを設定してください。")
