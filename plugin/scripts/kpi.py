#!/usr/bin/env python3
"""Read-only KPI worksheet and matched labor-productivity comparison; stdlib only.
No business code execution, remote collection, causal attribution, or profit estimation.
"""
import argparse
import json
import math

SEATS = dict(enumerate(['기술수준', '배분효율', '규모의 경제', '범위의 경제', '생산집합 확장',
                        '이동', '분할', '오가격 교정', '회전'], 1))


def template():
    def observation():
        return dict(kind='unknown', window='', source='', accepted_output=None,
                    total_output=None, labor_hours=None, actual_used_output=None, cost=None)
    return dict(primary_seat=None, rationale='', causal_chain=[], output_unit='',
                labor_scope='준비·입력·검토·수정·재작업을 포함한 모든 참여자의 합계 시간',
                quality_rule='', metrics=[],
                measurement_plan=dict(source='', collector='', window='', pairing='', frequency=''),
                comparability=dict(same_unit=None, same_mix=None, same_quality=None, same_labor_scope=None),
                before=observation(), after=observation(), realization_plan='',
                financial_link='미확인 — 노동생산성 변화와 이익 실현은 별도 확인')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def fields(value, keys, label):
    require(isinstance(value, dict) and set(value) == set(keys), label + ': 필드 불일치')


def text(value, label, complete=False):
    require(isinstance(value, str) and (not complete or value.strip()), label + ': 설명 필요')


def validate(k, complete=False):
    fields(k, template(), 'kpi')
    seat = k['primary_seat']
    require(seat is None or (type(seat) is int and seat in SEATS), '이익 통로는 1~9 또는 null')
    if complete:
        require(seat is not None, '주된 이익 통로 제안 필요')
    for name in ['rationale', 'output_unit', 'labor_scope', 'quality_rule', 'realization_plan', 'financial_link']:
        text(k[name], name, complete)
    require(isinstance(k['causal_chain'], list), '인과관계 목록 필요')
    for item in k['causal_chain']:
        text(item, '인과관계', True)
    require(not complete or len(k['causal_chain']) >= 3, '투입·변화·실현 경로 작성 필요')
    fields(k['measurement_plan'], template()['measurement_plan'], 'measurement_plan')
    for name, value in k['measurement_plan'].items():
        text(value, name, complete)
    fields(k['comparability'], template()['comparability'], 'comparability')
    for value in k['comparability'].values():
        require(value is None or type(value) is bool, '비교 조건은 true/false/null')
    require(isinstance(k['metrics'], list) and len(k['metrics']) <= 3, '핵심 KPI는 최대 3개')
    require(not complete or len(k['metrics']) >= 2, '생산력·품질 KPI 초안 필요')
    for metric in k['metrics']:
        fields(metric, ['name', 'formula', 'unit', 'direction', 'target', 'target_status', 'basis'], 'metric')
        for key, value in metric.items():
            text(value, 'metric.' + key, True)
        require(metric['direction'] in ['increase', 'decrease', 'maintain'], 'KPI 방향 오류')
        require(metric['target_status'] in ['proposed', 'human_confirmed', 'unknown'], '목표 확인 상태 오류')
    for label in ['before', 'after']:
        o = k[label]
        fields(o, template()[label], label)
        require(o['kind'] in ['unknown', 'self_report', 'measured', 'synthetic'], '관측 근거 구분 오류')
        for key in ['window', 'source']:
            text(o[key], key, o['kind'] != 'unknown')
        for key in ['accepted_output', 'total_output', 'labor_hours', 'actual_used_output', 'cost']:
            v = o[key]
            require(v is None or (type(v) in [int, float] and math.isfinite(v) and v >= 0), '관측값은 유한 비음수 또는 null')
            require(o['kind'] != 'unknown' or v is None, '미확인 관측은 null; 0을 만들지 않음')
        if o['accepted_output'] is not None and o['total_output'] is not None:
            require(o['accepted_output'] <= o['total_output'], '품질 통과 산출이 전체 산출보다 많음')
        if o['actual_used_output'] is not None and o['accepted_output'] is not None:
            require(o['actual_used_output'] <= o['accepted_output'], '실제 사용은 같은 관측 집합의 통과 산출 이하')
    return k


def compare(k) -> dict:
    validate(k)
    out = dict(status='measurement_pending', conclusion='측정 대기 — 생산력 향상 여부 미확인',
               before_rate=None, after_rate=None, change_percent=None,
               before_quality=None, after_quality=None,
               financial_conclusion='이익 실현 미확인 — 이 계산으로 이익·총요소생산성·AI 인과효과를 확정하지 않음')
    b, a = k['before'], k['after']
    needed = ['accepted_output', 'total_output', 'labor_hours']
    if any(o[x] is None for o in [b, a] for x in needed):
        return out
    if any(o['labor_hours'] <= 0 or o['total_output'] <= 0 for o in [b, a]):
        out.update(status='invalid_denominator', conclusion='비교 불가 — 시간·전체 산출 분모는 양수여야 함')
        return out
    if not all(v is True for v in k['comparability'].values()):
        out.update(status='not_comparable', conclusion='비교 보류 — 산출 단위·업무 난이도/구성·품질 기준·시간 범위를 맞춰야 함')
        return out
    br, ar = b['accepted_output']/b['labor_hours'], a['accepted_output']/a['labor_hours']
    bq, aq = b['accepted_output']/b['total_output'], a['accepted_output']/a['total_output']
    out.update(before_rate=br, after_rate=ar, change_percent=(ar/br-1)*100 if br else None,
               before_quality=bq, after_quality=aq)
    if aq < bq:
        status, result = 'quality_failed', '품질 통과율 하락 — 생산력 개선 성공으로 판정하지 않음'
    elif ar > br:
        status, result = 'increased', '동일 조건의 시간당 품질 통과 산출 증가 관찰'
    elif ar < br:
        status, result = 'decreased', '동일 조건의 시간당 품질 통과 산출 감소 관찰'
    else:
        status, result = 'unchanged', '동일 조건의 시간당 품질 통과 산출 변화 없음'
    if b['kind'] == a['kind'] == 'measured':
        out.update(status=status, conclusion='제공된 실측 기록 기준: ' + result)
    else:
        label = '합성 예시' if 'synthetic' in [b['kind'], a['kind']] else '자기보고'
        out.update(status='provisional_' + status, conclusion=label + ' 기준: ' + result + ' / 실제 성과 확정 아님')
    return out


def render(k):
    r = compare(k)
    def esc(v):
        return str(v).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('|', '&#124;').replace('\n', ' / ')
    lines = ['## KPI 설정과 생산력 전후 비교', '',
             '- 주된 이익 통로(제안): ' + SEATS.get(k['primary_seat'], '미확인'),
             '- 선택 근거: ' + esc(k['rationale']),
             '- 인과관계: ' + ' → '.join(esc(x) for x in k['causal_chain']),
             '- 산출 단위: ' + esc(k['output_unit']), '- 사람시간 범위: ' + esc(k['labor_scope']),
             '- 품질 기준: ' + esc(k['quality_rule']), '',
             '| KPI | 산식·단위 | 목표·확인 상태 | 근거 |', '|---|---|---|---|']
    labels = {'proposed': 'AI 제안', 'human_confirmed': '참가자 확인', 'unknown': '미확인'}
    for m in k['metrics']:
        lines.append('| ' + ' | '.join([esc(m['name']), esc(m['formula']+' / '+m['unit']),
                                      esc(m['target']+' / '+labels[m['target_status']]), esc(m['basis'])]) + ' |')
    lines.extend(['', '- 늘어난 능력의 사용: ' + esc(k['realization_plan']), '- 재무 연결: ' + esc(k['financial_link'])])
    for key, label in [('before', '도입 전'), ('after', '도입 후')]:
        o = k[key]
        kind = {'unknown': '미확인', 'self_report': '자기보고', 'measured': '실측', 'synthetic': '합성 예시'}[o['kind']]
        parts = [label+' / '+kind, o['window'] or '기간 미확인', '근거: '+(o['source'] or '미확인')]
        for field, title in [('accepted_output', '품질 통과 산출'), ('total_output', '전체 산출'), ('labor_hours', '합계 사람시간'), ('actual_used_output', '실제 사용 산출'), ('cost', '총비용(동일 통화)')]:
            parts.append(title+': '+('미확인' if o[field] is None else str(o[field])))
        lines.append('- '+' / '.join(esc(x) for x in parts))
    for name, label in [('source', '기록 출처'), ('collector', '기록 담당'), ('window', '측정 기간'), ('pairing', '비교 방법'), ('frequency', '재확인 주기')]:
        lines.append('- '+label+': '+esc(k['measurement_plan'][name]))
    lines.extend(['', '**'+r['conclusion']+'**'])
    if r['before_rate'] is not None:
        lines.append('시간당 품질 통과 산출: '+format(r['before_rate'], '.6g')+' → '+format(r['after_rate'], '.6g')+' '+esc(k['output_unit'])+'/사람시간')
        lines.append('변화율: '+(format(r['change_percent'], '.6g')+'%' if r['change_percent'] is not None else '기준값 0 — 백분율 산출 불가'))
    lines.extend([r['financial_conclusion'], ''])
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['template', 'evaluate'])
    parser.add_argument('--input')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    if args.command == 'template':
        print(json.dumps(template(), ensure_ascii=False, indent=2))
        return
    from plan import read_json
    k = read_json(args.input)
    if 'plan' in k:
        k = k['plan']
    if 'kpi' in k:
        k = k['kpi']
    print(json.dumps(compare(k), ensure_ascii=False, indent=2, allow_nan=False) if args.json else render(k))


if __name__ == '__main__':
    from portable import configure_stdio
    configure_stdio()
    try:
        main()
    except (ValueError, TypeError, OSError, KeyError) as error:
        raise SystemExit('KPI 입력 오류: '+str(error))
