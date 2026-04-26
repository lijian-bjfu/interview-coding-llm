#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
02_make_inductive_prompt.py

功能
----
为某个题目生成"归纳编码"用的完整 prompt。
- 列出 outline 中所有题目供用户选号
- 把 prompts/inductive_template.txt + 该题的访谈数据拼装成完整 prompt
- 写入 01_preprocessed/_prompts/inductive_q{NN}_prompt.txt
- 尝试自动复制到剪贴板（无 GUI 时降级为只写文件）

可双击运行；亦支持：
    python 02_make_inductive_prompt.py [--app <name>] [--q <num>]
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

from parameters import APP_NAME as DEFAULT_APP_NAME


# ============================================================
# 共通：路径
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR_BASE = PROJECT_ROOT / "data_dir"
TEMPLATE_PATH = PROJECT_ROOT / "prompts" / "inductive_template.txt"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--app", default=None, help="覆盖 parameters.py 的 APP_NAME")
    parser.add_argument("--q", type=int, default=None, help="题号（不填则进入交互选号）")
    args, _ = parser.parse_known_args()
    return args


def app_paths(app: str) -> dict:
    base = DATA_DIR_BASE / f"{app}_dir"
    return {
        "base": base,
        "rawdata": base / "00_rawdata",
        "raw_outline_csv": base / "00_rawdata" / f"{app}-outline.csv",
        "preprocessed": base / "01_preprocessed",
        "prompts_out": base / "01_preprocessed" / "_prompts",
        "outline": base / "02_outline",
    }


# ============================================================
# 工具：模板、剪贴板、文本清理
# ============================================================

def read_template(template_path: Path) -> str:
    """读模板：剔除以 # 开头的注释行（直到首行非注释/非空内容前的注释段）。"""
    raw = template_path.read_text(encoding="utf-8")
    lines = raw.splitlines()
    body_start = 0
    in_header = True
    for idx, line in enumerate(lines):
        if in_header and (line.startswith("#") or not line.strip()):
            continue
        body_start = idx
        in_header = False
        break
    return "\n".join(lines[body_start:]).lstrip("\n")


def copy_to_clipboard(text: str) -> bool:
    """尝试把 text 复制到系统剪贴板，成功返回 True。"""
    try:
        import platform
        import subprocess
        sys_name = platform.system()
        if sys_name == "Darwin":
            p = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
            p.communicate(text.encode("utf-8"))
            return p.returncode == 0
        if sys_name == "Windows":
            p = subprocess.Popen(["clip"], stdin=subprocess.PIPE, shell=True)
            p.communicate(text.encode("utf-16le"))
            return p.returncode == 0
        # Linux / 其他
        for cmd in (["xclip", "-selection", "clipboard"], ["xsel", "-b", "-i"]):
            try:
                p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
                p.communicate(text.encode("utf-8"))
                if p.returncode == 0:
                    return True
            except FileNotFoundError:
                continue
    except Exception:
        return False
    return False


def clean_text(s: str) -> str:
    if s is None:
        return ""
    s = str(s).replace("\\n", " ").replace("\\r", " ").replace("\n", " ").replace("\r", " ")
    s = s.replace("\\t", " ").replace("\t", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def normalize(s: str) -> str:
    return "".join(ch for ch in s if ch.isalnum())


# ============================================================
# outline / 数据
# ============================================================

def read_outline(outline_csv: Path) -> Tuple[Dict[int, str], Dict[int, str]]:
    """返回 (q_to_text, q_to_cat)。"""
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


def read_id_csv(id_csv: Path) -> Tuple[List[Dict[str, str]], List[str]]:
    with id_csv.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        cols = list(reader.fieldnames or [])
    return rows, cols


def match_column_for_question(q_text: str, csv_columns: List[str]) -> str | None:
    target = normalize(q_text)
    best, best_score = None, 0.0
    for col in csv_columns:
        col_norm = normalize(col)
        if not col_norm:
            continue
        if target in col_norm or col_norm in target:
            inter = len(set(target) & set(col_norm))
            union = len(set(target) | set(col_norm)) or 1
            score = inter / union
            if score > best_score:
                best_score = score
                best = col
    return best


def build_question_data_block(q_text: str, rows: List[Dict[str, str]], col: str) -> str:
    out: List[str] = [f"访谈问题：{q_text}", ""]
    for row in rows:
        ans = clean_text(row.get(col, ""))
        if not ans or ans.lower() == "nan":
            continue
        out.append(f"[ID:{row['_id']}] {ans}")
        out.append("")
    return "\n".join(out)


def list_outline(q_to_text: Dict[int, str], q_to_cat: Dict[int, str]) -> None:
    print("可选题目：")
    print(f"  {'题号':>4}  {'分类':<20}  问题")
    print(f"  {'-'*4:>4}  {'-'*20:<20}  {'-'*40}")
    for q_num in sorted(q_to_text.keys()):
        cat = q_to_cat.get(q_num, "")
        text = q_to_text[q_num]
        if len(text) > 60:
            text = text[:60] + "…"
        print(f"  {q_num:>4}  {cat[:20]:<20}  {text}")


def prompt_for_q(q_to_text: Dict[int, str]) -> int:
    while True:
        try:
            raw = input("\n请输入要生成 prompt 的题号：").strip()
        except EOFError:
            print("\n❌ 未读到输入，已退出。")
            sys.exit(1)
        try:
            q_num = int(raw)
        except ValueError:
            print(f"  '{raw}' 不是合法整数，请重新输入。")
            continue
        if q_num not in q_to_text:
            print(f"  题号 {q_num} 不在 outline 中，请重新输入。")
            continue
        return q_num


# ============================================================
# 主流程
# ============================================================

def main() -> int:
    args = parse_args()
    app = args.app or DEFAULT_APP_NAME
    paths = app_paths(app)

    print(f"=== 生成归纳编码 Prompt：{app} ===\n")

    if not TEMPLATE_PATH.exists():
        print(f"❌ 找不到模板文件：{TEMPLATE_PATH}")
        return 1
    if not paths["raw_outline_csv"].exists():
        print(f"❌ 找不到 outline：{paths['raw_outline_csv']}\n   请先运行 00_init_project.py。")
        return 1
    id_csv = paths["rawdata"] / f"{app}-id.csv"
    if not id_csv.exists():
        print(f"❌ 找不到 -id.csv：{id_csv}\n   请先运行 00_init_project.py。")
        return 1

    q_to_text, q_to_cat = read_outline(paths["raw_outline_csv"])
    rows, csv_cols = read_id_csv(id_csv)

    list_outline(q_to_text, q_to_cat)
    q_num = args.q if args.q is not None else prompt_for_q(q_to_text)
    if q_num not in q_to_text:
        print(f"❌ 题号 {q_num} 不在 outline 中。")
        return 1

    q_text = q_to_text[q_num]
    category = q_to_cat[q_num]

    # 找列
    other_cols = [c for c in csv_cols if c != "_id"]
    matched_col = match_column_for_question(q_text, other_cols)
    if matched_col is None:
        print(f"❌ 无法在原始 csv 中匹配到题号 {q_num} 的列。")
        return 1

    # 拼装
    template = read_template(TEMPLATE_PATH)
    data_block = build_question_data_block(q_text, rows, matched_col)
    prompt_text = template.replace("{{CATEGORY}}", category).replace(
        "{{QUESTION_DATA}}", data_block
    )

    # 写文件
    paths["prompts_out"].mkdir(parents=True, exist_ok=True)
    out_path = paths["prompts_out"] / f"inductive_q{q_num:02d}_prompt.txt"
    out_path.write_text(prompt_text, encoding="utf-8")
    print(f"\n✅ 已生成 prompt 文件：{out_path}")

    if copy_to_clipboard(prompt_text):
        print("📋 已复制到剪贴板，可直接粘贴到 LLM 对话窗口。")
    else:
        print("ℹ️  剪贴板复制失败（可能无 GUI 环境）。请手动打开上述文件复制。")

    print(f"\n下一步：把 LLM 生成的 JSON 文件丢进 _inbox/，再运行 03_dispatch_inductive.py。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
