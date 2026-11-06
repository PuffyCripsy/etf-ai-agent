
from fastapi import FastAPI
import pandas as pd

app = FastAPI(title="ETF Analysis AI Agent")

DATA_PATH = "data/etf_prices.csv"


@app.get("/")
def home():
    return {
        "message": "ETF 遺꾩꽍 AI Agent API媛 ?ㅽ뻾 以묒엯?덈떎."
    }


@app.get("/summary")
def get_summary():
    df = pd.read_csv(DATA_PATH)

    return {
        "etf": "KODEX 200",
        "data_count": int(len(df)),
        "start_date": str(df["date"].iloc[0]),
        "end_date": str(df["date"].iloc[-1]),
        "first_price": float(df["value"].iloc[0]),
        "latest_price": float(df["value"].iloc[-1]),
        "average_price": round(float(df["value"].mean()), 2),
        "maximum_price": float(df["value"].max()),
        "minimum_price": float(df["value"].min())
    }


@app.get("/data")
def get_data():
    df = pd.read_csv(DATA_PATH)
    return df.to_dict(orient="records")

from pydantic import BaseModel


class ETFRecord(BaseModel):
    date: str
    value: float
    memo: str = ""


@app.post("/data")
def add_data(record: ETFRecord):
    df = pd.read_csv(DATA_PATH)

    new_row = pd.DataFrame([record.model_dump()])
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv(DATA_PATH, index=False, encoding="utf-8-sig")

    return {"message": "?곗씠?곕? 異붽??덉뒿?덈떎.", "record": record}


@app.put("/data/{record_date}")
def update_data(record_date: str, record: ETFRecord):
    df = pd.read_csv(DATA_PATH)

    if record_date not in df["date"].astype(str).values:
        return {"message": "?대떦 ?좎쭨???곗씠?곌? ?놁뒿?덈떎."}

    df.loc[df["date"].astype(str) == record_date, ["date", "value", "memo"]] = [
        record.date, record.value, record.memo
    ]

    df.to_csv(DATA_PATH, index=False, encoding="utf-8-sig")
    return {"message": "?곗씠?곕? ?섏젙?덉뒿?덈떎."}


@app.delete("/data/{record_date}")
def delete_data(record_date: str):
    df = pd.read_csv(DATA_PATH)
    original_count = len(df)

    df = df[df["date"].astype(str) != record_date]

    if len(df) == original_count:
        return {"message": "?대떦 ?좎쭨???곗씠?곌? ?놁뒿?덈떎."}

    df.to_csv(DATA_PATH, index=False, encoding="utf-8-sig")
    return {"message": "?곗씠?곕? ??젣?덉뒿?덈떎."}
import os
from dotenv import load_dotenv
from openai import OpenAI
from fastapi import HTTPException

load_dotenv(override=True)

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url="https://copa.codyssey.kr/v1"
)


class ChatRequest(BaseModel):
    question: str


@app.post("/chat")
def chat_with_ai(request: ChatRequest):
    df = pd.read_csv(DATA_PATH)

    latest_price = float(df["value"].iloc[-1])
    average_price = float(df["value"].mean())
    maximum_price = float(df["value"].max())
    minimum_price = float(df["value"].min())

    analysis_context = f"""
    ETF: KODEX 200
    ?곗씠??媛쒖닔: {len(df)}
    遺꾩꽍 湲곌컙: {df["date"].iloc[0]} ~ {df["date"].iloc[-1]}
    理쒓렐 醫낃?: {latest_price:,.0f}??
    ?됯퇏 醫낃?: {average_price:,.0f}??
    理쒓퀬 醫낃?: {maximum_price:,.0f}??
    理쒖? 醫낃?: {minimum_price:,.0f}
     """

    try:
        response = client.chat.completions.create(
            model="gpt-5-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "??? ?? ETF ?? AI Agent???. "
                        "??? ???? ??? ???? ?????. "
                        "???? ?? ??? ????? ???. "
                        "?? ??? ???? ???."
                    )
                },
                {
                    "role": "user",
                    "content": f"""
[ETF ?? ???]
{analysis_context}

[??? ??]
{request.question}
"""
                }
            ]
        )

        return {"answer": response.choices[0].message.content}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"AI ?묐떟 ?앹꽦 ?ㅽ뙣: {type(e).__name__}"
        )
