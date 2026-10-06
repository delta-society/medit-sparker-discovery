#!/usr/bin/env python3
"""Selected Week 1/2 ZIP + confirmed Week 3 PDF catch-up submissions.

No recursive discovery, no fabrication of past work, no access to Camp credentials.
A reviewed JSON list pins each selected artifact by SHA before any network write.
"""
import argparse
import io
import json
from pathlib import Path
import re
import zipfile

import camp_submit as camp
import implementation as impl
import submission_bridge as bridge
from plan import require, safe_path
from portable import configure_stdio

NAMES = {1: 'week1-plan.zip', 2: 'week2-implementation.zip', 3: 'evaluation.pdf'}


def zip_artifact(path, week):
    path = safe_path(path)
    require(week in (1, 2), 'ZIP 제출은 1/2주차입니다')
    data = camp.stable_read(path, camp.MAX_ZIP)
    require(data.startswith(b'PK\x03\x04'), 'ZIP 파일이 필요합니다')
    if week == 1:
        result = camp.inspect(path)
        manifest = result['manifest']
        require(manifest['week'] == 1, '1주차 manifest가 아닙니다')
        require(not result['possible_secrets'], '민감정보 의심 파일은 검토 후 다시 준비하세요')
        revision = manifest['plan']['revision']
    else:
        # Reuse bounded archive/path checks; nothing is extracted or executed.
        impl.intake(path)
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            manifest = impl.parse(z.read('manifest.json'))
            require(set(manifest) == {'format', 'state', 'week', 'record_sha256', 'files'}, '2주차 manifest 필드 오류')
            require(manifest['format'] == 'sparker-week2-local-v1' and type(manifest['week']) is int
                    and manifest['week'] == 2 and manifest['state'] == 'prepared_locally_not_submitted', '2주차 manifest가 아닙니다')
            require(isinstance(manifest['record_sha256'], str) and re.fullmatch(r'[0-9a-f]{64}', manifest['record_sha256']), '구현 기록 해시 오류')
            files = manifest['files']
            require(isinstance(files, dict) and set(files) == set(z.namelist()) - {'manifest.json'}, '2주차 파일 목록 불일치')
            require('implementation.md' in files and any(Path(n).name.lower() == 'readme.md' for n in files), '보고서/README 필요')
            require(any(Path(n).suffix.lower() not in ('.md', '.txt', '.csv', '.json') for n in files), '구현 코드 필요')
            for name, digest in files.items():
                payload = z.read(name)
                impl.allowed(name, payload)
                require(camp.sha(payload) == digest, '2주차 파일 해시 불일치')
        revision = manifest['record_sha256']
    require(camp.stable_read(path, camp.MAX_ZIP) == data, '검사 중 파일 변경')
    return {'revision': revision}, data, dict(week=week, filename=NAMES[week], size=len(data), sha256=camp.sha(data))


def artifact(path, week):
    return bridge.current_pdf(path) if week == 3 else zip_artifact(path, week)


def inspect_items(items):
    require(isinstance(items, list) and 0 < len(items) <= 3, '선택한 1~3주차 목록이 필요합니다')
    seen = set()
    rows = []
    for item in items:
        require(isinstance(item, dict) and set(item) <= {'week', 'path', 'sha256'} and {'week', 'path'} <= set(item), '항목 필드 오류')
        week = item['week']
        require(type(week) is int and week in NAMES and week not in seen, '회차 중복/미지원. 회차마다 파일 하나를 선택하세요')
        seen.add(week)
        require(isinstance(item['path'], str) and Path(item['path']).is_absolute(), '명시한 절대 경로가 필요합니다')
        path = safe_path(item['path'])
        try:
            _, _, metadata = artifact(path, week)
            if 'sha256' in item:
                require(item['sha256'] == metadata['sha256'], '선택 후 파일이 바뀌었습니다. 다시 검토하세요')
            rows.append(dict(week=week, path=str(path), status='ready', **{k: metadata[k] for k in ('filename', 'size', 'sha256')}))
        except (ValueError, OSError, KeyError, TypeError, zipfile.BadZipFile, UnicodeError):
            rows.append(dict(week=week, path=str(path), status='blocked', message='해당 회차의 원본 기록·파일 형식·SHA를 확인하세요. 다른 회차는 계속할 수 있습니다.'))
    return sorted(rows, key=lambda row: row['week'])


def submit_items(items, *, consent=False, **options):
    require(consent, '선택한 회차·파일의 제출 요청이 필요합니다')
    # No TOFU at upload: SHA must have been exposed by inspect and reviewed.
    require(all(isinstance(i, dict) and isinstance(i.get('sha256'), str)
                and re.fullmatch(r'[0-9a-f]{64}', i['sha256']) for i in items), 'inspect 결과의 SHA로 제출 목록을 고정하세요')
    rows = inspect_items(items)
    for row in rows:
        if row['status'] != 'ready':
            continue
        week, expected = row['week'], row['sha256']
        def loader(path):
            result = artifact(path, week)
            require(result[2]['sha256'] == expected, '검토 후 파일 변경. 다시 검토하세요')
            return result
        try:
            result = bridge.submit(Path(row['path']), consent=True, scope=week, artifact_loader=loader, **options)
            if result['status'] == 'expired':
                result = bridge.submit(Path(row['path']), consent=True, scope=week, artifact_loader=loader, **options)
            row.update(result)
        except (ValueError, OSError, KeyError, TypeError, zipfile.BadZipFile, UnicodeError):
            row.update(status='blocked', message='접수 미확정. 해당 파일·주차 연결을 확인한 뒤 같은 목록으로 재개하세요.')
    return dict(status='submitted' if all(r['status'] == 'submitted' for r in rows) else 'incomplete', items=rows)


def main():
    configure_stdio()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('inspect', 'submit'))
    parser.add_argument('--items', required=True, help='회차/절대경로/검토 SHA 배열 JSON. 인증정보 아님')
    parser.add_argument('--submit', action='store_true')
    parser.add_argument('--origin', default=bridge.PRODUCTION)
    parser.add_argument('--local-test', action='store_true')
    parser.add_argument('--no-browser', action='store_true')
    parser.add_argument('--wait', type=float, default=120)
    parser.add_argument('--interval', type=float, default=2)
    parser.add_argument('--timeout', type=float, default=15)
    args = parser.parse_args()
    try:
        items = impl.parse(camp.stable_read(safe_path(args.items), 65536))
        if args.action == 'inspect':
            result = dict(status='inspected_not_submitted', items=inspect_items(items))
        else:
            result = submit_items(items, consent=args.submit, base=args.origin, local_test=args.local_test,
                                  no_browser=args.no_browser, wait=args.wait, interval=args.interval, timeout=args.timeout)
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result['status'] in ('submitted', 'inspected_not_submitted') else 2
    except (ValueError, OSError, KeyError, TypeError, zipfile.BadZipFile, UnicodeError):
        print(json.dumps(dict(status='blocked', message='선택 목록·회차·파일을 다시 확인하세요. 원본과 기존 접수는 보존됩니다.'), ensure_ascii=False))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
