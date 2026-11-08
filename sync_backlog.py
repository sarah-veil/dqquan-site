#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把公众号已发但站上缺的期次补进站点：定稿 md → src/html/NN.html + 封面 + BOOK_META

用法： python3 sync_backlog.py 32 41
"""
import re, os, sys, html, glob, shutil, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src" / "html"
COVERS = ROOT / "img" / "covers"

TITLES = {
    32: ("故事新编", "鲁迅", "圣人先是一个人，然后才是圣人。"),
    33: ("荆棘鸟", "考琳·麦卡洛", "最美好的东西，只能用深痛巨创去换。"),
    34: ("三体", "刘慈欣", "父亲在批斗台上，女儿在红岸按下了发射键。"),
    35: ("罪与罚", "陀思妥耶夫斯基", "一桩谋杀之后塌掉的，不是良心，是逻辑。"),
    36: ("我的精神家园", "王小波", "一只不肯被安排的猪，和思维的乐趣。"),
    37: ("都柏林人", "詹姆斯·乔伊斯", "十五个顿悟，一场落在所有人身上的雪。"),
    38: ("撒哈拉的故事", "三毛", "白手成家、结婚记、哑奴：沙漠里的日子。"),
    39: ("奇鸟行状录", "村上春树", "下到井底，把两个人放到同一个高度上。"),
    40: ("香椿树街故事", "苏童", "青石板缝里的血，和少年胳膊上的刺青。"),
    41: ("了不起的盖茨比", "菲茨杰拉德", "绿灯在对岸，账单在身后。"),
}

SHELL = (SRC / "31.html").read_text(encoding="utf-8")


def md_path(n):
    d = glob.glob(os.path.expanduser(f"~/CodexProjects/book{n}_*_work"))[0]
    return glob.glob(f"{d}/*定稿*.md")[0]


def paragraphs(n):
    raw = open(md_path(n), encoding="utf-8").read()
    lines = [l.rstrip() for l in raw.split("\n")]
    out, started = [], False
    for l in lines:
        s = l.strip()
        if not s:
            continue
        if s == "---" or re.match(r"^[^\s:]{1,12}:\s", s):     # frontmatter
            continue
        if s.startswith("#"):
            if s.startswith("# "):
                started = True            # 跳过一级标题
            continue                      # 其余层级标题都不要
        if re.fullmatch(r"第\s*\d+\s*期", s) or s == "半亩方塘 · 重温百部名著":
            continue
        if re.fullmatch(r"《.+?》\s*[｜|]\s*\S+", s):      # 书名｜作者 这种副标题行，h1 已表达
            continue
        s = re.sub(r"^>\s*", "", s)
        s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
        s = s.replace("**", "")
        out.append(html.escape(s, quote=False))
    return out


def build(n):
    title, author, desc = TITLES[n]
    ps = paragraphs(n)
    art = "<article>" + "".join(f"<p>{p}</p>" for p in ps) + "</article>"
    s = SHELL
    s = re.sub(r"<title>.*?</title>", f"<title>{html.escape(title)} · 半亩方塘</title>", s, count=1)
    s = re.sub(r"<h1>.*?</h1>", f"<h1>{html.escape(title)}</h1>", s, count=1)
    s = re.sub(r'<div class="meta">.*?</div>', f'<div class="meta">第 {n} 期</div>', s, count=1)
    s = re.sub(r"<article>.*?</article>", art, s, count=1, flags=re.S)
    (SRC / f"{n}.html").write_text(s, encoding="utf-8")

    jpg = Path(f"/Users/apple/cover{n}.jpg")
    dst = COVERS / f"b{n:02d}.webp"
    if jpg.exists():
        subprocess.run(["cwebp", "-quiet", "-q", "82", str(jpg), "-o", str(dst)], check=True)
    return len(ps), dst.exists()


if __name__ == "__main__":
    a, b = int(sys.argv[1]), int(sys.argv[2])
    for n in range(a, b + 1):
        cnt, cov = build(n)
        print(f"  ✓ 第 {n} 期：{TITLES[n][0]}｜{cnt} 段｜封面 {'已出' if cov else '缺'}")
