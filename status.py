#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
status.py

功能
----
扫描某个产品当前的项目状态，print 进度报告。完全只读，不写任何文件。
对 inbox 中的文件做识别预判，给出"建议跑哪个 dispatch"的提示。
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from io import StringIO
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
        "inbox": base / "_inbox",
        "rawdata": base / "00_rawdata",
        "preprocessed": base / "01_preprocessed",
        "outline": base / "02_outline",
        "variables": base / "03_variables",
        "variables_raw": base / "03_variables" / "raw",
        "raw_csv": base / "00_rawdata" / f"{app}.csv",
        "raw_id_csv": base / "00_rawdata" / f"{app}-id.csv",
        "raw_outline_csv": base / "00_rawdata" / f"{app}-outline.csv",
        "raw_uservar_csv": base / "00_rawdata" / f"{app}_user_var.csv",
        "user_var_merged": base / "03_variables" / "user_var.csv",
    }


def count_csv_rows(path: Path) -> int:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            next(reader, None)
            return sum(1 for _ in reader)
    except Exception:
        return 0


def count_var_def_count(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None:
                return 0
            first_col = reader.fieldnames[0]
            return sum(1 for r in reader if (r.get(first_col) or "").strip())
    except Exception:
        return 0


def read_outline(path: Path) -> Dict[str, List[int]]:
    """返回 {category: [q_num, ...]}（按 outline 顺序）。"""
    cat_to_qs: Dict[str, List[int]] = defaultdict(list)
    if not path.exists():
        return cat_to_qs
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        next(reader, None)
        for row in reader:
            if len(row) < 3:
                continue
            try:
                q_num = int(row[0].strip())
            except ValueError:
                continue
            cat = row[1].strip()
            if q_num not in cat_to_qs[cat]:
                cat_to_qs[cat].append(q_num)
    return cat_to_qs


def render_progress_bar(done: int, total: int, width: int = 10) -> str:
    if total <= 0:
        return "[" + "░" * width + "]"
    filled = int(round(width * done / total))
    filled = max(0, min(width, filled))
    return "[" + "█" * filled + "░" * (width - filled) + "]"


# ---------- inbox 文件识别 ----------

def detect_inbox_file(path: Path) -> Tuple[str, str]:
    """
    识别 inbox 文件，返回 (类别, 建议命令)。
    类别取值：
      - inductive_json
      - codebook_csv
      - variable_csv
      - summary_txt
      - unknown
    """
    suffix = path.suffix.lower()
    if suffix == ".json":
        try:
            with path.open("r", encoding="utf-8-sig") as f:
                data = json.load(f)
            if isinstance(data, list) and data and isinstance(data[0], dict) and "initial_codes" in data[0]:
                return "inductive_json", "03_dispatch_inductive.py"
        except Exception:
            pass
        return "unknown", ""
    if suffix == ".txt":
        try:
            with path.open("r", encoding="utf-8-sig") as f:
                first = f.readline().strip()
            if first.startswith("#") and "stage=" in first:
                return "summary_txt", "05_dispatch_summary.py"
        except Exception:
            pass
        return "unknown", ""
    if suffix == ".csv":
        try:
            with path.open("r", encoding="utf-8-sig") as f:
                first = f.readline().rstrip("\n").rstrip("\r")
                second = f.readline().rstrip("\n").rstrip("\r")
            if first.lstrip().startswith("#") and "category=" in first:
                # 可能是精炼 codebook
                try:
                    header = next(csv.reader(StringIO(second)), [])
                except Exception:
                    header = []
                if header and header[0].strip() == "Theme":
                    return "codebook_csv", "08_dispatch_codebook.py"
            else:
                # 普通 csv：判断是否是变量
                try:
                    header = next(csv.reader(StringIO(first)), [])
                except Exception:
                    header = []
                if header and header[0].strip() == "文件名":
                    return "variable_csv", "10_dispatch_variables.py"
        except Exception:
            pass
        return "unknown", ""
    return "unknown", ""


# ---------- 主报告 ----------

def main() -> int:
    app = parse_app_name()
    paths = app_paths(app)
    base = paths["base"]
    print(f"=== {app} 项目状态 ===\n")

    if not base.exists():
        print(f"❌ 项目目录尚未创建：{base}\n   请先运行 00_init_project.py。")
        return 0

    # ---- 原始数据 ----
    print("📂 原始数据")
    if paths["raw_csv"].exists():
        print(f"  ✓ {paths['raw_csv'].name} ({count_csv_rows(paths['raw_csv'])} 行)")
    else:
        print(f"  ✗ 缺失：{app}.csv")
    if paths["raw_outline_csv"].exists():
        n_q = count_csv_rows(paths["raw_outline_csv"])
        print(f"  ✓ {paths['raw_outline_csv'].name} ({n_q} 题)")
    else:
        print(f"  ✗ 缺失：{app}-outline.csv")
    if paths["raw_uservar_csv"].exists():
        n_v = count_var_def_count(paths["raw_uservar_csv"])
        print(f"  ✓ {paths['raw_uservar_csv'].name} (定义了 {n_v} 个变量)")
    else:
        print(f"  ○ 未提供 {app}_user_var.csv（变量提取功能不可用）")
    print()

    # ---- 归纳编码进度 ----
    cat_to_qs = read_outline(paths["raw_outline_csv"])
    print("📂 归纳编码进度")
    if not cat_to_qs:
        print("  （无 outline，无法计算归纳进度）")
    else:
        for category, q_nums in cat_to_qs.items():
            qdir = paths["outline"] / category / "question"
            done_qs = []
            if qdir.exists():
                for p in qdir.glob("inductive_q*.json"):
                    m = re.search(r"inductive_q(\d+)\.json$", p.name)
                    if m:
                        done_qs.append(int(m.group(1)))
            done_set = set(done_qs)
            total = len(q_nums)
            done = len([q for q in q_nums if q in done_set])
            bar = render_progress_bar(done, total)
            print(f"  {category}: {bar} {done}/{total} 题完成")
            missing = [q for q in q_nums if q not in done_set]
            if missing:
                missing_str = ", ".join(f"q{q:02d}" for q in missing)
                print(f"    未完成: {missing_str}")
    print()

    # ---- 编码本 ----
    print("📂 编码本")
    if not cat_to_qs:
        print("  （无 outline，无法报告）")
    else:
        for category in cat_to_qs.keys():
            cb_dir = paths["outline"] / category / "codebook"
            raw_ok = (cb_dir / f"raw_codebook_{category}.csv").exists()
            ref_ok = (cb_dir / f"codebook_{category}.csv").exists()
            print(
                f"  {category}: raw {'✓' if raw_ok else '✗'} | refined {'✓' if ref_ok else '✗'}"
            )
    print()

    # ---- 对话总结 ----
    print("📂 对话总结")
    if not cat_to_qs:
        print("  （无 outline，无法报告）")
    else:
        for category in cat_to_qs.keys():
            rec_dir = paths["outline"] / category / "recorder"
            n = len(list(rec_dir.glob("sum_*.txt"))) if rec_dir.exists() else 0
            print(f"  {category}: {n} 份")
    print()

    # ---- 用户变量 ----
    print("📂 用户变量")
    if paths["variables_raw"].exists():
        raw_count = len(list(paths["variables_raw"].glob("var_*.csv")))
    else:
        raw_count = 0
    rows_total = count_csv_rows(paths["raw_csv"]) if paths["raw_csv"].exists() else 0
    print(f"  raw 文件: {raw_count}{'/' + str(rows_total) if rows_total else ''}")
    if paths["user_var_merged"].exists():
        merged_n = count_csv_rows(paths["user_var_merged"])
        print(f"  user_var.csv: 已生成（{merged_n} 行）")
    else:
        print("  user_var.csv: 未生成")
    print()

    # ---- inbox ----
    print("📂 _inbox/ 待处理")
    if not paths["inbox"].exists():
        print("  （inbox 目录不存在）")
    else:
        files = sorted(p for p in paths["inbox"].iterdir() if p.is_file())
        if not files:
            print("  inbox 为空。")
        else:
            print(f"  {len(files)} 个文件:")
            for fp in files:
                kind, suggestion = detect_inbox_file(fp)
                if kind == "unknown":
                    print(f"    - 一个无法识别的文件: {fp.name}")
                else:
                    label = {
                        "inductive_json": "归纳编码？建议跑",
                        "codebook_csv": "精炼编码本？建议跑",
                        "variable_csv": "用户变量？建议跑",
                        "summary_txt": "对话总结？建议跑",
                    }[kind]
                    print(f"    - {fp.name} ({label} {suggestion})")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
