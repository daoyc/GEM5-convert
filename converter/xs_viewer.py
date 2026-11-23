"""Package the kmhv3 graph, input source files and offline viewer in a single page."""
import json
import re
from view_resources import VIEW

ASSETS = VIEW / "xs_view"


def _json_block(element_id, value):
    # JSON scripts are HTML raw-text elements, including inside an embedded page.
    encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    return f'<script type="application/json" id="{element_id}">{encoded}</script>'


def render_xs(model, root, source_browser_html):
    """Create a self-contained viewer. Source snapshots belong to the converted model."""
    page = (ASSETS / "index.html").read_text(encoding="utf-8-sig")

    def inline_script(match):
        source = (ASSETS / match[1]).read_text(encoding="utf-8-sig")
        return "<script>" + source + "</script>"

    page = re.sub(r'<script src="([\w-]+\.js)"></script>', inline_script, page)
    css = (ASSETS / "style.css").read_text(encoding="utf-8-sig")
    page = page.replace('<link rel="stylesheet" href="style.css">', "<style>" + css + "</style>")
    examples = ASSETS.parent / "examples"
    samples = {key: (examples / name).read_text(encoding="utf-8-sig")
               for key, name in [("sampleA", "baseline.ini"), ("sampleB", "variant.json")]}
    payload = {key: model[key] for key in ("name", "architecture", "sourceParameters", "instances",
                                           "config", "scope") if key in model}
    return page.replace("<!--xs-model-->", _json_block("xs-model", {"model": payload, "samples": samples})
                        + _json_block("source-browser", source_browser_html))

