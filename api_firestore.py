"""ETF AI Agent: Firestore-backed FastAPI service.

Run from the project folder:
    python -m uvicorn api_firestore:app --reload

Requires .env with FIREBASE_SERVICE_ACCOUNT_PATH and OPENAI_API_KEY.
"""
from __future__ import annotations

import os
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import firebase_admin
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from firebase_admin import credentials, firestore
from openai import OpenAI
from pydantic import BaseModel, Field, field_validator

load_dotenv(Path(__file__).resolve().parent / '.env')

app = FastAPI(title='ETF Analysis AI Agent', version='0.2.0')
_origins = [v.strip() for v in os.getenv('ALLOWED_ORIGINS', 'http://localhost:5500,http://127.0.0.1:5500').split(',') if v.strip()]
app.add_middleware(
    CORSMiddleware, allow_origins=_origins, allow_credentials=True,
    allow_methods=['GET', 'POST', 'PUT', 'DELETE'], allow_headers=['*'],
)


def get_db():
    if not firebase_admin._apps:
        key_path = os.getenv('FIREBASE_SERVICE_ACCOUNT_PATH')
        if key_path and Path(key_path).is_file():
            firebase_admin.initialize_app(credentials.Certificate(key_path))
        elif os.getenv('FIREBASE_SERVICE_ACCOUNT_JSON'):
            import json
            firebase_admin.initialize_app(credentials.Certificate(json.loads(os.environ['FIREBASE_SERVICE_ACCOUNT_JSON'])))
        else:
            # On Render, GOOGLE_APPLICATION_CREDENTIALS may point to a secret file.
            firebase_admin.initialize_app()
    return firestore.client()


class ETFRecord(BaseModel):
    date: date
    value: float = Field(gt=0)
    memo: str = Field(default='', max_length=500)


class ETFUpdate(BaseModel):
    date: date
    value: float = Field(gt=0)
    memo: str = Field(default='', max_length=500)


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    conversation_id: str | None = None


class ConversationRequest(BaseModel):
    title: str = Field(default='?????, min_length=1, max_length=100)


def _all_records() -> list[dict[str, Any]]:
    data = []
    for doc in get_db().collection('data').stream():
        row = doc.to_dict() or {}
        row['id'] = doc.id
        data.append(row)
    data.sort(key=lambda x: str(x.get('date', '')))
    return data


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {'period': {'start': None, 'end': None}, 'count': 0, 'metrics': {'average': None, 'max': None, 'min': None}, 'trend': '?곗씠???놁쓬'}
    vals = [float(r['value']) for r in rows]
    n = len(vals)
    window = min(20, n // 2)
    if window:
        latest = sum(vals[-window:]) / window
        earlier = sum(vals[-window * 2:-window]) / window
        trend = '利앷?' if latest > earlier else '媛먯냼' if latest < earlier else '蹂???놁쓬'
    else:
        trend = '鍮꾧탳???곗씠??遺議?
    return {
        'etf': 'KODEX 200',
        'period': {'start': str(rows[0]['date']), 'end': str(rows[-1]['date'])},
        'count': n,
        'metrics': {'average': round(sum(vals)/n, 2), 'max': max(vals), 'min': min(vals),
                    'first': vals[0], 'latest': vals[-1]},
        'trend': trend,
    }


@app.get('/')
def home():
    return {'message': 'ETF Analysis AI Agent API is running', 'docs': '/docs'}


@app.get('/api/data')
def get_data():
    return _all_records()


@app.get('/api/data/summary')
def get_data_summary():
    return _summary(_all_records())


@app.post('/api/data', status_code=201)
def add_data(record: ETFRecord):
    ref = get_db().collection('data').document(record.date.isoformat())
    if ref.get().exists:
        raise HTTPException(409, '?대떦 ?좎쭨???곗씠?곌? ?대? ?덉뒿?덈떎.')
    data = record.model_dump(mode='json')
    ref.set(data)
    return {'id': ref.id, **data}


@app.put('/api/data/{id}')
def update_data(id: str, record: ETFUpdate):
    ref = get_db().collection('data').document(id)
    if not ref.get().exists:
        raise HTTPException(404, '?대떦 ?곗씠?곌? ?놁뒿?덈떎.')
    new_id = record.date.isoformat()
    data = record.model_dump(mode='json')
    if id != new_id:
        new_ref = get_db().collection('data').document(new_id)
        if new_ref.get().exists:
            raise HTTPException(409, '蹂寃쏀븷 ?좎쭨???곗씠?곌? ?대? ?덉뒿?덈떎.')
        batch = get_db().batch()
        batch.set(new_ref, data)
        batch.delete(ref)
        batch.commit()
    else:
        ref.set(data)
    return {'id': new_id, **data}


@app.delete('/api/data/{id}')
def delete_data(id: str):
    ref = get_db().collection('data').document(id)
    if not ref.get().exists:
        raise HTTPException(404, '?대떦 ?곗씠?곌? ?놁뒿?덈떎.')
    ref.delete()
    return {'deleted': id}


@app.post('/api/conversations', status_code=201)
def create_conversation(req: ConversationRequest):
    now = datetime.now(timezone.utc).isoformat()
    ref = get_db().collection('conversations').document()
    data = {'title': req.title, 'created_at': now, 'updated_at': now, 'messages': []}
    ref.set(data)
    return {'id': ref.id, **data}


@app.get('/api/conversations')
def list_conversations():
    items = [{'id': d.id, **(d.to_dict() or {})} for d in get_db().collection('conversations').stream()]
    items.sort(key=lambda item: item.get('updated_at', ''), reverse=True)
    return items


@app.get('/api/conversations/{id}')
def get_conversation(id: str):
    doc = get_db().collection('conversations').document(id).get()
    if not doc.exists:
        raise HTTPException(404, '??붾? 李얠쓣 ???놁뒿?덈떎.')
    return {'id': doc.id, **doc.to_dict()}


@app.delete('/api/conversations/{id}')
def delete_conversation(id: str):
    ref = get_db().collection('conversations').document(id)
    if not ref.get().exists:
        raise HTTPException(404, '??붾? 李얠쓣 ???놁뒿?덈떎.')
    ref.delete()
    return {'deleted': id}


@app.post('/api/chat')
def chat(req: ChatRequest):
    summary = _summary(_all_records())
    if summary['count'] == 0:
        raise HTTPException(400, '癒쇱? ETF ?곗씠?곕? ?깅줉??二쇱꽭??')
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise HTTPException(503, 'OPENAI_API_KEY媛 ?ㅼ젙?섏? ?딆븯?듬땲??')
    db = get_db()
    ref = db.collection('conversations').document(req.conversation_id) if req.conversation_id else db.collection('conversations').document()
    snapshot = ref.get() if req.conversation_id else None
    if req.conversation_id and not snapshot.exists:
        raise HTTPException(404, '湲곗〈 ??붾? 李얠쓣 ???놁뒿?덈떎.')
    prev = (snapshot.to_dict() or {}).get('messages', []) if snapshot else []
    # Keep the API call small, without losing stored conversation history.
    recent = [m for m in prev[-8:] if m.get('role') in ('user', 'assistant')]
    system_message = (
        '?뱀떊? KODEX 200 ETF ?쒓퀎???곗씠?곕? ?ㅻ챸?섎뒗 AI?낅땲?? '
        '?꾨옒???쒓났???듦퀎留??뺤씤???ъ떎濡??ъ슜?섏꽭?? '
        '?붿빟???녿뒗 ?좎쭨蹂?媛寃? 嫄곕옒?? ?섏씡瑜? 誘몃옒 媛寃⑹쓣 留뚮뱾???댁? 留덉꽭?? '
        '異붽? ?곗씠?곌? ?꾩슂??吏덈Ц? ?뺤씤?????녿떎怨??듯븯?몄슂. '
        '?ъ옄 ?섏씡??蹂댁옣?섏? 留덉꽭??\n'
        f'?뺤씤???듦퀎: {summary}'
    )
    messages = [{'role': 'system', 'content': system_message}]
    messages.extend({'role': m['role'], 'content': m['content']} for m in recent)
    messages.append({'role': 'user', 'content': req.question})
    try:
        client = OpenAI(api_key=api_key, base_url=os.getenv('OPENAI_BASE_URL', 'https://copa.codyssey.kr/v1'))
        response = client.chat.completions.create(
            model=os.getenv('OPENAI_MODEL', 'gpt-5-mini'),
            messages=messages,
            max_completion_tokens=2000,
        )
        answer = response.choices[0].message.content or '?듬????앹꽦?섏? 紐삵뻽?듬땲??'
    except Exception as e:
        raise HTTPException(502, f'AI API ?몄텧 ?ㅽ뙣: {type(e).__name__}') from e
    now = datetime.now(timezone.utc).isoformat()
    full_messages = prev + [{'role': 'user', 'content': req.question}, {'role': 'assistant', 'content': answer}]
    original = snapshot.to_dict() if snapshot else {}
    ref.set({
        'title': original.get('title') or req.question[:60],
        'created_at': original.get('created_at') or now,
        'updated_at': now,
        'messages': full_messages,
    })
    return {'answer': answer, 'conversation_id': ref.id, 'summary': summary}

