#!/usr/bin/env python3
"""Code-first six-criterion evaluation. Offline revisions and single-page PDF."""
import argparse, copy, hashlib, html, json, os, re, sys, tempfile
from pathlib import Path
from plan import PlanError, digest, require, safe_path, ident
from week3 import clean
from pdf_browser import print_pdf, PdfError
from portable import configure_stdio

CRITERIA = ('쓸 이유', '자료와 권한', '결과의 신뢰성', '이용 가능성', '업무 연결', '지속 사용')
KINDS = ('코드', '실행', '사용자 설명', '미확인')

def template():
    return dict(title='프로그램 이름', purpose='아직 모름', user='아직 모름', done_when='아직 모름',
                source='코드 경로·검토 범위', human='아직 모름', keep='아직 모름',
                criteria=[dict(name=n, judgment='아직 모름', evidence='미확인', basis='아직 확인하지 않음',
                               next='업무 설명 또는 코드 근거 확인', reviewed=False) for n in CRITERIA],
                actions=[dict(action='다음 확인을 참가자와 정하기', check='확인할 근거 정하기')])

def txt(v, maximum):
    require(isinstance(v,str) and bool(v.strip()) and len(v)<=maximum,'문장이 비었거나 길이 한도를 넘었습니다. 의미를 보존해 요약하세요.')
    clean(v)

def validate(d):
    require(isinstance(d,dict) and set(d)==set(template()),'평가서 필드 오류')
    for k in ('title','purpose','user','done_when','source','human','keep'):txt(d[k],60 if k=='title' else 150)
    require(isinstance(d['criteria'],list) and len(d['criteria'])==6,'여섯 기준 필요')
    for r,n in zip(d['criteria'],CRITERIA):
        require(set(r)=={'name','judgment','evidence','basis','next','reviewed'} and r['name']==n,'기준 이름/순서 오류')
        require(r['judgment'] in ('확인됨','부족함','아직 모름') and r['evidence'] in KINDS,'판정/근거 종류 오류')
        require(type(r['reviewed']) is bool,'검토 상태 오류')
        require(r['evidence']!='미확인' or r['judgment']=='아직 모름','미확인 근거로 확인/부족을 확정할 수 없습니다')
        txt(r['basis'],160);txt(r['next'],100)
    require(isinstance(d['actions'],list) and 1<=len(d['actions'])<=3,'다음 행동은 1~3개')
    for a in d['actions']:
        require(set(a)=={'action','check'},'행동 필드 오류');txt(a['action'],120);txt(a['check'],120)
    clean(d)

def read(p):
    p=safe_path(Path(p));require(p.stat().st_size<200000,'기록 크기 초과')
    return json.loads(p.read_text(encoding='utf-8'))

def load(root):
    files=sorted(root.glob('r*.json'))
    require(bool(files),'저장된 평가가 없습니다')
    previous=None
    r=None
    for i,p in enumerate(files,1):
        require(p.name==f'r{i:06d}.json','리비전 누락')
        r=read(p);validate(r['document'])
        require(r['revision']==i and r['previous']==previous,'리비전 연결 오류')
        require(r['digest']==digest(r['document']),'평가서 무결성 오류')
        require(r['status'] in ('draft','confirmed'),'상태 오류')
        if r['status']=='confirmed':
            require(all(x['reviewed'] for x in r['document']['criteria']),'검토 미완료')
            txt(r['confirmation'],400)
        previous=digest(r)
    assert r is not None
    return r

def save(root,d,confirmation=None,expected=None):
    validate(d);root.mkdir(parents=True,exist_ok=True)
    lock=safe_path(root/'.lock');lock.mkdir()
    try:
        prev=load(root) if list(root.glob('r*.json')) else None
        if confirmation is not None:
            require(prev is not None and prev['digest']==expected and prev['document']==d,'보여준 평가서 이후 변경됨; 재검토 필요')
            require(all(x['reviewed'] for x in d['criteria']),'여섯 기준을 검토한 뒤 확정하세요. 아직 모름도 검토 결과입니다.')
            txt(confirmation,400)
        r=dict(revision=prev['revision']+1 if prev else 1,previous=digest(prev) if prev else None,
               status='confirmed' if confirmation is not None else 'draft',document=d,digest=digest(d),confirmation=confirmation)
        with safe_path(root/f"r{r['revision']:06d}.json").open('x',encoding='utf-8') as f:json.dump(r,f,ensure_ascii=False,indent=2)
        return r
    finally:lock.rmdir()

def document(r):
    d=r['document'];e=lambda v:html.escape(str(v),quote=True)
    css=(Path(__file__).resolve().parents[1]/'assets/pdf/fonts.css').read_text(encoding='utf-8')
    rows=''.join('<tr><th>'+e(x['name'])+'</th><td><b>'+e(x['judgment'])+'</b><small>'+e(x['evidence'])+'</small></td><td>'+e(x['basis'])+'</td><td>'+e(x['next'])+'</td></tr>' for x in d['criteria'])
    actions=''.join('<li><b>'+e(a['action'])+'</b><br><span>확인 방법 · '+e(a['check'])+'</span></li>' for a in d['actions'])
    body=f'''<header>SPARKER <span>{'참가자 검토 완료' if r['status']=='confirmed' else '검토 전 초안'} · r{r['revision']}</span></header>
<h1>내 프로그램 업무 활용 평가서</h1><h2>{e(d['title'])}</h2>
<p><b>사용자</b> {e(d['user'])}<br><b>맡을 일</b> {e(d['purpose'])}<br><b>업무 완료 기준</b> {e(d['done_when'])}</p>
<p class="source">검토 범위 · {e(d['source'])}</p>
<table><colgroup><col style="width:16%"><col style="width:14%"><col style="width:38%"><col style="width:32%"></colgroup><thead><tr><th>기준</th><th>판단 / 근거</th><th>핵심 근거</th><th>남은 문제·다음 확인</th></tr></thead><tbody>{rows}</tbody></table>
<section><b>유지할 부분</b> {e(d['keep'])}<br><b>사람이 맡을 일</b> {e(d['human'])}</section>
<h3>다음 행동 — 우선순위순</h3><ol>{actions}</ol>
<footer>참가자의 업무 설명과 검토 범위에 따른 평가입니다. 검토 완료는 구현·운영 효과 검증 완료를 뜻하지 않습니다.</footer>'''
    style='''@page{size:A4;margin:14mm}*{box-sizing:border-box}body{width:182mm;margin:0;font-family:"Noto Sans KR Variable",sans-serif;color:#182934;font-size:10pt;line-height:1.5;overflow-wrap:anywhere}header{font-size:10pt;font-weight:800;color:#176052;border-bottom:2px solid #176052;padding-bottom:8px}header span{float:right;font-weight:400;color:#52626b}h1{font-size:22pt;margin:17px 0 3px}h2{font-size:14pt;margin:0 0 12px}p{margin:10px 0}.source,small{font-size:8pt;color:#576975}small{display:block}table{border-collapse:collapse;width:100%;table-layout:fixed;margin:15px 0}th,td{border-bottom:1px solid #d4dfe1;padding:9px 7px;vertical-align:top;text-align:left}thead{background:#eaf1ef;font-size:9pt}tbody th{font-size:10pt}td{font-size:9pt}section{padding:10px;background:#f1f5f4;font-size:9pt}h3{font-size:12pt;margin:16px 0 5px}ol{margin:0;padding-left:20px}li{margin:5px 0;font-size:9pt}footer{font-size:8pt;color:#576975;margin-top:14px;border-top:1px solid #d4dfe1;padding-top:8px}'''
    js='''window.__sparkerPdfReady=(async()=>{await document.fonts.ready;await new Promise(r=>requestAnimationFrame(r));let h=document.body.getBoundingClientRect().height;let w=document.documentElement.scrollWidth;let ok=h<=1015&&w<=794;return {ok,code:ok?null:'layout',height:h,width:w,one_page:true};})();'''
    return '<!doctype html><html lang="ko"><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; script-src \'unsafe-inline\'; font-src data:; connect-src \'none\'"><style>'+css+style+'</style><body>'+body+'<script>'+js+'</script></body></html>'

def export(root,r,refresh=False):
    require(r['status']=='confirmed','최종 PDF는 전체 평가서를 보여주고 참가자 확인 후 만듭니다')
    out=safe_path(root/f"pdf-r{r['revision']:06d}")
    require(not out.exists() or refresh,'PDF가 이미 있습니다. 기존 경로를 사용하세요')
    require(load(root)==r, '최신 평가서만 출력할 수 있습니다')
    text=document(r);pdf,observation=print_pdf(text,'<span></span>')
    with tempfile.TemporaryDirectory(prefix='.pdf-',dir=root) as tmp:
        p=Path(tmp);(p/'evaluation.pdf').write_bytes(pdf);(p/'evaluation.html').write_text(text,encoding='utf-8')
        (p/'receipt.json').write_text(json.dumps(dict(digest=r['digest'],sha256=hashlib.sha256(pdf).hexdigest(),renderer=observation),ensure_ascii=False),encoding='utf-8')
        if out.exists():
            # Explicit refresh renders the confirmed source again, never attests old bytes.
            for name in ('evaluation.pdf','evaluation.html','receipt.json'):
                os.replace(p/name,safe_path(out/name))
        else:p.rename(out)
    return dict(pdf=str(out/'evaluation.pdf'),html=str(out/'evaluation.html'),renderer=observation)

def main():
    configure_stdio();p=argparse.ArgumentParser();p.add_argument('--root',default='.sparker-evaluation');p.add_argument('--case',default='my-product')
    s=p.add_subparsers(dest='cmd',required=True);s.add_parser('template');s.add_parser('show');a=s.add_parser('save');a.add_argument('--file',required=True)
    a=s.add_parser('confirm');a.add_argument('--digest',required=True);a.add_argument('--statement',required=True);a=s.add_parser('pdf');a.add_argument('--refresh',action='store_true')
    a=p.parse_args()
    try:
        ident(a.case);root=safe_path(Path(a.root).absolute()/a.case)
        if a.cmd=='template':result=template()
        elif a.cmd=='save':result=save(root,read(a.file))
        elif a.cmd=='show':result=load(root)
        elif a.cmd=='confirm':result=save(root,load(root)['document'],a.statement,a.digest)
        else:result=export(root,load(root),a.refresh)
        print(json.dumps(result,ensure_ascii=False,indent=2))
    except (PlanError,PdfError,ValueError,OSError,KeyError,TypeError) as exc:
        print(json.dumps({'error':str(exc)},ensure_ascii=False));return 1
    return 0
if __name__=='__main__':sys.exit(main())
