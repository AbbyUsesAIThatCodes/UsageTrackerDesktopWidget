"""Produce a portable Windows folder with a pinned, verified official Codex binary."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
CODEX_VERSION = "0.154.0"
CODEX_URL = f"https://github.com/openai/codex/releases/download/rust-v{CODEX_VERSION}/codex-x86_64-pc-windows-msvc.exe.zip"
CODEX_SHA256 = "53685f9f6bd171d4bd7d6c2be724fc04f6737a4001eb8471ec59824e5adc8042"


def download(url, path):
    request = urllib.request.Request(url, headers={"User-Agent": "UsageGarden-build/0.1.0"})
    with urllib.request.urlopen(request, timeout=120) as response, path.open("wb") as stream:
        shutil.copyfileobj(response, stream)


def main():
    if sys.platform != "win32":
        raise SystemExit("Build the Windows package on Windows or use the included GitHub Actions workflow.")
    from PySide6.QtWidgets import QApplication
    from usage_garden.art import app_icon
    app = QApplication([])
    ROOT.joinpath("assets").mkdir(exist_ok=True)
    app_icon().pixmap(128, 128).save(str(ROOT / "assets/usage-garden.ico"))
    subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--windowed",
                    "--onedir", "--name", "UsageGarden", "--icon", "assets/usage-garden.ico",
                    "--exclude-module", "PySide6.QtWebEngineCore", "--exclude-module", "PySide6.QtWebEngineWidgets",
                    "launch.py"], cwd=ROOT, check=True)
    output = ROOT / "dist/UsageGarden"
    vendor = output / "vendor"; vendor.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as temporary:
        archive = Path(temporary) / "codex.zip"; download(CODEX_URL, archive)
        with archive.open("rb") as archive_stream:
            digest = hashlib.file_digest(archive_stream, "sha256").hexdigest()
        if digest != CODEX_SHA256:
            raise RuntimeError("Official Codex download checksum mismatch")
        with zipfile.ZipFile(archive) as source:
            matches = [item for item in source.infolist() if Path(item.filename).name == "codex-x86_64-pc-windows-msvc.exe"]
            if len(matches) != 1:
                raise RuntimeError("Unexpected Codex archive layout")
            with source.open(matches[0]) as stream, (vendor / "codex.exe").open("wb") as target:
                shutil.copyfileobj(stream, target)
    for name in ("LICENSE", "NOTICE"):
        download(f"https://raw.githubusercontent.com/openai/codex/rust-v{CODEX_VERSION}/{name}", vendor / f"CODEX-{name}.txt")
    for name in ("README.md", "THIRD_PARTY_NOTICES.md", "Install-Usage-Garden.cmd", "Install-Usage-Garden.ps1"):
        shutil.copy2(ROOT / name, output / name)
    shutil.copy2(ROOT / "assets/usage-garden.ico", output / "usage-garden.ico")
    # Ship applicable Qt/PySide license texts and dynamically linked libraries.
    import PySide6
    licenses = Path(PySide6.__file__).parent / "Qt/licenses"
    if licenses.exists():
        shutil.copytree(licenses, output / "licenses/Qt", dirs_exist_ok=True)
    import importlib.metadata
    for package in ("PySide6", "PySide6_Essentials", "shiboken6", "pyinstaller"):
        distribution = importlib.metadata.distribution(package)
        for item in distribution.files or []:
            if any(term in str(item).lower() for term in ("license", "copying")) and str(item).endswith((".txt", ".md", "LICENSE", "COPYING")):
                origin = Path(distribution.locate_file(item))
                if origin.is_file():
                    target = output / "licenses" / package / origin.name
                    target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(origin, target)
    manifest = {"application": "Usage Garden", "version": "0.1.0", "codename": "First Bloom",
                "architecture": "Windows x64", "codex_version": CODEX_VERSION,
                "codex_download": CODEX_URL, "codex_archive_sha256": CODEX_SHA256}
    (output / "build-info.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    python_license = Path(sys.base_prefix) / "LICENSE.txt"
    if python_license.exists():
        shutil.copy2(python_license, output / "licenses/PYTHON-LICENSE.txt")
    # Check the real bundled process handshake without starting any task or model turn.
    from usage_garden.provider import RpcClient
    client = RpcClient([str(vendor / "codex.exe"), "app-server"])
    try:
        client.initialize(); response = client.request("account/read", {"refreshToken": False})
        if "account" not in response:
            raise RuntimeError("Bundled Codex protocol smoke check failed")
    finally:
        client.close()
    print(f"Portable package ready: {output}")


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    main()
