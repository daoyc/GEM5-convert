"""Compile source demonstrations against the final, enriched directed graphs."""
from collections import Counter


def verified(item):
    evidence = item.get("evidence") or {}
    return bool(evidence.get("file") and evidence.get("line") and not evidence.get("unresolved"))


def queue_templates(module):
    """Describe each resolved queue group's dispatch and ready-select handoff."""
    by_pair = {}
    for edge in module["internalEdges"]:
        by_pair.setdefault((edge["a"], edge["b"]), []).append(edge)
    routes = []
    for group in module.get("scheduler", {}).get("groups", []):
        node, label = group["nodeId"], group["label"]
        routes.append((node+".admit-select", label+" · 分派与就绪选择", ["issue.dispatch",node,"issue.iq"]))
        routes.append((node+".wakeup", label+" · 接收定向唤醒", ["issue.ports","issue.wakeup",node]))
    routes.append(("issue.rf-arbitration","就绪指令申请发射及读口",["issue.iq","issue.ports","issue.rf"]))
    for scene_id, title, path in routes:
        matches = [by_pair.get(pair, []) for pair in zip(path,path[1:])]
        if any(len(edges) != 1 for edges in matches):
            continue
        yield dict(id=scene_id, name=title,
                   steps=[dict(edgeId=e["id"], a=e["a"], b=e["b"],
                               type=e.get("eventType", e["label"]), text=e.get("description", e["label"]))
                          for (e,) in matches])


def audit_scenes(view):
    for graph in [view, *view["modules"]]:
        overview = graph is view
        nodes = {n["id"]: n for n in graph["modules" if overview else "parts"]}
        edges = graph["edges" if overview else "internalEdges"]
        counts = Counter(e["id"] for e in edges)
        by_id = {e["id"]: e for e in edges}
        templates = list(graph["scenarios"])
        if graph["id"] == "issue":
            templates.extend(queue_templates(graph))
        seen = set()
        accepted, rejected = [], []
        for scene in templates:
            reason = None
            if scene["id"] in seen or not scene.get("steps"):
                reason = "场景标识重复或步骤为空"
            for i, step in enumerate(scene["steps"], 1):
                edge = by_id.get(step.get("edgeId"))
                if not edge or counts[edge["id"]] != 1:
                    reason = f"步骤 {i} 不能唯一匹配边 {step.get('edgeId')}"
                    break
                a, b = step.get("a"), step.get("b")
                if (edge["a"], edge["b"]) != (a,b) or a not in nodes or b not in nodes:
                    reason = f"步骤 {i} 方向或端点不符合 {a} → {b}"
                    break
                if not all(verified(item) for item in (edge, nodes[a], nodes[b])):
                    reason = f"步骤 {i} 缺少节点或连线的源码定位"
                    break
                step["evidence"] = edge["evidence"]
            if reason:
                rejected.append(dict(id=scene["id"], name=scene["name"], reason=reason))
                view["warnings"].append(graph["id"]+" · "+scene["name"]+" · "+reason)
            else:
                seen.add(scene["id"])
                accepted.append(dict(scene, viewId=graph["id"], origin="源码演示"))
        graph["scenarios"] = accepted
        graph["replayAudit"] = dict(accepted=len(accepted), steps=sum(len(s["steps"]) for s in accepted),
                                    excluded=rejected)

