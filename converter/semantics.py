"""Evidence and stable identities for the Core Atlas graph."""
import ast
import hashlib
import json
import re
from collections import defaultdict
import tokenize


def identity(*parts):
    data = json.dumps(parts, ensure_ascii=False, separators=(",", ":")).encode()
    return hashlib.sha256(data).hexdigest()[:32]


def relation(kind, a, b, label, evidence, **extra):
    return dict(id=identity(kind, a, b, label), kind=kind, a=a, b=b, label=label,
                evidence=evidence, **extra)


def location(file, node, lines):
    return dict(file=file, line=node.lineno, text=lines[node.lineno-1].strip())


def declarations(root, nodes, old_edges):
    names = defaultdict(list)
    for n in nodes:
        names[n["name"]].append(n["id"])
    edges, parents, local = {}, defaultdict(list), {}
    bases = [(a, b) for a, b, label in old_edges if label == "继承"]
    for a, b in bases:
        parents[a].append(b)
    files = defaultdict(dict)
    for n in nodes:
        files[n["source"].rsplit(":", 1)[0]][n["name"]] = n
    for file, group in files.items():
        with tokenize.open(root/file) as stream:
            source = stream.read()
        lines = source.splitlines()
        for cls in ast.parse(source).body:
            if not isinstance(cls, ast.ClassDef) or cls.name not in group:
                continue
            n = group[cls.name]
            n.update(kind="declaration", evidence=location(file, cls, lines))
            params = local[n["id"]] = {}
            def link(kind, target, label, ev):
                edge = relation(kind, n["id"], target, label, ev)
                edges[edge["id"]] = edge
            for base in cls.bases:
                name = ast.unparse(base).split(".")[-1]
                for target in parents[n["id"]]:
                    if target in names[name]:
                        link("inheritance", target, "继承", location(file, base, lines))
            fields = {item.targets[0].id: item.value for item in cls.body
                      if isinstance(item, ast.Assign) and len(item.targets)==1
                      and isinstance(item.targets[0], ast.Name)}
            for key, val in fields.items():
                ev = location(file, val, lines)
                param = isinstance(val, ast.Call) and ast.unparse(val.func).startswith(("Param.", "VectorParam."))
                if param or key not in ("type", "cxx_class", "cxx_header"):
                    default = val.args[0] if param and len(val.args)>1 else val
                    params[key] = dict(value=None if param and len(val.args)==1 and isinstance(val.args[0], ast.Constant) and isinstance(val.args[0].value,str) else ast.unparse(default), evidence=ev)
                    if any(isinstance(v,(ast.Subscript,ast.IfExp,ast.ListComp)) for v in ast.walk(val)):
                        params[key]["unresolved"] = ast.unparse(val)
                for child in ast.walk(val):
                    if isinstance(child, ast.Call):
                        target = ast.unparse(child.func).split(".")[-1]
                        if len(names[target]) == 1:
                            link("declaration-reference", names[target][0], key, location(file, child, lines))
                    if isinstance(child, ast.Attribute) and isinstance(child.value, ast.Name) and child.value.id=="Parent":
                        sibling = fields.get(child.attr)
                        if isinstance(sibling, ast.Call) and len(names[ast.unparse(sibling.func)])==1 and child is not val:
                            link("declaration-reference", names[ast.unparse(sibling.func)][0],
                                 key+" → Parent."+child.attr, location(file, child, lines))
                        elif child is not val and isinstance(sibling,ast.Constant):
                            params.setdefault(key,{})["parentValue"]=dict(value=sibling.value,evidence=location(file,sibling,lines))
                        else:
                            params.setdefault(key, {})["unresolved"] = ast.unparse(child)
    for n in nodes:
        # Store references to declaring nodes so inherited fields keep their origin.
        lineage, seen = [], set()
        def visit(uid):
            if uid in seen:
                return
            seen.add(uid)
            lineage.append(uid)
            for parent in parents[uid]:
                visit(parent)
        visit(n["id"])
        n.update(parameters=local[n["id"]], lineage=lineage)
    return list(edges.values())


def endpoint(path, port):
    match = re.fullmatch(r"(.+?)\[(\d+)\]", port)
    return dict(path=path, port=match[1] if match else port,
                index=int(match[2]) if match else None)


def port_edge(a, b, evidence):
    label = lambda end: end["port"] + (f'[{end["index"]}]' if end["index"] is not None else "")
    edge = relation("port", a["path"], b["path"], label(a)+" → "+label(b), evidence,
                    sourcePort=a, targetPort=b)
    edge["id"] = "port:" + json.dumps([a["path"],a["port"],a["index"],b["path"],b["port"],b["index"]], ensure_ascii=False,separators=(",",":"))
    return edge


def runtime(file, declarations_by_id, by_type):
    import configparser
    nodes, edges, diagnostics = {}, {}, []
    ini = file.suffix.lower()==".ini"
    def visit(obj, parent=None):
        path = obj["path"]
        if not isinstance(path,str) or path in nodes:
            raise ValueError(f"重复或无效的实例路径 {path}")
        fields = {}
        matches = by_type.get(obj["type"], [])
        uid = matches[0] if len(matches)==1 else None
        evidence = dict(file=file.name, path=path, origin="运行实例")
        n = nodes[path] = dict(id=path, name=path, kind="instance", fields=fields,
                               evidence=evidence, declaration=uid, ports={})
        if parent is not None:
            e = relation("containment", parent, path, "包含", evidence)
            edges[e["id"]] = e
        for key, value in obj.items():
            if isinstance(value, dict) and "peer" in value:
                peers = value["peer"]
                vector = isinstance(peers, list)
                for i, peer in enumerate(peers if vector else [peers]):
                    owner, dot, port = str(peer).rpartition(".")
                    if not dot:
                        diagnostics.append(f"{path}.{key}: 未解析对端 {peer}")
                        continue
                    a = endpoint(path, f"{key}[{i}]" if vector else key)
                    b = endpoint(owner, port)
                    if str(value.get("is_source")).lower()=="false":
                        a,b=b,a
                    elif str(value.get("is_source")).lower()!="true":
                        diagnostics.append(f"{path}.{key}: 方向未知")
                        continue
                    ev = dict(evidence, key=key, declaration=uid, direction="源码端口推断" if ini else "config.json")
                    e = port_edge(a,b,ev)
                    edges[e["id"]] = e
            else:
                items = value if isinstance(value,list) else [value]
                children = [v for v in items if isinstance(v,dict) and {"type","path"}<=v.keys()]
                if children:
                    for child in children:
                        visit(child,path)
                else:
                    fields[key] = value
    if ini:
        cfg=configparser.ConfigParser(interpolation=None,delimiters=("=",))
        cfg.optionxform=str
        cfg.read(file,encoding="utf-8-sig")
        for path in cfg.sections():
            obj=dict(cfg[path])
            if "type" not in obj:
                continue
            matches=by_type.get(obj["type"],[])
            if len(matches)==1:
                decl=declarations_by_id[matches[0]]
                for base in decl["lineage"]:
                    for key,kind in declarations_by_id[base]["ports"].items():
                        if isinstance(obj.get(key),str):
                            raw=obj[key]
                            obj[key]=dict(peer=raw.split() if "Vector" in kind else raw,
                                          is_source=True if any(t in kind for t in ("Request","Master")) else
                                          False if any(t in kind for t in ("Response","Slave")) else None)
            visit(dict(obj,path=path))
            for child in obj.get("children","").split():
                target=("" if path=="root" else path+".")+child
                if cfg.has_section(target):
                    e=relation("containment",path,target,"包含",nodes[path]["evidence"])
                    edges[e["id"]]=e
    else:
        obj=json.loads(file.read_text(encoding="utf-8-sig"))
        if not isinstance(obj,dict) or not {"type","path"}<=obj.keys():
            raise ValueError("config.json 缺少实例根对象")
        visit(obj)
    if not nodes:
        raise ValueError("未找到配置实例")
    return list(nodes.values()),list(edges.values()),diagnostics


