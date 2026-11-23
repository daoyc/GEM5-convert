"""Build the standard-library-only converter with reproducible zip metadata."""
from pathlib import Path
from tempfile import NamedTemporaryFile
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

from view_resources import VIEW, PROFILES

ROOT = Path(__file__).resolve().parent
MODULES = ("convert_model", "semantics", "xiangshan", "xs_parameters", "xs_profile",
           "xs_viewer", "view_resources", "zenas_details", "backend_structure",
           "front_structure", "memory_structure", "replay_audit")


def build():
    output = ROOT / "GEM5-converter.pyz"
    with NamedTemporaryFile(dir=ROOT, delete=False) as tmp:
        archive = Path(tmp.name)
    try:
        with ZipFile(archive, "w") as bundle:
            def add(name, content):
                info = ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
                info.create_system = 3
                info.external_attr = 0o100644 << 16
                bundle.writestr(info, content, compress_type=ZIP_DEFLATED)

            add("__main__.py", "import warnings\nfrom convert_model import main\n"
                "warnings.filterwarnings('ignore', category=SyntaxWarning)\nmain(single_html=True)\n")
            for module in MODULES:
                name = module + ".py"
                add(name, (ROOT / name).read_bytes())
            add("profiles/kmhv3.json", (PROFILES / "kmhv3.json").read_bytes())
            for asset in ("models.html", "models.js", "coverage.js", "models.css", "atlas.js",
                          "viewer.css", "examples/baseline.ini", "examples/variant.json"):
                add("viewer/"+asset, (VIEW / asset).read_bytes())
            for file in sorted((VIEW / "xs_view").iterdir()):
                if file.suffix in (".html", ".js", ".css"):
                    add("viewer/xs_view/"+file.name, file.read_bytes())
        archive.replace(output)
    finally:
        archive.unlink(missing_ok=True)
    print(output)


if __name__ == "__main__":
    build()

