"""PDF-only layout hints from fields already visible in canonical Markdown.

Hints are applied only when the rendered source text matches after normalizing display whitespace. The ledger's
Markdown renderer is never changed. No private/legacy fields enter product output.
"""
from plan import METRICS


def display(value):
    return str(value).replace('\n', ' / ')


def hints(plan):
    product = 'planning_scope' in plan
    result = {'compounds': [], 'metrics': []}
    input_heading = '4. 구현에 필요한 입력과 확보 작업' if product else '4. 필요한 입력과 확보할 자료'
    referenced = {item['acquisition_id'] for item in plan['inputs']}
    for task in plan['acquisition_tasks']:
        if product and task['id'] not in referenced:
            continue
        value = f"{task['what']} / 담당: {task['owner']} / 방법: {task['method']} / 완료: {task['done_when']}"
        result['compounds'].append({
            'heading': input_heading, 'label': '확보할 것:', 'expected': display(value),
            'fields': [['확보할 것', display(task['what'])], ['담당', display(task['owner'])],
                       ['방법', display(task['method'])], ['완료', display(task['done_when'])]],
        })
    if product:
        for step in plan['workflow']:
            result['compounds'].append({
                'heading': '3. 현재 업무 흐름', 'label': display(step['step']) + ':',
                'expected': display(f"{step['actor']} / 입력: {step['input']} → 결과: {step['output']}"),
                'fields': [['담당', display(step['actor'])], ['입력', display(step['input'])],
                           ['결과', display(step['output'])]],
                'title': display(step['step']),
            })
        for step in plan['implementation_steps']:
            result['compounds'].append({
                'heading': '6. 구현 순서와 검증', 'label': '구현:',
                'expected': display(f"{step['action']} / 담당: {step['owner']} / 산출물: {step['output']} / 검증: {step['verify']}"),
                'fields': [['구현', display(step['action'])], ['담당', display(step['owner'])],
                           ['산출물', display(step['output'])], ['검증', display(step['verify'])]],
            })
    else:
        for index, step in enumerate(plan['implementation_steps'], 1):
            result['compounds'].append({
                'heading': '6. 구현 순서', 'list': 'ordered',
                'expected': display(f"{step['action']} — 담당: {step['owner']}; 결과: {step['output']}; 확인: {step['verify']}"),
                'title': f"{index}. {display(step['action'])}",
                'fields': [['담당', display(step['owner'])], ['결과', display(step['output'])],
                           ['확인', display(step['verify'])]],
            })
        labels = ['준비·검토·수정을 포함한 사람 시간', '시작부터 완료까지 경과시간', '재작업', '실제 사용', '추가 비용']
        for key, label in zip(METRICS, labels):
            metric = plan['baseline'][key]
            status = {'unknown': '미확인', 'self_report': '자기보고', 'measured': '실측'}[metric['status']]
            value = '미확인' if metric['value'] is None else str(metric['value']) + ' ' + {
                'minutes': '분', 'count': '건', 'KRW': '원'}.get(metric['unit'], metric['unit'])
            result['metrics'].append({
                'heading': '7. 지금의 기준과 효과 확인', 'label': label + ':',
                'expected': display(f"{value} / {metric['per']} / {status} / 근거: {metric['source']}"),
                'fields': [label, display(value), display(metric['per']), status, display(metric['source'])],
            })
    return result
