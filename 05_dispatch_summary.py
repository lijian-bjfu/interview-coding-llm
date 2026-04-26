#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
05_dispatch_summary.py

功能
----
扫描 _inbox/，识别"对话总结 TXT"并归位到：
    02_outline/{category}/recorder/sum_{stage}_{NN}.txt

识别签名：
- 文件扩展名为 .txt
- 首行以 `# stage=` 开头，且包含 `category=` 字段（任意顺序）

NN 编号规则：
- 全局递增：扫描所有 category 的 recorder/ 下已有 sum_{stage}_*.txt，
  取最大 NN +1（跨 category 全局唯一）。
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path
from typing import Optional, Tuple

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


def parse_first_line(line: str) -> Tuple[Optional[str], Optional[str]]:
    """
    解析形如 `# category=xxx, stage=ind`，返回 (category, stage)。
    解析失败返回 (None, None)。
    """
    if not line.startswith("#"):
        return None, None
    body = line.lstrip("#").strip()
    fields = {}
    for chunk in re.split(r"[,;]", body):
        if "=" in chunk:
            k, v = chunk.split("=", 1)
            fields[k.strip().lower()] = v.strip()
    cat = fields.get("category")
    stage = fields.get("stage")
    if not cat or not stage:
        return None, None
    return cat, stage


def detect_summary_txt(path: Path) -> Tuple[Optional[str], Optional[str]]:
    """读首行，按签名解析。返回 (category, stage)，失败返回 (None, None)。"""
    try:
        with path.open("r", encoding="utf-8-sig") as f:
            first = f.readline().strip()
    except Exception:
        return None, None
    if not first.startswith("#") or "stage=" not in first:
        return None, None
    return parse_first_line(first)


def next_global_seq(outline_root: Path, stage: str) -> int:
    """跨 category 扫描所有 recorder/sum_{stage}_*.txt，返回下一个序号。"""
    if not outline_root.exists():
        return 1
    used = []
    pattern = re.compile(rf"sum_{re.escape(stage)}_(\d+)\.txt$")
    for cat_dir in outline_root.iterdir():
        rec_dir = cat_dir / "recorder"
        if not rec_dir.exists():
            continue
        for p in rec_dir.glob(f"sum_{stage}_*.txt"):
            m = pattern.search(p.name)
            if m:
                used.append(int(m.group(1)))
    return (max(used) + 1) if used else 1


def main() -> int:
    app = parse_app_name()
    paths = app_paths(app)
    print(f"=== Dispatch 总结 TXT：{app} ===\n")

    if not paths["inbox"].exists():
        print(f"❌ 找不到 inbox：{paths['inbox']}")
        return 1

    txt_files = sorted(paths["inbox"].glob("*.txt"))
    if not txt_files:
        print("inbox 中没有 .txt 文件，结束。")
        return 0

    moved = 0
    skipped = 0
    errors = 0

    for tp in txt_files:
        category, stage = detect_summary_txt(tp)
        if category is None or stage is None:
            print(f"  跳过（首行不符合 stage= 签名）：{tp.name}")
            skipped += 1
            continue

        safe_cat = sanitize_dir_name(category)
        cat_dir = paths["outline"] / safe_cat
        if not cat_dir.exists():
            print(
                f"  ❌ {tp.name} 指定 category='{category}' 但 02_outline 下不存在该分类目录。"
                f"\n      （可能是 LLM 拼错了分类名；请检查 outline 或修改 LLM 输出。文件留在 inbox。）"
            )
            errors += 1
            continue

        rec_dir = cat_dir / "recorder"
        rec_dir.mkdir(parents=True, exist_ok=True)
        nn = next_global_seq(paths["outline"], stage)
        target = rec_dir / f"sum_{stage}_{nn:02d}.txt"
        shutil.move(str(tp), str(target))
        print(
            f"  归位：{tp.name} -> {target.relative_to(paths['base'])}"
            f"   (category={category}, stage={stage}, NN={nn:02d})"
        )
        moved += 1

    print(f"\n汇总：成功 {moved}，跳过 {skipped}，错误 {errors}。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
