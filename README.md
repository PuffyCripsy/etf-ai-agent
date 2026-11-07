# ETF AI Agent

KODEX 200 ETF 시계열 데이터를 분석하고, 데이터에 근거한 AI 채팅을 제공하는 웹 서비스 개발 프로젝트입니다.

> **배포 완료** — 아래의 구현 현황은 실제 배포된 서비스 기준이며, 기능 시연 스크린샷은 배포 사이트에서 캡처했습니다.

## 프로젝트 목표

- ETF 시계열 데이터 **100개 이상** 저장·조회 및 통계 요약
- 날짜(`date`), 값(`value`), 메모(`memo`)를 이용한 **CRUD**
- 실제 데이터 요약을 GPT 시스템 프롬프트에 주입하는 **AI 채팅**
- **Firestore** 기반 대화 자동 저장·목록 조회·불러오기·삭제
- **FastAPI → Render**, **HTML/CSS/Vanilla JS → Vercel** 배포

## 기술 스택

| 구분 | 기술 |
| --- | --- |
| 언어 | Python 3.10+, JavaScript |
| 백엔드 | FastAPI, Uvicorn, Pydantic |
| 프론트엔드 | HTML, CSS, Vanilla JavaScript |
| 데이터베이스 | Firebase Firestore |
| AI | OpenAI 호환 GPT API (`openai` SDK) |
| 환경 변수 | `python-dotenv` |
| 배포 | Render (백엔드), Vercel (프론트엔드) |

## 구현 현황

| 기능 | 상태 | 비고 |
| --- | --- | --- |
| KODEX 200 데이터 수집 | ✅ 완료 | 432개 관측값 확보 및 Firestore 적재 완료 |
| 기본 통계 분석 | ✅ 완료 | 기간·평균·최대·최소·최근 추세 요약 (`/api/data/summary`) |
| 기초 예측·백테스트 | ✅ 완료 | 필수 과제 범위 밖의 기존 기능 (로컬 분석 코드 및 차트 보존) |
| FastAPI 서버와 Swagger `/docs` | ✅ 완료 | 과제 규격 API 구현 및 Render 배포 (`/docs` 확인 가능) |
| 시계열 데이터 CRUD | ✅ 완료 | Firestore 기반 등록·조회·수정·삭제 및 웹 UI 연동 |
| GPT API 채팅 | ✅ 완료 | 통계 요약 프롬프트 주입, 로딩 스피너 및 대화 자동 저장 |
| Firestore 데이터/대화 관리 | ✅ 완료 | 대화 목록 조회 및 이전 대화 불러오기 구현 |
| 순수 JS 프론트엔드 | ✅ 완료 | Vanilla JS 기반 CRUD·채팅·통계 화면 구현 (Vercel 배포) |
| Render/Vercel 배포 | ✅ 완료 | 백엔드(Render) 및 프론트엔드(Vercel) 연동 배포 완료 |

## 필수 API 명세

### 시계열 데이터

| Method | Endpoint | 설명 |
| --- | --- | --- |
| `POST` | `/api/data` | 데이터 등록 |
| `GET` | `/api/data` | 데이터 목록 조회 |
| `PUT` | `/api/data/{id}` | 데이터 수정 |
| `DELETE` | `/api/data/{id}` | 데이터 삭제 |
| `GET` | `/api/data/summary` | 기간·건수·평균·최댓값·최솟값·추세 요약 |

### 대화 및 채팅

| Method | Endpoint | 설명 |
| --- | --- | --- |
| `POST` | `/api/conversations` | 대화 생성 |
| `GET` | `/api/conversations` | 대화 목록 조회 |
| `GET` | `/api/conversations/{id}` | 대화 상세 조회(또는 목록에 메시지 포함) |
| `DELETE` | `/api/conversations/{id}` | 대화 삭제 |
| `POST` | `/api/chat` | 시계열 통계 기반 AI 답변 및 대화 자동 저장 |

## 데이터 형식

예시:

```json
{
  "date": "2026-10-01",
  "value": 100000,
  "memo": "KODEX 200 종가"
}
```

실제 시계열 데이터 100건 이상을 이용합니다. AI 답변에는 서버에서 계산한 통계를 넣고, 데이터에 없는 숫자를 추정 사실처럼 제시하지 않도록 구성합니다.

## 로컬 실행 안내

> 실제 파일 구조와 진입점을 확인한 뒤 명령을 업데이트할 예정입니다. 현재 설명은 기존에 사용하던 루트의 `api.py`를 기준으로 합니다.

Windows PowerShell에서 프로젝트 폴더로 이동한 뒤:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install fastapi uvicorn firebase-admin openai python-dotenv
uvicorn api:app --reload
```

Swagger UI: <http://127.0.0.1:8000/docs>

## 환경 변수

루트 폴더에 `.env` 파일을 사용합니다. 실제 인증 정보는 절대 GitHub에 업로드하지 않습니다.

```dotenv
OPENAI_API_KEY=your_api_key
# OpenAI 호환 API 제공자를 사용하는 경우 별도 base URL 설정
OPENAI_BASE_URL=your_provider_base_url
FIREBASE_SERVICE_ACCOUNT_JSON=your_service_account_json
ALLOWED_ORIGINS=http://localhost:3000
API_BASE_URL=http://127.0.0.1:8000
```

- `.env`, 서비스 계정 JSON 파일, `.venv/` 등은 `.gitignore`로 제외합니다.
- API 제공자에 따라 `OPENAI_BASE_URL` 및 모델 이름 설정이 달라질 수 있습니다.
- 배포 환경에서는 Render/Vercel의 환경 변수 설정을 사용합니다.

## 배포 주소

| 서비스 | URL |
| --- | --- |
| Frontend (Vercel) | <https://etf-ai-agent-etffrontend.vercel.app> |
| Backend (Render) | <https://etf-ai-agent-4lle.onrender.com> |
| Swagger UI | <https://etf-ai-agent-4lle.onrender.com/docs> |

## 기능 시연 스크린샷

배포된 사이트에서 캡처한 실제 동작 화면입니다.

### 1. 데이터 기반 AI 채팅

통계 요약을 시스템 프롬프트에 주입한 AI 답변 (데이터 432건 기준 평균·최고가·추세).

![AI 채팅](./docs/screenshots/01_ai_chat.png)

### 2. 시계열 데이터 CRUD

날짜 `2026-11-01`, 값 `95000`, 메모 `11월 관측 데이터` 등록 → 목록에 새 행 추가 및 통계 갱신(433건).

![데이터 CRUD](./docs/screenshots/02_data_crud.png)

### 3. 대화 관리

Firestore에 자동 저장된 대화 목록에서 이전 대화 불러오기.

![대화 관리](./docs/screenshots/03_conversations.png)

### 4. Swagger UI

Render에 배포된 백엔드의 `/docs` API 명세.

![Swagger UI](./docs/screenshots/04_swagger_docs.png)

## 필수 시연 및 제출 체크리스트

- [x] Firestore에 ETF 시계열 데이터 100개 이상 저장
- [x] 데이터 등록/조회/수정/삭제 시연
- [x] 통계 요약 API 및 화면 시연
- [x] AI 채팅의 로딩 표시 및 실제 데이터 요약 활용 확인
- [x] 대화 자동 저장 및 이전 대화 불러오기 시연
- [x] Render 백엔드 배포 및 `/docs` 접속 확인
- [x] Vercel 프론트엔드 배포 및 API 연동 확인
- [x] 배포 URL 및 로컬 실행 안내 기재
- [x] 채팅·CRUD·대화 기록 스크린샷 첨부

## 요구사항 원문 정리

자세한 과제 요구사항은 [`MISSION_REQUIREMENTS.md`](./MISSION_REQUIREMENTS.md)를 참고하세요.
