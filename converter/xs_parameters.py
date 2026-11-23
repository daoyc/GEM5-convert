"""Read the KMHV3 parameter panel from the selected source checkout without importing gem5."""
import ast
import re
from pathlib import PurePosixPath

ENTRY = "configs/example/kmhv3.py"
OPTIONS = "configs/common/Options.py"
SYSTEM = "configs/common/xiangshan.py"
CACHES = "configs/common/Caches.py"
CACHE_CONFIG = "configs/common/CacheConfig.py"
TLB = "src/arch/riscv/RiscvTLB.py"
UNKNOWN = object()


def literal(node):
    try:
        return ast.literal_eval(node)
    except (ValueError, TypeError, SyntaxError):
        return UNKNOWN


def read_trees(root, paths):
    trees = {}
    for path in paths:
        try:
            trees[path] = ast.parse((root / path).read_text(encoding="utf-8-sig"), filename=path)
        except (OSError, SyntaxError, UnicodeError):
            trees[path] = ast.Module(body=[], type_ignores=[])
    return trees


def option_defaults(trees):
    options = {}
    for file in (OPTIONS, SYSTEM):
        for call in ast.walk(trees[file]):
            if not isinstance(call, ast.Call) or not ast.unparse(call.func).endswith(".add_argument"):
                continue
            names = [a.value[2:].replace("-", "_") for a in call.args
                     if isinstance(a, ast.Constant) and isinstance(a.value, str) and a.value.startswith("--")]
            if not names:
                continue
            kw = {k.arg: k.value for k in call.keywords}
            dest = literal(kw["dest"]) if "dest" in kw else names[0]
            if not isinstance(dest, str):
                continue
            action = literal(kw["action"]) if "action" in kw else None
            value = literal(kw["default"]) if "default" in kw else {"store_true": False, "store_false": True}.get(action)
            options[dest] = (value, file, kw.get("default", call))
    return options


def memory_bytes(value):
    if isinstance(value, int) and value >= 0:
        return value
    match = re.fullmatch(r"(\d+)\s*([kmgt]?)(?:i?b)?", str(value), re.I)
    return int(match[1]) * 1024 ** ("", "k", "m", "g", "t").index(match[2].lower()) if match else UNKNOWN


def source_parameters(root, settings):
    o3 = "src/cpu/o3/BaseO3CPU.py"
    cache = "src/mem/cache/Cache.py"
    trees = read_trees(root, (ENTRY, SYSTEM, OPTIONS, CACHES, CACHE_CONFIG, TLB, o3, cache))
    options = option_defaults(trees)
    for key, value in settings.items():
        if type(options.get(key, (None,))[0]) is int and isinstance(value, str) and re.fullmatch(r"-?\d+",value):
            value = int(value)
        options[key] = (value, None, None)
    result = {}
    variables = {}
    kmh = trees[ENTRY]

    def field(key, value, file, node):
        result[key] = {"value": None if value is UNKNOWN else value,
                       "path": f"GEM5/{file}:{node.lineno}" if file and node else None}

    def setting(key):
        return options.get(key, (UNKNOWN, None, None))

    def evaluate(expr):
        value = literal(expr)
        if value is not UNKNOWN:
            return value
        if isinstance(expr, ast.Name):
            return variables.get(expr.id, UNKNOWN)
        if isinstance(expr, ast.Attribute) and ast.unparse(expr).startswith("args."):
            return setting(expr.attr)[0]
        if isinstance(expr, ast.UnaryOp) and isinstance(expr.op, ast.Not):
            value = evaluate(expr.operand)
            return not value if value is not UNKNOWN else UNKNOWN
        if isinstance(expr, ast.Compare) and len(expr.ops) == 1 and isinstance(expr.ops[0], ast.Eq):
            a, b = evaluate(expr.left), evaluate(expr.comparators[0])
            return a == b if UNKNOWN not in (a, b) else UNKNOWN
        if isinstance(expr, ast.Call):
            name = ast.unparse(expr.func)
            if name == "getattr" and len(expr.args) == 3 and ast.unparse(expr.args[0]) == "args":
                key = literal(expr.args[1])
                return options[key][0] if key in options else evaluate(expr.args[2])
            if name == "hybrid_policy_requested":
                return "hybrid" in str(settings.get("param", "")).lower()
            if isinstance(expr.func, ast.Name) and expr.func.id.endswith("RP"):
                return expr.func.id
        return UNKNOWN

    # Entry-point assignments override command-line defaults before system construction.
    for stmt in kmh.body:
        if not isinstance(stmt, ast.If) or "__m5_main__" not in ast.unparse(stmt.test):
            continue
        for item in stmt.body:
            if isinstance(item, ast.Assign) and len(item.targets) == 1:
                target = ast.unparse(item.targets[0])
                if target.startswith("args."):
                    options[target[5:]] = (evaluate(item.value), ENTRY, item)

    # The classic XS builder explicitly enables these caches by iterating option names.
    for loop in ast.walk(trees[SYSTEM]):
        if isinstance(loop, ast.For) and isinstance(loop.iter, (ast.List, ast.Tuple)):
            names = literal(loop.iter)
            if not isinstance(names, (tuple, list)) or not any(
                isinstance(n, ast.Call) and ast.unparse(n.func) == "setattr"
                and len(n.args) == 3 and ast.unparse(n.args[1]) == ast.unparse(loop.target)
                and literal(n.args[2]) is True for n in ast.walk(loop)):
                continue
            for key in names:
                if key in ("caches", "l2cache", "l3cache") and not settings.get("ruby") and not (
                        key == "l3cache" and setting("no_l3cache")[0] is True):
                    options[key] = (True, SYSTEM, loop)

    def declarations(file, class_name, owner, keys):
        cls = next((c for c in trees[file].body if isinstance(c, ast.ClassDef) and c.name == class_name), None)
        for stmt in cls.body if cls else []:
            if not isinstance(stmt, ast.Assign):
                continue
            key = ast.unparse(stmt.targets[0])
            if key not in keys:
                continue
            expr = stmt.value
            if isinstance(expr, ast.Call) and ast.unparse(expr.func).startswith("Param.") and expr.args:
                expr = expr.args[0]
            field(owner+"."+key, evaluate(expr), file, stmt)

    declarations(o3, "BaseO3CPU", "cpu", {"wbWidth"})
    for owner in ("mmu.itb", "mmu.dtb"):
        declarations(TLB, "RiscvTLB", owner, {"size"})
        field(owner+".walker.ptw_miss_queue_size", *setting("ptw_miss_queue_size"))
    declarations(TLB, "RiscvTLB", "mmu.l2_shared", {"l2tlb_"+level+"_size" for level in ("l0","l1","l2","l3","sp")})
    declarations(CACHES, "L3ToMemBus", "membus", {"width"})
    for owner in ("icache", "l3"):
        declarations(cache, "BaseCache", owner, {"replacement_policy"})
    declarations(CACHES, "L1_DCache", "dcache", {"replacement_policy"})

    for level, owner in (("l1i","icache"), ("l1d","dcache"), ("l2","slice"), ("l3","l3")):
        field(owner+".assoc", *setting(level+"_assoc"))
    for level, owner in (("l1i","icache"), ("l1d","dcache"), ("l2","slice"), ("l2_wrapper","wrapper"), ("l3","l3")):
        value, file, node = setting(level+"_hwp_type")
        field(owner+".prefetcher", "Null" if value is None or setting("no_pf")[0] is True else value, file, node)
    for option, key in (("l2_size","wrapper.size"), ("l3_size","l3.size")):
        value, file, node = setting(option)
        field(key, memory_bytes(value), file, node)
    slices, file, node = setting("l2_slices")
    field("wrapper.num_slices", slices, file, node)
    for item in ast.walk(trees[CACHE_CONFIG]):
        if isinstance(item,ast.Assign) and ast.unparse(item.targets[0])=="inner_cache.size":
            if ast.unparse(item.value)=="inner_cache.size / num_l2_slices":
                size = result["wrapper.size"]["value"]
                value = size//slices if isinstance(slices,int) and slices>0 and size is not None and size%slices==0 else UNKNOWN
                field("slice.size", value, CACHE_CONFIG, item)
    value,file,node = setting("dramsim3_ini")
    if value is None and setting("mem_type")[0] == "DRAMsim3":
        func_name = "build_xiangshan_system" if setting("enable_trace_mode")[0] is True else "config_xiangshan_inputs"
        func = next((f for f in trees[SYSTEM].body if isinstance(f,ast.FunctionDef) and f.name == func_name), None)
        for item in ast.walk(func) if func else []:
            if isinstance(item, ast.Assign) and ast.unparse(item.targets[0]) == "args.dramsim3_ini" and isinstance(item.value,ast.Call):
                value = literal(item.value.args[-1]) if item.value.args else UNKNOWN
                file,node = SYSTEM,item
    field("mem_ctrls.configFile", PurePosixPath(value).name if isinstance(value,str) else UNKNOWN, file,node)

    # Follow the default configuration's conditional assignments in source order.
    def walk(stmts, uncertain=False):
        for stmt in stmts:
            if isinstance(stmt, ast.For):
                walk(stmt.body, uncertain)
            elif isinstance(stmt, ast.If):
                test = evaluate(stmt.test)
                if test is UNKNOWN:
                    walk(stmt.body, True)
                    walk(stmt.orelse, True)
                else:
                    walk(stmt.body if test else stmt.orelse, uncertain)
            elif isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
                target = ast.unparse(stmt.targets[0])
                value = UNKNOWN if uncertain else evaluate(stmt.value)
                if isinstance(stmt.targets[0], ast.Name):
                    variables[target] = value
                elif target.startswith("cpu."):
                    key = target[4:] if target.count(".")>1 else target
                    if "[" not in key and (value is not UNKNOWN or key in result or key.startswith(("mmu.","branchPred."))):
                        field(key, memory_bytes(value) if key in ("icache.size","dcache.size") else value, ENTRY, stmt)
                    elif target.count(".")==1:
                        field(key,value,ENTRY,stmt)
                elif target == "system.l3.num_slices":
                    field("l3.num_slices",value,ENTRY,stmt)
                elif target == "l2_wrapper.slices[j].inner_cache.replacement_policy":
                    field("slice.replacement_policy",value,ENTRY,stmt)
    for func in kmh.body:
        if isinstance(func,ast.FunctionDef) and func.name=="setKmhV3Params":
            walk(func.body)
    return result

