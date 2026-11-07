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
    title: str = Field(default='새 대화', min_length=1, max_length=100)


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
        return {'period': {'start': None, 'end': None}, 'count': 0, 'metrics': {'average': None, 'max': None, 'min': None}, 'trend': '데이터 없음'}
    vals = [float(r['value']) for r in rows]
    n = len(vals)
    window = min(20, n // 2)
    if window:
        latest = sum(vals[-window:]) / window
        earlier = sum(vals[-window * 2:-window]) / window
        trend = '증가' if latest > earlier else '감소' if latest < earlier else '변화 없음'
    else:
        trend = '비교할 데이터 부족'
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
        raise HTTPException(409, '해당 날짜의 데이터가 이미 있습니다.')
    data = record.model_dump(mode='json')
    ref.set(data)
    return {'id': ref.id, **data}


@app.put('/api/data/{id}')
def update_data(id: str, record: ETFUpdate):
    ref = get_db().collection('data').document(id)
    if not ref.get().exists:
        raise HTTPException(404, '해당 데이터가 없습니다.')
    new_id = record.date.isoformat()
    data = record.model_dump(mode='json')
    if id != new_id:
        new_ref = get_db().collection('data').document(new_id)
        if new_ref.get().exists:
            raise HTTPException(409, '변경할 날짜의 데이터가 이미 있습니다.')
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
        raise HTTPException(404, '해당 데이터가 없습니다.')
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
        raise HTTPException(404, '대화를 찾을 수 없습니다.')
    return {'id': doc.id, **doc.to_dict()}


@app.delete('/api/conversations/{id}')
def delete_conversation(id: str):
    ref = get_db().collection('conversations').document(id)
    if not ref.get().exists:
        raise HTTPException(404, '대화를 찾을 수 없습니다.')
    ref.delete()
    return {'deleted': id}


@app.post('/api/chat')
def chat(req: ChatRequest):
    summary = _summary(_all_records())
    if summary['count'] == 0:
        raise HTTPException(400, '먼저 ETF 데이터를 등록해 주세요.')
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise HTTPException(503, 'OPENAI_API_KEY가 설정되지 않았습니다.')
    db = get_db()
    ref = db.collection('conversations').document(req.conversation_id) if req.conversation_id else db.collection('conversations').document()
    snapshot = ref.get() if req.conversation_id else None
    if req.conversation_id and not snapshot.exists:
        raise HTTPException(404, '기존 대화를 찾을 수 없습니다.')
    prev = (snapshot.to_dict() or {}).get('messages', []) if snapshot else []
    # Keep the API call small, without losing stored conversation history.
    recent = [m for m in prev[-8:] if m.get('role') in ('user', 'assistant')]
    system_message = (
        '당신은 KODEX 200 ETF 시계열 데이터를 설명하는 AI입니다. '
        '아래에 제공한 통계만 확인된 사실로 사용하세요. '
        '요약에 없는 날짜별 가격, 거래량, 수익률, 미래 가격을 만들어 내지 마세요. '
        '추가 데이터가 필요한 질문은 확인할 수 없다고 답하세요. '
        '투자 수익을 보장하지 마세요.\n'
        f'확인된 통계: {summary}'
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
        answer = response.choices[0].message.content or '답변을 생성하지 못했습니다.'
    except Exception as e:
        raise HTTPException(502, f'AI API 호출 실패: {type(e).__name__}') from e
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
