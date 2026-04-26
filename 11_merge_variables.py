#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
11_merge_variables.py

功能
----
合并 03_variables/raw/ 下所有 var_NN.csv，输出到：
    03_variables/user_var.csv

列对齐规则：
- 以 00_rawdata/{app}_user_var.csv 中的"变量名"列为准
- 最终大表列顺序：`文件名` + 变量定义中的所有变量名
- raw 文件中：
    缺列 -> 填空值（警告）
    多列 -> 丢弃多余列（警告）
- 重复"文件名"（同 ID 多行）-> 报错提示用户检查
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

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
        "raw_uservar_csv": base / "00_rawdata" / f"{app}_user_var.csv",
        "variables_raw": base / "03_variables" / "raw",
        "merged_csv": base / "03_variables" / "user_var.csv",
    }


def read_var_names(uservar_csv: Path) -> List[str]:
    with uservar_csv.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise RuntimeError(f"变量定义 CSV 为空：{uservar_csv}")
        first_col = reader.fieldnames[0]
        names = []
        for row in reader:
            n = (row.get(first_col) or "").strip()
            if n:
                names.append(n)
    return names


def list_raw_files(raw_dir: Path) -> List[Path]:
    files = sorted(raw_dir.glob("var_*.csv"), key=lambda p: int(
        re.search(r"var_(\d+)\.csv$", p.name).group(1)
    ) if re.search(r"var_(\d+)\.csv$", p.name) else 10**6)
    return files


def main() -> int:
    app = parse_app_name()
    paths = app_paths(app)
    print(f"=== 合并用户变量大表：{app} ===\n")

    if not paths["raw_uservar_csv"].exists():
        print(f"❌ 找不到变量定义 CSV：{paths['raw_uservar_csv']}")
        return 1
    if not paths["variables_raw"].exists():
        print(f"❌ 找不到 raw 目录：{paths['variables_raw']}")
        return 1

    var_names = read_var_names(paths["raw_uservar_csv"])
    if not var_names:
        print("❌ 变量定义中没有有效变量。")
        return 1
    final_cols = ["文件名"] + var_names

    files = list_raw_files(paths["variables_raw"])
    if not files:
        print("ℹ️  raw 目录下没有 var_*.csv，无需合并。")
        return 0

    all_rows: List[Dict[str, str]] = []
    seen_ids: Dict[str, str] = {}  # id -> 来自哪个文件
    duplicates: List[Tuple[str, str, str]] = []

    for fp in files:
        with fp.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None:
                print(f"  ⚠️  {fp.name} 为空，跳过。")
                continue
            file_cols = list(reader.fieldnames)
            if file_cols[0].strip() != "文件名":
                print(f"  ⚠️  {fp.name} 首列不是 '文件名'，跳过。")
                continue

            missing_cols = [c for c in var_names if c not in file_cols]
            extra_cols = [c for c in file_cols if c != "文件名" and c not in var_names]
            if missing_cols:
                print(f"  ⚠️  {fp.name} 缺列 {missing_cols}（合并时填空值）。")
            if extra_cols:
                print(f"  ⚠️  {fp.name} 多列 {extra_cols}（合并时丢弃）。")

            for row in reader:
                uid = (row.get("文件名") or "").strip()
                if not uid:
                    continue
                if uid in seen_ids:
                    duplicates.append((uid, seen_ids[uid], fp.name))
                seen_ids[uid] = fp.name
                merged_row = {"文件名": uid}
                for vn in var_names:
                    merged_row[vn] = (row.get(vn) or "").strip()
                all_rows.append(merged_row)

    if duplicates:
        print("\n❌ 发现重复 '文件名'（同 ID 多行），请检查以下冲突：")
        for uid, src1, src2 in duplicates:
            print(f"   ID={uid} 同时出现在 {src1} 和 {src2}")
        print("   合并已中止。请手动处理后重新运行。")
        return 1

    paths["merged_csv"].parent.mkdir(parents=True, exist_ok=True)
    with paths["merged_csv"].open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=final_cols)
        writer.writeheader()
        for row in all_rows:
            writer.writerow(row)

    print(f"\n✅ 合并完成：{paths['merged_csv'].relative_to(paths['base'])}")
    print(f"   共 {len(all_rows)} 行，{len(final_cols)} 列。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
