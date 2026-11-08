#!/usr/bin/env python3
"""发布前只读检查：域名、旧库引用和图片敏感元数据。"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EXPECTED_DOMAIN = "dqquan.com"
IMAGE_SUFFIXES = {
    ".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".heic", ".avif",
}
TEXT_SUFFIXES = {
    ".py", ".md", ".html", ".txt", ".xml", ".yml", ".yaml", ".json",
}
STALE_REPO_PATTERNS = (
    re.compile(r"(?:~/|/Users/apple/CodexProjects/)?dqquan[_-]home/", re.IGNORECASE),
    re.compile(r"github\.com/[\w.-]+/dqquan-home", re.IGNORECASE),
    re.compile(r"^\s*(?:cd|ROOT\s*=|WORK(?:DIR|SPACE)\s*=).*dqquan[_-]home", re.IGNORECASE | re.MULTILINE),
)
SENSITIVE_TAGS = (
    "$GPSLatitude or $GPSLongitude or $GPSPosition or "
    "$SerialNumber or $BodySerialNumber or $InternalSerialNumber or "
    "$DateTimeOriginal or $CreateDate or $XMP:all or $IPTC:all"
)


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)


def tracked_files() -> list[str]:
    result = run(["git", "ls-files", "-z"])
    if result.returncode:
        raise SystemExit(f"git ls-files 失败：{result.stderr.strip()}")
    return [name for name in result.stdout.split("\0") if name]


def check_domain(errors: list[str]) -> None:
    cname = ROOT / "CNAME"
    if not cname.exists():
        errors.append("缺少 CNAME")
        return
    value = cname.read_text(encoding="utf-8").strip()
    if value != EXPECTED_DOMAIN:
        errors.append(f"CNAME 应为 {EXPECTED_DOMAIN}，实际为 {value!r}")


def check_repo_references(files: list[str], errors: list[str]) -> None:
    for name in files:
        path = ROOT / name
        if path.suffix.lower() not in TEXT_SUFFIXES or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in STALE_REPO_PATTERNS:
            if pattern.search(text):
                errors.append(f"{name} 仍指向旧库：{pattern.pattern}")

    remote = run(["git", "remote", "get-url", "origin"])
    if remote.returncode:
        errors.append("无法读取 origin 仓库地址")
    elif "dqquan-site" not in remote.stdout:
        errors.append(f"origin 不是 dqquan-site：{remote.stdout.strip()}")


def check_image_metadata(files: list[str], errors: list[str]) -> None:
    images = [
        str(ROOT / name)
        for name in files
        if Path(name).suffix.lower() in IMAGE_SUFFIXES
        and (name.startswith("img/") or name.startswith("photos/"))
    ]
    if not images:
        return
    if not shutil.which("exiftool"):
        errors.append("缺少 exiftool，无法检查图片元数据")
        return

    result = subprocess.run(
        [
            "exiftool", "-q", "-m", "-if", SENSITIVE_TAGS,
            "-p", "$Directory/$FileName", *images,
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    # exiftool uses exit status 2 when no file matches the -if condition.
    if result.returncode not in (0, 2):
        errors.append(f"exiftool 检查失败：{result.stderr.strip()[:300]}")
        return
    dirty = [line for line in result.stdout.splitlines() if line.strip()]
    if dirty:
        errors.append("图片仍有敏感元数据：" + "、".join(dirty[:8]))


def main() -> int:
    errors: list[str] = []
    files = tracked_files()
    check_domain(errors)
    check_repo_references(files, errors)
    check_image_metadata(files, errors)

    if errors:
        print("发布检查未通过：")
        for error in errors:
            print(f"  ✗ {error}")
        return 1
    print(
        f"发布检查通过：CNAME={EXPECTED_DOMAIN}，"
        f"无旧库路径，{sum(1 for n in files if Path(n).suffix.lower() in IMAGE_SUFFIXES)} 张图片元数据干净。"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
