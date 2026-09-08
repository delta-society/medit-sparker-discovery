#!/usr/bin/env python3
"""Read-only educational example rendering; stdlib, no file/network/ledger writes.
Assumes one correctly matched receipt, one currency, no other adjustments.
Input provenance/real-business validity still requires source review.
"""
import argparse
from datetime import date
from decimal import Decimal
import json
import re


def money(value):
    if not isinstance(value,str) or not re.fullmatch(r'\d{1,12}(?:\.\d{1,2})?',value):
        raise ValueError('금액은 0 이상 소수점 두 자리 이하 숫자 문자열이어야 합니다.')
    return Decimal(value)


def ar_example(sap_open, receipt, posted='unknown', aligned='unknown', due=None, as_of=None, currency='EUR'):
    opening, amount = money(sap_open), money(receipt)
    if posted not in ('yes','no','unknown') or aligned not in ('yes','no','unknown'):
        raise ValueError('posted/aligned는 yes, no, unknown 중 하나입니다.')
    if not re.fullmatch(r'[A-Z]{3}',currency):raise ValueError('통화는 대문자 세 글자입니다.')
    dd = date.fromisoformat(due) if due else None
    ad = date.fromisoformat(as_of) if as_of else None
    days = max(0,(ad-dd).days) if dd and ad else None
    balance = None
    if posted == 'unknown' or aligned != 'yes':
        action='SAP 반영상태와 기준시점 정합성을 확인한다. 잔액 수정·회수 금액은 아직 정하지 않는다.'
        formula='계산 보류 — 반영상태와 기준시점 정합성 필요'
    elif posted == 'yes':
        balance=opening
        formula='은행 입금은 SAP 미결에 이미 반영됨 → SAP 미결 유지'
        action=f'회수 검토 금액 {balance:.2f} {currency}를 확인한다. 이 입금은 다시 차감하지 않는다.'
    elif amount > opening:
        formula='미반영 입금이 SAP 미결을 초과함 → 원천·배분 확인'
        action='초과 입금의 귀속을 확인한다. 음수 회수액이나 자동 수정 금액을 만들지 않는다.'
    else:
        balance=opening-amount
        formula=f'{opening:.2f} − {amount:.2f} = {balance:.2f}'
        action=f'미반영 입금 {amount:.2f} {currency}의 SAP 반영 필요를 확인하고 회수 검토 금액 {balance:.2f} {currency}를 확인한다.'
    labels={'yes':'확인됨','no':'아님','unknown':'미확인'}
    postlabels={'yes':'기반영','no':'미반영','unknown':'미확인'}
    rows=[('SAP 미결',f'{opening:.2f} {currency}'),('대응 은행 입금',f'{amount:.2f} {currency}'),
          ('SAP 반영상태',postlabels[posted]),('기준시점 정합',labels[aligned]),
          ('연체일수',f'{days}일' if days is not None else '지급기일 또는 기준일 미확인'),
          ('aging 구간·우선순위','현업 기준 미제공 — 판정하지 않음'),
          ('회수 검토 금액',f'{balance:.2f} {currency}' if balance is not None else '미확정'),
          ('처리 근거',formula),('담당자 다음 행동',action)]
    md='합성 기획 예제 — 실제 거래 검증 아님. 동일 통화·인보이스와 입금의 대응 확인·다른 조정 없음이라는 단순 예제 전제.\n\n'
    md+='| 항목 | 결과 |\n|---|---|\n'+'\n'.join(f'| {k} | {v} |' for k,v in rows)
    if posted == 'unknown':
        question='이 은행 입금은 SAP 미결에 이미 반영됐나요, 아직 미반영인가요?\n① 이미 반영 ② 아직 미반영 ③ 기타: 직접 입력 ④ 아직 모름\n번호만 답하거나 자기 말로 설명해도 됩니다.'
    elif aligned != 'yes':
        question='SAP 미결과 은행 입금의 기준시점 정합성을 어떤 조회나 자료로 확인할 수 있나요?'
    elif days is None:
        question='지급기일과 비교 기준일은 각각 언제인가요?'
    elif balance is None:
        question='초과 입금의 귀속을 확인할 원천 자료는 무엇인가요?'
    else:
        question='현재 사용 중인 aging 구간과 후속 조치 기준은 어떤 문서나 SAP 설정에서 확인할 수 있나요?'
    md+='\n\n**질문 하나:** '+question
    return dict(review_balance=f'{balance:.2f}' if balance is not None else None,
                aging_days=days,next_action=action,markdown=md)


def st_example(quantity, setup, per_unit):
    if not re.fullmatch(r'[1-9]\d{0,8}',quantity):raise ValueError('수량은 양의 정수입니다.')
    q=int(quantity);s=money(setup);u=money(per_unit)
    md='합성 기획 예제 — 회사 ST 산식·여유율·준비시간 배부 규칙 미확인.\n\n'
    md+='| 항목 | 결과 |\n|---|---|\n'
    rows=[('수량',f'{q}개'),('준비시간',f'{s:.2f}분'),('가공시간',f'{u:.2f}분/개'),
          ('총 가공시간',f'{q} × {u:.2f} = {q*u:.2f}분'),
          ('ST 산식','회사 기준 미확인 — 산식을 제시하지 않음'),
          ('ST 값','미확정'),('준비시간 배부·여유율','회사 기준 미확인'),
          ('제안 출력','입력값·총 가공시간·규칙 출처·ST 값·검토 상태를 분리'),
          ('담당자 다음 행동','기존 ST 계산표의 산식과 입력 단위를 확인한다. ST 값 입력이나 합격 판정은 아직 하지 않는다.')]
    md+='\n'.join(f'| {k} | {v} |' for k,v in rows)
    md+='\n\n**질문 하나:** 현재 사용하는 ST 산식은 어떤 계산표나 문서에서 확인할 수 있나요?'
    return dict(st_value=None,processing_minutes=f'{q*u:.2f}',markdown=md)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='command',required=True)
    a=sub.add_parser('ar',help='단일 AR 대표 예제 계산·표·다음 행동 (읽기 전용)')
    a.add_argument('--sap-open',required=True)
    a.add_argument('--receipt',required=True)
    a.add_argument('--posted',choices=['yes','no','unknown'],default='unknown')
    a.add_argument('--aligned',choices=['yes','no','unknown'],default='unknown')
    a.add_argument('--due')
    a.add_argument('--as-of')
    a.add_argument('--currency',default='EUR')
    a.add_argument('--json',action='store_true')
    s=sub.add_parser('st',help='회사 산식 미확인 ST 대표 예제 (읽기 전용)')
    s.add_argument('--quantity',required=True)
    s.add_argument('--setup',required=True)
    s.add_argument('--per-unit',required=True)
    s.add_argument('--json',action='store_true')
    v=vars(p.parse_args());kind=v.pop('command');js=v.pop('json')
    try:r=(ar_example if kind=='ar' else st_example)(**v)
    except ValueError as e:p.error(str(e))
    print(json.dumps(r,ensure_ascii=False,indent=2) if js else r['markdown'])

if __name__=='__main__':main()
