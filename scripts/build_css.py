#!/usr/bin/env python
"""Build the project stylesheet with the pinned Tailwind CSS standalone CLI.

Downloads the official Tailwind v3.4.17 binary for the current platform
into .tailwind/ (git-ignored), verifies it against the SHA-256 checksums
published on the release, then compiles static/src/tailwind.css into
static/css/tailwind.css. Requires no Node.js.

    python scripts/build_css.py             # one-off minified build
    python scripts/build_css.py --watch     # rebuild on change (development)
"""
import argparse
import hashlib
import os
import platform
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
TOOL_DIR = BASE_DIR / ".tailwind"
INPUT_CSS = BASE_DIR / "static" / "src" / "tailwind.css"
OUTPUT_CSS = BASE_DIR / "static" / "css" / "tailwind.css"
CONFIG = BASE_DIR / "tailwind.config.js"

TAILWIND_VERSION = "3.4.17"
RELEASE_URL = (
    "https://github.com/tailwindlabs/tailwindcss/releases/"
    "download/v{version}/{asset}"
)

# SHA-256 checksums from sha256sums.txt on the official release page:
# https://github.com/tailwindlabs/tailwindcss/releases/tag/v3.4.17
BINARIES = {
    ("Windows", "AMD64"): (
        "tailwindcss-windows-x64.exe",
        "67f1c5e3f5a03406a7bf5badf5ada09b79f3ae78ec43450c15f7e983068da346",
    ),
    ("Windows", "ARM64"): (
        "tailwindcss-windows-arm64.exe",
        "76f516476784c00f1562160b5758e3d8f0e6c48957efb26b5b50fbdfd76aa382",
    ),
    ("Linux", "x86_64"): (
        "tailwindcss-linux-x64",
        "7d24f7fa191d2193b78cd5f5a42a6093e14409521908529f42d80b11fde1f1d4",
    ),
    ("Linux", "aarch64"): (
        "tailwindcss-linux-arm64",
        "69b1378b8133192d7d2feb12a116fa12d035594f58db3eff215879e4ad8cf39b",
    ),
    ("Linux", "armv7l"): (
        "tailwindcss-linux-armv7",
        "704e7d91afba6e1f630889afd0d7db36b4634e628512cc141d504a5beae28860",
    ),
    ("Darwin", "x86_64"): (
        "tailwindcss-macos-x64",
        "6cbdad74be776c087ffa5e9a057512c54898f9fe8828d3362212dfe32fc933a3",
    ),
    ("Darwin", "arm64"): (
        "tailwindcss-macos-arm64",
        "a1d0c7985759accca0bf12e51ac1dcbf0f6cf2fffb62e6e0f62d091c477a10a3",
    ),
}


def resolve_binary_info():
    key = (platform.system(), platform.machine())
    info = BINARIES.get(key)
    if info is None:
        supported = ", ".join(sorted("/".join(k) for k in BINARIES))
        sys.exit(
            "No Tailwind binary for %s/%s. Supported: %s"
            % (key[0], key[1], supported)
        )
    return info


def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_cli():
    name, expected = resolve_binary_info()
    binary = TOOL_DIR / name
    if binary.exists() and sha256_of(binary) == expected:
        return binary

    TOOL_DIR.mkdir(exist_ok=True)
    url = RELEASE_URL.format(version=TAILWIND_VERSION, asset=name)
    print("Downloading Tailwind CSS v%s CLI ..." % TAILWIND_VERSION)
    print("  %s" % url)
    with tempfile.NamedTemporaryFile(dir=TOOL_DIR, delete=False) as tmp:
        try:
            with urllib.request.urlopen(url) as response:
                while True:
                    chunk = response.read(1 << 20)
                    if not chunk:
                        break
                    tmp.write(chunk)
            tmp.close()
            actual = sha256_of(tmp.name)
            if actual != expected:
                raise SystemExit(
                    "Checksum mismatch for %s:\n  expected %s\n  got      %s\n"
                    "The download may be corrupted; delete it and retry."
                    % (name, expected, actual)
                )
            os.replace(tmp.name, binary)
        finally:
            if os.path.exists(tmp.name):
                os.unlink(tmp.name)

    if os.name == "posix":
        binary.chmod(0o755)
    print("Verified Tailwind CSS CLI at %s" % binary)
    return binary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--watch",
        action="store_true",
        help="rebuild automatically when source files change",
    )
    args = parser.parse_args()

    for required in (INPUT_CSS, CONFIG):
        if not required.exists():
            sys.exit("Missing %s" % required)

    cli = ensure_cli()
    command = [str(cli), "-i", str(INPUT_CSS), "-o", str(OUTPUT_CSS)]
    if args.watch:
        command.append("--watch")
    else:
        command.append("--minify")

    print("Building %s ..." % OUTPUT_CSS)
    result = subprocess.run(command, cwd=str(BASE_DIR))
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
