"""
根据大纲category建立初始编码本。
三层循环结构：
最外层：遍历预定义的问题大纲（category）。
中层：遍历当前category的所有独立JSON文件（每个文件代表一个具体访谈问题的LLM分析结果）。
内层：遍历一个JSON文件（一个问题)
核心操作： 对于每个识别出的编码（内层循环），脚本会：
提取其名称、定义、来源问题、所属主题、所有相关的引文，以及统计出现品书。
调用 select_excerpts_for_codebook 来选取一部分引文作为示例。
建立csv格式编码本，包含编码名称、定义、隶属category、来源问题、参考主题、提取引文，以及统计出现频次。
输出：三个csv编码本，分别对应三个category。
"""

# build_codebook_raw.py

import json
import os
import re
import logging
import random # 用于随机选取引文
import pandas as pd
from collections import defaultdict
from typing import Dict, List, Optional, Any, Tuple
from parameters import (
    get_path,                    # 获取单个文件或目录路径
    get_category_specific_path,  # 获取特定分类的路径
    OUTLINE,                     # 分类-问题映射字典
    UNIQUE_CATEGORIES,          # 所有分类名称列表
    APP_NAME,                   # 应用名称
    QUESTION_MAP,              # 问题编号到问题文本的映射
    SDIR_GROUP_QDATA,           # categor的 question data 路径
    SDIR_GROUP_CBOOK,           # category的 codebook data 路径
)
# 配置日志系统
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('workflow.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ---信息提取模块--

# 解析单个JSON文件，提取核心编码，从json文件中提取编码信息，输入为json.load(f)的返回值
def extract_code_details(question_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    从每个问题编码的json文件中提取编码信息
    
    参数:
        question_data (Dict): 单个问题的JSON数据 (即 loaded_json[0])。

        [{"question_text": "问题的文本",
        "initial_codes": [{ 
            "respondent_id": int, "original_answer_segment": str, "code_name": ["初始编码1的名称"], "supporting_quote": ["支持初始编码1的引文"], "quote_range": [[start index, end index], ...],"pairs": ["1-1", "2-2", ...]}, {},...],
        "codes": [{"code_name": "编码名称","code_definition": "编码定义"}, {}...],
        "themes": [{"theme_name": "主题编码名称", "theme_definition": "主题编码定义", "included_initial_codes": ["初始编码1的名称"]}, {}...],
        }],

    返回:
        List[Dict]: 一个列表，每个字典代表一个编码实例的详细信息。
    """
    # 提取 question_text 的逻辑现在移到了函数内部
    question_text = question_data.get('question_text', '未知问题')
    
    extracted_codes = []
    
    # 1. 快速建立问题内 "编码 -> 主题" 的映射
    theme_map = {
        initial_code: theme.get('theme_name', 'N/A')
        for theme in question_data.get('themes', [])
        for initial_code in theme.get('included_initial_codes', [])
    }

    # 2. 遍历该问题中定义的所有编码 ("codes" 列表)
    for code_info in question_data.get('codes', []):
        code_name = code_info.get('code_name')
        if not code_name:
            continue

        code_entry = {
            "code_name": code_name,
            "definition": code_info.get('code_definition', ''),
            "source_question": question_text, # 在这里使用提取出的 question_text
            "theme": theme_map.get(code_name, 'N/A'),
            "frequency_in_question": 0,
            "all_quotes": []
        }

        # 3. 遍历所有回答，为当前编码查找引文和统计频次
        # (这部分内部逻辑保持不变)
        for response in question_data.get('initial_codes', []):
            if code_name in response.get('code_name', []):
                code_entry["frequency_in_question"] += 1
                try:
                    code_idx = response['code_name'].index(code_name)
                    for pair in response.get('pairs', []):
                        p_code_idx, p_quote_idx = map(int, pair.split('-'))
                        if p_code_idx - 1 == code_idx:
                            quote = response['supporting_quote'][p_quote_idx - 1]
                            code_entry['all_quotes'].append(quote)
                except (ValueError, IndexError):
                    continue

        extracted_codes.append(code_entry)
        
    return extracted_codes

# 处理编码的重名问题，如果两个编码的名称相同，则添加后缀 _1, _2, ...
def rename_duplicate_codes(codes_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    遍历编码列表，为重名的编码添加后缀 (e.g., _1, _2)。

    参数:
        codes_list (List[Dict]): 从一个Category收集到的所有编码实例的列表。

    返回:
        List[Dict]: code_name 已被重命名的列表。
    """
    name_counts = defaultdict(int)
    # 直接修改传入的列表中的字典
    for code_entry in codes_list:
        original_name = code_entry['code_name']
        count = name_counts[original_name]
        
        if count > 0:
            code_entry['code_name'] = f"{original_name}_{count}"
            
        name_counts[original_name] += 1
        
    return codes_list

# 从当前编码的引文中提取引文
def select_excerpts_quote(quotes: List[str], n: int = 2) -> List[str]:
    """
    从引文列表中，选取 n 个最长的引文作为代表。

    参数:
        quotes (List[str]): 原始引文列表。
        n (int): 要选取的引文数量。

    返回:
        List[str]: 最长的 n 个引文组成的列表。
    """
    if not quotes or n <= 0:
        return []
    
    # 按字符串长度降序排序，然后选取前n个
    return sorted(quotes, key=len, reverse=True)[:n]

# ---核心任务流---
def get_and_validate_json_files_in_category(category: str) -> Tuple[bool, List[str], set, set]:
    """
    获取给定分类目录中的JSON文件，并验证其是否与大纲(OUTLINE)一致。

    这个函数被重构了，它现在自己负责查找文件，使得逻辑更清晰。

    参数:
        category (str): 要验证的分类名称。

    返回:
        Tuple[bool, List[str], set, set]: 一个元组，包含：
            - is_valid (bool): 是否验证通过。
            - valid_paths (List[str]): 验证通过的JSON文件路径列表。
            - missing_numbers (set): 缺失的问题编号。
            - extra_files (set): 多余的（不在大纲中）的JSON文件名。
    """
    # 1. 从OUTLINE中获取对应category中预期的quetion number信息
    expected_numbers = set(OUTLINE.get(category, []))
    if not expected_numbers:
        logger.warning(f"分类 '{category}' 在 OUTLINE 中没有对应的问题。")
        return True, [], set(), set() # 如果分类下没问题，直接返回成功
    
    # 2. 从特定分类目录中查找实际存在的文件
    try:
        # 使用get_category_specific_path获取特定分类的路径
        qdata_path = get_category_specific_path(category, SDIR_GROUP_QDATA)
        logger.info(f"正在检查目录: {qdata_path}")
        
        # 使用 os.listdir() 查找目录下的所有文件，避免手动拼接
        all_files = os.listdir(qdata_path)
        json_files = [f for f in all_files if f.startswith('inductive_question') and f.endswith('.json')]
    
    except FileNotFoundError:
        logger.error(f"目录不存在: {qdata_path}")
        return False, [], expected_numbers, set() # 目录不存在，所有预期的文件都缺失

    # 3. 提取实际文件的编号
    actual_numbers = set()
    for f in json_files:
        try:
            # 使用正则表达式来灵活地解析文件名
            # 这个模式会查找 "inductive_question" 后面可能存在的非数字字符(\D*)，然后捕获第一个连续的数字串(\d+)
            # 它能正确处理 "inductive_question12.json", "inductive_question_12.json", "inductive_question12-13.json" 等情况
            match = re.search(r'inductive_question\D*(\d+)', f)
            
            if match:
                # 提取捕获到的第一个数字组并转换为整数
                num = int(match.group(1))
                actual_numbers.add(num)
            else:
                # 如果正则表达式没有匹配到，说明文件名格式不符合预期
                logger.warning(f"无法从文件名 '{f}' 中解析问题编号，格式不符，已跳过。")
                
        except ValueError:
            # 这个异常捕获理论上不太可能触发，因为正则保证了group(1)是数字，但保留以增加健壮性
            logger.warning(f"从文件名 '{f}' 中解析出的内容不是有效数字，已跳过。")
            continue

    # 4. 对比并返回结果
    if actual_numbers == expected_numbers:
        valid_paths = [os.path.join(qdata_path, f) for f in json_files]
        return True, sorted(valid_paths), set(), set()
    else:
        # 找出缺失的json文件编号
        missing = expected_numbers - actual_numbers
        # 找出多余文件对应的文件编号
        extra_nums = actual_numbers - expected_numbers
        extra_files = {f for f in json_files if int(f.split('.')[0].replace('inductive_question', '')) in extra_nums}
        
        return False, [], missing, extra_files


def generate_category_codebook() -> Dict[str, pd.DataFrame]:
    """
    为每个分类生成编码本(Codebook)的DataFrame。
    """
    logger.info("开始：为每个分类生成编码本。")
    
    # 初始化一个字典来存储每个分类的编码本
    codebook_dict = {}

    # 外层循环: 遍历所有分类
    # **修正点**: 使用 UNIQUE_CATEGORIES 遍历可以确保我们处理所有定义过的分类
    for category in UNIQUE_CATEGORIES:
        logger.info(f"--- 开始处理分类: '{category}' ---")

        # **核心逻辑修正**:
        # 验证步骤应该在循环开始时执行一次，而不是在循环内部反复执行。
        is_valid, valid_json_paths, missing_nums, extra_files = get_and_validate_json_files_in_category(category)

        if not is_valid:
            error_msg = f"分类 '{category}' 文件验证失败! "
            if missing_nums:
                error_msg += f"缺失的问题编号: {missing_nums}. "
            if extra_files:
                error_msg += f"发现多余的文件: {extra_files}."
            # 打印缺失和多余的文件编号
            logger.error(error_msg)
            # 可以选择是跳过这个分类还是终止程序，这里我们选择跳过
            logger.warning(f"--- 跳过分类: '{category}' ---")
            continue
        
        logger.info(f"分类 '{category}' 文件验证通过，将处理 {len(valid_json_paths)} 个JSON文件。")
        

        # 中层循环: 遍历该分类下所有已验证的JSON文件
        # 1. 数据收集：遍历JSON文件，提取所有编码实例
        all_codes_for_category = []
        for json_path in valid_json_paths: 
            # 内层循环: 遍历JSON文件中的内容 (这里是为 @codebook-extract 任务预留的框架)
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    question_data_list = json.load(f)
                    if not question_data_list: continue

                    question_data = question_data_list[0] 
                    # 调用函数1: 提取单个文件中的所有编码信息
                    codes_from_file = extract_code_details(question_data)
                    all_codes_for_category.extend(codes_from_file)

            except Exception as e:
                logger.error(f"处理文件 {json_path} 时出错: {e}")
                continue

        # 2. 后处理步骤
        # 调用函数2: 处理分类内跨问题的重名编码
        # 返回的信息格式为：
        # code_entry = {
        #     "code_name": code_name,
        #     "definition": code_info.get('code_definition', ''),
        #     "source_question": question_text, # 在这里使用提取出的 question_text
        #     "theme": theme_map.get(code_name, 'N/A'),
        #     "frequency_in_question": 0,
        #     "all_quotes": []
        # }
        unique_named_codes = rename_duplicate_codes(all_codes_for_category)
        
        # 调用函数3: 为每个编码实例筛选代表性引文
        for code_entry in unique_named_codes:
            code_entry['representative_quotes'] = select_excerpts_quote(code_entry['all_quotes'], n=2)
            # 删除原始的长引文列表以节省空间
            del code_entry['all_quotes'] 

        # 3. 转换为DataFrame
        # 定义最终编码本的列顺序
        columns_order = [
            'code_name', 'definition', 'theme', 
            'source_question', 'frequency_in_question', 'representative_quotes'
        ]
        df = pd.DataFrame(unique_named_codes)
        # 确保所有列都存在，不存在的列会以NaN填充
        df = df.reindex(columns=columns_order)
        
        codebook_dict[category] = df
        logger.info(f"分类 '{category}' 编码本生成完毕，共包含 {len(df)} 个编码条目。")
        logger.info(f"--- 完成处理分类: '{category}' ---\n")

    # TODO: @codebook-save 逻辑
    logger.info("任务 @codebook 已完成所有数据处理和转换。")
    return codebook_dict

def save_codebooks(codebooks_dict: Dict[str, pd.DataFrame]):
    """
    将生成的编码本DataFrames保存为CSV文件。

    参数:
        codebooks_dict (Dict[str, pd.DataFrame]): 键为分类名称，值为对应编码本DataFrame的字典。
    """
    logger.info("任务 @codebook-save 开始：保存编码本到CSV文件。")
    if not codebooks_dict:
        logger.warning("没有可保存的编码本数据。")
        return

    for category, df in codebooks_dict.items():
        try:
            # 获取该分类下用于保存编码本的目录路径
            save_dir = get_category_specific_path(category, SDIR_GROUP_CBOOK)
            
            # 确保目录存在
            os.makedirs(save_dir, exist_ok=True)
            
            # 定义完整的文件路径和名称
            file_path = os.path.join(save_dir, f"raw_codebook_{category}.csv")
            
            # 保存为CSV文件
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
            
            logger.info(f"成功保存编码本到: {file_path}")
            
        except Exception as e:
            logger.error(f"保存分类 '{category}' 的编码本时出错: {e}")

    logger.info("任务 @codebook-save 完成。")

def main():
    final_codebooks = generate_category_codebook()
    save_codebooks(final_codebooks)

# --- 主程序入口，用于测试 ---
if __name__ == '__main__':
    # 假设你的文件结构已经建立，这里只是为了演示函数调用
    # 在实际运行时，请确保文件和目录已根据规范创建
    main()