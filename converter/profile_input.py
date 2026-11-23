"""Read a raw m5out config from stdin using the topology converter's readers."""
import configparser
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from semantics import runtime

def main():
    kind = sys.argv[1]
    with TemporaryDirectory() as directory:
        path = Path(directory, "config." + kind)
        path.write_bytes(sys.stdin.buffer.read())
        nodes, _, _ = runtime(path, {}, {})
    nodes = [dict(id=n["id"], fields={k: v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
                                      for k,v in n["fields"].items()}) for n in nodes]
    # The detailed view only needs instance paths and parameter fields.
    json.dump(dict(format="core-atlas/1", mode="instances", nodes=nodes), sys.stdout)

if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, UnicodeError, configparser.Error) as error:
        sys.exit(str(error))
