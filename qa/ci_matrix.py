"""Select explicitly allowed disposable native QA runners and scenario groups."""
import argparse
import json
import os
from pathlib import Path
import sys


RUNNER_OSES = ('windows-2022', 'macos-15')
GROUPS = ('planning', 'finalize', 'camp', 'reuse')
DEFAULT_REQUEST = Path(__file__).resolve().with_name('live-request.json')


def selection(request, field, allowed):
    values = request.get(field, list(allowed))
    if (not isinstance(values, list) or not values or
            any(not isinstance(value, str) or value not in allowed for value in values)):
        raise ValueError(field + ' must be a nonempty list of allowed values')
    if len(values) != len(set(values)):
        raise ValueError(field + ' must not contain duplicates')
    return values


def build_matrix(request):
    if not isinstance(request, dict):
        raise ValueError('live request must be a JSON object')
    return {'os': selection(request, 'runner_oses', RUNNER_OSES),
            'group': selection(request, 'groups', GROUPS)}


def unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate request field')
        result[key] = value
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', type=Path, default=DEFAULT_REQUEST)
    args = parser.parse_args(argv)
    try:
        request = json.loads(args.request.read_text(encoding='utf-8'), object_pairs_hook=unique_keys)
        payload = json.dumps(build_matrix(request), separators=(',', ':'), ensure_ascii=True)
        output = os.environ.get('GITHUB_OUTPUT')
        if output:
            # Both axes have fixed allowlists: the value is one JSON line and
            # cannot inject another Actions output or select a self-hosted host.
            with Path(output).open('a', encoding='utf-8', newline='\n') as handle:
                handle.write('matrix=' + payload + '\n')
        print(payload)
    except (ValueError, OSError, UnicodeError) as error:
        print(str(error), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
