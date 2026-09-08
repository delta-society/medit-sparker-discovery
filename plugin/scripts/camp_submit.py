#!/usr/bin/env python3
"""Prepare an inspectable Camp assignment for the existing participant app.

Local only, Python 3.9+ standard library. Never reads auth configuration, modifies
hooks, uploads data or claims that preparation is a server submission receipt.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import sys
import uuid
import zipfile

from plan import PlanError, Store, canonical, no_duplicates, require, safe_path

APP_URL = "https://leaderboard-production-eac2.up.railway.app/"
FORMAT = "sparker-camp-submission-v1"
MAX_ZIP = 5 * 1024 * 1024
MAX_FILE = 20 * 1024 * 1024
MAX_TOTAL = 50 * 1024 * 1024
MAX_SESSIONS = 32
MAX_MANIFEST = 128 * 1024
SECRET_PATTERNS = {
    "private-key": rb"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----",
    "github-token": rb"(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})",
    "api-key": rb"\bsk-(?:ant-|proj-)?[A-Za-z0-9_-]{20,}",
    "aws-access-key": rb"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b",
    "bearer-token": rb"\bBearer\s+[A-Za-z0-9._~+/=-]{20,}",
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def json_bytes(value):
    return (canonical(value) + "\n").encode("utf-8")


def read_object(data):
    value = json.loads(data.decode("utf-8"), object_pairs_hook=no_duplicates,
                      parse_constant=lambda _: (_ for _ in ()).throw(PlanError("비유한 JSON 수")))
    require(isinstance(value, dict), "JSON 객체가 필요합니다")
    return value


def stable_read(path, limit=MAX_FILE):
    path = safe_path(path)
    require(path.is_file(), "파일이 없습니다: " + str(path))
    before = path.stat()
    require(0 < before.st_size <= limit, "파일 크기 한도 초과 또는 빈 파일: " + path.name)
    with path.open("rb") as handle:
        data = handle.read(limit + 1)
        after = os.fstat(handle.fileno())
    key = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
    require(len(data) <= limit and key(before) == key(after) == key(path.stat()),
            "읽는 동안 파일이 바뀌었습니다. 기록이 멈춘 뒤 다시 준비하세요: " + path.name)
    return data


def session_id(value):
    require(isinstance(value, str), "세션 ID가 필요합니다")
    try:
        normalized = str(uuid.UUID(value))
    except (ValueError, AttributeError):
        raise PlanError("세션 ID는 UUID여야 합니다") from None
    require(normalized == value.lower(), "세션 ID 형식을 확인하세요")
    return normalized


def read_session(path, project):
    path = safe_path(path)
    require(path.suffix == ".jsonl", "세션 기록은 JSONL 파일이어야 합니다")
    sid = session_id(path.stem)
    data = stable_read(path)
    records = validate_session(data, sid, os.path.normcase(str(safe_path(project))))
    return sid, data, records


def validate_session(data, sid, expected_cwd=None):
    matched_id = matched_cwd = False
    records = 0
    for number, line in enumerate(data.splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = read_object(line)
        except (ValueError, UnicodeError):
            raise PlanError(f"세션 {sid}의 {number}번째 줄이 불완전하거나 잘못된 JSON입니다. 원본을 자르지 않고 중단합니다") from None
        records += 1
        if "sessionId" in row:
            require(row["sessionId"] == sid, "파일명과 세션 ID가 다르거나 여러 세션이 섞여 있습니다")
            matched_id = True
        if "cwd" in row:
            cwd = row["cwd"]
            require(isinstance(cwd, str) and (PurePosixPath(cwd).is_absolute() or PureWindowsPath(cwd).is_absolute()),
                    "세션 작업 폴더를 확인할 수 없습니다")
            if expected_cwd is not None:
                require(os.path.normcase(os.path.abspath(cwd)) == expected_cwd,
                        "선택한 프로젝트 밖의 대화가 포함되어 있습니다. 해당 세션은 제외하거나 운영진에게 확인하세요")
            matched_cwd = True
    require(records and matched_id and matched_cwd, "세션 ID와 작업 폴더 근거가 모두 있는 Claude Code 원본이 필요합니다")
    return records


def candidates(project, directory=None):
    """List filenames/sizes only, never recursively scan the user's projects."""
    project = safe_path(project)
    if directory is not None:
        folders = [safe_path(directory)]
    else:
        # These are location hints, not proof of project membership. prepare
        # verifies the actual cwd fields before including any transcript.
        slugs = {re.sub(r"[^A-Za-z0-9]", "-", str(project)),
                 re.sub(r"[/\\.]", "-", str(project))}
        folders = [safe_path(Path.home() / ".claude" / "projects" / slug) for slug in sorted(slugs)]
    result = []
    for folder in folders:
        if not folder.is_dir():
            continue
        for path in sorted(folder.glob("*.jsonl")):
            safe_path(path)
            if not path.is_file():
                continue
            try:
                sid = session_id(path.stem)
            except PlanError:
                continue
            stat = path.stat()
            result.append({"session_id": sid, "path": str(path), "bytes": stat.st_size,
                           "modified_at_unix": stat.st_mtime})
    return {"project": str(project), "sessions": result,
            "scope": "선택한 프로젝트의 최상위 후보 파일만. 다른 프로젝트·subagent 폴더는 탐색하지 않음",
            "membership_verified": False,
            "note": "수정 시각은 회차 소속의 근거가 아닙니다. 포함할 세션을 직접 선택하세요. 없으면 해당 세션 기록 폴더를 지정하세요."}


def secret_findings(files):
    return [{"file": name, "kind": kind, "matches": len(re.findall(pattern, data))}
            for name, data in files.items() for kind, pattern in SECRET_PATTERNS.items()
            if re.search(pattern, data)]


def make_zip(files):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100600 << 16
            archive.writestr(info, data)
    return stream.getvalue()


def prepare(root, case, expected_revision, week, project, sessions, output, include_raw=False):
    require(type(week) is int and 1 <= week <= 4, "캠프 회차는 1~4입니다")
    require(type(expected_revision) is int and expected_revision > 0, "검토할 기획서 리비전을 지정하세요")
    require(len(sessions) <= MAX_SESSIONS, "세션은 최대 32개까지 선택할 수 있습니다")
    require(not sessions or include_raw, "원본 대화·실행 기록 포함을 선택한 경우에만 --include-session-records를 사용하세요")
    require(not include_raw or sessions, "포함할 세션 파일을 선택하세요")
    record = Store(root).load(case)
    require(record["revision"] == expected_revision, "기획서 리비전이 바뀌었습니다. 최신 내용을 확인한 뒤 다시 준비하세요")
    plan_path = safe_path(Path(root) / case / f"r{expected_revision:06d}" / "plan.md")
    from plan import markdown
    plan_bytes = markdown(record).encode("utf-8")
    require(stable_read(plan_path) == plan_bytes, "기획서가 읽는 동안 바뀌었습니다")
    files = {"plan.md": plan_bytes}
    session_refs = []
    ids = set()
    total = len(plan_bytes)
    for path in sessions:
        sid, data, count = read_session(path, project)
        require(sid not in ids, "같은 세션이 두 번 선택되었습니다")
        ids.add(sid)
        total += len(data)
        require(total <= MAX_TOTAL, "원본 합계는 50 MiB 이하만 준비할 수 있습니다. 세션을 줄이거나 운영진에게 전달 방법을 확인하세요")
        name = "sessions/" + sid + ".jsonl"
        files[name] = data
        session_refs.append({"session_id": sid, "file": name, "records": count})
    manifest = {
        "format": FORMAT, "week": week,
        "plan": {"case_id": case, "revision": expected_revision,
                 "status": record["status"], "plan_sha256": record["plan_sha256"]},
        "sessions": sorted(session_refs, key=lambda row: row["session_id"]),
        "files": [{"path": name, "bytes": len(data), "sha256": sha(data)} for name, data in sorted(files.items())],
        "raw_session_records": bool(sessions),
        "scope": "선택한 세션의 준비 시점 원본. 다른 세션·subagent·외부 첨부 파일은 포함하지 않음",
        "identity_source": "participant-app-authenticated-session",
    }
    manifest["bundle_id"] = sha(json_bytes(manifest))
    files["manifest.json"] = json_bytes(manifest)
    archive = make_zip(files)
    require(len(archive) <= MAX_ZIP,
            f"압축 후 {len(archive):,} bytes로 참가자 앱의 5 MiB 한도를 초과합니다. 원본은 자르지 않습니다. 세션 선택을 줄이거나 운영진에게 전달 방법을 확인하세요")
    target = safe_path(output)
    require(target.suffix == ".zip", "제출 파일의 확장자는 .zip이어야 합니다")
    require(target not in [safe_path(p) for p in sessions] and target != plan_path, "원본 경로에 출력할 수 없습니다")
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    # An identical retry can reuse the same exact artifact. Different bytes must
    # get a new filename; exclusive creation also prevents concurrent overwrite.
    reused = False
    try:
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        require(stable_read(target, MAX_ZIP) == archive, "다른 제출 파일이 이미 있습니다. 새 출력 파일명을 사용하세요")
        reused = True
    else:
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(archive)
                handle.flush()
                os.fsync(handle.fileno())
        except BaseException:
            target.unlink(missing_ok=True)
            raise
    report = inspect(target)
    report["reused"] = reused
    return report


def inspect(path):
    data = stable_read(path, MAX_ZIP)
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        entries = archive.infolist()
        names = [entry.filename for entry in entries]
        require(2 <= len(names) <= MAX_SESSIONS + 2 and len(names) == len(set(names)), "파일 수 또는 중복 경로 오류")
        require("manifest.json" in names and "plan.md" in names, "기획서와 manifest가 필요합니다")
        for entry in entries:
            require(entry.filename in ("plan.md", "manifest.json") or re.fullmatch(r"sessions/[0-9a-f-]{36}\.jsonl", entry.filename), "허용하지 않는 ZIP 경로")
            require(not entry.flag_bits & 1 and (entry.external_attr >> 16) & 0o170000 != 0o120000,
                    "암호화·심볼릭 링크 항목은 허용하지 않습니다")
            require(entry.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED), "지원하지 않는 압축 방식")
            limit = MAX_MANIFEST if entry.filename == "manifest.json" else MAX_FILE
            require(0 < entry.file_size <= limit, "압축 해제 크기 제한 초과")
        require(sum(e.file_size for e in entries) <= MAX_TOTAL + MAX_MANIFEST, "압축 해제 합계 제한 초과")
        manifest = read_object(archive.read("manifest.json"))
        require(manifest.get("format") == FORMAT, "지원하지 않는 제출 형식")
        require(set(manifest) == {"format", "week", "plan", "sessions", "files", "raw_session_records", "scope", "identity_source", "bundle_id"}, "manifest 필드 오류")
        without_id = {k: v for k, v in manifest.items() if k != "bundle_id"}
        require(manifest["bundle_id"] == sha(json_bytes(without_id)), "제출 묶음 해시 불일치")
        require(type(manifest["week"]) is int and 1 <= manifest["week"] <= 4, "회차 오류")
        from plan import ident
        plan_ref = manifest["plan"]
        require(isinstance(plan_ref, dict) and set(plan_ref) == {"case_id", "revision", "status", "plan_sha256"}, "기획서 참조 오류")
        ident(plan_ref["case_id"])
        require(type(plan_ref["revision"]) is int and plan_ref["revision"] > 0 and plan_ref["status"] in ("draft", "finalized"), "기획서 상태 오류")
        require(isinstance(plan_ref["plan_sha256"], str) and re.fullmatch(r"[0-9a-f]{64}", plan_ref["plan_sha256"]), "기획서 해시 형식 오류")
        require(manifest["identity_source"] == "participant-app-authenticated-session", "신원 출처 오류")
        require(isinstance(manifest["files"], list), "파일 목록 오류")
        payloads = {}
        for file in manifest["files"]:
            require(isinstance(file, dict) and set(file) == {"path", "bytes", "sha256"}, "파일 항목 오류")
            name = file["path"]
            require(isinstance(name, str) and name in names and name != "manifest.json" and name not in payloads, "파일 목록 불일치")
            contents = archive.read(name)
            require(type(file["bytes"]) is int and len(contents) == file["bytes"] and sha(contents) == file["sha256"], "제출 파일 해시 불일치")
            payloads[name] = contents
        require(set(payloads) == set(names) - {"manifest.json"}, "목록 밖 파일이 있습니다")
        sessions = manifest["sessions"]
        require(isinstance(sessions, list) and len(sessions) <= MAX_SESSIONS, "세션 목록 오류")
        session_files = set()
        for row in sessions:
            require(isinstance(row, dict) and set(row) == {"session_id", "file", "records"}, "세션 참조 오류")
            sid = session_id(row["session_id"])
            name = "sessions/" + sid + ".jsonl"
            require(row["file"] == name and name in payloads and name not in session_files, "세션 파일 참조 오류")
            require(type(row["records"]) is int and row["records"] > 0, "세션 기록 수 오류")
            require(validate_session(payloads[name], sid) == row["records"], "세션 기록 수 불일치")
            session_files.add(name)
        require(session_files == set(payloads) - {"plan.md"}, "세션 목록과 실제 파일 불일치")
        require(type(manifest["raw_session_records"]) is bool and manifest["raw_session_records"] == bool(sessions), "원본 포함 표시 불일치")
        findings = secret_findings(payloads)
    return {"state": "prepared_locally_not_submitted", "path": str(safe_path(path)),
            "bytes": len(data), "sha256": sha(data), "manifest": manifest,
            "possible_secrets": findings,
            "review_note": "기획서와 선택한 대화·실행 기록은 마스킹 없이 포함됩니다. 탐지는 일부 키 패턴만 확인하며 개인정보·기밀 부재를 보장하지 않습니다." if sessions else "기획서 내용과 회차를 확인하세요. 내부 JSON·대화 원본은 포함하지 않았습니다.",
            "submit_url": APP_URL,
            "next_action": "파일 내용을 확인한 뒤 참가자 앱에 로그인해 같은 주차 과제로 업로드하세요. 서버가 표시하는 제출 기록을 확인해야 제출 완료입니다. 재업로드는 새 제출 이력이 됩니다."}


def main():
    parser = argparse.ArgumentParser(description="Sparker Camp 기획서·선택 세션 제출 묶음 (로컬 준비, 자동 전송 없음)")
    sub = parser.add_subparsers(dest="command", required=True)
    listing = sub.add_parser("sessions", help="현재 프로젝트의 세션 파일 후보만 표시")
    listing.add_argument("--project", default=str(Path.cwd()))
    listing.add_argument("--directory", help="알려진 Claude Code 프로젝트 기록 폴더")
    prep = sub.add_parser("prepare", help="검증한 기획서와 선택한 원본을 ZIP으로 준비")
    prep.add_argument("--root", default=".sparker-discovery")
    prep.add_argument("--case", required=True)
    prep.add_argument("--expected-revision", type=int, required=True)
    prep.add_argument("--week", type=int, required=True)
    prep.add_argument("--project", default=str(Path.cwd()))
    prep.add_argument("--session-file", action="append", default=[])
    prep.add_argument("--include-session-records", action="store_true")
    prep.add_argument("--output", required=True)
    check = sub.add_parser("inspect", help="ZIP을 풀지 않고 파일 목록·해시·범위를 다시 확인")
    check.add_argument("path")
    args = parser.parse_args()
    try:
        if args.command == "sessions":
            result = candidates(args.project, args.directory)
        elif args.command == "prepare":
            result = prepare(args.root, args.case, args.expected_revision, args.week, args.project,
                             args.session_file, args.output, args.include_session_records)
        else:
            result = inspect(args.path)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (PlanError, OSError, ValueError, TypeError, KeyError, zipfile.BadZipFile, RuntimeError) as exc:
        # JSON parse errors include positions, not raw document contents.
        print(json.dumps({"state": "failed", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    from portable import configure_stdio
    configure_stdio()
    sys.exit(main())
