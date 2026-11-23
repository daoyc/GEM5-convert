"""Hash every supplied source file, without writing to either checkout."""
import hashlib
import json
import sys
from pathlib import Path

def digest(root):
    h = hashlib.sha256()
    count = 0
    size = 0
    for f in sorted(root.rglob('*')):
        if not f.is_file() or '.git' in f.relative_to(root).parts:
            continue
        data = f.read_bytes()
        h.update(f.relative_to(root).as_posix().encode() + b'\0' + hashlib.sha256(data).digest())
        count += 1
        size += len(data)
    return dict(files=count, bytes=size, sha256=h.hexdigest())

if __name__ == '__main__':
    result = {str(root):digest(root) for root in map(Path,sys.argv[2:])}
    target = Path(sys.argv[1])
    if target.exists():
        if json.loads(target.read_text(encoding='utf8')) != result:
            raise SystemExit('Input tree changed')
        print('Input hashes match')
    else:
        target.write_text(json.dumps(result, indent=2), encoding='utf8')
        print(result)

