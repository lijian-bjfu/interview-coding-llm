#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
访谈数据预处理脚本

本脚本用于将原始访谈数据转换为以下三种格式：
1. 横向数据：按问题组织的所有被访者回答
2. 纵向数据：按被访者组织的所有问题回答
3. 分类数据：按分类组织的问题及回答

数据流程：
1. 从原始CSV文件加载数据
2. 生成横向格式文本
3. 生成纵向格式文本
4. 按分类生成专题文本
5. 保存所有生成的文件到指定位置

依赖说明：
- pandas: 用于数据处理
- parameters.py: 项目配置和路径管理
"""

import os
import logging
import pandas as pd
from collections import defaultdict
from typing import Dict, List, Optional
from parameters import (
    get_path,                    # 获取单个文件或目录路径
    get_category_specific_path,  # 获取特定分类的路径
    OUTLINE,                     # 分类-问题映射字典
    UNIQUE_CATEGORIES,          # 所有分类名称列表
    SDIR_GROUP_QDATA,          # 分类问题数据目录常量
    APP_NAME,                   # 应用名称
    QUESTION_MAP,              # 问题编号到问题文本的映射
)

# 暂时注释掉日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('workflow.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def ensure_directory_exists(file_path: str) -> None:
    """
    确保文件路径的目录存在，如不存在则创建
    
    参数:
        file_path: 文件完整路径
        
    注意:
        - 会创建多级目录
        - 会记录目录创建日志
    """
    directory = os.path.dirname(file_path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)
        logger.info(f"创建目录: {directory}")

def clean_text(text: str) -> str:
    """
    清理文本中的无效字符，包括换行符、制表符和多余的空格
    
    参数:
        text: 需要清理的原始文本
        
    返回:
        str: 清理后的文本
        
    处理内容:
        - 移除换行符 (\n, \r, \\n, \\r)
        - 移除制表符 (\t, \\t)
        - 将多个连续空格替换为单个空格
        - 移除首尾空格
    """
    if not isinstance(text, str):
        text = str(text)
        
    # 处理换行符和制表符
    replacements = {
        '\n': '', '\r': '', '\\n': '', '\\r': '',
        '\t': ' ', '\\t': ' '
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
        
    # 处理多余的空格
    text = ' '.join(text.split())
    
    return text

def format_answer_with_id(id_: int, answer: str) -> str:
    """
    格式化带ID的回答文本
    
    参数:
        id_: 内部ID
        answer: 回答内容
        
    返回:
        str: 格式化后的文本，格式为 "[ID:X] 回答内容"
    """
    return f"[ID:{id_}] {answer}"

def format_respondent_header(id_: int) -> str:
    """
    格式化被访者标题
    
    参数:
        id_: 内部ID
        
    返回:
        str: 格式化后的标题，格式为 "被访者：[ID:X]"
    """
    return f"被访者：[ID:{id_}]"

def save_text_file(content: str, file_path: str) -> bool:
    """
    安全地将文本内容保存到文件
    
    参数:
        content: 要保存的文本内容
        file_path: 目标文件路径
        
    返回:
        bool: 保存成功返回True，失败返回False
        
    处理流程:
        1. 确保目录存在
        2. 以UTF-8编码写入文件
        3. 记录操作日志
        4. 捕获并记录可能的错误
    """
    try:
        ensure_directory_exists(file_path)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"成功保存文件: {file_path}")
        return True
    except Exception as e:
        logger.error(f"保存文件失败 {file_path}: {e}")
        return False

def get_all_question_numbers() -> List[int]:
    """
    从OUTLINE中获取所有问题编号，并按顺序排序
    
    返回:
        List[int]: 排序后的问题编号列表
    """
    # 收集所有问题编号
    all_numbers = set()
    for questions in OUTLINE.values():
        all_numbers.update(questions)
    
    # 转换为列表并排序
    return sorted(list(all_numbers))

def find_best_match_column(target_text: str, columns: List[str]) -> str:
    """
    在DataFrame的列名中找到与目标问题文本最匹配的列名
    
    参数:
        target_text: 标准问题文本
        columns: DataFrame中的列名列表
        
    返回:
        str: 最匹配的列名
    """
    # 移除标点符号和空格后比较
    def normalize_text(text: str) -> str:
        return ''.join(char for char in text if char.isalnum())
    
    target_normalized = normalize_text(target_text)
    
    # 计算每个列名与目标文本的相似度
    best_match = None
    best_similarity = 0
    
    for col in columns:
        col_normalized = normalize_text(col)
        # 计算两个标准化文本之间的相似度
        # 这里使用一个简单的包含关系检查
        if target_normalized in col_normalized or col_normalized in target_normalized:
            similarity = len(set(target_normalized) & set(col_normalized)) / len(set(target_normalized) | set(col_normalized))
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = col
    
    return best_match if best_match else columns[0]  # 如果没有找到匹配，返回第一个列名

def load_raw_data() -> Optional[tuple[pd.DataFrame, Dict[int, str]]]:
    """
    加载并验证原始访谈数据，同时为问题建立题号映射
    
    返回:
        Optional[tuple[pd.DataFrame, Dict[int, str]]]: 
            成功返回(DataFrame, 题号到列名的映射字典)，失败返回None
    """
    try:
        csv_path = get_path('UI_id')
        df = pd.read_csv(csv_path)
        
        if df.empty:
            logger.error("CSV文件为空")
            return None
            
        if '_id' not in df.columns:
            logger.error("未找到内部ID列 '_id'")
            return None
            
        ordered_question_numbers = get_all_question_numbers()
        question_map = {}
        question_map[0] = '_id'
        logger.info("使用内部ID列 '_id' 映射到题号 0")
        
        all_columns = [col for col in df.columns if col != '_id']
        
        for q_num in ordered_question_numbers:
            if q_num == 0:
                continue
                
            standard_question = QUESTION_MAP.get(q_num)
            if standard_question:
                matched_column = find_best_match_column(standard_question, all_columns)
                question_map[q_num] = matched_column
                if matched_column in all_columns:
                    all_columns.remove(matched_column)
                logger.info(f"映射题号 {q_num} 到列 '{matched_column}'")
            else:
                logger.warning(f"题号 {q_num} 在 QUESTION_MAP 中未找到对应的标准问题")
        
        missing_numbers = set(ordered_question_numbers) - set(question_map.keys())
        if missing_numbers:
            logger.warning(f"以下题号未找到对应的列: {missing_numbers}")
        
        used_columns = set(question_map.values())
        unused_columns = set(df.columns) - used_columns
        if unused_columns and '_id' in unused_columns:
            unused_columns.remove('_id')
        if unused_columns:
            logger.warning(f"以下列未被映射到任何题号: {unused_columns}")
        
        logger.info(f"成功加载数据，形状: {df.shape}")
        logger.info(f"建立了 {len(question_map)} 个题号映射")
        
        return df, question_map
        
    except Exception as e:
        logger.error(f"加载原始数据失败: {e}")
        return None

def generate_by_question_text(df: pd.DataFrame) -> str:
    """
    生成横向格式文本，按问题组织数据
    
    参数:
        df: 包含访谈数据的DataFrame
        
    返回:
        str: 格式化的文本，包含所有问题及其回答
        
    格式示例:
        问题1

        [ID:0] 回答1

        [ID:1] 回答2
        ...
        
        ---
        
        问题2

        [ID:0] 回答1

        [ID:1] 回答2
        ...
    """
    # logger.info("开始生成横向（按问题）格式文本")
    
    output_lines = []
    first_question = True
    
    # 获取所有非ID列
    question_columns = [col for col in df.columns if col != '_id']
    
    for column in question_columns:
        # 除第一个问题外，其他问题前添加分隔线
        if not first_question:
            output_lines.append("---")
            output_lines.append("")
        else:
            first_question = False
            
        # 添加问题
        output_lines.append(f"{column}")
        output_lines.append("")  # 问题和第一个回答之间空一行
        
        # 获取该问题的所有非空回答及对应的ID
        valid_responses = df[['_id', column]].dropna(subset=[column])
        
        # 添加带ID的回答，每个回答之间空一行
        for _, row in valid_responses.iterrows():
            response = clean_text(str(row[column]))
            formatted_response = format_answer_with_id(row['_id'], response)
            output_lines.append(formatted_response)
            output_lines.append("")  # 回答之间空一行
    
    # logger.info("成功生成横向格式文本")
    return "\n".join(output_lines)

def generate_by_respondent_text(df: pd.DataFrame) -> str:
    """
    生成纵向格式文本，按被访者组织数据
    
    参数:
        df: 包含访谈数据的DataFrame
        
    返回:
        str: 格式化的文本，包含所有被访者及其回答
        
    格式示例:
        被访者：[ID:0]
        
        问题1：您什么时候开始玩这个游戏的？
        回答：2014年左右
        
        问题2：您平时都玩什么游戏？
        回答：射击游戏
        ...
        
        ---
        
        被访者：[ID:1]
        ...
    """
    # logger.info("开始生成纵向（按被访者）格式文本")
    
    output_lines = []
    first_respondent = True
    
    # 获取所有非ID列作为问题列
    question_columns = [col for col in df.columns if col != '_id']
    
    for _, row in df.iterrows():
        # 除第一个被访者外，其他被访者前添加分隔线
        if not first_respondent:
            output_lines.append("---")
            output_lines.append("")
        else:
            first_respondent = False
        
        # 添加被访者标题（使用内部ID）
        respondent_id = int(row['_id'])
        output_lines.append(format_respondent_header(respondent_id))
        output_lines.append("")  # 被访者标题后空一行
        
        # 添加每个问题和回答
        first_question = True
        for column in question_columns:
            # 问题之间空一行（除第一个问题外）
            if not first_question:
                output_lines.append("")
            else:
                first_question = False
                
            # 处理空值情况并清理文本
            answer = str(row[column]) if pd.notna(row[column]) else "未回答"
            cleaned_answer = clean_text(answer)
            
            output_lines.append(f"问题：{column}")
            output_lines.append(f"回答：{cleaned_answer}")
    
    # logger.info("成功生成纵向格式文本")
    return "\n".join(output_lines)

def generate_category_texts(df: pd.DataFrame, column_question_map: Dict[int, str]) -> Dict[str, str]:
    """
    从DataFrame生成分类专题文本
    
    参数:
        df: 包含访谈数据的DataFrame
        column_question_map: 题号到列名的映射字典
        
    返回:
        Dict[str, str]: 字典，键为分类名称，值为该分类的文本内容
        
    格式示例:
        {
            "分类1": "问题1\n\n[ID:0] 回答1\n\n[ID:1] 回答2\n\n---\n\n问题2...",
            "分类2": "..."
        }
    """
    # logger.info("=== 开始生成分类专题文本 ===")
    # logger.info(f"DataFrame信息: 形状{df.shape}")
    
    category_texts = defaultdict(list)
    
    # 遍历OUTLINE，处理每个分类下的问题
    for category, question_numbers in OUTLINE.items():
        # logger.info(f"\n处理分类: '{category}'")
        questions_processed = 0
        questions_found = 0
        first_question = True
        
        # 处理该分类下的每个问题编号
        for q_num in question_numbers:
            questions_processed += 1
            # 使用column_question_map获取对应的列名
            column_name = column_question_map.get(q_num)
            
            if column_name is None:
                # logger.warning(f"  题号 {q_num} 在数据中未找到对应的列名")
                continue
                
            # logger.info(f"  处理题号 {q_num}: {column_name}")
            
            if column_name in df.columns:
                questions_found += 1
                # 构建问题文本块
                question_block_lines = []
                
                # 除第一个问题外，其他问题前添加分隔线
                if not first_question:
                    question_block_lines.append("---")
                    question_block_lines.append("")
                else:
                    first_question = False
                
                # 添加问题标题（使用QUESTION_MAP中的标准问题文本）
                question_text = QUESTION_MAP.get(q_num, column_name)
                question_block_lines.append(question_text)
                question_block_lines.append("")  # 问题和第一个回答之间空一行
                
                # 获取并添加所有非空回答，同时清理文本
                valid_responses = df[['_id', column_name]].dropna(subset=[column_name])
                # logger.info(f"    - 找到 {len(valid_responses)} 个非空回答")
                
                # 添加带ID的回答，每个回答之间空一行
                for _, row in valid_responses.iterrows():
                    response = clean_text(str(row[column_name]))
                    formatted_response = format_answer_with_id(row['_id'], response)
                    question_block_lines.append(formatted_response)
                    question_block_lines.append("")  # 回答之间空一行
                
                # 将问题块添加到对应分类的列表中
                block_text = "\n".join(question_block_lines)
                category_texts[category].append(block_text)
                # logger.info(f"    √ 成功处理题号 {q_num}")
            else:
                # logger.warning(f"    × 列名 '{column_name}' 未在DataFrame的列中找到")
                pass
        
        # logger.info(f"  分类 '{category}' 处理完成:")
        # logger.info(f"  - 总问题数: {len(question_numbers)}")
        # logger.info(f"  - 处理的问题数: {questions_processed}")
        # logger.info(f"  - 成功找到的问题数: {questions_found}")
    
    # 将每个分类的问题块组合成最终文本
    final_category_texts = {
        cat: "\n".join(blocks) 
        for cat, blocks in category_texts.items()
    }
    
    # logger.info("\n=== 分类专题文本生成总结 ===")
    # logger.info(f"- 处理的分类总数: {len(OUTLINE)}")
    # logger.info(f"- 成功生成文本的分类数: {len(final_category_texts)}")
    # for cat, text in final_category_texts.items():
    #     logger.info(f"- 分类 '{cat}' 的文本长度: {len(text)} 字符")
    # logger.info("=============================\n")
    
    return final_category_texts

# TODO: 添加函数，例如 generate_category_user_text, 该函数用于生成分类专题文本，按被访者组织数据

def main() -> None:
    """
    主函数：协调整个数据转换流程
    """
    logger.info("开始数据转换流程")
    
    # 用于收集生成的文件信息
    horizontal_file = None
    vertical_file = None
    category_files = []
    
    # 加载原始数据
    result = load_raw_data()
    if result is None:
        logger.error("加载原始数据失败，退出程序")
        return
        
    df, column_question_map = result
    
    # 生成横向格式文本
    horizontal_text = generate_by_question_text(df)
    horizontal_path = get_path('UI_qtxt')
    if save_text_file(horizontal_text, horizontal_path):
        horizontal_file = {
            "name": os.path.basename(horizontal_path),
            "path": os.path.dirname(horizontal_path)
        }
    else:
        logger.error("保存横向格式文本失败，退出程序")
        return
    
    # 生成纵向格式文本
    vertical_text = generate_by_respondent_text(df)
    vertical_path = get_path('UI_utxt')
    if save_text_file(vertical_text, vertical_path):
        vertical_file = {
            "name": os.path.basename(vertical_path),
            "path": os.path.dirname(vertical_path)
        }
    else:
        logger.error("保存纵向格式文本失败，退出程序")
        return
    
    # 生成并保存分类专题文本
    category_texts = generate_category_texts(df, column_question_map)
    
    for category, text in category_texts.items():
        category_path = get_category_specific_path(category, SDIR_GROUP_QDATA)
        file_name = f"{APP_NAME}_question_{category}.txt"
        file_path = os.path.join(category_path, file_name)
        if save_text_file(text, file_path):
            category_files.append({
                "name": file_name,
                "path": category_path
            })
        else:
            logger.error(f"保存分类 '{category}' 的文本失败")
    
    # 打印生成文件的总结报告
    logger.info("\n=== 文件生成报告 ===")
    
    # 打印横向文本信息
    if horizontal_file:
        logger.info(f"横向文本：")
        logger.info(f"名称：{horizontal_file['name']}")
        logger.info(f"路径：{horizontal_file['path']}")
    
    # 打印纵向文本信息
    if vertical_file:
        logger.info(f"纵向文本：")
        logger.info(f"名称：{vertical_file['name']}")
        logger.info(f"路径：{vertical_file['path']}")
    
    # 打印分类文本信息
    category_count = len(category_files)
    logger.info(f"横向category文本：")
    logger.info(f"个数：{category_count}")
    
    if category_count > 0:
        for i, file_info in enumerate(category_files, 1):
            full_path = os.path.join(file_info['path'], file_info['name'])
            logger.info(f"文件{i}: {full_path}")
    
    logger.info("\n数据转换流程成功完成")

if __name__ == "__main__":
    main()