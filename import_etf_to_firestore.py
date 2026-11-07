"""Import existing ETF CSV data into the Firebase Firestore `data` collection."""
import csv
import os
from datetime import date
from pathlib import Path

import firebase_admin
from dotenv import load_dotenv
from firebase_admin import credentials, firestore

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / '.env')
key_file = os.getenv('FIREBASE_SERVICE_ACCOUNT_PATH')
if not key_file or not Path(key_file).is_file():
    raise SystemExit('Firebase credentials file not found; check FIREBASE_SERVICE_ACCOUNT_PATH in .env')

if not firebase_admin._apps:
    firebase_admin.initialize_app(credentials.Certificate(key_file))

db = firestore.client()
records = []
with (ROOT / 'data' / 'etf_prices.csv').open(encoding='utf-8-sig', newline='') as f:
    for raw in csv.DictReader(f):
        records.append({
            'date': date.fromisoformat(raw['date'].strip()).isoformat(),
            'value': float(raw['value']),
            'memo': raw.get('memo', '') or '',
        })

if len(records) < 100:
    raise SystemExit(f'Expected at least 100 records, found {len(records)}.')
if len({r['date'] for r in records}) != len(records):
    raise SystemExit('Duplicate dates found. Import cancelled.')

for start in range(0, len(records), 400):
    batch = db.batch()
    for record in records[start:start + 400]:
        batch.set(db.collection('data').document(record['date']), record)
    batch.commit()
    print(f'Uploaded {min(start+400,len(records))}/{len(records)} records')

print(f'Firestore import successful: {len(records)} records')
