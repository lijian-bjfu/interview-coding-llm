#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
10_dispatch_variables.py

功能
----
扫描 _inbox/，识别"用户变量 CSV"并归位到：
    03_variables/raw/var_{NN}.csv

识别签名：
- 文件扩展名为 .csv
- 表头第一列是 `文件名`
  （注意：精炼编码本 CSV 是 # category=... 注释行 + Theme 表头，不会被误判）

NN 编号规则：
- 扫描 03_variables/raw/ 下已有 var_*.csv，取最大 NN +1
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
        "variables_raw": base / "03_variables" / "raw",
    }


def detect_variable_csv(path: Path) -> bool:
    """若文件符合用户变量 CSV 签名，返回 True。"""
    try:
        with path.open("r", encoding="utf-8-sig") as f:
            first = f.readline().rstrip("\n").rstrip("\r")
    except Exception:
        return False
    # 精炼编码本以 # 开头，先剔除
    if first.lstrip().startswith("#"):
        return False
    try:
        reader = csv.reader(StringIO(first))
        header = next(reader, [])
    except Exception:
        return False
    if not header:
        return False
    return header[0].strip() == "文件名"


def next_seq(raw_dir: Path) -> int:
    if not raw_dir.exists():
        return 1
    used = []
    for p in raw_dir.glob("var_*.csv"):
        m = re.search(r"var_(\d+)\.csv$", p.name)
        if m:
            used.append(int(m.group(1)))
    return (max(used) + 1) if used else 1


def main() -> int:
    app = parse_app_name()
    paths = app_paths(app)
    print(f"=== Dispatch 用户变量 CSV：{app} ===\n")

    if not paths["inbox"].exists():
        print(f"❌ 找不到 inbox：{paths['inbox']}")
        return 1
    paths["variables_raw"].mkdir(parents=True, exist_ok=True)

    csv_files = sorted(paths["inbox"].glob("*.csv"))
    if not csv_files:
        print("inbox 中没有 .csv 文件，结束。")
        return 0

    moved = 0
    skipped = 0
    for cp in csv_files:
        if not detect_variable_csv(cp):
            print(f"  跳过（非用户变量 CSV 签名）：{cp.name}")
            skipped += 1
            continue
        nn = next_seq(paths["variables_raw"])
        target = paths["variables_raw"] / f"var_{nn:02d}.csv"
        shutil.move(str(cp), str(target))
        print(f"  归位：{cp.name} -> {target.relative_to(paths['base'])}")
        moved += 1

    print(f"\n汇总：成功 {moved}，跳过 {skipped}。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
