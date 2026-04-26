#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
00_init_project.py

功能
----
初始化某个产品（APP_NAME）的项目目录结构，并把用户预先放在项目根目录
下的原始文件归位到 00_rawdata/。

输入
----
- parameters.py 的 APP_NAME（可被 --app 覆盖）
- 项目根目录下的：
    {APP_NAME}.csv             # 原始访谈数据（必需）
    {APP_NAME}-outline.csv     # 大纲定义     （必需）
    {APP_NAME}_user_var.csv    # 变量定义     （可选）

输出
----
- data_dir/{APP_NAME}_dir/ 目录树：
    _inbox/
    00_rawdata/
    01_preprocessed/
    02_outline/
    03_variables/raw/
- 把根目录的 csv 移动到 00_rawdata/
- 生成 {APP_NAME}-id.csv（首列加 _id 内部 ID）

可双击运行（VSCode "Run Python File"），亦支持命令行：
    python 00_init_project.py [--app <name>]
"""

from __future__ import annotations

import argparse
import csv
import shutil
import sys
from pathlib import Path

from parameters import APP_NAME as DEFAULT_APP_NAME


# ============================================================
# 共通：路径与命令行
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR_BASE = PROJECT_ROOT / "data_dir"


def parse_app_name() -> str:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument(
        "--app",
        default=None,
        help="覆盖 parameters.py 中的 APP_NAME（可选）",
    )
    args, _ = parser.parse_known_args()
    return args.app or DEFAULT_APP_NAME


def app_paths(app: str) -> dict:
    """返回该产品下所有关键路径（pathlib.Path 对象）。"""
    base = DATA_DIR_BASE / f"{app}_dir"
    return {
        "base": base,
        "inbox": base / "_inbox",
        "rawdata": base / "00_rawdata",
        "preprocessed": base / "01_preprocessed",
        "preprocessed_prompts": base / "01_preprocessed" / "_prompts",
        "outline": base / "02_outline",
        "variables": base / "03_variables",
        "variables_raw": base / "03_variables" / "raw",
        # 原始数据三件套
        "raw_csv": base / "00_rawdata" / f"{app}.csv",
        "raw_id_csv": base / "00_rawdata" / f"{app}-id.csv",
        "raw_outline_csv": base / "00_rawdata" / f"{app}-outline.csv",
        "raw_uservar_csv": base / "00_rawdata" / f"{app}_user_var.csv",
    }


# ============================================================
# 主流程
# ============================================================

def ensure_dir(path: Path) -> None:
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
        print(f"  创建目录: {path}")
    else:
        print(f"  已存在: {path}")


def move_if_present(src: Path, dst: Path) -> None:
    """把 src 移动到 dst；若 src 不存在但 dst 已存在，则跳过。"""
    if dst.exists():
        print(f"  目标已存在，跳过移动: {dst.name}")
        return
    if src.exists():
        shutil.move(str(src), str(dst))
        print(f"  移动: {src.name} -> {dst}")
    else:
        # src 也不在；仅当是必须文件时由调用方报错
        pass


def add_internal_id(src_csv: Path, dst_csv: Path) -> None:
    """读取 src_csv，在最左边插入一列 _id（从 1 起递增），写出到 dst_csv。"""
    if dst_csv.exists():
        print(f"  {dst_csv.name} 已存在，跳过 ID 生成。")
        return
    with src_csv.open("r", encoding="utf-8-sig", newline="") as fin:
        reader = csv.reader(fin)
        rows = list(reader)
    if not rows:
        print(f"  ⚠️  {src_csv.name} 为空，无法生成 -id.csv。")
        return
    header = ["_id"] + rows[0]
    new_rows = [header]
    for idx, row in enumerate(rows[1:], start=1):
        new_rows.append([str(idx)] + row)
    with dst_csv.open("w", encoding="utf-8-sig", newline="") as fout:
        writer = csv.writer(fout)
        writer.writerows(new_rows)
    print(f"  生成内部 ID 文件: {dst_csv.name}（{len(new_rows) - 1} 行）")


def main() -> int:
    app = parse_app_name()
    paths = app_paths(app)

    print(f"=== 初始化项目：{app} ===\n")

    # 1) 建立目录树
    print("[1/3] 创建目录结构 ...")
    for key in (
        "base",
        "inbox",
        "rawdata",
        "preprocessed",
        "preprocessed_prompts",
        "outline",
        "variables",
        "variables_raw",
    ):
        ensure_dir(paths[key])
    # 02_outline/ 下的 category 子目录留给 01_prepare_data.py 创建
    print()

    # 2) 把根目录下的原始 csv 移动到 00_rawdata/
    print("[2/3] 归位根目录原始数据 ...")
    raw_src = PROJECT_ROOT / f"{app}.csv"
    outline_src = PROJECT_ROOT / f"{app}-outline.csv"
    uservar_src = PROJECT_ROOT / f"{app}_user_var.csv"

    move_if_present(raw_src, paths["raw_csv"])
    move_if_present(outline_src, paths["raw_outline_csv"])
    move_if_present(uservar_src, paths["raw_uservar_csv"])

    if not paths["raw_csv"].exists():
        print(
            f"\n❌ 找不到原始访谈数据：{app}.csv\n"
            f"   请把 {app}.csv 放在项目根目录（或 00_rawdata/ 下），再次运行本脚本。"
        )
        return 1
    if not paths["raw_outline_csv"].exists():
        print(
            f"\n❌ 找不到大纲文件：{app}-outline.csv\n"
            f"   请把 {app}-outline.csv 放在项目根目录（或 00_rawdata/ 下），再次运行本脚本。"
        )
        return 1
    if not paths["raw_uservar_csv"].exists():
        print(
            f"  ℹ️  未发现变量定义文件 {app}_user_var.csv，变量提取流程将不可用（可选功能）。"
        )
    print()

    # 3) 生成 -id.csv
    print("[3/3] 生成内部 ID 文件 ...")
    add_internal_id(paths["raw_csv"], paths["raw_id_csv"])
    print()

    print(f"✅ 初始化完成。下一步请运行 01_prepare_data.py 生成 LLM 用文本。")
    print(f"   产品根目录: {paths['base']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
