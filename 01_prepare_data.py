#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
01_prepare_data.py

功能
----
从 00_rawdata/ 下的 -id.csv + -outline.csv 读取原始访谈数据，生成：
  - 01_preprocessed/{app}_question.txt   横向，所有问题
  - 01_preprocessed/{app}_user.txt       纵向，所有用户
  - 02_outline/{category}/ 下的 question/、user/、codebook/、recorder/ 子目录
  - 02_outline/{category}/question/{app}_question_{category}.txt
  - 02_outline/{category}/user/{app}_user_{category}.txt

输入
----
- data_dir/{app}_dir/00_rawdata/{app}-id.csv
- data_dir/{app}_dir/00_rawdata/{app}-outline.csv

数据格式
--------
- outline.csv 三列（含表头）：q_num, outlines, Questions
- 每个 question 的回答数据格式：`[ID:X] 回答内容`
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
# 共通：路径与命令行
# ============================================================

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
        "rawdata": base / "00_rawdata",
        "preprocessed": base / "01_preprocessed",
        "outline": base / "02_outline",
        "raw_id_csv": base / "00_rawdata" / f"{app}-id.csv",
        "raw_outline_csv": base / "00_rawdata" / f"{app}-outline.csv",
        "question_txt": base / "01_preprocessed" / f"{app}_question.txt",
        "user_txt": base / "01_preprocessed" / f"{app}_user.txt",
    }


# ============================================================
# 工具函数
# ============================================================

def clean_text(text: str) -> str:
    """清理回答里的换行/制表符/多余空格。"""
    if text is None:
        return ""
    s = str(text)
    s = (s.replace("\\n", " ").replace("\\r", " ")
           .replace("\n", " ").replace("\r", " ")
           .replace("\\t", " ").replace("\t", " "))
    s = re.sub(r"\s+", " ", s).strip()
    return s


def sanitize_dir_name(name: str) -> str:
    """让分类名能在所有 OS 下作为合法目录名。"""
    safe = re.sub(r'[<>:"/\\|?*\x00-\x1F]', "_", name)
    safe = re.sub(r"_+", "_", safe).strip("_. ")
    return safe or "uncategorized"


# ============================================================
# 读 outline + 数据
# ============================================================

def read_outline(outline_csv: Path) -> Tuple[Dict[int, str], Dict[int, str], Dict[str, List[int]]]:
    """
    返回:
        q_to_text:    {问题号: 问题原文}
        q_to_cat:     {问题号: 大纲分类}
        cat_to_qs:    {分类: [问题号, ...]}（按出现顺序）
    """
    q_to_text: Dict[int, str] = {}
    q_to_cat: Dict[int, str] = {}
    cat_to_qs: Dict[str, List[int]] = defaultdict(list)

    with outline_csv.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        header = next(reader, None)  # 跳过表头
        if header is None:
            raise RuntimeError(f"outline 文件为空: {outline_csv}")
        for row in reader:
            if len(row) < 3:
                continue
            q_num_raw = row[0].strip()
            category = row[1].strip()
            question = row[2].strip()
            if not q_num_raw or not category or not question:
                continue
            try:
                q_num = int(q_num_raw)
            except ValueError:
                print(f"  ⚠️  跳过 outline 中无法解析的问题号: {q_num_raw!r}")
                continue
            q_to_text[q_num] = question
            q_to_cat[q_num] = category
            if q_num not in cat_to_qs[category]:
                cat_to_qs[category].append(q_num)
    return q_to_text, q_to_cat, cat_to_qs


def normalize(s: str) -> str:
    """用于列名匹配的标准化：仅保留中英文数字。"""
    return "".join(ch for ch in s if ch.isalnum())


def read_id_csv(id_csv: Path) -> Tuple[List[Dict[str, str]], List[str]]:
    """读 -id.csv，返回 (rows, original_columns_after_id)."""
    with id_csv.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise RuntimeError(f"-id.csv 为空: {id_csv}")
        cols = list(reader.fieldnames)
        rows = list(reader)
    if "_id" not in cols:
        raise RuntimeError(f"-id.csv 缺少 _id 列: {id_csv}（请重新运行 00_init_project.py）")
    other_cols = [c for c in cols if c != "_id"]
    return rows, other_cols


def match_columns_for_questions(
    q_to_text: Dict[int, str],
    csv_columns: List[str],
) -> Dict[int, str]:
    """
    把 outline 中的每个问题号匹配到 csv 的某一列。
    匹配策略：
      1) 按出现顺序，先做"标准化包含"匹配；
      2) 一旦匹配上，把该列从候选中移除（避免多个问题号撞到同一列）。
    """
    available = list(csv_columns)
    q_to_col: Dict[int, str] = {}
    for q_num in sorted(q_to_text.keys()):
        target = normalize(q_to_text[q_num])
        best_col = None
        best_score = 0
        for col in available:
            col_norm = normalize(col)
            if not col_norm:
                continue
            if target in col_norm or col_norm in target:
                # 用集合相似度作为打分
                inter = len(set(target) & set(col_norm))
                union = len(set(target) | set(col_norm)) or 1
                score = inter / union
                if score > best_score:
                    best_score = score
                    best_col = col
        if best_col is not None:
            q_to_col[q_num] = best_col
            available.remove(best_col)
        else:
            print(f"  ⚠️  题号 {q_num} 在原始 csv 中找不到匹配列：{q_to_text[q_num][:30]}...")
    return q_to_col


# ============================================================
# 文本生成
# ============================================================

def gen_question_txt(rows: List[Dict[str, str]], q_to_text: Dict[int, str], q_to_col: Dict[int, str]) -> str:
    out: List[str] = []
    first = True
    for q_num in sorted(q_to_text.keys()):
        col = q_to_col.get(q_num)
        if col is None:
            continue
        if not first:
            out.append("---")
            out.append("")
        first = False
        out.append(q_to_text[q_num])
        out.append("")
        for row in rows:
            ans = clean_text(row.get(col, ""))
            if not ans or ans.lower() == "nan":
                continue
            out.append(f"[ID:{row['_id']}] {ans}")
            out.append("")
    return "\n".join(out)


def gen_user_txt(rows: List[Dict[str, str]], q_to_text: Dict[int, str], q_to_col: Dict[int, str]) -> str:
    out: List[str] = []
    first_user = True
    for row in rows:
        if not first_user:
            out.append("---")
            out.append("")
        first_user = False
        out.append(f"被访者：[ID:{row['_id']}]")
        out.append("")
        first_q = True
        for q_num in sorted(q_to_text.keys()):
            col = q_to_col.get(q_num)
            if col is None:
                continue
            ans = clean_text(row.get(col, ""))
            if not ans or ans.lower() == "nan":
                ans = "未回答"
            if not first_q:
                out.append("")
            first_q = False
            out.append(f"问题：{q_to_text[q_num]}")
            out.append(f"回答：{ans}")
    return "\n".join(out)


def gen_category_question_txt(
    rows: List[Dict[str, str]],
    q_nums: List[int],
    q_to_text: Dict[int, str],
    q_to_col: Dict[int, str],
) -> str:
    out: List[str] = []
    first = True
    for q_num in q_nums:
        col = q_to_col.get(q_num)
        if col is None:
            continue
        if not first:
            out.append("---")
            out.append("")
        first = False
        out.append(q_to_text[q_num])
        out.append("")
        for row in rows:
            ans = clean_text(row.get(col, ""))
            if not ans or ans.lower() == "nan":
                continue
            out.append(f"[ID:{row['_id']}] {ans}")
            out.append("")
    return "\n".join(out)


def gen_category_user_txt(
    rows: List[Dict[str, str]],
    q_nums: List[int],
    q_to_text: Dict[int, str],
    q_to_col: Dict[int, str],
) -> str:
    out: List[str] = []
    first_user = True
    for row in rows:
        block: List[str] = [f"被访者：[ID:{row['_id']}]", ""]
        wrote_any = False
        first_q = True
        for q_num in q_nums:
            col = q_to_col.get(q_num)
            if col is None:
                continue
            ans = clean_text(row.get(col, ""))
            if not ans or ans.lower() == "nan":
                continue
            if not first_q:
                block.append("")
            first_q = False
            block.append(f"问题：{q_to_text[q_num]}")
            block.append(f"回答：{ans}")
            wrote_any = True
        if not wrote_any:
            continue
        if not first_user:
            out.append("---")
            out.append("")
        first_user = False
        out.extend(block)
    return "\n".join(out)


# ============================================================
# 主流程
# ============================================================

def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"  写入: {path}")


def main() -> int:
    app = parse_app_name()
    paths = app_paths(app)
    print(f"=== 预处理数据：{app} ===\n")

    if not paths["raw_id_csv"].exists():
        print(f"❌ 找不到 {paths['raw_id_csv']}\n   请先运行 00_init_project.py。")
        return 1
    if not paths["raw_outline_csv"].exists():
        print(f"❌ 找不到 {paths['raw_outline_csv']}\n   请先运行 00_init_project.py。")
        return 1

    print("[1/4] 读取大纲与原始数据 ...")
    q_to_text, q_to_cat, cat_to_qs = read_outline(paths["raw_outline_csv"])
    rows, csv_cols = read_id_csv(paths["raw_id_csv"])
    print(f"  outline 中共有 {len(q_to_text)} 个问题，{len(cat_to_qs)} 个分类。")
    print(f"  原始数据共有 {len(rows)} 行受访者。")
    print()

    print("[2/4] 把 outline 问题文本匹配到 csv 列 ...")
    q_to_col = match_columns_for_questions(q_to_text, csv_cols)
    print(f"  匹配上 {len(q_to_col)}/{len(q_to_text)} 题。")
    print()

    print("[3/4] 生成总览 question.txt 与 user.txt ...")
    write_text(paths["question_txt"], gen_question_txt(rows, q_to_text, q_to_col))
    write_text(paths["user_txt"], gen_user_txt(rows, q_to_text, q_to_col))
    print()

    print("[4/4] 为每个分类生成子目录与 question/user 文本 ...")
    for category, q_nums in cat_to_qs.items():
        safe_cat = sanitize_dir_name(category)
        cat_dir = paths["outline"] / safe_cat
        sub_question = cat_dir / "question"
        sub_user = cat_dir / "user"
        sub_codebook = cat_dir / "codebook"
        sub_recorder = cat_dir / "recorder"
        for d in (sub_question, sub_user, sub_codebook, sub_recorder):
            d.mkdir(parents=True, exist_ok=True)

        # 注意：文件名沿用原始 category（不做 sanitize），便于人眼对照。
        # 若分类名含有非法路径字符，文件名也会被自动写入相应目录。
        # TODO: 如未来分类名包含路径分隔符等情况，需要在此扩展处理。
        q_path = sub_question / f"{app}_question_{safe_cat}.txt"
        u_path = sub_user / f"{app}_user_{safe_cat}.txt"
        write_text(q_path, gen_category_question_txt(rows, q_nums, q_to_text, q_to_col))
        write_text(u_path, gen_category_user_txt(rows, q_nums, q_to_text, q_to_col))
    print()

    print("✅ 数据预处理完成。下一步请运行 02_make_inductive_prompt.py 生成首题归纳 prompt。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
