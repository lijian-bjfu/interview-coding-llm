#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
08_dispatch_codebook.py

功能
----
扫描 _inbox/，识别"精炼编码本 CSV"并归位到：
    02_outline/{category}/codebook/codebook_{category}.csv

识别签名：
- 文件扩展名为 .csv
- 第一行（首行）以 `# category=` 开头（注释行）
- 第二行（真正表头）第一列必须是 `Theme`

行为：
- 直接覆盖目标文件（精炼阶段一次完整产出，重做即覆盖）
- 不符合签名的 csv 留在 inbox（10_dispatch_variables.py 会处理变量 csv）
"""

from __future__ import annotations

import argparse
import csv
import re
import shutil
import sys
from io import StringIO
from pathlib import Path
from typing import Optional

from parameters import APP_NAME as DEFAULT_APP_NAME


PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR_BASE = PROJECT_ROOT / "data_dir"


def parse_app_name() -> str:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--app", default=None, help="覆盖 parameters.py 的 APP_NAME")
    args, _ = parser.parse_known_args()
    return args.app or DEFAULT_APP_NAME


def app_paths(app: str) -> dict:
    base = DATA_DIR_BASE / f"{app}_dir"
    return {
        "base": base,
        "inbox": base / "_inbox",
        "outline": base / "02_outline",
    }


def sanitize_dir_name(name: str) -> str:
    safe = re.sub(r'[<>:"/\\|?*\x00-\x1F]', "_", name)
    safe = re.sub(r"_+", "_", safe).strip("_. ")
    return safe or "uncategorized"


def detect_codebook_csv(path: Path) -> Optional[str]:
    """
    若文件符合精炼编码本签名，返回 category；否则返回 None。
    """
    try:
        with path.open("r", encoding="utf-8-sig") as f:
            first = f.readline().rstrip("\n").rstrip("\r")
            second = f.readline().rstrip("\n").rstrip("\r")
    except Exception:
        return None

    # 第一行必须是 # category=xxx
    if not first.lstrip().startswith("#"):
        return None
    body = first.lstrip().lstrip("#").strip()
    fields = {}
    for chunk in re.split(r"[,;]", body):
        if "=" in chunk:
            k, v = chunk.split("=", 1)
            fields[k.strip().lower()] = v.strip()
    category = fields.get("category")
    if not category:
        return None

    # 第二行解析为 csv，第一列必须是 Theme
    try:
        reader = csv.reader(StringIO(second))
        header = next(reader, [])
    except Exception:
        return None
    if not header or header[0].strip() != "Theme":
        return None
    return category


def main() -> int:
    app = parse_app_name()
    paths = app_paths(app)
    print(f"=== Dispatch 精炼编码本 CSV：{app} ===\n")

    if not paths["inbox"].exists():
        print(f"❌ 找不到 inbox：{paths['inbox']}")
        return 1

    csv_files = sorted(paths["inbox"].glob("*.csv"))
    if not csv_files:
        print("inbox 中没有 .csv 文件，结束。")
        return 0

    moved = 0
    skipped = 0
    errors = 0

    for cp in csv_files:
        category = detect_codebook_csv(cp)
        if category is None:
            print(f"  跳过（非精炼编码本签名）：{cp.name}")
            skipped += 1
            continue

        safe_cat = sanitize_dir_name(category)
        cat_dir = paths["outline"] / safe_cat
        if not cat_dir.exists():
            print(
                f"  ❌ {cp.name} 指定 category='{category}' 但 02_outline 下不存在该分类目录。"
                f"\n      （文件留在 inbox）"
            )
            errors += 1
            continue
        cb_dir = cat_dir / "codebook"
        cb_dir.mkdir(parents=True, exist_ok=True)
        target = cb_dir / f"codebook_{category}.csv"
        if target.exists():
            print(f"  ⚠️  目标已存在，将覆盖：{target.relative_to(paths['base'])}")
        shutil.move(str(cp), str(target))
        print(f"  归位：{cp.name} -> {target.relative_to(paths['base'])}")
        moved += 1

    print(f"\n汇总：成功 {moved}，跳过 {skipped}，错误 {errors}。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
