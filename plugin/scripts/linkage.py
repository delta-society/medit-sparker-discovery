"""Bounded planning contract, not an integration client or KPI calculator."""
CONTRACT = 'objective-linkage-v1'
SCOPES = ['objective', 'linkage']
OBJECTIVE = ['outcome', 'metric_reference', 'definition', 'quality', 'unit', 'source',
             'desired_direction', 'causal_relation', 'alignment_owner', 'measurement_owner']
LINKS = {
    'upstream': ['app', 'record_id', 'trigger', 'fields'],
    'downstream': ['app', 'record_mapping', 'fields', 'status_mapping', 'dedupe', 'failure'],
    'measurement': ['app', 'metric_reference', 'event_mapping', 'record_mapping', 'dedupe', 'failure'],
}


def template():
    return {
        'planning_contract': CONTRACT,
        'objective': {**{k: '' for k in OBJECTIVE}, 'status': 'unknown',
                      'confirmation': None, 'acquisition_ids': []},
        'linkage': {'surface_strategy': '', 'reuse_basis': '',
                    **{name: {**{k: '' for k in keys}, 'status': 'unknown',
                              'basis': '', 'acquisition_ids': []} for name, keys in LINKS.items()},
                    'measurement': {**{k: '' for k in LINKS['measurement']}, 'status': 'record_only',
                                    'basis': '', 'acquisition_ids': []}},
    }


def validate(p, complete, require, obj, text, texts):
    """Use caller's validation primitives so errors retain its public exception type."""
    tasks = {t['id'] for t in p['acquisition_tasks']}

    def refs(value, label, needed=False):
        texts(value, label, needed)
        require(len(value) == len(set(value)), label + ': 중복 참조')
        require(set(value) <= tasks, label + ': 획득 작업 참조 없음')

    link = p['linkage']
    obj(link, ['surface_strategy', 'reuse_basis', *LINKS], 'linkage')
    for name, keys in LINKS.items():
        obj(link[name], [*keys, 'status', 'basis', 'acquisition_ids'], 'linkage.' + name)
    o = p['objective']
    obj(o, [*OBJECTIVE, 'status', 'confirmation', 'acquisition_ids'], 'objective')
    require(o['status'] in ['unknown', 'proposed', 'human_confirmed'], 'objective.status 오류')
    confirmed = o['status'] == 'human_confirmed'
    for key in OBJECTIVE:
        text(o[key], 'objective.' + key, (confirmed or complete) and not
             (key == 'measurement_owner' and p['linkage']['measurement']['status'] == 'record_only'))
    refs(o['acquisition_ids'], 'objective.acquisition_ids')
    if confirmed:
        obj(o['confirmation'], ['actor', 'quote', 'explicit', 'definition_sha256'], 'objective.confirmation')
        c = o['confirmation']
        require(c['actor'] == 'human' and c['explicit'] is True, 'KPI 사람 확인 필요')
        text(c['quote'], 'KPI 실제 확인 발화')
        require(c['definition_sha256'] == objective_digest(o), 'KPI 확인 대상 정의 변경: 다시 확인 필요')
    else:
        require(o['confirmation'] is None, '미확정 KPI에 사람 확인 기록 금지')
    require(not complete or confirmed, '목표 KPI 미확정: 설계는 초안으로 계속, 사람 선택 후 complete')
    link = p['linkage']
    obj(link, ['surface_strategy', 'reuse_basis', *LINKS], 'linkage')
    require(link['surface_strategy'] in ['', 'reuse_existing', 'new_surface_exception'], 'surface_strategy 오류')
    text(link['reuse_basis'], '기존 업무 앱 재사용 검토/새 표면 예외 이유', complete)
    require(not complete or bool(link['surface_strategy']), '입출력 표면 전략 필요')
    for name, keys in LINKS.items():
        x = link[name]
        obj(x, [*keys, 'status', 'basis', 'acquisition_ids'], 'linkage.' + name)
        allowed = ['unknown', 'draft', 'bound'] + (['record_only'] if name == 'measurement' else [])
        require(x['status'] in allowed, '연동 상태 오류; record_only는 KPI 기록에만 허용, live 상태 아님')
        recording = name == 'measurement' and x['status'] == 'record_only'
        bound = x['status'] == 'bound'
        for key in keys:
            text(x[key], name + '.' + key, bound or (complete and recording and key != 'app'))
        text(x['basis'], name + '.basis', bound or (complete and recording))
        refs(x['acquisition_ids'], name + '.acquisition_ids', complete and not bound and not recording)
    m = link['measurement']
    if m['metric_reference']:
        require(m['metric_reference'] == o['metric_reference'], '측정 연결의 metric_reference 불일치')


def objective_digest(objective):
    import hashlib
    import json
    data = {k: objective[k] for k in OBJECTIVE}
    return hashlib.sha256(json.dumps(data, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()


def render(p):
    def esc(v):
        v = str(v).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('\n', ' / ')
        for c in '#`|[]*_':
            v = v.replace(c, '&#' + str(ord(c)) + ';')
        return v
    lines = ['## 목적 KPI와 기존 업무 앱 연결', '',
             '제출 업무는 변경 후보입니다. 정합성 판정·측정 운영은 외부 프로그램 책임이며 아래는 연결 설계입니다.',
             'bound는 문서상 매핑 명시이며 API 접속·실행·운영 준비 검증이 아닙니다.', '']
    labels = ['업무 결과', '지표 참조', '정의/산식', '유효 품질 조건', '단위', '측정 출처',
              '원하는 변화 방향', '변경→결과의 인과 가설', '정합성 책임', '측정 책임']
    o = p['objective']
    lines.append('- KPI 상태: ' + esc(o['status']))
    for key, label in zip(OBJECTIVE, labels):
        lines.append('- ' + label + ': ' + esc(o[key] or '미확인'))
    link = p['linkage']
    lines.extend(['', '- 표면 전략: ' + esc(link['surface_strategy'] or '미확인'),
                  '- 기존 기능 검토/예외 이유: ' + esc(link['reuse_basis'] or '미확인')])
    for name, label in [('upstream', '입력·계기'), ('downstream', '결과 반영'), ('measurement', 'KPI 관련 결과·근거 기록 (외부 전달 선택)')]:
        x = link[name]
        lines.extend(['', '### ' + label + ' — ' + esc(x['status'])])
        for key in [*LINKS[name], 'basis']:
            label = ('외부 전달처 (선택)' if key == 'app' and name == 'measurement' else key)
            empty = ('미지정 — 기록만 유지' if key == 'app' and name == 'measurement' and x['status'] == 'record_only' else '미확인')
            lines.append('- ' + esc(label) + ': ' + esc(x[key] or empty))
        lines.append('- 확보 작업 참조: ' + esc(', '.join(x['acquisition_ids']) or '없음'))
    refs = set(o['acquisition_ids'])
    for name in LINKS:
        refs.update(link[name]['acquisition_ids'])
    for task in p['acquisition_tasks']:
        if task['id'] in refs:
            lines.append('- 확보 작업: ' + esc(' / '.join(task.values())))
    return '\n'.join(lines) + '\n'
