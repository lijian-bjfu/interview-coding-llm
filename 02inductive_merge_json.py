#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
02inductive_merge_json.py

数据流程：
1. 通过 parameters.py 接口获取所有归纳编码JSON文件路径
2. 验证文件完整性和格式
3. 合并所有JSON文件内容
4. 保存合并后的数据

依赖说明：
- parameters.py: 项目配置和路径管理
"""

import os
import json
import logging
import re
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

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

try:
    from parameters import (
        APP_NAME,
        get_path,
        get_path_list
    )
    logger.info("成功从 parameters.py 导入配置")
except ImportError as e:
    logger.critical(f"无法从 parameters.py 导入配置: {e}")
    raise


# ======================================================================
# 1. 输入机制模块 (@ds-n1-load)
# ======================================================================

def validate_json_file(file_path: str) -> Tuple[bool, Optional[List[Dict[str, Any]]]]:
    """
    验证JSON文件的有效性和格式

    参数:
        file_path: JSON文件路径

    返回:
        Tuple[bool, Optional[List[Dict[str, Any]]]]: 
            - 验证结果（True/False）
            - 验证通过时返回解析后的数据，失败时返回None
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        if not isinstance(data, list):
            logger.warning(f"文件格式错误 '{os.path.basename(file_path)}': 根结构不是列表")
            return False, None
            
        # 验证每个问题对象的结构
        for idx, item in enumerate(data):
            if not isinstance(item, dict):
                logger.warning(f"文件 '{os.path.basename(file_path)}' 中第 {idx+1} 个元素不是字典")
                return False, None
                
            # 验证必需字段
            required_fields = ['question_text', 'initial_codes', 'codes', 'themes']
            missing_fields = [field for field in required_fields if field not in item]
            if missing_fields:
                logger.warning(f"文件 '{os.path.basename(file_path)}' 中第 {idx+1} 个元素缺少必需字段: {missing_fields}")
                return False, None
        
        return True, data
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON解析错误 '{os.path.basename(file_path)}': {e}")
        return False, None
    except Exception as e:
        logger.error(f"验证文件时发生错误 '{os.path.basename(file_path)}': {e}")
        return False, None

def get_all_inductive_json_paths() -> Optional[List[str]]:
    """
    严格通过 get_path_list 获取所有待处理的 inductive_questionN.json 文件路径。
    并确保返回一个扁平化的路径字符串列表。
    """
    logger.info("准备通过 get_path_list 获取所有输入文件路径...")
    
    try:
        key_for_all_jsons = 'grouped_inductive_q_jsons' 
        nested_list_of_paths = get_path_list(key_for_all_jsons)
        
        all_json_paths = [path for sublist in nested_list_of_paths for path in sublist]

        if not all_json_paths:
            logger.warning(f"从 get_path_list('{key_for_all_jsons}') 获取并扁平化后，文件列表为空")
        else:
            logger.info(f"通过 get_path_list('{key_for_all_jsons}') 获取并扁平化后，共找到 {len(all_json_paths)} 个文件路径")
            
            # 详细的文件信息日志
            logger.info("详细文件列表:")
            for i, path in enumerate(all_json_paths):
                file_name = os.path.basename(path)
                logger.info(f"  {i+1}. 文件名: {file_name}")
                logger.info(f"     路径: {path}")
                
        logger.info("文件路径获取和处理完成")
        return all_json_paths
        
    except KeyError as e:
        logger.critical(f"失败: 在 parameters.py 中未找到预定义的 key: '{key_for_all_jsons}'")
        return None 
    except TypeError as e:
        logger.critical(f"失败: get_path_list('{key_for_all_jsons}') 返回的不是一个列表的列表")
        return None
    except Exception as e:
        logger.critical(f"失败: 意外错误 {e}")
        return None

# ======================================================================
# 2. 核心功能模块 (@json-merge)
# ======================================================================

def extract_file_order(filename: str) -> Tuple[List[int], str]:
    """
    从文件名中提取排序信息。支持多种格式：
    1. 数字格式: 'inductive_question1.json' -> ([1], 'question')
    2. 范围格式: 'inductive_question4-5.json' -> ([4, 5], 'question')
    3. 自定义前缀: 'inductive_q1.json' -> ([1], 'q')
    
    参数:
        filename: 文件名
        
    返回:
        Tuple[List[int], str]: (序号列表, 前缀类型)
    """
    # 支持多种前缀格式
    prefix_patterns = [
        (r'(?:questio(?:n)?|q)(\d+(?:-\d+)?)', 'question'),  # 匹配 question/questio/q
        (r'_(\d+(?:-\d+)?)', 'number'),  # 匹配纯数字
    ]
    
    for pattern, prefix_type in prefix_patterns:
        match = re.search(pattern, filename, re.IGNORECASE)
        if match:
            number_part = match.group(1)
            
            # 处理范围格式 (例如: "4-5")
            if '-' in number_part:
                start, end = map(int, number_part.split('-'))
                return list(range(start, end + 1)), prefix_type
            
            # 处理单个数字
            return [int(number_part)], prefix_type
    
    logger.warning(f"无法从文件名 '{filename}' 中提取序号，将使用文件名自然排序")
    return [0], 'default'

def natural_sort_key(filename: str) -> Tuple[int, str]:
    """
    生成用于自然排序的键。
    如果无法提取序号，则使用文件名本身进行排序。
    """
    numbers, prefix_type = extract_file_order(filename)
    primary_key = numbers[0] if numbers else 0
    return (primary_key, filename)

def merge_all_inductive_jsons(file_paths_list: List[str]) -> List[Dict[str, Any]]:
    """
    接收一个扁平的文件路径列表，将所有JSON文件的内容合并成一个单一的列表。
    使用更灵活的排序机制，不再严格依赖序号。
    
    参数:
        file_paths_list: JSON文件路径列表
        
    返回:
        List[Dict[str, Any]]: 合并后的问题对象列表
    """
    if not file_paths_list:
        logger.info("[JSON-MERGE]: 接收到的文件列表为空，无需合并")
        return []

    logger.info("[JSON-MERGE]: 开始合并JSON文件内容...")
    logger.info("\n[排序过程] 原始文件列表:")
    for path in file_paths_list:
        logger.info(f"  - {os.path.basename(path)}")
    
    # 创建一个列表来存储文件内容和其对应的排序信息
    file_contents = []
    processed_files = 0
    failed_files = 0
    
    # 首先按文件名自然排序
    sorted_paths = sorted(file_paths_list, key=lambda p: natural_sort_key(os.path.basename(p)))
    
    # 读取所有文件内容
    for file_path in sorted_paths:
        filename = os.path.basename(file_path)
        logger.info(f"\n处理文件: {filename}")
        
        # 获取文件排序信息
        order_numbers, prefix_type = extract_file_order(filename)
        logger.info(f"  提取的排序信息: 序号={order_numbers}, 类型={prefix_type}")
        
        # 验证文件
        is_valid, data = validate_json_file(file_path)
        if is_valid and data:
            # 将每个问题对象与其序号一起存储
            for idx, question in enumerate(data):
                # 使用文件序号和问题在文件中的位置作为排序依据
                order_number = order_numbers[idx] if idx < len(order_numbers) else order_numbers[-1]
                file_contents.append({
                    'order': order_number,
                    'file_index': idx,
                    'question': question,
                    'filename': filename,
                    'prefix_type': prefix_type
                })
                logger.info(f"    问题 {idx + 1}: 分配序号 {order_number}")
            
            processed_files += 1
            logger.info(f"  √ 成功读取文件: {filename} (包含 {len(data)} 个问题对象)")
        else:
            failed_files += 1
            logger.error(f"  × 跳过无效文件: {filename}")
    
    # 按多个条件排序：序号、文件中的位置、文件名
    file_contents.sort(key=lambda x: (x['order'], x['file_index'], x['filename']))
    
    # 输出排序后的顺序
    logger.info("\n[排序结果] 问题排序后的顺序:")
    for item in file_contents:
        logger.info(f"  - 文件: {item['filename']}, 序号: {item['order']}, "
                   f"文件内位置: {item['file_index']}, 类型: {item['prefix_type']}")
    
    # 提取排序后的问题对象
    aggregated_question_objects = [item['question'] for item in file_contents]
    
    # 合并完成后的统计信息
    logger.info("\n[JSON-MERGE] 合并完成统计:")
    logger.info(f"- 总文件数: {len(file_paths_list)}")
    logger.info(f"- 成功处理: {processed_files}")
    logger.info(f"- 处理失败: {failed_files}")
    logger.info(f"- 合并后的问题对象总数: {len(aggregated_question_objects)}")
    
    return aggregated_question_objects

def validate_respondent_id(merged_data: List[Dict[str, Any]]) -> bool:
    """
    验证合并后的数据中respondent_id是否符合要求：
    每个问题下的respondent_id应该是从1到n的完整序列
    
    参数:
        merged_data: 合并后的问题对象列表
        
    返回:
        bool: 验证通过返回True，否则返回False
    """
    if not merged_data:
        logger.warning("验证ID: 数据为空")
        return False
        
    try:
        all_valid = True
        for question in merged_data:
            question_text = question.get('question_text', 'Unknown Question')
            
            # 获取该问题下的所有ID
            question_ids = [response['respondent_id'] for response in question['initial_codes']]
            unique_ids = sorted(set(question_ids))
            
            # 计算期望的ID序列
            expected_ids = list(range(1, len(unique_ids) + 1))
            
            # 检查该问题下的ID是否完整
            if unique_ids != expected_ids:
                logger.error(f"\n验证ID: 问题 '{question_text}' 的ID序列不完整")
                logger.error(f"期望ID序列: {expected_ids}")
                logger.error(f"实际ID序列: {unique_ids}")
                # 找出缺失的ID
                missing_ids = set(expected_ids) - set(unique_ids)
                if missing_ids:
                    logger.error(f"缺失的ID: {sorted(missing_ids)}")
                # 找出多余的ID
                extra_ids = set(unique_ids) - set(expected_ids)
                if extra_ids:
                    logger.error(f"多余的ID: {sorted(extra_ids)}")
                all_valid = False
                
            # 检查该问题下是否有重复ID
            if len(unique_ids) != len(question_ids):
                logger.error(f"\n验证ID: 问题 '{question_text}' 存在重复ID")
                # 统计重复的ID
                from collections import Counter
                id_counts = Counter(question_ids)
                duplicate_ids = {id_: count for id_, count in id_counts.items() if count > 1}
                for id_, count in duplicate_ids.items():
                    logger.error(f"ID {id_} 在该问题中重复出现 {count} 次")
                all_valid = False
                
        if all_valid:
            logger.info("验证ID: 所有问题的ID序列都符合要求")
            return True
        return False
        
    except KeyError as e:
        logger.error(f"验证ID: 数据结构错误，缺少必要字段: {e}")
        return False
    except Exception as e:
        logger.error(f"验证ID: 意外错误 {e}")
        return False

# ======================================================================
# 3. 输出机制模块 (@ds-n1-save)
# ======================================================================

def save_merged_json(data_to_save: List[Dict[str, Any]], output_filepath: str) -> bool:
    """
    将合并后的数据保存到指定的输出路径。
    
    参数:
        data_to_save: 要保存的数据
        output_filepath: 输出文件路径
        
    返回:
        bool: 保存成功返回True，失败返回False
    """
    if not data_to_save:
        logger.warning("待保存的数据为空，不生成输出文件")
        return False

    logger.info(f"准备保存合并后的JSON文件到: {output_filepath}")
    
    try:
        # 确保输出目录存在
        output_dir = os.path.dirname(output_filepath)
        if not os.path.exists(output_dir):
            logger.info(f"输出目录 '{output_dir}' 不存在，将自动创建")
            os.makedirs(output_dir)

        # 保存数据
        with open(output_filepath, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=2)
            
        # 验证保存的文件
        is_valid, _ = validate_json_file(output_filepath)
        if not is_valid:
            logger.error("保存的文件验证失败")
            return False
            
        logger.info("数据已成功保存并验证")
        return True
        
    except Exception as e:
        logger.error(f"保存文件时发生错误: {e}")
        return False

def generate_issue_report(file_paths_list: List[str], merged_data: List[Dict[str, Any]]) -> None:
    """
    生成问题汇总报告，包括：
    1. JSON结构问题
    2. 缺少字段问题
    3. 问题编码重复问题
    4. 其他问题
    
    参数:
        file_paths_list: 所有JSON文件路径
        merged_data: 合并后的数据
    """
    logger.info("\n" + "="*50)
    logger.info("问题汇总报告")
    logger.info("="*50)
    
    # 1. 检查每个文件的结构问题
    logger.info("\n1. JSON结构问题:")
    logger.info("-" * 30)
    structure_issues = []
    field_issues = []
    
    for file_path in file_paths_list:
        filename = os.path.basename(file_path)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            if not isinstance(data, list):
                structure_issues.append(f"  - {filename}: 根结构不是列表")
                continue
                
            # 检查必需字段
            for item in data:
                if not isinstance(item, dict):
                    structure_issues.append(f"  - {filename}: 包含非字典类型的元素")
                    continue
                    
                missing_fields = []
                for field in ['question_text', 'initial_codes', 'codes', 'themes']:
                    if field not in item:
                        missing_fields.append(field)
                
                if missing_fields:
                    field_issues.append(f"  - {filename}: 缺少字段 {', '.join(missing_fields)}")
                    
        except json.JSONDecodeError:
            structure_issues.append(f"  - {filename}: JSON解析失败")
        except Exception as e:
            structure_issues.append(f"  - {filename}: 其他错误 - {str(e)}")
            
    if structure_issues:
        for issue in structure_issues:
            logger.error(issue)
    else:
        logger.info("  √ 未发现JSON结构问题")
        
    # 2. 缺少字段问题
    logger.info("\n2. 缺少字段问题:")
    logger.info("-" * 30)
    if field_issues:
        for issue in field_issues:
            logger.error(issue)
    else:
        logger.info("  √ 未发现字段缺失问题")
        
    # 3. 问题编码重复问题
    logger.info("\n3. 问题编码重复问题:")
    logger.info("-" * 30)
    question_counts = {}
    for file_path in file_paths_list:
        filename = os.path.basename(file_path)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    count = len(data)
                    if count > 1:
                        question_counts[filename] = count
        except:
            continue
            
    if question_counts:
        for filename, count in question_counts.items():
            logger.warning(f"  - {filename}: 包含 {count} 个问题对象")
    else:
        logger.info("  √ 未发现问题编码重复问题")
        
    # 4. 问题编号连续性检查
    logger.info("\n4. 问题编号连续性检查:")
    logger.info("-" * 30)
    
    # 提取所有问题编号
    question_numbers = []
    for file_path in file_paths_list:
        match = re.search(r'question(\d+)', os.path.basename(file_path))
        if match:
            question_numbers.append(int(match.group(1)))
            
    if question_numbers:
        question_numbers.sort()
        expected_numbers = list(range(min(question_numbers), max(question_numbers) + 1))
        missing_numbers = set(expected_numbers) - set(question_numbers)
        
        if missing_numbers:
            logger.warning(f"  - 问题编号不连续，缺少编号: {sorted(missing_numbers)}")
        else:
            logger.info("  √ 问题编号连续")
    
    logger.info("\n" + "="*50)

# ======================================================================
# 任务流程编排 (Main Execution)
# ======================================================================

def main() -> None:
    """主执行函数，编排整个任务流程"""
    logger.info("="*50)
    logger.info(f"开始执行 @ds-n1-sample 任务: 合并初步归纳编码JSON文件")
    logger.info(f"脚本: 02inductive_merge_json.py | 版本: 2.3")
    logger.info(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*50)

    try:
        # 1. 获取输入文件路径
        input_paths = get_all_inductive_json_paths()
        if input_paths is None:
            logger.error("由于配置错误，无法获取输入文件列表。任务终止。")
            return

        # 2. 合并JSON文件
        merged_data = merge_all_inductive_jsons(input_paths)
        if not merged_data:
            logger.error("合并过程未产生有效数据。任务终止。")
            return
            
        # 2.1 验证respondent_id
        if not validate_respondent_id(merged_data):
            logger.error("respondent_id验证失败。任务终止。")
            return

        # 3. 保存合并结果
        try:
            output_directory = get_path('inductive_global_dir')
            output_filename = f"{APP_NAME}_inductive_codes.json"
            full_output_path = os.path.join(output_directory, output_filename)
            
            if save_merged_json(merged_data, full_output_path):
                logger.info(f"任务成功完成，输出文件: {full_output_path}")
            else:
                logger.error("保存合并结果失败")
                
        except KeyError:
            logger.critical("无法获取输出目录路径。请确保 'inductive_global_dir' key 在 parameters.py 中已定义")
            return
            
        # 4. 生成问题汇总报告
        generate_issue_report(input_paths, merged_data)
            
    except Exception as e:
        logger.critical(f"执行过程中发生未预期的错误: {e}")
        return
        
    finally:
        logger.info("="*50)
        logger.info("任务执行完毕")
        logger.info("="*50)

if __name__ == "__main__":
    main()