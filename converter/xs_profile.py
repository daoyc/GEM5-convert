"""Bind the reviewed KMHV3 architecture map to a supplied XS-GEM5 source tree."""

import json
import re
from collections import defaultdict
from pathlib import Path
from view_resources import PROFILES


ENTRY = "configs/example/kmhv3.py"
TEMPLATE = PROFILES / "kmhv3.json"
RETURN_TYPES = {"response", "reply", "return", "refill", "hit", "fault",
                "响应", "返回", "回填", "命中", "异常"}


def _normalized(line):
    return " ".join(line.split())


class _SourceFile:
    """Index real code lines; a reference line number alone cannot verify a mapping."""

    def __init__(self, source):
        self.lines = source.splitlines()
        self.positions = defaultdict(list)
        self.statements = []
        self.line_numbers = []
        self.assignments = defaultdict(list)
        for number, line in enumerate(self.lines, start=1):
            statement = _normalized(line)
            if not statement:
                continue
            index = len(self.statements)
            self.statements.append(statement)
            self.line_numbers.append(number)
            self.positions[statement].append(index)
            assignment = re.match(r"([\w.]+)\s*=(?!=)", statement)
            if assignment:
                self.assignments[assignment[1]].append(index)

    def locate(self, rule):
        matches = self.positions.get(_normalized(rule["text"]), [])
        # A tunable is identified by its field name even when its value changes.
        # An assignment with the same RHS elsewhere must not win on line proximity.
        if rule.get("assignment"):
            matches = self.assignments.get(rule["assignment"], [])
        if "before" in rule:
            before = [_normalized(s) for s in rule["before"]]
            after = [_normalized(s) for s in rule["after"]]
            matches = [i for i in matches
                       if self.statements[max(0, i-len(before)):i] == before and
                       self.statements[i+1:i+1+len(after)] == after]
        if len(matches) != 1:
            return None, "匹配不唯一" if matches else "未找到源码语句"
        number = self.line_numbers[matches[0]]
        return number, self.lines[number-1].strip()


def _resolve(root, template):
    anchors = defaultdict(list)
    for location, rule in template["anchors"].items():
        file, _ = location.rsplit(":", 1)
        anchors[file].append((location, rule))

    sources, evidence, warnings = {}, {}, []
    for file in sorted(set(anchors) | set(template["parameterFiles"])):
        try:
            source = (root / file).read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError) as error:
            reason = "无法读取文件" if isinstance(error, OSError) else "源文件编码无法识别"
            warnings.append(f"{file} · {reason}")
            for location, rule in anchors[file]:
                evidence[location] = dict(file=file, expected=rule["text"], unresolved=reason)
            continue

        sources[file] = source
        index = _SourceFile(source)
        for location, rule in anchors[file]:
            line, text = index.locate(rule)
            if line is None:
                warnings.append(f"{file} · {text} · {rule['text']}")
                evidence[location] = dict(file=file, expected=rule["text"], unresolved=text)
            else:
                evidence[location] = dict(file=file, line=line, text=text)

    return sources, evidence, warnings


def _attach(item, evidence):
    resolved = evidence[item["path"]]
    item["evidence"] = resolved
    if resolved.get("unresolved"):
        item["path"] = ""
    else:
        item["path"] = f"GEM5/{resolved['file']}:{resolved['line']}"


def _bind_graph(graph, evidence):
    graph_id = graph["id"]
    nodes = {node["id"]: node for node in graph["nodes"]}
    for node in nodes.values():
        _attach(node, evidence)
        node["kind"] = "architecture-module" if graph_id == "overview" else "component"

    pairs = {}
    for edge in graph["edges"]:
        _attach(edge, evidence)
        a, b = edge["a"], edge["b"]
        edge["id"] = f"{graph_id}/{a}/{b}"
        edge["kind"] = "logical-flow"
        pairs[a, b] = edge

    verified = []
    excluded = []
    for stream in graph["streams"]:
        _attach(stream, evidence)
        stream["origin"] = "源码演示"
        stream["viewId"] = graph_id
        complete = bool(stream["path"])
        for step in stream["steps"]:
            a, b = step["a"], step["b"]
            edge = pairs.get((a, b))
            if edge is None and step["type"].lower() in RETURN_TYPES:
                edge = pairs.get((b, a))
            if edge is None:
                complete = False
                continue
            step["edgeId"] = edge["id"]
            if step.get("path"):
                _attach(step, evidence)
            else:
                step["evidence"] = edge["evidence"]
                step["path"] = edge["path"]
            if not (step["path"] and edge["path"] and nodes[a]["path"] and nodes[b]["path"]):
                complete = False
        if complete:
            verified.append(stream)
        else:
            excluded.append(stream["name"])
    graph["streams"] = verified
    graph["excludedSources"] = excluded


def build_profile(root):
    """Construct the default single-core, non-trace view of configs/example/kmhv3.py.

    The template stores reviewed component/flow relationships and their code anchors.
    Each invocation resolves these against the caller's checkout and packages that
    checkout's source files. Missing or ambiguous anchors invalidate dependent demos.
    """
    template = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    sources, evidence, warnings = _resolve(Path(root), template)
    overview = template["overview"]
    modules = template["modules"]
    for graph in [overview, *modules.values()]:
        _bind_graph(graph, evidence)
        if graph["excludedSources"]:
            missing = "、".join(graph["excludedSources"])
            warnings.append(f"{graph['id']} · 源码依据不完整的场景 · {missing}")
    return dict(id="xs-dev.kmhv3", source=ENTRY, overview=overview, modules=modules,
                sources=sources, warnings=warnings,
                referenceRevision=template["referenceRevision"])

