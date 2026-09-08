"""Synthetic design probe only. No SAP/Citibank connector, posting or LLM.
SAP open balance is authoritative; unposted bank receipts are shown separately.
"""
import copy
import json
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path


def money(value):
    try:
        n = Decimal(str(value))
        if not n.is_finite() or n < 0 or n != n.quantize(Decimal('0.01')):
            raise ValueError('invalid money')
        return n
    except InvalidOperation as e:
        raise ValueError('invalid money') from e


def reconcile(data):
    if data.get('synthetic') is not True:
        raise ValueError('합성 설계 시험 전용: synthetic=true 필요')
    day = date.fromisoformat(data['as_of'])
    invoices, groups, seen, errors = {}, {}, {}, []
    for row in data['invoices']:
        key = (row['company'], row['invoice'])
        if key in invoices:
            raise ValueError('duplicate invoice key')
        if row['as_of'] != data['as_of']:
            raise ValueError('snapshot mismatch')
        money(row['sap_open'])
        if row['due']:
            date.fromisoformat(row['due'])
        invoices[key], groups[key] = row, []
    for r in data['bank']:
        key = (r['company'], r['account'], r['txn_id'])
        if not all(key):
            raise ValueError('missing transaction identity')
        if key in seen:
            if r != seen[key]:
                raise ValueError('same transaction ID with conflicting content')
            continue
        seen[key] = r
        money(r['amount'])
        reason = None
        ikey = (r['company'], r['invoice'])
        inv = invoices.get(ikey)
        if date.fromisoformat(r['date']) > day:
            reason = '기준일 이후 거래'
        elif r['status'] != 'booked':
            reason = '취소·정정·미확정 거래'
        elif not inv:
            reason = '인보이스 번호 없음 또는 미매칭'
        elif r['currency'] != inv['currency'] or r['dealer'] != inv['dealer']:
            reason = '통화·딜러 불일치'
        elif r['sap_reflected'] not in ['yes', 'no']:
            reason = 'SAP 반영 상태 미확인'
        if reason:
            errors.append({'txn_id': r['txn_id'], 'reason': reason})
        else:
            groups[ikey].append(r)
    result = []
    for key, inv in invoices.items():
        receipts = groups[key]
        unposted = sum((money(r['amount']) for r in receipts if r['sap_reflected'] == 'no'), Decimal('0'))
        opening = money(inv['sap_open'])
        remaining = opening - unposted
        days = max(0, (day - date.fromisoformat(inv['due'])).days) if inv['due'] else None
        status = '회수 전 검토' if days and remaining > 0 else '기일 미경과' if remaining > 0 else '은행 입금 전액 대응'
        if unposted:
            status = 'SAP 반영 확인 / ' + status
        if days is None:
            status = '지급기일 확인 필요'
        if remaining < 0:
            status = '과입금·배분 확인 필요'
        if errors:
            status = '입력 예외 해결 전 잠정 / ' + status
        result.append({'company': inv['company'], 'invoice': inv['invoice'], 'dealer': inv['dealer'],
                       'currency': inv['currency'], 'sap_open': str(opening.quantize(Decimal('.01'))),
                       'unposted_bank': str(unposted.quantize(Decimal('.01'))),
                       'review_remaining': str(remaining.quantize(Decimal('.01'))) if remaining >= 0 else None,
                       'overdue_days': days, 'status': status,
                       'evidence': [r['txn_id'] for r in receipts]})
    aging = {}
    for r in result:
        key = (r['dealer'], r['currency'])
        a = aging.setdefault(key, {'dealer':key[0], 'currency':key[1], 'sap_overdue':'0.00', 'review_overdue':'0.00', 'status':'검토용·확정 회수액 아님'})
        if r['overdue_days'] and r['review_remaining'] is not None:
            a['sap_overdue'] = str(money(a['sap_overdue']) + money(r['sap_open']))
            a['review_overdue'] = str(money(a['review_overdue']) + money(r['review_remaining']))
        if r['overdue_days'] is None or r['review_remaining'] is None or errors:
            a['status'] = '불완전·예외 해결 필요'
    return {'synthetic': True, 'as_of': data['as_of'], 'invoices': result, 'dealer_aging': list(aging.values()), 'exceptions': errors}


def fixture():
    return {'synthetic': True, 'as_of': '2026-09-07', 'invoices': [
        {'company':'DE01','invoice':'INV-101','dealer':'Dealer-A','currency':'EUR','sap_open':'600.00','due':'2026-09-01','as_of':'2026-09-07'},
        {'company':'DE01','invoice':'INV-102','dealer':'Dealer-B','currency':'EUR','sap_open':'500.00','due':'2026-09-10','as_of':'2026-09-07'}],
        'bank': [
        {'company':'DE01','account':'SYNTH-ACCOUNT','txn_id':'T1','invoice':'INV-101','dealer':'Dealer-A','currency':'EUR','amount':'400.00','date':'2026-09-02','sap_reflected':'yes','status':'booked'},
        {'company':'DE01','account':'SYNTH-ACCOUNT','txn_id':'T2','invoice':'INV-101','dealer':'Dealer-A','currency':'EUR','amount':'300.00','date':'2026-09-07','sap_reflected':'no','status':'booked'}]}


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    data = json.loads(args.input.read_text(encoding='utf-8')) if args.input else fixture()
    result = reconcile(data)  # validate all before publishing any output
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output/'input.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    (args.output/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    lines = ['# 합성 AR 처리 결과', '', '실제 거래·실측 성과가 아닌 설계 시험 결과입니다.', '',
             '|인보이스|SAP 미결(EUR)|미반영 입금(EUR)|회수 검토 잔액(EUR)|연체일수|상태|근거|',
             '|---|---:|---:|---:|---:|---|---|']
    for r in result['invoices']:
        lines.append('|'+ '|'.join(str(r[k]) for k in ['invoice','sap_open','unposted_bank','review_remaining','overdue_days','status','evidence'])+'|')
    lines += ['', '## 딜러별 aging', '```json',json.dumps(result['dealer_aging'],ensure_ascii=False,indent=2),'```']
    (args.output/'result.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))

if __name__ == '__main__':
    main()
