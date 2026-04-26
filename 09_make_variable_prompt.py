#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
09_make_variable_prompt.py

功能
----
为指定的若干受访者 ID，生成"变量提取"用的 prompt。

输入
----
- prompts/variable_template.txt
- 00_rawdata/{app}_user_var.csv         # 变量定义（必需）
- 01_preprocessed/{app}_user.txt        # 按用户组织的纵向数据
- 用户输入：一个或多个受访者 ID（逗号分隔）

输出
----
- 01_preprocessed/_prompts/variable_u{IDS}_prompt.txt
- 复制到剪贴板（可用时）

变量定义 CSV 约定
----------------
- 第一列固定为 `变量名`
- 其余列若包含 `类型`/`说明`/`取值范围` 等会原样作为提取规则的一部分
  说明文字（脚本不强制列名）。
"""

from __future__ import annotations

import argparse
import csv
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple

from parameters import APP_NAME as DEFAULT_APP_NAME


PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR_BASE = PROJECT_ROOT / "data_dir"
TEMPLATE_PATH = PROJECT_ROOT / "prompts" / "variable_template.txt"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--app", default=None, help="覆盖 parameters.py 的 APP_NAME")
    parser.add_argument(
        "--ids",
        default=None,
        help="逗号分隔的受访者 ID 列表（不填则交互输入）",
    )
    args, _ = parser.parse_known_args()
    return args


def app_paths(app: str) -> dict:
    base = DATA_DIR_BASE / f"{app}_dir"
    return {
        "base": base,
        "raw_uservar_csv": base / "00_rawdata" / f"{app}_user_var.csv",
        "user_txt": base / "01_preprocessed" / f"{app}_user.txt",
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


def read_var_defs(uservar_csv: Path) -> Tuple[List[str], List[Dict[str, str]]]:
    """
    读取变量定义 CSV，返回:
        var_names:  变量名列表（按出现顺序）
        defs:       每个变量的完整字段字典列表
    """
    with uservar_csv.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise RuntimeError(f"变量定义 CSV 为空：{uservar_csv}")
        cols = list(reader.fieldnames)
        if cols[0].strip() != "变量名":
            print(f"  ⚠️  变量定义 CSV 首列不是 '变量名'（当前为 '{cols[0]}'），已按首列作为变量名处理。")
        rows = list(reader)
    var_names: List[str] = []
    defs: List[Dict[str, str]] = []
    for r in rows:
        # 取首列作为变量名
        name = (r.get(cols[0]) or "").strip()
        if not name:
            continue
        var_names.append(name)
        defs.append({k: (v or "").strip() for k, v in r.items()})
    return var_names, defs


def render_var_definitions(defs: List[Dict[str, str]], cols: List[str]) -> str:
    """把变量定义渲染成 prompt 中的"提取规则"自然语言段。"""
    out: List[str] = []
    for i, d in enumerate(defs, 1):
        name = d.get(cols[0], "").strip()
        extras = []
        for c in cols[1:]:
            v = d.get(c, "").strip()
            if v:
                extras.append(f"{c}={v}")
        extras_str = ("（" + "；".join(extras) + "）") if extras else ""
        out.append(f"{i}. {name}{extras_str}")
    return "\n".join(out)


def parse_user_blocks(user_txt: Path) -> Dict[int, str]:
    """
    解析 user.txt，按 `---` 分隔，返回 {id_int: block_text}。
    每个 block 形如：
        被访者：[ID:1]

        问题：...
        回答：...
        ...
    """
    text = user_txt.read_text(encoding="utf-8")
    blocks = re.split(r"\n-{3,}\n", text)
    result: Dict[int, str] = {}
    for blk in blocks:
        m = re.search(r"\[ID:(\d+)\]", blk)
        if not m:
            continue
        try:
            uid = int(m.group(1))
        except ValueError:
            continue
        result[uid] = blk.strip()
    return result


def prompt_for_ids() -> List[int]:
    while True:
        try:
            raw = input("请输入受访者 ID（多个用英文逗号分隔，如 1,2,3）：").strip()
        except EOFError:
            print("\n❌ 未读到输入，已退出。")
            sys.exit(1)
        if not raw:
            print("  输入为空。")
            continue
        try:
            ids = [int(x.strip()) for x in raw.split(",") if x.strip()]
            if ids:
                return ids
        except ValueError:
            pass
        print(f"  无法解析为整数 ID 列表：{raw!r}，请重新输入。")


def main() -> int:
    args = parse_args()
    app = args.app or DEFAULT_APP_NAME
    paths = app_paths(app)
    print(f"=== 生成变量提取 Prompt：{app} ===\n")

    if not TEMPLATE_PATH.exists():
        print(f"❌ 找不到模板：{TEMPLATE_PATH}")
        return 1
    if not paths["raw_uservar_csv"].exists():
        print(
            f"❌ 找不到变量定义 CSV：{paths['raw_uservar_csv']}\n"
            f"   请先把 {app}_user_var.csv 放到 00_rawdata/ 下（再次运行 00_init_project.py 也会归位）。"
        )
        return 1
    if not paths["user_txt"].exists():
        print(
            f"❌ 找不到 user.txt：{paths['user_txt']}\n"
            f"   请先运行 01_prepare_data.py。"
        )
        return 1

    var_names, defs = read_var_defs(paths["raw_uservar_csv"])
    if not var_names:
        print(f"❌ 变量定义 CSV 没有任何有效变量行。")
        return 1
    cols = list(defs[0].keys()) if defs else ["变量名"]

    user_blocks = parse_user_blocks(paths["user_txt"])
    if not user_blocks:
        print(f"❌ user.txt 中未解析出任何受访者块。")
        return 1

    available_ids = sorted(user_blocks.keys())
    print(f"可用受访者 ID：{available_ids}\n")

    if args.ids:
        try:
            ids = [int(x.strip()) for x in args.ids.split(",") if x.strip()]
        except ValueError:
            print(f"❌ --ids 参数格式错误：{args.ids}")
            return 1
    else:
        ids = prompt_for_ids()

    missing = [i for i in ids if i not in user_blocks]
    if missing:
        print(f"❌ 以下 ID 在 user.txt 中找不到：{missing}")
        return 1

    var_def_text = render_var_definitions(defs, cols)
    var_columns = ",".join(["文件名"] + var_names)
    interview_text = "\n\n---\n\n".join(user_blocks[i] for i in ids)

    template = read_template(TEMPLATE_PATH)
    prompt_text = (
        template
        .replace("{{VARIABLE_DEFINITIONS}}", var_def_text)
        .replace("{{VARIABLE_COLUMNS}}", var_columns)
        .replace("{{USER_INTERVIEW_DATA}}", interview_text)
    )

    paths["prompts_out"].mkdir(parents=True, exist_ok=True)
    ids_tag = "_".join(str(i) for i in ids)
    out_path = paths["prompts_out"] / f"variable_u{ids_tag}_prompt.txt"
    out_path.write_text(prompt_text, encoding="utf-8")
    print(f"\n✅ 已生成 prompt 文件：{out_path}")

    if copy_to_clipboard(prompt_text):
        print("📋 已复制到剪贴板，可直接粘贴到 LLM 对话窗口。")
    else:
        print("ℹ️  剪贴板复制失败（可能无 GUI 环境）。请手动从上述文件复制。")

    print("\n下一步：把 LLM 输出的变量 CSV 丢进 _inbox/，再运行 10_dispatch_variables.py。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
