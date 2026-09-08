# 합성 AR 처리 결과

실제 거래·실측 성과가 아닌 설계 시험 결과입니다.

|인보이스|SAP 미결(EUR)|미반영 입금(EUR)|회수 검토 잔액(EUR)|연체일수|상태|근거|
|---|---:|---:|---:|---:|---|---|
|INV-101|600.00|300.00|300.00|6|SAP 반영 확인 / 회수 전 검토|['T1', 'T2']|
|INV-102|500.00|0.00|500.00|0|기일 미경과|[]|

## 딜러별 aging
```json
[
  {
    "dealer": "Dealer-A",
    "currency": "EUR",
    "sap_overdue": "600.00",
    "review_overdue": "300.00",
    "status": "검토용·확정 회수액 아님"
  },
  {
    "dealer": "Dealer-B",
    "currency": "EUR",
    "sap_overdue": "0.00",
    "review_overdue": "0.00",
    "status": "검토용·확정 회수액 아님"
  }
]
```
