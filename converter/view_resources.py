"""Locations of the same viewer assets in a checkout and a portable zipapp."""
from pathlib import Path
from zipfile import Path as ZipPath
from zipimport import zipimporter

if isinstance(__loader__, zipimporter):
    package = ZipPath(__loader__.archive)
    VIEW = package / "viewer"
    PROFILES = package / "profiles"
else:
    directory = Path(__file__).resolve().parent
    VIEW = directory if (directory / "models.html").is_file() else directory.parent / "view" / "converter"
    PROFILES = directory / "profiles"
