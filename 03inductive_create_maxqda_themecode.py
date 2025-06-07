"""
MaxQDA Theme Code Generator

将LLM分析的JSON数据转换为MaxQDA兼容的结构化文本格式。
实现了系统化的编码生成和主题组织方法，同时保持数据完整性和可追溯性。

作者: Your Name
日期: 2024
版本: 3.0
"""

import os
import json
import re
import csv
import pandas as pd
from fuzzywuzzy import process, fuzz
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple, Set

def setup_logging() -> None:
    """配置日志系统，包含文件和控制台输出。"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            logging.FileHandler('workflow.log', mode='a', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

setup_logging()
logger = logging.getLogger(__name__)

# 导入配置参数
try:
    from parameters import (
        get_path,
        P_DBUG_RESPONDENT_ID,
        P_DBUG_QUESTION_TEXT_RAW,
        get_id_manager
    )
    logger.info("成功从 parameters.py 导入配置")
except ImportError as e:
    logger.critical(f"无法从 parameters.py 导入配置: {e}")
    raise

# 全局调试控制
PRINT_CURRENT_ITEM_DETAILS = False

# TODO: 未来的被访者ID可能全部转换为标准的内部_id, 该函数可能需要修改为直接返回内部_id
def normalize_respondent_id(respondent_id: str) -> Optional[str]:
    """
    将不同格式的respondent_id标准化为数字格式
    例如：
    "1" -> "1"
    "P1" -> "1"
    "被访者1" -> "1"
    """
    if not respondent_id:
        return None
    
    # 如果已经是纯数字
    if str(respondent_id).isdigit():
        return str(respondent_id)
    
    # 移除所有非数字字符
    numbers = re.findall(r'\d+', str(respondent_id))
    if numbers:
        return numbers[0]
    
    return None

def clean_text_for_maxqda(text: Optional[str], is_for_code_name: bool = False) -> str:
    """
    清理和标准化文本以适配MaxQDA格式。
    
    参数:
        text: 需要清理的文本，可以为None
        is_for_code_name: 如果为True，应用额外的编码名称清理规则
    
    返回:
        str: 清理后的文本字符串
    """
    global PRINT_CURRENT_ITEM_DETAILS
    if text is None:
        return ""
    
    # 基本清理
    cleaned_text = str(text).replace('\r\n', ' ').replace('\n', ' ').replace('\r', ' ').replace('#', '')
    
    if is_for_code_name:
        # 处理路径分隔符和引号
        cleaned_text = cleaned_text.replace('\\', '/').replace('"', "'")
        
        # 统一中英文标点
        punctuation_map = {
            '？': '?', '！': '!', '：': ':', '；': ';',
            '，': ',', '。': '.', '"': '"', '"': '"',
            ''': "'", ''': "'", '（': '(', '）': ')',
            '【': '[', '】': ']', '《': '<', '》': '>',
            '…': '...', '—': '-', '～': '~', '·': '.'
        }
        for ch, en in punctuation_map.items():
            cleaned_text = cleaned_text.replace(ch, en)
            
        # 移除结尾的标点符号
        cleaned_text = re.sub(r'[.!?:;,]+$', '', cleaned_text)
        
    # 规范化空格
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
    
    if PRINT_CURRENT_ITEM_DETAILS:
        logger.debug(f"文本清理 - 原文: '{str(text)[:50]}...', 清理后: '{cleaned_text[:50]}...'")
    
    return cleaned_text

def _find_locations_for_single_quote(text_to_search_in: str, quote_to_find: str) -> List[Dict[str, Any]]:
    """
    在文本中查找引文的所有出现位置，支持模糊匹配。
    
    参数:
        text_to_search_in: 要搜索的源文本
        quote_to_find: 要定位的引文文本
    
    返回:
        List[Dict]: 包含每个匹配位置信息的字典列表
        每个字典包含:
            - start: 匹配的起始位置
            - end: 匹配的结束位置
            - matched_text: 实际匹配的文本
            - match_type: 'exact'(精确匹配) 或 'fuzzy'(模糊匹配)
            - score: (仅模糊匹配) 匹配相似度分数
    """
    global PRINT_CURRENT_ITEM_DETAILS
    
    if not quote_to_find:
        return []
        
    processed_text = re.sub(r'\s+', ' ', text_to_search_in).strip()
    processed_quote = re.sub(r'\s+', ' ', quote_to_find).strip()
    
    if not processed_quote:
        return []
        
    if PRINT_CURRENT_ITEM_DETAILS:
        logger.debug(f"尝试定位引文: '{processed_quote[:50]}...' 在文本中: '{processed_text[:70]}...'")
    
    # 首先尝试精确匹配
    locations = []
    current_pos = 0
    while current_pos < len(processed_text):
        idx = processed_text.find(processed_quote, current_pos)
        if idx == -1:
            break
        locations.append({
            'start': idx,
            'end': idx + len(processed_quote),
            'matched_text': processed_text[idx : idx + len(processed_quote)],
            'match_type': 'exact'
        })
        current_pos = idx + len(processed_quote)
    
    if locations:
        if PRINT_CURRENT_ITEM_DETAILS:
            logger.debug(f"精确匹配找到 {len(locations)} 处")
        return locations
        
    # 如果精确匹配失败，尝试模糊匹配
    if PRINT_CURRENT_ITEM_DETAILS:
        logger.debug(f"精确匹配失败，尝试模糊匹配引文: '{processed_quote[:50]}...'")
    
    threshold = 85 
    min_len_for_fuzzy = 3
    if len(processed_quote) >= min_len_for_fuzzy:
        possible_substrings = [processed_text[i:j] for i in range(len(processed_text)) 
                               for j in range(i + len(processed_quote) - int(len(processed_quote)*0.3),
                                              i + len(processed_quote) + int(len(processed_quote)*0.3) + 1)
                               if j <= len(processed_text) and len(processed_text[i:j]) >= min_len_for_fuzzy]
        if not possible_substrings:
             if PRINT_CURRENT_ITEM_DETAILS: print(f"        模糊定位: 没有生成用于比较的子字符串。")
             return []
        results = process.extractBests(processed_quote, possible_substrings,
                                       scorer=fuzz.ratio, score_cutoff=threshold, limit=5) 
        temp_fuzzy_locations = []
        for matched_text, score in results:
            s_idx = 0
            while s_idx < len(processed_text):
                pos = processed_text.find(matched_text, s_idx)
                if pos == -1: break
                is_new = True
                for loc_in_temp in temp_fuzzy_locations:
                    if loc_in_temp['start'] == pos and loc_in_temp['end'] == pos + len(matched_text):
                        is_new = False; break
                if is_new:
                    temp_fuzzy_locations.append({'start': pos, 'end': pos + len(matched_text),
                                                 'matched_text': matched_text, 
                                                 'match_type': 'fuzzy', 'score': score})
                s_idx = pos + len(matched_text)
        if temp_fuzzy_locations:
            temp_fuzzy_locations.sort(key=lambda x: x['score'], reverse=True)
            if temp_fuzzy_locations: # 确保列表非空
                 locations.append(temp_fuzzy_locations[0]) 
                 if PRINT_CURRENT_ITEM_DETAILS:
                     print(f"        模糊定位: 找到 {len(temp_fuzzy_locations)} 个潜在匹配。选用最佳: '{locations[0]['matched_text'][:30]}...' (得分: {locations[0].get('score')})")
        elif PRINT_CURRENT_ITEM_DETAILS:
            print(f"        模糊定位: 未找到足够相似的片段。")
    return locations

def validate_initial_code_entry(entry: Dict, question_text: str) -> bool:
    """
    验证初始编码条目的结构完整性
    
    Args:
        entry: 初始编码条目
        question_text: 当前处理的问题文本，用于日志
    
    Returns:
        bool: 是否是有效的初始编码条目
    """
    required_fields = ['respondent_id', 'original_answer_segment', 'code_name', 'supporting_quote', 'pairs']
    
    # 检查必需字段
    for field in required_fields:
        if field not in entry:
            logger.warning(f"问题 '{question_text}' 的初始编码条目缺少必需字段: {field}")
            return False
            
    # 验证数组字段
    if not isinstance(entry['code_name'], list) or not isinstance(entry['supporting_quote'], list):
        logger.warning(f"问题 '{question_text}' 的初始编码条目中 code_name 或 supporting_quote 不是数组")
        return False
        
    # 验证pairs的格式
    if not isinstance(entry['pairs'], list):
        logger.warning(f"问题 '{question_text}' 的初始编码条目中 pairs 不是数组")
        return False
        
    for pair in entry['pairs']:
        if not isinstance(pair, str) or '-' not in pair:
            logger.warning(f"问题 '{question_text}' 的初始编码条目中存在无效的pair格式: {pair}")
            return False
            
    return True

def validate_theme_entry(theme: Dict, question_text: str) -> bool:
    """
    验证主题编码条目的结构完整性
    
    Args:
        theme: 主题编码条目
        question_text: 当前处理的问题文本，用于日志
    
    Returns:
        bool: 是否是有效的主题编码条目
    """
    required_fields = ['theme_name', 'theme_definition', 'included_initial_codes']
    
    # 检查必需字段
    for field in required_fields:
        if field not in theme:
            logger.warning(f"问题 '{question_text}' 的主题编码条目缺少必需字段: {field}")
            return False
            
    # 验证included_initial_codes是否为数组
    if not isinstance(theme['included_initial_codes'], list):
        logger.warning(f"问题 '{question_text}' 的主题编码条目中 included_initial_codes 不是数组")
        return False
        
    return True

def load_llm_json_data(merged_json_filepath: str) -> Optional[Dict[str, Any]]:
    """
    加载并处理LLM分析的JSON数据。
    
    Args:
        merged_json_filepath: 合并后的LLM分析JSON文件路径
        
    Returns:
        Optional[Dict]: 清理后的问题文本到分析数据的映射，加载失败时返回None
    """
    logger.info(f"开始加载LLM分析JSON文件: {merged_json_filepath}")
    
    if not os.path.exists(merged_json_filepath):
        logger.error(f"未找到合并后的JSON文件: '{merged_json_filepath}'")
        return None
        
    try:
        with open(merged_json_filepath, 'r', encoding='utf-8') as f:
            llm_analysis_data = json.load(f)
            
        if not isinstance(llm_analysis_data, list):
            logger.error("JSON文件格式错误：根级别应该是数组")
            return None
            
        logger.info(f"成功加载LLM JSON文件，包含 {len(llm_analysis_data)} 个问题的分析")
        
        llm_data_by_question_map = {}
        for question_idx, question_analysis in enumerate(llm_analysis_data, 1):
            # 验证问题文本
            q_text_from_json = question_analysis.get("question_text", "")
            if not q_text_from_json:
                logger.warning(f"第 {question_idx} 个问题分析条目缺少question_text字段，已跳过")
                continue
                
            cleaned_q_text_for_key = clean_text_for_maxqda(q_text_from_json, is_for_code_name=True)
            logger.debug(f"处理问题 {question_idx}: '{q_text_from_json}' (清理后: '{cleaned_q_text_for_key}')")
            
            # 验证并过滤有效的初始编码
            initial_codes = question_analysis.get("initial_codes", [])
            valid_initial_codes = [
                code for code in initial_codes
                if validate_initial_code_entry(code, q_text_from_json)
            ]
            
            if len(valid_initial_codes) < len(initial_codes):
                logger.warning(f"问题 '{q_text_from_json}' 的 {len(initial_codes) - len(valid_initial_codes)} 个初始编码条目无效")
            
            # 验证并过滤有效的主题
            themes = question_analysis.get("themes", [])
            valid_themes = [
                theme for theme in themes
                if validate_theme_entry(theme, q_text_from_json)
            ]
            
            if len(valid_themes) < len(themes):
                logger.warning(f"问题 '{q_text_from_json}' 的 {len(themes) - len(valid_themes)} 个主题编码条目无效")
            
            # 验证codes数组
            codes = question_analysis.get("codes", [])
            valid_codes = [
                code for code in codes
                if isinstance(code, dict) and "code_name" in code and "code_definition" in code
            ]
            
            if len(valid_codes) < len(codes):
                logger.warning(f"问题 '{q_text_from_json}' 的 {len(codes) - len(valid_codes)} 个编码定义无效")
            
            # 更新或创建问题数据映射
            if cleaned_q_text_for_key not in llm_data_by_question_map:
                llm_data_by_question_map[cleaned_q_text_for_key] = {
                    'themes_for_this_question': valid_themes,
                    'all_initial_code_entries_for_question': valid_initial_codes,
                    'code_definitions_for_this_question': valid_codes
                }
                logger.info(f"问题 '{q_text_from_json}' 处理完成: {len(valid_initial_codes)} 个初始编码, "
                          f"{len(valid_themes)} 个主题, {len(valid_codes)} 个编码定义")
            else:
                logger.warning(f"发现重复问题 '{q_text_from_json}'，正在合并数据...")
                # 合并数据时去重
                existing_data = llm_data_by_question_map[cleaned_q_text_for_key]
                
                # 使用集合去重
                existing_themes = {theme['theme_name']: theme for theme in existing_data['themes_for_this_question']}
                for theme in valid_themes:
                    if theme['theme_name'] not in existing_themes:
                        existing_data['themes_for_this_question'].append(theme)
                
                # 使用respondent_id去重初始编码
                existing_codes = {
                    (code.get('respondent_id', ''), code.get('original_answer_segment', '')): code
                    for code in existing_data['all_initial_code_entries_for_question']
                }
                for code in valid_initial_codes:
                    key = (code.get('respondent_id', ''), code.get('original_answer_segment', ''))
                    if key not in existing_codes:
                        existing_data['all_initial_code_entries_for_question'].append(code)
                
                # 使用code_name去重编码定义
                existing_definitions = {
                    code['code_name']: code
                    for code in existing_data['code_definitions_for_this_question']
                }
                for code in valid_codes:
                    if code['code_name'] not in existing_definitions:
                        existing_data['code_definitions_for_this_question'].append(code)
                
        logger.info(f"LLM编码数据已映射到 {len(llm_data_by_question_map)} 个问题")
        return llm_data_by_question_map
        
    except json.JSONDecodeError as e:
        logger.error(f"解析JSON文件 '{merged_json_filepath}' 失败: {e}")
        return None
    except Exception as e:
        logger.error(f"加载LLM JSON '{merged_json_filepath}' 时发生意外错误: {e}")
        logger.debug("错误堆栈:", exc_info=True)
        return None

def load_interview_csv_data(original_csv_filepath: str, respondent_id_csv_column: str = None) -> Tuple[Optional[List[Dict]], Optional[List[str]]]:
    """
    加载访谈CSV数据。
    
    参数:
        original_csv_filepath: 原始访谈CSV文件路径
        respondent_id_csv_column: 可选，指定ID列名。如果不指定，使用第一列作为ID列
        
    返回:
        Tuple[Optional[List[Dict]], Optional[List[str]]]: 包含:
            - 访谈数据字典列表，加载失败时返回None
            - CSV表头列表，加载失败时返回None
    """
    logger.info(f"开始加载原始CSV访谈数据: {original_csv_filepath}")
    
    if not os.path.exists(original_csv_filepath):
        logger.error(f"未找到原始CSV文件: '{original_csv_filepath}'")
        return None, None
        
    try:
        original_interviews_data = []
        with open(original_csv_filepath, 'r', encoding='utf-8-sig') as csvfile:
            reader = csv.DictReader(csvfile)
            if not reader.fieldnames:
                logger.error(f"CSV文件 '{original_csv_filepath}' 表头为空或无法读取")
                return None, None
                
            csv_header_list = reader.fieldnames
            
            # 使用第一列作为ID列
            id_column = csv_header_list[0]
            if respondent_id_csv_column and respondent_id_csv_column != id_column:
                logger.warning(f"指定的ID列 '{respondent_id_csv_column}' 与第一列 '{id_column}' 不同，将使用第一列作为ID列")
            
            logger.info(f"CSV表头: {csv_header_list}")
            logger.info(f"使用 '{id_column}' 作为ID列")
            
            # 读取所有行的ID
            for i, row in enumerate(reader):
                # 跳过空行
                if not any(row.values()):
                    logger.debug(f"跳过第{i+1}行：空行")
                    continue
                    
                original_interviews_data.append(row)
                id_value = row.get(id_column, "").strip()
                logger.info(f"第{i+1}行的ID值: '{id_value}'")
                
        valid_records = [row for row in original_interviews_data if row.get(id_column, "").strip()]
        logger.info(f"成功加载CSV数据，共 {len(valid_records)} 条有效被访者记录")
        return valid_records, csv_header_list
        
    except Exception as e:
        logger.error(f"读取或处理CSV文件 '{original_csv_filepath}' 失败: {e}")
        logger.debug("错误堆栈:", exc_info=True)
        return None, None

def load_data(merged_json_path: str, original_csv_path: str, respondent_id_col: str = None) -> Tuple[Optional[Dict], Optional[List[Dict]], Optional[List[str]]]:
    """
    加载MaxQDA转换过程所需的所有数据。
    
    参数:
        merged_json_path: 合并后的LLM分析JSON文件路径
        original_csv_path: 原始访谈CSV文件路径
        respondent_id_col: 可选，指定ID列名。如果不指定，使用第一列作为ID列
        
    返回:
        Tuple[Optional[Dict], Optional[List[Dict]], Optional[List[str]]]: 包含:
            - LLM分析数据字典
            - 访谈数据字典列表
            - CSV表头列表
            任何加载操作失败时返回 (None, None, None)
    """
    logger.info("开始数据加载流程...")
    
    llm_data = load_llm_json_data(merged_json_path)
    original_data, csv_headers = load_interview_csv_data(original_csv_path, respondent_id_col)
    
    if llm_data is not None and original_data is not None and csv_headers is not None:
        logger.info("所有数据加载成功")
        return llm_data, original_data, csv_headers
    else:
        logger.error("数据加载失败")
        return None, None, None

# --- 将JSON信息转换为MAXQDA结构文本的方法 ---
def get_segments_and_codes_for_answer(
    original_answer_processed: str,
    current_respondent_id: str,
    llm_initial_code_entries_for_respondent: List[Dict],
    themes_for_current_question: List[Dict],
    parent_question_cleaned: str
) -> List[Dict]:
    """获取答案的分段和编码信息"""
    aggregated_segments_map = {}
    
    # 标准化当前被访者ID
    # TODO: 这里需要获取world-id.csv的 _id
    normalized_current_id = normalize_respondent_id(current_respondent_id)
    if not normalized_current_id:
        return []
    
    # 处理每个编码条目
    for llm_entry in llm_initial_code_entries_for_respondent:
        # 标准化编码条目中的被访者ID

        # TODO: 合并的JSON文件已经在 02inductive_merge_json.py 中验证过，无需再次验证了，直接获取respondent_id即可
        entry_id = normalize_respondent_id(llm_entry.get('respondent_id'))
        #TODO: 这里直接比较 _id 与 respondent_id 是否一致即可
        if entry_id != normalized_current_id:
            continue
            
        code_names_list = llm_entry.get("code_name", [])
        supporting_quotes_list = llm_entry.get("supporting_quote", [])
        pairs_list = llm_entry.get("pairs", [])
        
        # 验证数据格式
        if not (isinstance(code_names_list, list) and 
                isinstance(supporting_quotes_list, list) and 
                isinstance(pairs_list, list)):
            continue
            
        # 处理每个编码-引文对
        for pair_str in pairs_list:
            try:
                # 解析编码-引文对的索引
                code_idx_str, quote_idx_str = pair_str.split('-')
                code_idx = int(code_idx_str) - 1
                quote_idx = int(quote_idx_str) - 1
                
                # 验证索引范围
                if not (0 <= code_idx < len(code_names_list) and 
                       0 <= quote_idx < len(supporting_quotes_list)):
                    continue
                    
                # 获取编码和引文
                raw_initial_code = code_names_list[code_idx]
                raw_supporting_quote = supporting_quotes_list[quote_idx]
                
                # 跳过无效数据
                if str(raw_initial_code).upper() == "NULL" or not str(raw_supporting_quote).strip():
                    continue
                    
                # 清理编码和引文文本
                cleaned_initial_code = clean_text_for_maxqda(raw_initial_code, is_for_code_name=True)
                if not cleaned_initial_code:
                    continue
                    
                quote_to_find = clean_text_for_maxqda(raw_supporting_quote, is_for_code_name=False)
                if not quote_to_find:
                    continue
                    
                # 在原文中定位引文
                found_locations = _find_locations_for_single_quote(original_answer_processed, quote_to_find)
                if not found_locations:
                    continue
                    
                # 处理找到的每个位置
                for loc_data in found_locations:
                    start, end = loc_data['start'], loc_data['end']
                    matched_text = loc_data['matched_text']
                    segment_key = (start, end)
                    
                    # 初始化新的段落
                    if segment_key not in aggregated_segments_map:
                        aggregated_segments_map[segment_key] = {
                            'matched_text': matched_text,
                            'codes_to_apply_set': set()
                        }
                        
                    # 尝试找到对应的主题
                    found_theme = False
                    for theme_entry in themes_for_current_question:
                        theme_name_raw = theme_entry.get("theme_name")
                        included_ics = theme_entry.get("included_initial_codes", [])
                        cleaned_included_ics = [clean_text_for_maxqda(ic, True) for ic in included_ics]
                        
                        if cleaned_initial_code in cleaned_included_ics:
                            cleaned_theme_name = clean_text_for_maxqda(theme_name_raw, is_for_code_name=True)
                            if cleaned_theme_name:
                                # 构建三级编码
                                hierarchical_code = f"{parent_question_cleaned}\\{cleaned_theme_name}\\{cleaned_initial_code}"
                                found_theme = True
                                aggregated_segments_map[segment_key]['codes_to_apply_set'].add(hierarchical_code)
                                break
                                
                    # 如果没找到主题，使用二级编码
                    if not found_theme:
                        hierarchical_code = f"{parent_question_cleaned}\\{cleaned_initial_code}"
                        aggregated_segments_map[segment_key]['codes_to_apply_set'].add(hierarchical_code)
                        
            except Exception as e:
                logger.warning(f"处理编码-引文对时出错: {e}")
                continue
                
    # 转换为列表格式并排序
    final_located_list = []
    for (start, end), data in aggregated_segments_map.items():
        if data['codes_to_apply_set']:  # 只添加有编码的段落
            final_located_list.append({
                'start': start,
                'end': end,
                'matched_text': data['matched_text'],
                'all_applicable_codes_set': data['codes_to_apply_set']
            })
    final_located_list.sort(key=lambda x: x['start'])
            
    return final_located_list

def resolve_overlaps_and_aggregate_codes(
    sorted_located_segments: List[Dict],
    original_answer_for_tagging: str
) -> List[Dict]:
    """解决重叠并聚合编码"""
    if not sorted_located_segments:
        return []
        
    final_non_overlapping_segments = []
    current_merged_s = None
    
    for next_s_data in sorted_located_segments:
        if current_merged_s is None:
            current_merged_s = {
                'start': next_s_data['start'],
                'end': next_s_data['end'],
                'codes_to_apply_set': set(next_s_data['all_applicable_codes_set'])
            }
        elif next_s_data['start'] < current_merged_s['end']:
            current_merged_s['end'] = max(current_merged_s['end'], next_s_data['end'])
            current_merged_s['codes_to_apply_set'].update(next_s_data['all_applicable_codes_set'])
        else:
            text_for_merged = original_answer_for_tagging[current_merged_s['start']:current_merged_s['end']]
            final_non_overlapping_segments.append({
                'start': current_merged_s['start'],
                'end': current_merged_s['end'],
                'text_to_code': text_for_merged,
                'final_combined_codes_str': "&&".join(sorted(list(current_merged_s['codes_to_apply_set'])))
            })
            current_merged_s = {
                'start': next_s_data['start'],
                'end': next_s_data['end'],
                'codes_to_apply_set': set(next_s_data['all_applicable_codes_set'])
            }
            
    if current_merged_s:
        text_for_merged = original_answer_for_tagging[current_merged_s['start']:current_merged_s['end']]
        final_non_overlapping_segments.append({
            'start': current_merged_s['start'],
            'end': current_merged_s['end'],
            'text_to_code': text_for_merged,
            'final_combined_codes_str': "&&".join(sorted(list(current_merged_s['codes_to_apply_set'])))
        })
        
    return final_non_overlapping_segments

def build_tagged_line_from_segments(
    original_answer_for_tagging: str,
    final_non_overlapping_segments: List[Dict]
) -> str:
    """从分段构建带标签的行"""
    if not final_non_overlapping_segments:
        return original_answer_for_tagging
        
    result_parts = []
    current_pos_in_original = 0
    
    for segment in final_non_overlapping_segments:
        if segment['start'] > current_pos_in_original:
            uncoded_part = original_answer_for_tagging[current_pos_in_original:segment['start']]
            result_parts.append(uncoded_part)
            
        text_coded_cleaned = clean_text_for_maxqda(segment['text_to_code'], is_for_code_name=False)
        maxqda_tag_segment = f"#CODE {segment['final_combined_codes_str']}#{text_coded_cleaned}#ENDCODE#"
        result_parts.append(maxqda_tag_segment)
        current_pos_in_original = segment['end']
        
    if current_pos_in_original < len(original_answer_for_tagging):
        remaining_uncoded_part = original_answer_for_tagging[current_pos_in_original:]
        result_parts.append(remaining_uncoded_part)
        
    final_line = "".join(result_parts).strip()
    return final_line if final_line else original_answer_for_tagging

# --- 主转换流程控制函数 ---
def run_maxqda_conversion(
    loaded_llm_data_map: Dict[str, Any],
    loaded_original_interviews: List[Dict[str, str]],
    loaded_csv_headers: List[str],
    respondent_id_csv_column: str,
    questions_to_skip_coding: List[str] = None
) -> str:
    """
    执行MaxQDA转换流程，将LLM分析数据转换为MaxQDA格式。
    
    参数:
        loaded_llm_data_map: 问题到LLM分析数据的映射
        loaded_original_interviews: 原始访谈数据列表
        loaded_csv_headers: CSV文件的列标题列表
        respondent_id_csv_column: 受访者ID列名
        questions_to_skip_coding: 需要跳过编码的问题列表
        
    返回:
        str: MaxQDA格式的文本内容
    """
    logger.info("开始MaxQDA格式转换")
    
    # 获取调试目标
    target_id_for_debug = str(P_DBUG_RESPONDENT_ID).strip() if P_DBUG_RESPONDENT_ID is not None else None
    target_q_cleaned_for_debug = clean_text_for_maxqda(P_DBUG_QUESTION_TEXT_RAW, is_for_code_name=True) \
                               if P_DBUG_QUESTION_TEXT_RAW is not None else None
    
    # 标准化调试目标ID
    if target_id_for_debug:
        target_id_for_debug = normalize_respondent_id(target_id_for_debug)
    
    # 验证输入数据
    if not all([loaded_llm_data_map, loaded_original_interviews, loaded_csv_headers]):
        logger.error("核心数据不完整，无法继续")
        return ""
    
    structured_text_parts = []
    
    try:
        # 处理每个受访者的数据
        for i, respondent_dict_data in enumerate(loaded_original_interviews):
            current_respondent_id = respondent_dict_data.get(respondent_id_csv_column, "").strip()
            
            # 标准化当前受访者ID
            normalized_id = normalize_respondent_id(current_respondent_id)
            if not normalized_id:
                continue
            
            # 检查是否匹配调试目标
            respondent_matches_target = (target_id_for_debug is None or 
                                      normalized_id == target_id_for_debug)
            
            # 写入受访者标题
            structured_text_parts.append(f"#TEXT {normalized_id}\n\n")
            
            # 处理每个问题
            for question_header_from_csv in loaded_csv_headers:
                # 跳过ID列
                if question_header_from_csv == respondent_id_csv_column:
                    continue
                
                # 获取原始回答并清理
                original_answer_raw = respondent_dict_data.get(question_header_from_csv, "")
                current_parent_code_q_cleaned = clean_text_for_maxqda(
                    question_header_from_csv, 
                    is_for_code_name=True
                )
                
                # 设置调试标志
                global PRINT_CURRENT_ITEM_DETAILS
                PRINT_CURRENT_ITEM_DETAILS = (
                    respondent_matches_target and
                    (target_q_cleaned_for_debug is None or 
                     current_parent_code_q_cleaned == target_q_cleaned_for_debug)
                )
                
                # 跳过排除列表中的问题
                if question_header_from_csv in questions_to_skip_coding:
                    continue
                
                # 清理和验证回答文本
                original_answer_processed = clean_text_for_maxqda(original_answer_raw)
                if not original_answer_processed:
                    continue
                
                # 查找问题的LLM分析数据
                if current_parent_code_q_cleaned in loaded_llm_data_map:
                    llm_data = loaded_llm_data_map[current_parent_code_q_cleaned]
                    
                    # 获取问题的编码数据
                    all_initial_codes = llm_data.get('all_initial_code_entries_for_question', [])
                    themes_for_question = llm_data.get('themes_for_this_question', [])
                    
                    # 处理编码并生成分段
                    located_segments = get_segments_and_codes_for_answer(
                        original_answer_processed,
                        normalized_id,
                        all_initial_codes,
                        themes_for_question,
                        current_parent_code_q_cleaned
                    )
                    
                    # 只有当有编码时才输出
                    if located_segments:
                        # 解决重叠并构建最终输出
                        non_overlapping = resolve_overlaps_and_aggregate_codes(
                            located_segments,
                            original_answer_processed
                        )
                        tagged_line = build_tagged_line_from_segments(
                            original_answer_processed,
                            non_overlapping
                        )
                        structured_text_parts.append(f"{tagged_line}\n\n")
            
            # 受访者之间添加空行
            structured_text_parts.append("\n")
            
        logger.info("成功生成MaxQDA格式文本")
        return "".join(structured_text_parts)
        
    except Exception as e:
        logger.error(f"生成MaxQDA输出时出错: {e}")
        return ""

def get_original_id_and_save_maxqda(structured_txt: str, output_maxqda_filepath: str) -> bool:
    """
    将生成的MaxQDA结构化文本保存到文件。
    
    参数:
        structured_txt: MaxQDA格式的结构化文本
        output_maxqda_filepath: 输出文件路径
        
    返回:
        bool: 保存成功返回True，否则返回False
    """
    # TODO: 使用ID转换工具获取原始csv序号
    
    if not structured_txt:
        logger.error("结构化文本为空，无法保存")
        return False
        
    try:
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_maxqda_filepath), exist_ok=True)
        
        # 写入文件
        with open(output_maxqda_filepath, 'w', encoding='utf-8') as f:
            f.write(structured_txt)
            
        logger.info(f"成功保存MaxQDA文件: {output_maxqda_filepath}")
        return True
        
    except Exception as e:
        logger.error(f"保存MaxQDA文件时出错: {e}")
        logger.debug("错误堆栈:", exc_info=True)
        return False

# ======================================================================
# 主程序
# ======================================================================
def main() -> None:
    """
    主执行函数，编排MaxQDA转换流程。
    
    功能:
    1. 设置日志和配置
    2. 加载所需数据文件
    3. 执行转换流程
    4. 处理执行过程中的错误
    """
    logger.info("="*80)
    logger.info("开始任务: 生成最终MaxQDA导入文件")
    logger.info("脚本: 03inductive_create_maxqda_themecode.py | 版本: 3.0")
    logger.info(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*80)

    try:
        # 步骤1: 从parameters获取标准化文件路径
        logger.info("步骤1: 从 parameters.py 获取文件路径...")
        
        merged_json_path = get_path('inductive_merged_json')
        original_csv_path = get_path('UI')
        output_maxqda_path = get_path('inductive_maxqda_themecode')
        

        logger.info("文件路径配置:")
        logger.info(f"  - 合并JSON: '{merged_json_path}'")
        logger.info(f"  - 原始CSV: '{original_csv_path}'")
        logger.info(f"  - 输出MaxQDA: '{output_maxqda_path}'")

        # 步骤2: 加载所有源数据
        logger.info("\n步骤2: 加载源数据...")
        llm_data, original_data, csv_headers = load_data(
            merged_json_path, 
            original_csv_path
        )

        if not (llm_data and original_data and csv_headers):
            logger.critical("数据加载失败，任务终止")
            return

        logger.info("所有源数据加载成功！")
        
        # 获取原始ID列（第一列）为ID列
        original_file = get_path('UI')
        df = pd.read_csv(original_file)
        id_column = df.columns[0]
        questions_to_skip = [id_column]  # 使用ID列作为要跳过编码的列
        logger.info(f"使用第一列 '{questions_to_skip}' 作为ID列")

        # 步骤3: 执行核心转换流程
        logger.info("\n步骤3: 执行核心转换流程...")
        
        structured_text = run_maxqda_conversion(
            llm_data,
            original_data,
            csv_headers,
            id_column,  # 使用第一列作为ID列
            questions_to_skip_coding=questions_to_skip
        )
        
        # 保存结果
        if not get_original_id_and_save_maxqda(structured_text, output_maxqda_path):
            logger.error("MAXQDA文本保存失败")
            return
            
        logger.info("MAXQDA主题编码生成完成")
        
    except Exception as e:
        logger.error(f"处理过程中发生错误: {str(e)}")
        raise

if __name__ == "__main__":
    main()