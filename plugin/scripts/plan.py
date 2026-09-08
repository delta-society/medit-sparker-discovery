#!/usr/bin/env python3
"""Sparker local plan ledger. Python 3.9+, stdlib only; never runs plan content.

Immutable revision bundles; local cooperative writer lock; optimistic revision check.
This is validation/persistence, not an LLM or a human-identity authentication service.
"""
import argparse
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
from datetime import datetime, timezone

VERSION = 1
MAX_JSON_BYTES = 2_000_000
ID = re.compile(r"[a-z0-9][a-z0-9-]{0,63}\Z")
RESERVED = {"con", "prn", "aux", "nul", *[f"com{i}" for i in range(1, 10)], *[f"lpt{i}" for i in range(1, 10)]}
SCOPES = ["user_result", "selected_change", "acceptance_tests"]
METRICS = ["people_time", "end_to_end", "rework", "actual_use", "additional_cost"]


class PlanError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise PlanError(message)


def text(value, label, nonempty=True):
    require(isinstance(value, str) and (not nonempty or bool(value.strip())), label + ": 문자열 필요")


def obj(value, keys, label):
    require(isinstance(value, dict), label + ": 객체 필요")
    require(set(value) == set(keys), label + ": 필드 불일치 (필요: " + ", ".join(keys) + ")")


def texts(value, label, nonempty=False):
    require(isinstance(value, list), label + ": 목록 필요")
    if nonempty:
        require(bool(value), label + ": 한 항목 이상 필요")
    for item in value:
        text(item, label)


def ident(value):
    require(isinstance(value, str) and ID.fullmatch(value) and value not in RESERVED,
            "ID는 영문 소문자/숫자/하이픈 1~64자이며 예약 이름은 금지")
    return value


def canonical(data):
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(data):
    return hashlib.sha256(canonical(data).encode("utf-8")).hexdigest()


def no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "중복 JSON 키: " + key)
        result[key] = value
    return result


def read_json(path):
    p = safe_path(path)
    require(p.is_file(), "JSON 파일이 없습니다: " + str(p))
    require(p.stat().st_size <= MAX_JSON_BYTES, "JSON은 2MB 이하만 허용")
    with p.open(encoding="utf-8-sig") as handle:
        return json.load(handle, object_pairs_hook=no_duplicates,
                         parse_constant=lambda x: (_ for _ in ()).throw(PlanError("비유한 수 금지")))


def safe_path(path):
    """Reject symlinks in every existing component; do not silently resolve aliases.

    Assumes a user-controlled local directory (not a hostile concurrent filesystem).
    On macOS use /private/tmp instead of the /tmp symlink.
    """
    p = Path(os.path.abspath(os.path.expanduser(str(path))))
    for component in [*reversed(p.parents), p]:
        require(not component.is_symlink(), "심볼릭 링크 경로 금지: " + str(component))
        isjunction = getattr(component, "is_junction", None)
        require(not (isjunction and isjunction()), "junction 경로 금지: " + str(component))
    return p


def template(product=False, linked=False):
    plan = {
        "submission": {"text": "", "source": ""},
        "facts": [],
        "user_result": {"user": "", "result": "", "use_when": ""},
        "workflow": [],
        "bottlenecks": [],
        "selected_change": {"candidate_id": None, "change": "", "reason": "", "non_goals": []},
        "responsibilities": {"ai": [], "code": [], "human": []},
        "inputs": [],
        "acquisition_tasks": [],
        "quality_conditions": [],
        "acceptance_tests": [],
        "implementation_steps": [],
        "baseline": {name: {"status": "unknown", "value": None,
                             "unit": "minutes" if name in METRICS[:2] else "count" if name in METRICS[2:4] else "KRW",
                             "per": "동일 업무 1건", "source": "미확인"} for name in METRICS},
        "comparison": {"same_work_unit": "", "quality_guard": "", "collection": "", "future_check": "", "frequency": "미확인"},
        "next_action": {"owner": "", "action": "", "done_when": ""},
        "open_questions": [],
    }
    if product or linked:
        for key in ["submission", "facts", "bottlenecks", "baseline", "comparison"]:
            del plan[key]
        plan["planning_scope"] = "product"
    if linked:
        from linkage import template as linkage_template
        plan.update(linkage_template())
    return plan


def validate_plan(p, complete=False):
    expected_keys = set(template())
    require(isinstance(p, dict), "plan: 객체 필요")
    product = "planning_scope" in p
    linked = "planning_contract" in p
    original = p
    if linked:
        from linkage import CONTRACT
        require(product and p["planning_contract"] == CONTRACT, "planning_contract 오류")
        require({"objective", "linkage"} <= set(p), "목표·연동 계약 필요")
    if product:
        require(p["planning_scope"] == "product", "planning_scope: product만 허용")
        required = set(template(product=True))
        extras = {"planning_contract", "objective", "linkage"} if linked else set()
        require(required <= set(p) <= expected_keys | {"kpi", "planning_scope"} | extras, "plan: 필드 불일치")
        # Defaults are validation-only: never migrate or mutate persisted JSON.
        p = {**template(), **p}
    else:
        require(set(p) in [expected_keys, expected_keys | {"kpi"}], "plan: 필드 불일치")
    if "kpi" in p:
        from kpi import validate as validate_kpi
        validate_kpi(p["kpi"], complete and not product)
    obj(p["submission"], ["text", "source"], "submission")
    for k, v in p["submission"].items():
        text(v, "submission." + k, not product)
    require(isinstance(p["facts"], list), "facts 목록 필요")
    fact_ids = set()
    for f in p["facts"]:
        obj(f, ["id", "text", "source", "kind"], "fact")
        ident(f["id"])
        require(f["id"] not in fact_ids, "fact ID 중복")
        fact_ids.add(f["id"])
        text(f["text"], "fact.text")
        text(f["source"], "fact.source")
        require(f["kind"] in ["submitted", "human_confirmed", "ai_hypothesis"], "fact.kind 오류")
    obj(p["user_result"], ["user", "result", "use_when"], "user_result")
    for k, v in p["user_result"].items():
        text(v, k, complete)
    require(isinstance(p["workflow"], list), "workflow 목록 필요")
    for w in p["workflow"]:
        obj(w, ["step", "actor", "input", "output", "wait_or_rework", "basis"], "workflow")
        for k, v in w.items():
            text(v, k, not product or k not in ["basis", "wait_or_rework"])
    require(isinstance(p["bottlenecks"], list), "bottlenecks 목록 필요")
    candidates = {}
    for b in p["bottlenecks"]:
        obj(b, ["id", "claim", "evidence", "counterevidence", "status"], "bottleneck")
        ident(b["id"])
        require(b["id"] not in candidates, "병목 ID 중복")
        candidates[b["id"]] = b
        text(b["claim"], "claim")
        texts(b["evidence"], "evidence", not product)
        texts(b["counterevidence"], "counterevidence", not product)
        require(b["status"] in ["hypothesis", "human_confirmed", "rejected"], "병목 status 오류")
        for ref in b["evidence"]:
            require(ref in fact_ids, "병목 근거는 fact ID여야 합니다: " + ref)
    change = p["selected_change"]
    obj(change, ["candidate_id", "change", "reason", "non_goals"], "selected_change")
    if change["candidate_id"] is not None:
        require(change["candidate_id"] in candidates, "선택 병목 ID 없음")
        require(candidates[change["candidate_id"]]["status"] != "rejected", "거절한 병목 선택 금지")
    for key in ["change", "reason"]:
        text(change[key], key, complete and (not product or key == "change"))
    texts(change["non_goals"], "non_goals", complete)
    obj(p["responsibilities"], ["ai", "code", "human"], "responsibilities")
    for key, value in p["responsibilities"].items():
        texts(value, key, complete)
    require(isinstance(p["acquisition_tasks"], list), "acquisition_tasks 목록 필요")
    tasks = set()
    for a in p["acquisition_tasks"]:
        obj(a, ["id", "what", "owner", "method", "done_when"], "acquisition")
        ident(a["id"])
        require(a["id"] not in tasks, "획득 작업 ID 중복")
        tasks.add(a["id"])
        for k, v in a.items():
            text(v, k)
    require(isinstance(p["inputs"], list), "inputs 목록 필요")
    for i in p["inputs"]:
        obj(i, ["name", "source", "access", "acquisition_id"], "input")
        text(i["name"], "input.name")
        text(i["source"], "input.source")
        require(i["access"] in ["user_reported", "verified", "unknown", "missing"], "access 오류")
        if i["access"] in ["unknown", "missing"]:
            require(i["acquisition_id"] in tasks, "미확인/미확보 입력에 획득 작업 필요")
        elif i["acquisition_id"] is not None:
            require(i["acquisition_id"] in tasks, "획득 작업 참조 없음")
    texts(p["quality_conditions"], "quality_conditions", complete)
    require(isinstance(p["acceptance_tests"], list), "acceptance_tests 목록 필요")
    test_ids, types = set(), set()
    for t in p["acceptance_tests"]:
        obj(t, ["id", "type", "input", "steps", "expected", "pass_condition", "runner"], "acceptance_test")
        ident(t["id"])
        require(t["id"] not in test_ids, "시험 ID 중복")
        test_ids.add(t["id"])
        require(t["type"] in ["normal", "exception"], "시험은 normal/exception")
        types.add(t["type"])
        for k in ["input", "expected", "pass_condition", "runner"]:
            text(t[k], "test." + k)
        texts(t["steps"], "test.steps", True)
    require(isinstance(p["implementation_steps"], list), "implementation_steps 목록 필요")
    for s in p["implementation_steps"]:
        obj(s, ["action", "owner", "output", "verify"], "implementation_step")
        for k, v in s.items():
            text(v, k)
    obj(p["baseline"], METRICS, "baseline")
    for name, metric in p["baseline"].items():
        obj(metric, ["status", "value", "unit", "per", "source"], name)
        require(metric["status"] in ["unknown", "self_report", "measured"], "baseline.status 오류")
        for k in ["unit", "per", "source"]:
            text(metric[k], name + "." + k)
        value = metric["value"]
        if metric["status"] == "unknown":
            require(value is None, "미확인은 null; 0이 아닙니다")
        else:
            require((type(value) in [int, float] and math.isfinite(value) and value >= 0) or
                    (isinstance(value, str) and value.strip()), "기준값은 비음수 수 또는 원문 범위 문자열")
        if name in METRICS[:2]:
            require(metric["unit"] == "minutes", "시간 단위는 minutes")
    obj(p["comparison"], ["same_work_unit", "quality_guard", "collection", "future_check", "frequency"], "comparison")
    for k, v in p["comparison"].items():
        text(v, "comparison." + k, complete and not product)
    obj(p["next_action"], ["owner", "action", "done_when"], "next_action")
    for k, v in p["next_action"].items():
        text(v, k, complete)
    texts(p["open_questions"], "open_questions")
    if complete:
        for key in (["workflow", "inputs", "implementation_steps"] if product else
                    ["facts", "workflow", "bottlenecks", "inputs", "implementation_steps"]):
            require(bool(p[key]), key + ": 확정 전에 작성 필요")
        if not product:
            require(change["candidate_id"] is not None, "확정 전에 변경 근거 후보 선택 필요 (가설 허용)")
        require(types == {"normal", "exception"}, "정상/예외 시험 모두 필요")
    if linked:
        from linkage import validate as validate_linkage
        validate_linkage(original, complete, require, obj, text, texts)
    return original


def markdown(record):
    """Readable participant handoff; exact structured provenance remains in JSON."""
    if "planning_scope" in record["plan"]:
        require(record["plan"]["planning_scope"] == "product", "planning_scope: product만 허용")
        rendered = product_markdown(record)
        if "planning_contract" in record["plan"]:
            from linkage import render
            rendered = rendered.replace("## 1. 제품 목표와 사용자",
                                        render(record["plan"]) + "\n## 1. 제품 목표와 사용자", 1)
        return rendered
    p = record['plan']
    def esc(v):
        s = str(v).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('\n', ' / ')
        for ch in '#`|[]*_':
            s = s.replace(ch, '&#'+str(ord(ch))+';')
        return s
    lines = [f"# 구현 기획서 — {esc(record['case_id'])}", '',
             f"상태: {'사람 확정' if record['status'] == 'finalized' else '초안 · 미확정'} · 수정 {record['revision']}", '',
             '이 문서는 구현할 업무와 시험 기준을 정한 기획서입니다. 구현 완료나 실제 성과를 뜻하지 않습니다.', '']
    def section(title):lines.extend(['## '+title, ''])
    def item(label, value):lines.append('- **'+label+':** '+esc(value if value not in [None, '', []] else '미확인'))
    def bullets(values):
        lines.extend(['- '+esc(v) for v in values] or ['- 아직 작성하지 않음'])
        lines.append('')
    section('1. 누구의 어떤 일을 바꾸는가')
    for key, label in [('user','사용자'),('result','완료할 결과'),('use_when','사용 시점')]:item(label,p['user_result'][key])
    section('2. 현재 흐름과 막히는 곳')
    for i,w in enumerate(p['workflow'],1):
        lines.append(f"{i}. {esc(w['step'])} — {esc(w['actor'])}")
        lines.append(f"   입력: {esc(w['input'])} → 결과: {esc(w['output'])}. 대기·재작업: {esc(w['wait_or_rework'])}. 근거: {esc(w['basis'])}")
    facts={f['id']:f for f in p['facts']}
    for b in p['bottlenecks']:
        labels={'hypothesis':'AI 가설 · 미확정','human_confirmed':'참가자 확인','rejected':'철회'}
        lines.extend(['',f"**{esc(b['claim'])} — {labels[b['status']]}**"])
        item('근거','; '.join(facts[x]['text'] for x in b['evidence']))
        item('다르게 판단할 신호','; '.join(b['counterevidence']))
    section('3. 이번에 만들 것과 만들지 않을 것')
    for key,label in [('change','변경'),('reason','선택 이유')]:item(label,p['selected_change'][key])
    item('이번 범위에서 제외','; '.join(p['selected_change']['non_goals']))
    for key,label in [('ai','AI가 제안·해석'),('code','코드로 반복·검사'),('human','사람이 확인·결정')]:item(label,'; '.join(p['responsibilities'][key]))
    section('4. 필요한 입력과 확보할 자료')
    access={'user_reported':'접근 가능(참가자 진술)','verified':'접근 확인','unknown':'접근 미확인','missing':'미확보'}
    for x in p['inputs']:item(x['name'],x['source']+' · '+str(access[x['access']]))
    for a in p['acquisition_tasks']:item('확보할 것',f"{a['what']} / 담당: {a['owner']} / 방법: {a['method']} / 완료: {a['done_when']}")
    section('5. 잘됐다고 판단할 기준')
    bullets(p['quality_conditions'])
    for t in p['acceptance_tests']:
        lines.append('### '+('정상 입력 시험' if t['type']=='normal' else '예외 입력 시험'))
        item('입력',t['input']);item('수행', ' → '.join(t['steps']));item('예상 결과',t['expected']);item('통과 조건',t['pass_condition']);item('시험 담당',t['runner'])
    section('6. 구현 순서')
    for i,s in enumerate(p['implementation_steps'],1):
        lines.append(f"{i}. {esc(s['action'])} — 담당: {esc(s['owner'])}; 결과: {esc(s['output'])}; 확인: {esc(s['verify'])}")
    section('7. 지금의 기준과 효과 확인')
    for key,label in [('people_time','준비·검토·수정을 포함한 사람 시간'),('end_to_end','시작부터 완료까지 경과시간'),('rework','재작업'),('actual_use','실제 사용'),('additional_cost','추가 비용')]:
        m=p['baseline'][key]; status={'unknown':'미확인','self_report':'자기보고','measured':'실측'}[m['status']]
        value='미확인' if m['value'] is None else str(m['value'])+' '+{'minutes':'분','count':'건','KRW':'원'}.get(m['unit'],m['unit'])
        item(label,f"{value} / {m['per']} / {status} / 근거: {m['source']}")
    for key,label in [('frequency','발생 빈도'),('same_work_unit','비교 단위'),('quality_guard','동일 품질 조건'),('collection','전후 측정 방법'),('future_check','향후 확인')]:item(label,p['comparison'][key])
    section('8. 다음 행동과 남은 질문')
    for key,label in [('owner','담당'),('action','할 일'),('done_when','완료 조건')]:item(label,p['next_action'][key])
    bullets(p['open_questions'])
    section('근거와 구분')
    for f in p['facts']:
        kind={'submitted':'제출 내용','human_confirmed':'참가자 확인','ai_hypothesis':'AI 가설'}[f['kind']]
        item(kind,f['text']+' / '+f['source'])
    section('최초 제출')
    item('출처',p['submission']['source']);lines.extend(['',esc(p['submission']['text']),''])
    if record['confirmation']:
        item('확정 발화',record['confirmation']['quote'])
    rendered = '\n'.join(lines)+'\n'
    if 'kpi' in p:
        from kpi import render as render_kpi
        rendered += '\n'+render_kpi(p['kpi'])
    return rendered


def product_markdown(record):
    """Allowlisted build handoff; legacy evidence and measurement stay in JSON."""
    p = record["plan"]

    def esc(value):
        value = str(value).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('\n', ' / ')
        for ch in '#`|[]*_':
            value = value.replace(ch, '&#' + str(ord(ch)) + ';')
        return value

    lines = [f"# 제품 구현 기획서 — {esc(record['case_id'])}", '',
             f"상태: {'사람 확정' if record['status'] == 'finalized' else '초안 · 미확정'} · 수정 {record['revision']}", '']

    def section(title):
        lines.extend(['', '## ' + title, ''])

    def item(label, value):
        lines.append('- **' + esc(label) + ':** ' + esc(value if value not in [None, '', []] else '아직 작성하지 않음'))

    section('1. 제품 목표와 사용자')
    for key, label in [('user', '사용자'), ('result', '완료할 결과'), ('use_when', '사용 시점')]:
        item(label, p['user_result'][key])
    section('2. 합의할 변경과 제외 범위')
    item('만들 것', p['selected_change']['change'])
    item('만들지 않을 것', '; '.join(p['selected_change']['non_goals']))
    for key, label in [('ai', 'AI 역할'), ('code', '코드 역할'), ('human', '사람 역할')]:
        item(label, '; '.join(p['responsibilities'][key]))
    section('3. 현재 업무 흐름')
    for w in p['workflow']:
        item(w['step'], f"{w['actor']} / 입력: {w['input']} → 결과: {w['output']}")
    section('4. 구현에 필요한 입력과 확보 작업')
    access = {'user_reported': '접근 가능(사용자 진술)', 'verified': '접근 확인', 'unknown': '접근 미확인', 'missing': '미확보'}
    for x in p['inputs']:
        item(x['name'], x['source'] + ' · ' + access[x['access']])
    referenced = {x['acquisition_id'] for x in p['inputs'] if x['acquisition_id'] is not None}
    for a in p['acquisition_tasks']:
        if a['id'] in referenced:
            item('확보할 것', f"{a['what']} / 담당: {a['owner']} / 방법: {a['method']} / 완료: {a['done_when']}")
    section('5. 기술 규칙과 수용 시험')
    for rule in p['quality_conditions']:
        item('규칙', rule)
    for t in p['acceptance_tests']:
        lines.extend(['', '### ' + ('정상 입력 시험' if t['type'] == 'normal' else '예외 입력 시험')])
        for label, value in [('입력', t['input']), ('수행', ' → '.join(t['steps'])),
                             ('예상 결과', t['expected']), ('통과 조건', t['pass_condition']), ('시험 담당', t['runner'])]:
            item(label, value)
    section('6. 구현 순서와 검증')
    for s in p['implementation_steps']:
        item('구현', f"{s['action']} / 담당: {s['owner']} / 산출물: {s['output']} / 검증: {s['verify']}")
    section('7. 다음 구현 행동과 남은 질문')
    for key, label in [('owner', '담당'), ('action', '할 일'), ('done_when', '완료 조건')]:
        item(label, p['next_action'][key])
    for question in p['open_questions']:
        item('남은 질문', question)
    return '\n'.join(lines) + '\n'


class Store:
    def __init__(self, root):
        self.root = safe_path(root)

    def case_path(self, case):
        return safe_path(self.root / ident(case))

    def revisions(self, case):
        path = self.case_path(case)
        if not path.exists():
            return []
        require(path.is_dir(), "과제 경로는 디렉터리여야 합니다")
        result = []
        for child in path.iterdir():
            safe_path(child)
            if re.fullmatch(r"r[0-9]{6}", child.name):
                require(child.is_dir(), "리비전 경로 오류")
                result.append(child)
            else:
                require(child.name == ".lock" or child.name.startswith(".pending-"), "알 수 없는 저장 파일: " + child.name)
        result.sort()
        require([x.name for x in result] == [f"r{i:06d}" for i in range(1, len(result) + 1)], "리비전 연속성 오류")
        return result

    def read_revision(self, path, case, index, last):
        """Validate both files identically before publication and during resume."""
        record = read_json(path / "plan.json")
        obj(record, ["schema_version", "case_id", "revision", "status", "created_at", "plan", "plan_sha256", "previous_sha256", "event", "confirmation"], "record")
        require(record["schema_version"] == VERSION and record["case_id"] == case and record["revision"] == index, "리비전 메타데이터 오류")
        require(record["status"] in ["draft", "finalized"], "저장 상태 오류")
        validate_plan(record["plan"], record["status"] == "finalized")
        previous = digest(last) if last is not None else None
        require(record["plan_sha256"] == digest(record["plan"]) and record["previous_sha256"] == previous, "리비전 해시 불일치")
        if record["status"] == "finalized":
            require(last is not None, "확정은 기존 초안에서만 가능")
            validate_confirmation(record["confirmation"], last)
        else:
            require(record["confirmation"] is None, "초안에 유효 확인 기록 금지")
        md = safe_path(path / "plan.md")
        # Keep the existing renderer and immutable bytes, including literal CR.
        # Text-mode universal newlines would falsely report these as corruption.
        require(md.is_file() and md.read_bytes() == markdown(record).encode("utf-8"), "Markdown/JSON 불일치")
        return record

    def load(self, case):
        revisions = self.revisions(case)
        require(bool(revisions), "저장된 과제가 없습니다")
        last = None
        for index, path in enumerate(revisions, 1):
            last = self.read_revision(path, case, index, last)
        return last

    def write(self, case, action, plan=None, expected=None, reason=None, candidate=None, confirmation=None):
        require(action in ["new", "update", "reject", "finalize", "reopen"], "지원하지 않는 작업")
        case_path = self.case_path(case)
        self.root.mkdir(parents=True, exist_ok=True)
        safe_path(self.root)
        case_path.mkdir(exist_ok=True)
        lock = safe_path(case_path / ".lock")
        try:
            lock.mkdir()
        except FileExistsError:
            raise PlanError("다른 저장 진행 중 또는 중단된 잠금. 쓰기 프로세스 종료 확인 후 .lock만 수동 제거")
        pending = None
        try:
            exists = bool(self.revisions(case))
            if action == "new":
                require(not exists, "기존 과제 덮어쓰기 금지; update/reopen 사용")
                require(plan is not None, "새 plan 필요")
                old, revision = None, 1
                p = copy.deepcopy(plan)
            else:
                require(exists, "과제 없음; new 필요")
                old = self.load(case)
                require(type(expected) is int and expected == old["revision"], "리비전 충돌: 최신 show 후 재시도")
                revision = old["revision"] + 1
                p = copy.deepcopy(old["plan"])
                require((action == "reopen" and old["status"] == "finalized") or
                        (action != "reopen" and old["status"] == "draft"), "확정본은 reopen 후 수정; reopen은 확정본만")
                if action in ["update", "reject", "reopen"]:
                    text(reason, "변경/거절/재개 이유")
                if action == "update":
                    require(plan is not None, "수정 plan 필요")
                    p = copy.deepcopy(plan)
                    if "planning_contract" in old["plan"]:
                        require(p.get("planning_contract") == old["plan"]["planning_contract"], "연동 계약 제거/하향 변경 금지")
                    require(p.get("submission") == old["plan"].get("submission"), "최초 제출 원문은 불변; 정정은 facts와 변경 이유로 기록")
                elif action == "reject":
                    ident(candidate)
                    matches = [b for b in p.get("bottlenecks", []) if b["id"] == candidate]
                    require(bool(matches), "거절할 병목 후보 없음")
                    require(matches[0]["status"] != "rejected", "이미 거절된 후보")
                    matches[0]["status"] = "rejected"
                    if p["selected_change"]["candidate_id"] == candidate:
                        p["selected_change"] = {"candidate_id": None, "change": "", "reason": "", "non_goals": []}
                elif action == "finalize":
                    validate_confirmation(confirmation, old)
            require(revision <= 999999, "리비전 한도 도달")
            validate_plan(p, action == "finalize")
            record = {"schema_version": VERSION, "case_id": case, "revision": revision,
                      "status": "finalized" if action == "finalize" else "draft",
                      "created_at": datetime.now(timezone.utc).isoformat(), "plan": p,
                      "plan_sha256": digest(p), "previous_sha256": digest(old) if old else None,
                      "event": {"action": action, "reason": reason, "candidate_id": candidate},
                      "confirmation": copy.deepcopy(confirmation) if action == "finalize" else None}
            record_json = json.dumps(record, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
            require(len(record_json.encode("utf-8")) <= MAX_JSON_BYTES, "저장 레코드는 메타데이터 포함 2MB 이하만 허용")
            pending = Path(tempfile.mkdtemp(prefix=".pending-", dir=case_path))
            for name, content in [("plan.json", record_json),
                                  ("plan.md", markdown(record))]:
                with (pending / name).open("x", encoding="utf-8", newline="\n") as handle:
                    handle.write(content)
                    handle.flush()
                    os.fsync(handle.fileno())
            require(self.read_revision(pending, case, revision, old) == record, "공개 전 재검증 실패")
            target = safe_path(case_path / f"r{revision:06d}")
            require(not target.exists(), "리비전 덮어쓰기 금지")
            pending.rename(target)
            pending = None
            return record
        finally:
            if pending is not None:
                shutil.rmtree(pending)
            lock.rmdir()

    def export(self, case, output):
        record = self.load(case)
        target = safe_path(output)
        require(target.suffix.lower() == ".md", "내보내기는 .md 경로만")
        require(target.parent.is_dir(), "내보내기 상위 폴더가 없습니다")
        with target.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(markdown(record))
        return target


def validate_confirmation(c, old):
    obj(c, ["actor", "quote", "revision", "plan_sha256", "scopes", "explicit"], "confirmation")
    require(c["actor"] == "human" and c["explicit"] is True, "사용자의 명시적 확인만 확정 가능")
    text(c["quote"], "사용자의 실제 확인 발화")
    require(type(c["revision"]) is int and c["revision"] == old["revision"], "확인 대상 리비전 불일치")
    require(c["plan_sha256"] == old["plan_sha256"], "확인 대상 계획 해시 불일치")
    scopes = SCOPES.copy()
    if "planning_contract" in old["plan"]:
        from linkage import SCOPES as linkage_scopes
        scopes += linkage_scopes
    require(isinstance(c["scopes"], list) and sorted(c["scopes"]) == sorted(scopes), "사용자/결과·변경·시험 및 계약별 목표·연동 확인 필요")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Sparker 구현 기획서 — 로컬 불변 리비전 저장/검증/내보내기")
    parser.add_argument("--root", default=".sparker-discovery", help="사용자가 승인한 로컬 저장 폴더")
    sub = parser.add_subparsers(dest="command", required=True)
    tpl = sub.add_parser("template", help="빈 plan JSON 출력")
    tpl.add_argument("--product", action="store_true", help="0.3 호환 제품 기획서")
    tpl.add_argument("--linked", action="store_true", help="목표 KPI·외부 앱 연결 기획서 (신규 권장)")
    val = sub.add_parser("validate")
    val.add_argument("--input", required=True)
    val.add_argument("--complete", action="store_true")
    for action in ["new", "update", "save", "reject", "finalize", "reopen", "show", "resume", "history", "export", "pdf"]:
        cmd = sub.add_parser(action)
        cmd.add_argument("case_id")
        if action in ["new", "update", "save"]:
            cmd.add_argument("--input", required=True, help="plan 객체 JSON, record 전체가 아님")
        if action in ["update", "save", "reject", "finalize", "reopen", "pdf"]:
            cmd.add_argument("--expected-revision", required=True, type=int)
        if action in ["update", "save", "reject", "reopen"]:
            cmd.add_argument("--reason", required=True)
        if action == "reject":
            cmd.add_argument("--candidate", required=True)
        if action == "finalize":
            cmd.add_argument("--confirmation", required=True, help="실제 사용자 발화와 대상 해시/리비전")
        if action == "export":
            cmd.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "template":
            result = template(product=args.product, linked=args.linked)
        elif args.command == "validate":
            validate_plan(read_json(args.input), args.complete)
            result = {"valid": True, "complete_structure": args.complete,
                      "notice": "구조 검증만 완료. 인간 확인/의미 타당성/시험 실행 증명이 아닙니다."}
        else:
            store = Store(args.root)
            if args.command in ["show", "resume"]:
                result = store.load(args.case_id)
            elif args.command == "history":
                store.load(args.case_id)
                result = [{"revision": (r := read_json(path / "plan.json"))["revision"],
                           "status": r["status"], "event": r["event"], "created_at": r["created_at"]}
                          for path in store.revisions(args.case_id)]
            elif args.command == "pdf":
                from pdf_export import export_pdf
                result = export_pdf(store, args.case_id, args.expected_revision)
            elif args.command == "export":
                result = {"exported": str(store.export(args.case_id, args.output))}
            else:
                record = store.write(args.case_id, "update" if args.command == "save" else args.command,
                                     plan=read_json(args.input) if hasattr(args, "input") else None,
                                     expected=getattr(args, "expected_revision", None),
                                     reason=getattr(args, "reason", None), candidate=getattr(args, "candidate", None),
                                     confirmation=read_json(args.confirmation) if hasattr(args, "confirmation") else None)
                # Read back both immutable files before reporting success.
                require(store.load(args.case_id) == record, "저장 후 재검증 실패")
                result = {"case_id": record["case_id"], "revision": record["revision"], "status": record["status"],
                          "plan_sha256": record["plan_sha256"],
                          "directory": str(store.case_path(args.case_id) / f"r{record['revision']:06d}")}
                if args.command == "finalize":
                    from pdf_export import export_pdf
                    result["pdf"] = export_pdf(store, args.case_id, record["revision"])
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return 0
    except (PlanError, OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    from portable import configure_stdio
    configure_stdio()
    sys.exit(main())
