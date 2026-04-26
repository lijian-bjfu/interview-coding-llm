#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
06_create_raw_codebook.py

功能
----
合并所有归纳编码 JSON，并为每个 category 生成 raw_codebook（中间档案）。

输入
----
- 02_outline/{category}/question/inductive_q*.json  （所有 category 所有题）

输出
----
- 01_preprocessed/{app}_inductive_merged.json   合并大档案
- 02_outline/{category}/codebook/raw_codebook_{category}.csv

raw_codebook 列：
- code_name, definition, theme, source_question,
  frequency_in_question, representative_quotes

raw_codebook 不带 `# category=...` 注释行（这是程序产物，不进 inbox 流程）。
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

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
        "preprocessed": base / "01_preprocessed",
        "outline": base / "02_outline",
        "merged_json": base / "01_preprocessed" / f"{app}_inductive_merged.json",
    }


def extract_q_num(file_name: str) -> int:
    m = re.search(r"inductive_q(\d+)\.json$", file_name)
    return int(m.group(1)) if m else 10**6


def extract_codes_from_question(qdata: dict) -> List[Dict]:
    """从一个题目的 JSON 数据中抽出编码条目列表。"""
    question_text = qdata.get("question_text", "未知问题")
    theme_map: Dict[str, str] = {}
    for theme in qdata.get("themes", []) or []:
        tname = theme.get("theme_name", "N/A")
        for ic in theme.get("included_initial_codes", []) or []:
            theme_map[ic] = tname

    out: List[Dict] = []
    for code in qdata.get("codes", []) or []:
        code_name = code.get("code_name")
        if not code_name:
            continue
        entry = {
            "code_name": code_name,
            "definition": code.get("code_definition", ""),
            "theme": theme_map.get(code_name, "N/A"),
            "source_question": question_text,
            "frequency_in_question": 0,
            "representative_quotes": [],
        }
        # 统计频次 + 收集引文
        for resp in qdata.get("initial_codes", []) or []:
            names = resp.get("code_name", []) or []
            quotes = resp.get("supporting_quote", []) or []
            pairs = resp.get("pairs", []) or []
            if code_name in names:
                entry["frequency_in_question"] += 1
                try:
                    code_idx = names.index(code_name)
                    for pair in pairs:
                        if "-" not in pair:
                            continue
                        try:
                            p_code, p_quote = (int(x) for x in pair.split("-", 1))
                        except ValueError:
                            continue
                        if p_code - 1 == code_idx and 1 <= p_quote <= len(quotes):
                            entry["representative_quotes"].append(quotes[p_quote - 1])
                except Exception:
                    # TODO: pairs 字段格式异常时保守跳过
                    pass
        out.append(entry)
    return out


def merge_same_named_codes(entries: List[Dict]) -> List[Dict]:
    """同一 code_name 在同一 category 下出现多次：合并 frequency 与 quotes。"""
    merged: Dict[str, Dict] = {}
    order: List[str] = []
    for e in entries:
        key = e["code_name"]
        if key not in merged:
            merged[key] = {
                "code_name": key,
                "definition": e["definition"],
                "theme": e["theme"],
                "source_question": e["source_question"],
                "frequency_in_question": e["frequency_in_question"],
                "representative_quotes": list(e["representative_quotes"]),
            }
            order.append(key)
        else:
            cur = merged[key]
            cur["frequency_in_question"] += e["frequency_in_question"]
            cur["representative_quotes"].extend(e["representative_quotes"])
            # 来源题/定义/主题不同时，用 " | " 串联
            if e["source_question"] not in cur["source_question"]:
                cur["source_question"] += " | " + e["source_question"]
            if e["definition"] and e["definition"] not in cur["definition"]:
                cur["definition"] = (cur["definition"] + " | " + e["definition"]).strip(" |")
            if e["theme"] and e["theme"] not in cur["theme"]:
                cur["theme"] = (cur["theme"] + " | " + e["theme"]).strip(" |")
    return [merged[k] for k in order]


def write_codebook_csv(out_path: Path, entries: List[Dict]) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cols = [
        "code_name",
        "definition",
        "theme",
        "source_question",
        "frequency_in_question",
        "representative_quotes",
    ]
    with out_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for e in entries:
            quotes_str = " || ".join(q.replace("\n", " ").strip() for q in e["representative_quotes"])
            w.writerow([
                e["code_name"],
                e["definition"],
                e["theme"],
                e["source_question"],
                e["frequency_in_question"],
                quotes_str,
            ])


def main() -> int:
    app = parse_app_name()
    paths = app_paths(app)
    print(f"=== 构建 raw_codebook：{app} ===\n")

    if not paths["outline"].exists():
        print(f"❌ 找不到 02_outline 目录：{paths['outline']}")
        return 1

    merged_all: List[dict] = []
    cats_seen = 0
    cats_built = 0

    for cat_dir in sorted(p for p in paths["outline"].iterdir() if p.is_dir()):
        category = cat_dir.name
        cats_seen += 1
        question_dir = cat_dir / "question"
        if not question_dir.exists():
            print(f"  分类 '{category}' 下无 question/ 目录，跳过。")
            continue

        json_files = sorted(question_dir.glob("inductive_q*.json"), key=lambda p: extract_q_num(p.name))
        if not json_files:
            print(f"  分类 '{category}' 下无归纳 JSON，跳过。")
            continue

        all_entries: List[Dict] = []
        for jp in json_files:
            try:
                with jp.open("r", encoding="utf-8-sig") as f:
                    arr = json.load(f)
            except Exception as e:
                print(f"  ⚠️  解析失败：{jp.name}：{e}")
                continue
            if not isinstance(arr, list):
                continue
            for qdata in arr:
                if not isinstance(qdata, dict):
                    continue
                merged_all.append(qdata)
                all_entries.extend(extract_codes_from_question(qdata))

        if not all_entries:
            print(f"  分类 '{category}' 提取到 0 个编码，跳过 raw_codebook 生成。")
            continue

        merged_entries = merge_same_named_codes(all_entries)
        out_path = cat_dir / "codebook" / f"raw_codebook_{category}.csv"
        write_codebook_csv(out_path, merged_entries)
        print(f"  分类 '{category}' raw_codebook 写入：{out_path.relative_to(paths['base'])}（{len(merged_entries)} 行）")
        cats_built += 1

    # 写 merged json
    paths["merged_json"].parent.mkdir(parents=True, exist_ok=True)
    paths["merged_json"].write_text(
        json.dumps(merged_all, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\n  合并大档案写入：{paths['merged_json'].relative_to(paths['base'])}")

    print(f"\n汇总：扫描分类 {cats_seen} 个，生成 raw_codebook {cats_built} 份。")
    print("下一步：选某个 category 运行 07_make_codebook_prompt.py 生成精炼 prompt。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
