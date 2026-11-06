
import pandas as pd

# 저장된 ETF 데이터 불러오기
file_path = "data/etf_prices.csv"
df = pd.read_csv(file_path)

# 날짜와 종가 데이터 확인
df["date"] = pd.to_datetime(df["date"])
df["value"] = pd.to_numeric(df["value"])

# 기본 통계 계산
first_price = df["value"].iloc[0]
last_price = df["value"].iloc[-1]
average_price = df["value"].mean()
max_price = df["value"].max()
min_price = df["value"].min()

# 전체 기간 가격 변동률
change_rate = (last_price / first_price - 1) * 100

# 최근 20개 데이터의 평균과 이전 20개 평균 비교
recent_avg = df["value"].tail(20).mean()
previous_avg = df["value"].iloc[-40:-20].mean()

if recent_avg > previous_avg:
    trend = "상승 추세"
elif recent_avg < previous_avg:
    trend = "하락 추세"
else:
    trend = "횡보 추세"

# 분석 결과 출력
print("\n===== KODEX 200 ETF 분석 결과 =====")
print("데이터 개수:", len(df))
print("분석 시작일:", df["date"].min().date())
print("분석 종료일:", df["date"].max().date())
print(f"첫 종가: {first_price:,.0f}원")
print(f"최근 종가: {last_price:,.0f}원")
print(f"평균 종가: {average_price:,.2f}원")
print(f"최고 종가: {max_price:,.0f}원")
print(f"최저 종가: {min_price:,.0f}원")
print(f"전체 기간 가격 변동률: {change_rate:.2f}%")
print(f"최근 20개 평균: {recent_avg:,.2f}원")
print(f"그 이전 20개 평균: {previous_avg:,.2f}원")
print("최근 추세:", trend)
print("===================================")

import matplotlib.pyplot as plt

# 날짜순으로 종가 그래프 그리기
plt.figure(figsize=(12, 6))
plt.plot(df["date"], df["value"], label="KODEX 200 Close")

plt.title("KODEX 200 ETF Closing Price")
plt.xlabel("Date")
plt.ylabel("Price (KRW)")
plt.legend()
plt.grid(True)
plt.tight_layout()

# 그래프 파일 저장
plt.savefig("data/etf_price_chart.png", dpi=150)
print("가격 그래프 저장: data/etf_price_chart.png")

# 그래프 화면에 표시
plt.show()

# ===== 가격 예측 및 간단한 백테스트 =====

# 과거 5일 종가 평균으로 다음 날 가격 예측
df["prediction"] = df["value"].rolling(5).mean().shift(1)

# 예측값이 존재하는 데이터만 사용
test = df.dropna(subset=["prediction"]).copy()

# 실제 종가와 예측값의 차이
test["error"] = test["value"] - test["prediction"]
test["absolute_error"] = test["error"].abs()

# 평균 절대 오차(MAE)
mae = test["absolute_error"].mean()

# 평균 절대 백분율 오차(MAPE)
mape = (
    test["absolute_error"] / test["value"].abs()
).mean() * 100

# 예측 결과 출력
print("\n===== ETF 가격 예측 및 백테스트 =====")
print(f"평균 절대 오차(MAE): {mae:,.2f}원")
print(f"평균 절대 백분율 오차(MAPE): {mape:.2f}%")
print("\n최근 예측 결과 5개:")
print(
    test[["date", "value", "prediction"]]
    .tail(5)
    .to_string(index=False)
)

# 예측 결과 저장
test.to_csv(
    "data/etf_backtest.csv",
    index=False,
    encoding="utf-8-sig"
)

print("\n백테스트 결과 저장: data/etf_backtest.csv")
