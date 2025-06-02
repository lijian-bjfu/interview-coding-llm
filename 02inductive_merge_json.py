# inductive_merge_json.py

import json
import os
import re # 仍然需要 re 来排序（如果文件名中的数字提取复杂）或清理
from parameters import file_dir, app # app 可能用于日志或确认


def merge_all_inductive_jsons(
    # 【修改点】第一个参数现在直接是嵌套的文件路径列表
    list_of_grouped_json_filepaths, 
    output_merged_filepath
    ):
    """
    接收一个按组划分的、嵌套的文件路径列表，读取所有指定的JSON文件，
    并将它们的内容（假设每个文件代表一个问题的分析对象）合并到一个单一的JSON列表中。
    """
    print(f"\n开始合并所有分组的归纳编码JSON文件到: {output_merged_filepath}")
    all_question_analysis_data = [] # 用于存储从所有文件中读取的所有问题分析对象

    if not list_of_grouped_json_filepaths:
        print("没有提供任何JSON文件路径列表进行合并。")
        return False

    group_index_for_log = 0
    for group_file_list in list_of_grouped_json_filepaths: # 外层循环遍历每个组的文件列表
        group_index_for_log += 1
        if not isinstance(group_file_list, list):
            print(f"警告: 分组 {group_index_for_log} 的文件数据不是预期的列表格式，已跳过。数据: {group_file_list}")
            continue

        print(f"  正在处理分组 {group_index_for_log} 的文件列表 (共 {len(group_file_list)} 个文件)...")
        if not group_file_list:
            print(f"    该分组文件列表为空，跳过。")
            continue
            
        # 文件在 parameters.py 中被 glob.glob 获取后，已经通过 sorted() 排序了
        # 所以这里直接遍历即可
        for filepath in group_file_list: # 内层循环遍历组内的每个文件路径
            print(f"      读取文件: {filepath}") # 打印完整路径以便追踪
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 假设每个 inductive_questionN.json 文件内容直接是一个问题分析对象 (dict)
                    # 或者是一个包含单个此类对象的列表 [dict] (如您之前确认的LLM输出)
                    if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
                        question_analysis_object = data[0] # 取列表中的第一个对象
                        if len(data) > 1:
                            print(f"        警告: 文件 '{os.path.basename(filepath)}' 的顶层列表包含多个问题对象，但只处理了第一个。")
                        all_question_analysis_data.append(question_analysis_object)
                    elif isinstance(data, dict): # 如果文件内容直接是对象
                        all_question_analysis_data.append(data)
                    else:
                        print(f"        警告: 文件 '{os.path.basename(filepath)}' 的内容不是预期的格式（单个对象或包含单个对象的列表），已跳过。")
            except json.JSONDecodeError:
                print(f"        错误: 解析JSON文件 '{os.path.basename(filepath)}' 失败，已跳过。")
            except FileNotFoundError:
                print(f"        错误: 文件 '{filepath}' 未找到（可能在parameters.py生成列表后被移动或删除），跳过。")
            except Exception as e:
                print(f"        处理文件 '{os.path.basename(filepath)}' 时发生意外错误: {e}")

    if not all_question_analysis_data:
        print("未能从任何分组的JSON文件中加载数据进行合并。不会生成合并文件。")
        return False

    try:
        output_merged_dir = os.path.dirname(output_merged_filepath)
        if output_merged_dir and not os.path.exists(output_merged_dir):
            os.makedirs(output_merged_dir)
            print(f"  已创建合并JSON的输出目录: {output_merged_dir}")

        with open(output_merged_filepath, 'w', encoding='utf-8') as outfile:
            json.dump(all_question_analysis_data, outfile, ensure_ascii=False, indent=2)
        print(f"\n所有分组的归纳编码JSON数据已成功合并到: {output_merged_filepath}")
        return True
    except Exception as e:
        print(f"写入合并后的JSON文件 '{output_merged_filepath}' 时发生错误: {e}")
        return False

# --- 主程序执行 ---
if __name__ == "__main__":
    print("--- 开始合并各分组的LLM归纳编码JSON文件 (inductive_merge_json.py - 使用parameters.py动态路径) ---")

    # 确保 app 和 file_dir 已通过顶部的 try-except 加载或设置了默认值

    # 1. 从 file_dir 获取已经由 parameters.py 动态组织好的嵌套文件路径列表
    try:
        # 这个键 'grouped_inductive_q_jsons' 是在 parameters.py 中动态生成的
        # 其值应该是一个嵌套列表，例如: [[g1_q1.json, g1_q2.json], [g2_q1.json], ...]
        nested_json_files_to_merge = file_dir['grouped_inductive_q_jsons']
        print(f"INFO: 从 parameters.py 获取到 grouped_inductive_q_jsons，包含 {len(nested_json_files_to_merge)} 个分组的文件列表。")
    except KeyError:
        print("错误: parameters.py 中的 file_dir 未定义 'grouped_inductive_q_jsons'。请确保 parameters.py 已按最新版本更新并正确执行。")
        exit() # 如果这个关键数据没有，脚本无法继续

    # 2. 获取最终合并后JSON文件的输出路径
    try:
        # 这个键 'inductive_merged_json' 应该在 parameters.py 中定义并指向正确的输出文件路径
        # 例如 'data_dir/myworld_dir/03_inductive_coding_dir/myworld_inductive_codes.json'
        output_merged_json_path = file_dir['inductive_merged_json']
        print(f"INFO: 合并后的JSON将输出到: {output_merged_json_path}")
    except KeyError:
        print(f"错误: parameters.py 中的 file_dir 未定义 'inductive_merged_json' 作为输出路径。")
        # 提供一个备用输出路径（如果需要，但理想情况下 parameters.py 应完整）
        if 'app' not in globals(): app = "unknown_app" # 再次确保app存在
        output_merged_json_path = f'data_dir/{app}_dir/03_inductive_coding_dir/{app}_inductive_codes_DEFAULT.json'
        print(f"警告: 将尝试写入到默认路径: {output_merged_json_path}")
        # 确保这个默认路径的目录也存在 (通常 parameters.py 已处理目录创建)
        default_out_dir = os.path.dirname(output_merged_json_path)
        if default_out_dir and not os.path.exists(default_out_dir):
            try:
                os.makedirs(default_out_dir)
            except OSError as e:
                print(f"创建默认输出目录失败: {e}")
                exit()


    if not isinstance(nested_json_files_to_merge, list) :
        print(f"错误: 'grouped_inductive_q_jsons' 的值不是预期的列表格式。请检查 parameters.py。")
    elif not any(nested_json_files_to_merge) : # 检查是否所有内层列表都为空，或者外层列表本身为空
        print("警告: 'grouped_inductive_q_jsons' 为空或所有分组均无文件，没有文件需要合并。")
    else:
        success = merge_all_inductive_jsons(
            nested_json_files_to_merge,
            output_merged_json_path
        )

        if success:
            print("\n所有分组的归纳编码JSON文件合并任务完成。")
        else:
            print("\n归纳编码JSON文件合并任务失败或没有文件可合并。")

    print("--- inductive_merge_json.py 执行结束 ---")