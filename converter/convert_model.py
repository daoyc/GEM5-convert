"""Extract declared gem5 SimObjects and optional instantiated topology without running model code."""
import argparse
import ast
import json
import os
import tempfile
import tokenize
import warnings as python_warnings
from collections import defaultdict
from pathlib import Path


def symbol(node):
    return ast.unparse(node).rsplit(".", 1)[-1]


def scan(root):
    classes = {}
    names = defaultdict(list)
    warnings = []
    for directory, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if not d.startswith(".") and d not in
                         {"build", "build_opts", "ext", "node_modules", "__pycache__", "m5out"})
        for filename in sorted(files):
            if not filename.endswith(".py"):
                continue
            file = Path(directory, filename)
            relative = file.relative_to(root).as_posix()
            try:
                with tokenize.open(file) as stream:
                    tree = ast.parse(stream.read(), filename=relative)
            except (SyntaxError, UnicodeError, OSError) as exc:
                warnings.append(f"{relative}: {exc}")
                continue
            for cls in (c for c in tree.body if isinstance(c, ast.ClassDef)):
                uid = f"{relative}:{cls.name}"
                fields = {}
                for item in cls.body:
                    if isinstance(item, ast.Assign) and len(item.targets) == 1 and isinstance(item.targets[0], ast.Name):
                        fields[item.targets[0].id] = item.value
                classes[uid] = (cls, fields, relative)
                names[cls.name].append(uid)

    memo = {}
    def is_model(uid, visiting):
        if uid in memo:
            return memo[uid]
        if uid in visiting:
            return False
        cls, fields, _ = classes[uid]
        found = (("cxx_class" in fields or cls.name == "SimObject") and "type" in fields and isinstance(fields["type"], ast.Constant) and
                 isinstance(fields["type"].value, str)) or any(
            symbol(b) == "SimObject" or any(is_model(i, visiting | {uid}) for i in names.get(symbol(b), []))
            for b in cls.bases)
        memo[uid] = found
        return found

    nodes, links = [], []
    by_type = defaultdict(list)
    for uid, (cls, fields, relative) in classes.items():
        if not is_model(uid, set()):
            continue
        details, ports = {}, {}
        def connect(name, label):
            candidates = [i for i in names.get(name, []) if is_model(i, set())]
            if len(candidates) == 1 and candidates[0] != uid:
                links.append([uid, candidates[0], label])
        for base in cls.bases:
            connect(symbol(base), "继承")
        for key, val in fields.items():
            if isinstance(val, ast.Call):
                func = symbol(val.func)
                if func.endswith("Port"):
                    ports[key] = func
                connect(func, key)
            details[key] = ast.unparse(val)[:240]
        typ = fields.get("type")
        if isinstance(typ, ast.Constant) and isinstance(typ.value, str):
            by_type[typ.value].append(uid)
        nodes.append(dict(id=uid, name=cls.name, source=f"{relative}:{cls.lineno}",
                          fields=details, ports=ports))
    return nodes, links, by_type, warnings


def standalone_browser(model):
    from view_resources import VIEW as directory
    page = (directory / "models.html").read_text(encoding="utf-8-sig")
    for filename in ("models.css", "viewer.css"):
        css = (directory / filename).read_text(encoding="utf-8-sig")
        page = page.replace(f'<link rel="stylesheet" href="{filename}">', "<style>"+css+"</style>")
    for filename in ("models.js", "coverage.js", "atlas.js"):
        script = (directory / filename).read_text(encoding="utf-8-sig")
        page = page.replace(f'<script src="{filename}"></script>', "<script>"+script+"</script>")
    payload = json.dumps(model, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    return page.replace("<!--model-->", '<script type="application/json" id="embedded">'+payload+"</script>")


def main(single_html=False):
    from semantics import declarations, runtime
    from xiangshan import ENTRY, profile
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--name")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--instance", help="CPU or system instance path")
    parser.add_argument("--entry", help="architecture configuration relative to root")
    parser.add_argument("--set", action="append", default=[], metavar="OPTION=VALUE")
    parser.add_argument("--html", type=Path, help="generate a standalone viewer")
    parser.add_argument("-o","--output",type=Path,help="output model JSON (optional)")
    parser.add_argument("--through-round",type=int,choices=range(0,11),default=10,
                        help="reproduce a cumulative Xiangshan mapping checkpoint (default: final)")
    args=parser.parse_args()
    root=args.root.resolve()
    if single_html and args.output is None and args.html is None:
        args.html = Path.cwd() / (root.name + ".html")
    if args.output is None and args.html is None:
        from view_resources import VIEW as directory
        args.html = directory / (root.name + ".html")
        args.output = directory / "models" / (root.name + ".json")
        if args.html.exists() and root.name.casefold() == "models":
            parser.error("请用 --html 指定独立页文件名，以免覆盖浏览器入口")
    from xs_parameters import ENTRY as XS_ENTRY
    if args.entry:
        candidate = root / args.entry
        try:
            entry = candidate.resolve().relative_to(root).as_posix()
        except ValueError:
            parser.error("配置入口必须位于输入源码目录内")
    else:
        entry = next((name for name in (XS_ENTRY, ENTRY) if (root/name).is_file()), None)
    if args.output and args.html and args.output.resolve() == args.html.resolve():
        parser.error("JSON 和 HTML 需要不同的输出路径")
    nodes, old, types, warnings=scan(root)
    if not nodes:
        parser.error("未找到 SimObject 声明")
    edges=declarations(root,nodes,old)
    settings={}
    for item in args.set:
        key,sep,value=item.partition("=")
        if not sep:
            parser.error("--set requires OPTION=VALUE")
        settings[key.lstrip("-").replace("-","_")] = {"true":True,"false":False}.get(value.lower(),value)
    view=profile(root,settings,args.through_round) if entry==ENTRY and (root/ENTRY).is_file() else None
    is_xs = entry == XS_ENTRY and (root/entry).is_file()
    if entry and not view and not is_xs:
        warnings.append("没有匹配的架构映射 "+entry)
    instances,connections=[],[]
    if args.config:
        try:
            instances,connections,issues=runtime(args.config,{n["id"]:n for n in nodes},types)
        except (KeyError,ValueError,OSError) as error:
            parser.error(str(error))
        warnings.extend(issues)
        if args.instance and args.instance not in {n["id"] for n in instances}:
            parser.error("实例路径不存在")
        if args.instance:
            children=defaultdict(list)
            for edge in connections:
                if edge["kind"]=="containment":
                    children[edge["a"]].append(edge["b"])
            selected=set()
            pending=[args.instance]
            while pending:
                path=pending.pop()
                if path not in selected:
                    selected.add(path)
                    pending.extend(children[path])
            connections=[edge for edge in connections if
                         (edge["a"] in selected and edge["b"] in selected) or
                         (edge["kind"]=="port" and (edge["a"] in selected or edge["b"] in selected))]
            boundary={edge[k] for edge in connections for k in ("a","b")} - selected
            instances=[n for n in instances if n["id"] in selected or n["id"] in boundary]
            for n in instances:
                n["boundary"]=n["id"] in boundary
    data=dict(format="core-atlas/2",name=args.name or root.name,nodes=nodes,edges=edges,
              instances=instances,connections=connections,view=view,scope=args.instance,
              config=args.config.name if args.config else None,warnings=warnings)
    # Embed short source excerpts once per location, also for offline inspection.
    import linecache
    excerpts={}
    def collect(value):
        if isinstance(value,list):
            for child in value:
                collect(child)
        elif isinstance(value,dict):
            file,line=value.get("file"),value.get("line")
            if isinstance(file,str) and isinstance(line,int):
                key=f"{file}:{line}"
                if key not in excerpts and (root/file).is_file():
                    lines=linecache.getlines(str(root/file))
                    excerpts[key]="\n".join(f"{i:5}  {lines[i-1].rstrip()}" for i in range(max(1,line-2),min(len(lines),line+2)+1))
            else:
                for child in value.values():
                    collect(child)
    collect(data)
    data["excerpts"]=excerpts
    if is_xs:
        from xs_profile import build_profile
        from xs_parameters import source_parameters
        data["architecture"] = build_profile(root)
        data["sourceParameters"] = source_parameters(root, settings)
        data["entry"] = entry
        data["settings"] = settings
        if settings:
            data["architecture"]["warnings"].append(
                "当前使用 KMHV3 默认结构映射；参数按可静态求值的配置覆盖解析，其他结构变化需用运行配置核对。")
        for message in data["architecture"]["warnings"]:
            print("映射提示 ·", message)
    payload=json.dumps(data,ensure_ascii=False,separators=(",",":"))
    def write(path,content):
        path.parent.mkdir(parents=True,exist_ok=True)
        with tempfile.NamedTemporaryFile(mode="w",encoding="utf-8",dir=path.parent,delete=False) as tmp:
            tmp.write(content)
        os.replace(tmp.name,path)
    if args.output:
        write(args.output,payload)
        print(args.output.resolve())
    if args.html:
        if is_xs:
            from xs_viewer import render_xs
            # The object browser only needs declarations and instances.
            source_model = {k:v for k,v in data.items() if k not in ("architecture", "sourceParameters")}
            page = render_xs(data, root, standalone_browser(source_model))
        else:
            page = standalone_browser(data)
        write(args.html,page)
        print(args.html.resolve())
    print(f"{len(nodes)} declarations, {len(edges)} relations, {len(instances)} instances")

if __name__ == "__main__":
    with python_warnings.catch_warnings():
        python_warnings.simplefilter("ignore", SyntaxWarning)
        main()


