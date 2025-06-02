"""
build_codebook_raw.py (主脚本执行)
    │
    ├── // 1. 导入 parameters.py 中的 file_dir, app
    │   //    (打印导入成功或失败/使用默认值的宏观信息)
    │
    ├── // 2. 定义要处理的分组配置 (groups_to_process_config)
    │   //    (例如："user_states": {"json_dir_key": "json_g1", "output_txt_key": "txt_g1"}, ...)
    │
    ├── // 3. 从 file_dir 获取通用的独立JSON文件名模式 (individual_json_file_pattern)
    │
    └── (对于 groups_to_process_config 中的每个 group_name, group_config): // 外层循环：遍历每个问题分组
        │
        ├── group_json_dir_path = file_dir[group_config['json_dir_key']]
        ├── output_txt_filepath = file_dir[group_config['output_txt_key']]
        ├── (打印 "正在处理分组: {group_name}")
        │
        ├── // 3a. 检查分组的JSON输入目录是否存在
        │   └── (如果目录不存在，打印警告，跳过此分组，继续下一个分组)
        │
        ├── full_pattern_for_group = os.path.join(group_json_dir_path, individual_json_file_pattern)
        ├── json_files_in_group = sorted(glob.glob(full_pattern_for_group)) // 查找并排序该组的独立JSON文件
        │
        ├── (如果 json_files_in_group 为空，打印警告，跳过此分组的后续处理)
        │
        ├── all_codebook_entries_for_this_group = [] // 初始化用于存储该组所有TXT编码条目的列表
        │
        ├── (对于 json_files_in_group 中的每个 json_filepath): // 中层循环：遍历该分组内的每个独立JSON文件 (每个文件代表一个问题)
        │   │
        │   ├── (打印 "正在处理JSON文件: {os.path.basename(json_filepath)}")
        │   ├── 读取并解析 json_filepath 的内容 (data)
        │   │   └── (处理可能的JSON解析错误)
        │   │
        │   ├── // 3b. 处理JSON顶层结构 (可能是列表 `[{...}]` 或直接是对象 `{...}`)
        │   │   └── (提取出实际的问题分析对象列表 `question_analysis_list`，通常只有一个元素)
        │   │
        │   └── (对于 question_analysis_list 中的每个 question_data): // 通常这个循环只执行一次
        │       │
        │       ├── current_question_text = question_data.get("question_text", "未知问题")
        │       ├── codes_and_quotes_list = question_data.get("codes_and_quotes", [])
        │       │
        │       ├── (如果 codes_and_quotes_list 为空，打印提示，跳过此问题的后续处理)
        │       │
        │       └── (对于 codes_and_quotes_list 中的每个 code_info): // 内层循环：遍历一个问题下的每个“编码块”
        │           │
        │           ├── code_name = code_info.get("code_name", "未命名编码")
        │           ├── code_definition = code_info.get("code_definition", "未提供定义")
        │           ├── excerpts_list = code_info.get("excerpts", [])
        │           │
        │           ├── selected_excerpts_formatted = select_excerpts_for_codebook(excerpts_list, num_to_select=3)
        │           │   └── (内部逻辑：随机选取或全选，并格式化为 "引文 (ID: X)")
        │           │
        │           ├── txt_codebook_entry = format_codebook_entry_to_txt(
        │           │   │                               code_name,
        │           │   │                               code_definition,
        │           │   │                               current_question_text, // 编码的来源问题
        │           │   │                               selected_excerpts_formatted
        │           │   │                           )
        │           │   └── (内部逻辑：将上述信息格式化为您期望的TXT条目字符串)
        │           │
        │           └── all_codebook_entries_for_this_group.append(txt_codebook_entry)
        │               └── (打印 "已提取编码: '{code_name}'...")
        │
        ├── // 3c. (一个分组的所有JSON文件处理完毕后)
        ├── (如果 all_codebook_entries_for_this_group 不为空):
        │   ├── 确保输出TXT文件的目录存在 (os.makedirs)
        │   └── 将 all_codebook_entries_for_this_group 中的所有条目写入 output_txt_filepath
        │       └── (包括文件头和条目间的格式)
        └── (打印该分组TXT文件生成成功或失败的信息)
        │
        └── (返回外层循环，处理下一个分组)
    │
    └── // 4. 所有分组处理完毕后
        └── (打印总结信息，例如“所有分组的编码本原始素材TXT文件已成功生成”)
        └── (脚本执行结束)

三层循环结构：
最外层：遍历预定义的问题分组（用户经验、用户体验、游戏特征）。
中层：遍历当前分组内的所有独立JSON文件（每个文件代表一个具体访谈问题的LLM分析结果）。
内层：遍历一个JSON文件（一个问题）中的codes_and_quotes列表，即该问题下LLM识别出的不同编码（例如“单人孤独”、“内容局限”）。
核心操作： 对于每个识别出的编码（内层循环），脚本会：
提取其名称、定义和所有相关的引文。
调用 select_excerpts_for_codebook 来选取一部分引文作为示例。
调用 format_codebook_entry_to_txt 将这些信息格式化成您期望的TXT条目。
文件输出： 每个问题分组的所有编码条目会被汇总并写入一个单独的TXT文件中。
这个结构应该能更清晰地反映 build_codebook_raw.py 脚本的工作流程。
"""

# build_codebook_raw.py

import json
import os
import glob
import random # 用于随机选取引文
import re     # 用于文本清理
from parameters import file_dir, app # app 变量可能用于日志或确认


def clean_text_for_codebook_material(text):
    """
    专门为生成编码本原始素材TXT文件中的文本进行清理。
    主要目的是移除可能干扰LLM阅读的多余换行和空格。
    """
    if text is None:
        return ""
    cleaned_text = str(text)
    # 将所有类型的换行符替换为单个空格
    cleaned_text = cleaned_text.replace('\r\n', ' ').replace('\n', ' ').replace('\r', ' ')
    # 合并多个空格为一个，并去除首尾空格
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
    return cleaned_text

def select_excerpts_for_codebook(excerpts_list, num_to_select=3):
    """
    从引文列表中选取引文及其被访者ID，用于编码本。
    Args:
        excerpts_list (list): 包含 {'respondent_id': '...', 'quote': '...'} 对象的列表。
        num_to_select (int): 希望选取的引文数量。
    Returns:
        list: 包含格式化后的引文字符串的列表，例如 ["引文1 (ID:X)", "引文2 (ID:Y)"]
    """
    if not excerpts_list:
        return ["(无引文示例)"]
    
    valid_excerpts = []
    for excerpt_entry in excerpts_list:
        quote_text = excerpt_entry.get("quote", "").strip()
        if quote_text: # 只选择有内容的引文
            valid_excerpts.append(excerpt_entry)

    if not valid_excerpts:
        return ["(无有效引文示例)"]
    
    if len(valid_excerpts) <= num_to_select:
        selected = valid_excerpts
    else:
        selected = random.sample(valid_excerpts, num_to_select)
        
    formatted_excerpts = []
    for excerpt_entry in selected:
        resp_id = excerpt_entry.get("respondent_id", "未知ID")
        # 清理引文以适应TXT格式
        quote_text_cleaned = clean_text_for_codebook_material(excerpt_entry.get("quote", ""))
        if quote_text_cleaned:
            formatted_excerpts.append(f"{quote_text_cleaned} (ID: {resp_id})")
            
    return formatted_excerpts if formatted_excerpts else ["(有效引文处理后为空或无内容)"]

def format_codebook_entry_to_txt(code_name, code_definition, source_question_text, selected_excerpts):
    """
    将单个编码的信息格式化为TXT编码本条目字符串。
    """
    # 对所有文本内容进行清理，以确保在TXT中格式良好
    cleaned_code_name = clean_text_for_codebook_material(code_name)
    cleaned_code_definition = clean_text_for_codebook_material(code_definition)
    cleaned_source_question = clean_text_for_codebook_material(source_question_text)
    
    excerpts_str_list = []
    for i, ex_str in enumerate(selected_excerpts): # selected_excerpts已经是格式化后的字符串列表
        excerpts_str_list.append(f"  示例{i+1}: {ex_str}")

    excerpts_block = "\n".join(excerpts_str_list)

    entry = (
        f"编码名称：{cleaned_code_name}\n"
        f"编码定义：{cleaned_code_definition}\n"
        f"来自访谈问题：{cleaned_source_question}\n"
        f"编码引文示例：\n{excerpts_block}\n"
        f"----\n" # 使用四个短横线作为更明确的条目分隔符
    )
    return entry



def process_codebook_json_files_for_group(json_file_list, output_txt_filepath, group_name=""):
    """
    处理一个分组内的所有独立JSON文件，提取编码信息，并写入到一个TXT编码本素材文件中。
    """
    print(f"\n>>> 处理分组：{group_name}")
    print(f"    输入JSON文件数：{len(json_file_list)}")
    print(f"    输出路径：{output_txt_filepath}")

    if not json_file_list:
        print(f"  警告：分组'{group_name}'无任何 JSON 文件，输出空文件。")
        try:
            out_dir = os.path.dirname(output_txt_filepath)
            if out_dir and not os.path.exists(out_dir):
                os.makedirs(out_dir)
            with open(output_txt_filepath, 'w', encoding='utf-8') as outfile:
                outfile.write(f"# 编码本素材 - 分组: {group_name}\n# (此分组下未找到源JSON文件)\n")
            print(f"  已生成空标记TXT: {output_txt_filepath}")
        except Exception as e:
            print(f"  生成空TXT失败: {e}")
        return 0

    all_entries = []
    total_codes = 0
    total_questions = 0

    for json_fp in json_file_list:
        print(f"  读取: {os.path.basename(json_fp)}")
        try:
            with open(json_fp, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list) and data and isinstance(data[0], dict):
                    question_objs = [data[0]]
                    if len(data) > 1:
                        print(f"    注意: {os.path.basename(json_fp)} 列表含多个对象，仅取第一个")
                elif isinstance(data, dict):
                    question_objs = [data]
                else:
                    print(f"    警告: {os.path.basename(json_fp)} 顶层结构异常，跳过")
                    continue

                for question in question_objs:
                    total_questions += 1
                    q_text = question.get("question_text", "未知问题")
                    codes_and_quotes = question.get("codes_and_quotes", [])
                    if not codes_and_quotes:
                        print(f"    无codes_and_quotes，跳过。")
                        continue
                    for code in codes_and_quotes:
                        code_name = code.get("code_name", "未命名编码")
                        code_definition = code.get("code_definition", "未提供定义")
                        excerpts = code.get("excerpts", [])
                        selected_excerpts = select_excerpts_for_codebook(excerpts)
                        entry = format_codebook_entry_to_txt(
                            code_name, code_definition, q_text, selected_excerpts)
                        all_entries.append(entry)
                        total_codes += 1
                        print(f"    提取编码: {code_name[:30]}...")

        except Exception as e:
            print(f"  读取或解析JSON出错: {e}")

    try:
        out_dir = os.path.dirname(output_txt_filepath)
        if out_dir and not os.path.exists(out_dir):
            os.makedirs(out_dir)
        with open(output_txt_filepath, 'w', encoding='utf-8') as outfile:
            outfile.write(f"# 编码本素材 - 分组: {group_name}\n")
            outfile.write(f"# 共提取 {total_codes} 个编码条目，涉及 {total_questions} 个问题\n----\n\n")
            for entry in all_entries:
                outfile.write(entry + "\n")
        print(f"  分组 {group_name}：TXT文件生成成功，共 {total_codes} 个编码条目，{total_questions} 个问题。")
    except Exception as e:
        print(f"  写入TXT出错: {e}")

    return total_codes

if __name__ == "__main__":
    print("=== LLM编码本原始素材TXT 批量生成 ===")
    grouped_json_lists = file_dir['grouped_inductive_q_cbook_jsons']
    grouped_txt_paths = file_dir['grouped_raw_codebook_txts']

    assert len(grouped_json_lists) == len(grouped_txt_paths), "分组数量不一致！"

    all_groups_total = 0
    all_groups_codes = 0

    for idx, (json_list, txt_path) in enumerate(zip(grouped_json_lists, grouped_txt_paths)):
        group_name = f"分组{idx+1}"
        num_codes = process_codebook_json_files_for_group(json_list, txt_path, group_name=group_name)
        all_groups_total += 1
        all_groups_codes += num_codes

    print("\n=== 全部分组处理完毕 ===")
    print(f"共处理分组数：{all_groups_total}")
    print(f"共生成编码条目数：{all_groups_codes}")
    print("=== 脚本执行结束 ===")