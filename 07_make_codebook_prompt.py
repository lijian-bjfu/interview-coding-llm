#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
07_make_codebook_prompt.py

功能
----
为某个大纲分类生成"精炼编码本"用的 prompt（拼接 raw_codebook + 模板）。
- 列出所有已有 raw_codebook 的 category 让用户选
- 拼装 prompts/codebook_template.txt + raw_codebook_{category}.csv
- 写入 01_preprocessed/_prompts/codebook_{category}_prompt.txt
- 尝试自动复制到剪贴板
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Dict, List

from parameters import APP_NAME as DEFAULT_APP_NAME


PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR_BASE = PROJECT_ROOT / "data_dir"
TEMPLATE_PATH = PROJECT_ROOT / "prompts" / "codebook_template.txt"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--app", default=None, help="覆盖 parameters.py 的 APP_NAME")
    parser.add_argument("--category", default=None, help="目标分类名（不填则进入交互选号）")
    args, _ = parser.parse_known_args()
    return args


def app_paths(app: str) -> dict:
    base = DATA_DIR_BASE / f"{app}_dir"
    return {
        "base": base,
        "outline": base / "02_outline",
        "prompts_out": base / "01_preprocessed" / "_prompts",
    }


def read_template(template_path: Path) -> str:
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
    try:
        import platform
        sys_name = platform.system()
        if sys_name == "Darwin":
            p = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
            p.communicate(text.encode("utf-8"))
            return p.returncode == 0
        if sys_name == "Windows":
            p = subprocess.Popen(["clip"], stdin=subprocess.PIPE, shell=True)
            p.communicate(text.encode("utf-16le"))
            return p.returncode == 0
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


def find_categories_with_raw(outline_root: Path) -> Dict[str, Path]:
    """返回 {category: raw_codebook_csv_path} 字典。"""
    out: Dict[str, Path] = {}
    if not outline_root.exists():
        return out
    for cat_dir in sorted(p for p in outline_root.iterdir() if p.is_dir()):
        cb_csv = cat_dir / "codebook" / f"raw_codebook_{cat_dir.name}.csv"
        if cb_csv.exists():
            out[cat_dir.name] = cb_csv
    return out


def prompt_for_category(cats: List[str]) -> str:
    print("可选 category（已有 raw_codebook）：")
    for i, c in enumerate(cats, 1):
        print(f"  [{i}] {c}")
    while True:
        try:
            raw = input("\n请输入序号或 category 名：").strip()
        except EOFError:
            print("\n❌ 未读到输入，已退出。")
            sys.exit(1)
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(cats):
                return cats[idx]
            print("  序号超出范围。")
            continue
        if raw in cats:
            return raw
        print(f"  '{raw}' 不在候选 category 列表中。")


def main() -> int:
    args = parse_args()
    app = args.app or DEFAULT_APP_NAME
    paths = app_paths(app)
    print(f"=== 生成精炼编码本 Prompt：{app} ===\n")

    if not TEMPLATE_PATH.exists():
        print(f"❌ 找不到模板：{TEMPLATE_PATH}")
        return 1
    cats_map = find_categories_with_raw(paths["outline"])
    if not cats_map:
        print("❌ 没有任何分类下存在 raw_codebook，请先运行 06_create_raw_codebook.py。")
        return 1

    cats = sorted(cats_map.keys())
    category = args.category if args.category else prompt_for_category(cats)
    if category not in cats_map:
        print(f"❌ 分类 '{category}' 没有 raw_codebook，请先运行 06。")
        return 1

    raw_csv_text = cats_map[category].read_text(encoding="utf-8-sig")
    template = read_template(TEMPLATE_PATH)
    prompt_text = template.replace("{{CATEGORY}}", category).replace(
        "{{RAW_CODEBOOK_CSV}}", raw_csv_text
    )

    paths["prompts_out"].mkdir(parents=True, exist_ok=True)
    out_path = paths["prompts_out"] / f"codebook_{category}_prompt.txt"
    out_path.write_text(prompt_text, encoding="utf-8")
    print(f"\n✅ 已生成 prompt 文件：{out_path}")

    if copy_to_clipboard(prompt_text):
        print("📋 已复制到剪贴板，可直接粘贴到 LLM 对话窗口。")
    else:
        print("ℹ️  剪贴板复制失败（可能无 GUI 环境）。请手动从上述文件复制。")

    print(f"\n下一步：把 LLM 输出的精炼编码本 CSV 丢进 _inbox/，再运行 08_dispatch_codebook.py。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
