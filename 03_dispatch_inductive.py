#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
03_dispatch_inductive.py

功能
----
扫描 data_dir/{app}_dir/_inbox/，识别"归纳编码 JSON"并归位到：
    02_outline/{category}/question/inductive_q{NN}.json

识别签名（策略 A，仅看内容）：
- 文件扩展名为 .json
- 顶层为数组（list）
- 数组元素是 dict 且含 `initial_codes` 字段

身份字段：
- 数组元素的 `category` 字段决定归位的分类目录
- 优先用 outline.csv 反查 question_text -> 题号；反查不到时按
  该 category 已归位文件数 +1 编号

不符合签名的 .json 留在 inbox（其他 dispatch 脚本会忽略），
但 .csv / .txt 等其他扩展名根本不会被本脚本检查。
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

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
        "raw_outline_csv": base / "00_rawdata" / f"{app}-outline.csv",
        "outline": base / "02_outline",
    }


def sanitize_dir_name(name: str) -> str:
    safe = re.sub(r'[<>:"/\\|?*\x00-\x1F]', "_", name)
    safe = re.sub(r"_+", "_", safe).strip("_. ")
    return safe or "uncategorized"


def normalize(s: str) -> str:
    return "".join(ch for ch in s if ch.isalnum())


def read_outline(outline_csv: Path) -> Tuple[Dict[int, str], Dict[int, str]]:
    q_to_text: Dict[int, str] = {}
    q_to_cat: Dict[int, str] = {}
    with outline_csv.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        next(reader, None)
        for row in reader:
            if len(row) < 3:
                continue
            try:
                q_num = int(row[0].strip())
            except ValueError:
                continue
            q_to_cat[q_num] = row[1].strip()
            q_to_text[q_num] = row[2].strip()
    return q_to_text, q_to_cat


def lookup_q_num(question_text: str, q_to_text: Dict[int, str]) -> Optional[int]:
    if not question_text:
        return None
    target = normalize(question_text)
    best_q, best_score = None, 0.0
    for q_num, text in q_to_text.items():
        text_norm = normalize(text)
        if not text_norm:
            continue
        if target == text_norm:
            return q_num
        if target in text_norm or text_norm in target:
            inter = len(set(target) & set(text_norm))
            union = len(set(target) | set(text_norm)) or 1
            score = inter / union
            if score > best_score:
                best_score = score
                best_q = q_num
    return best_q if best_score >= 0.6 else None


def detect_inductive_json(path: Path) -> Optional[List[dict]]:
    """若文件符合归纳 JSON 签名，返回解析后的数组；否则返回 None。"""
    try:
        with path.open("r", encoding="utf-8-sig") as f:
            data = json.load(f)
    except Exception:
        return None
    if not isinstance(data, list) or not data:
        return None
    first = data[0]
    if not isinstance(first, dict) or "initial_codes" not in first:
        return None
    return data


def next_seq_for_category(question_dir: Path) -> int:
    """该 category 的 question 目录里下一个可用的两位数序号。"""
    if not question_dir.exists():
        return 1
    used = []
    for p in question_dir.glob("inductive_q*.json"):
        m = re.search(r"inductive_q(\d+)\.json$", p.name)
        if m:
            used.append(int(m.group(1)))
    return (max(used) + 1) if used else 1


def main() -> int:
    app = parse_app_name()
    paths = app_paths(app)
    print(f"=== Dispatch 归纳 JSON：{app} ===\n")

    if not paths["inbox"].exists():
        print(f"❌ 找不到 inbox：{paths['inbox']}\n   请先运行 00_init_project.py。")
        return 1
    if not paths["raw_outline_csv"].exists():
        print(f"❌ 找不到 outline：{paths['raw_outline_csv']}")
        return 1

    q_to_text, q_to_cat = read_outline(paths["raw_outline_csv"])

    json_files = sorted(paths["inbox"].glob("*.json"))
    if not json_files:
        print("inbox 中没有 .json 文件，结束。")
        return 0

    moved = 0
    skipped = 0
    errors = 0
    for jp in json_files:
        data = detect_inductive_json(jp)
        if data is None:
            print(f"  跳过（非归纳 JSON 签名）：{jp.name}")
            skipped += 1
            continue
        # 取首元素的 category 决定归位目录
        first = data[0]
        category = (first.get("category") or "").strip()
        if not category:
            print(f"  ❌ {jp.name} 缺少 category 字段，留在 inbox。")
            errors += 1
            continue
        safe_cat = sanitize_dir_name(category)
        cat_dir = paths["outline"] / safe_cat
        question_dir = cat_dir / "question"
        question_dir.mkdir(parents=True, exist_ok=True)

        # 决定题号 NN
        question_text = first.get("question_text", "")
        q_num = lookup_q_num(question_text, q_to_text)
        if q_num is None:
            q_num = next_seq_for_category(question_dir)
            print(
                f"  ℹ️  {jp.name}: 未能反查到题号，按目录顺序分配 q{q_num:02d}（category={category}）"
            )

        target = question_dir / f"inductive_q{q_num:02d}.json"
        if target.exists():
            print(f"  ⚠️  目标已存在，将覆盖：{target}")
        shutil.move(str(jp), str(target))
        print(f"  归位：{jp.name} -> {target.relative_to(paths['base'])}")
        moved += 1

    print(f"\n汇总：成功 {moved}，跳过 {skipped}，错误 {errors}。")
    return 0 if errors == 0 else 0  # 错误也不退出非零，便于其他 dispatch 继续


if __name__ == "__main__":
    sys.exit(main())
