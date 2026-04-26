#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
04_make_summary_prompt.py

功能
----
生成"让 LLM 总结当前对话"的提示词（无需拼接数据，是一段纯指令）。
- 把 prompts/summary_template.txt 读出来
- print 到终端
- 写入 01_preprocessed/_prompts/summary_prompt.txt
- 尝试自动复制到剪贴板
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from parameters import APP_NAME as DEFAULT_APP_NAME


PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR_BASE = PROJECT_ROOT / "data_dir"
TEMPLATE_PATH = PROJECT_ROOT / "prompts" / "summary_template.txt"


def parse_app_name() -> str:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--app", default=None, help="覆盖 parameters.py 的 APP_NAME")
    args, _ = parser.parse_known_args()
    return args.app or DEFAULT_APP_NAME


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


def main() -> int:
    app = parse_app_name()
    print(f"=== 生成对话总结 Prompt：{app} ===\n")

    if not TEMPLATE_PATH.exists():
        print(f"❌ 找不到模板文件：{TEMPLATE_PATH}")
        return 1

    text = read_template(TEMPLATE_PATH)

    out_dir = DATA_DIR_BASE / f"{app}_dir" / "01_preprocessed" / "_prompts"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "summary_prompt.txt"
    out_path.write_text(text, encoding="utf-8")

    print("--- 总结 Prompt 内容（亦可在文件中查看） ---\n")
    print(text)
    print("\n--- 内容结束 ---")
    print(f"\n✅ 已写入：{out_path}")

    if copy_to_clipboard(text):
        print("📋 已复制到剪贴板，可直接粘贴到 LLM 对话窗口。")
    else:
        print("ℹ️  剪贴板复制失败（可能无 GUI 环境）。请手动从上述文件复制。")

    print("\n下一步：把 LLM 输出的总结 .txt 丢进 _inbox/，再运行 05_dispatch_summary.py。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
