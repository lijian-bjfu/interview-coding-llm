# parameters.py
"""
项目参数管理模块

本模块分为以下几个主要区域：

1. 公开接口 (Public Interfaces)
   - 全局变量
   - 公开函数
   - 数据类型定义

2. 内部实现 (Internal Implementation)
   - 内部辅助函数
   - 内部数据结构
   - 工具类实现

=== 公开接口说明 ===

全局变量:
- PROJECT_ROOT: str
    项目根目录的绝对路径
- APP_NAME: str
    当前应用名称，默认为 'myworld'
- OUTLINE: Dict[str, List[int]]
    访谈大纲结构，格式：{"分类名": [问题编号列表]}
- QUESTION_MAP: Dict[int, str]
    问题编号到问题文本的映射
- UNIQUE_CATEGORIES: List[str]
    所有分类名称列表

公开函数:
1. 路径管理:
- get_path(key: str) -> str
    获取单个文件或目录的路径
    参数:
        key: 路径键名（如 'UI', 'UI_id', 'APP_PATH' 等）
    返回:
        对应的文件或目录的完整路径

- get_path_list(key: str) -> List[str]
    获取路径列表（如按分类分组的文件路径列表）
    参数:
        key: 路径列表键名（如 'grouped_user_g_txts'）
    返回:
        路径字符串列表

- get_category_specific_path(category_name: str, sub_dir_type: str, file_name: Optional[str] = None) -> str
    获取特定分类下的路径
    参数:
        category_name: 分类名称
        sub_dir_type: 子目录类型（SDIR_GROUP_QDATA/UDATA/CBOOK/META）
        file_name: 可选的文件名
    返回:
        完整的文件或目录路径

2. 项目管理:
- setup_project(mode: str = "setup") -> bool
    项目初始化设置
    参数:
        mode: "setup" 或 "reset"
    返回:
        设置是否成功

3. ID系统:
- setup_id_system() -> bool
    建立内部ID系统
    返回:
        是否成功建立ID系统

- get_id_manager() -> IDManager
    获取ID管理器实例
    返回:
        IDManager实例，用于ID转换

常量定义:
- SDIR_GROUP_QDATA: str = "question_data_dir"
- SDIR_GROUP_UDATA: str = "user_data_dir"
- SDIR_GROUP_CBOOK: str = "codebook_data_dir"
- SDIR_GROUP_META: str = "meta_data_dir"
    分组内部功能性子文件夹名称常量

=== 内部实现说明 ===

以下划线开头的函数和变量为内部实现，不建议外部直接调用：
- _ensure_file_dir_initialized()
- _build_project_file_dir_internal()
- _PROJECT_FILE_DIR
- _ID_MANAGER

"""

import os
import csv
import glob # For file pattern matching
import re   # For sanitize_folder_name
from collections import defaultdict
import traceback # For detailed error reporting in parse_interview_outline
from typing import Dict, List, Tuple, Optional, Any, Set, Callable
import shutil # For file operations
import sys    # For command line arguments
from datetime import datetime
from dataclasses import dataclass
import pandas as pd
import logging  # 替换外部logger导入

# 配置内置logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('workflow.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ===================== 公开接口 (Public Interfaces) =====================

# --- 全局变量 ---
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR_BASE_NAME = "data_dir"
APP_NAME = '金铲铲之战'

# --- 调试配置 ---
P_DBUG_RESPONDENT_ID = 10  # 调试目标受访者ID
P_DBUG_QUESTION_TEXT_RAW = 7  # 调试目标问题文本

# --- 全局数据结构 ---
OUTLINE: Dict[str, List[int]] = {}  # {"中文Category名称": [问题号列表]}
QUESTION_MAP: Dict[int, str] = {}   # 问题编号到问题文本的映射
UNIQUE_CATEGORIES: List[str] = []   # 所有分类名称列表

# --- 常量定义 ---
# 各阶段子目录的固定名称
SDIR_00_RAW = "00_rawdata_dir"
SDIR_01_PREPROC = "01_preprocessed_for_llm_dir"
SDIR_02_OUTLINE = "02_interview_outline_dir"
SDIR_03_INDUCTIVE = "03_inductive_coding_dir"
SDIR_04_DEDUCTIVE = "04_deductive_coding_dir"

# 分组内部功能性子文件夹名称
SDIR_GROUP_QDATA = "question_data_dir"
SDIR_GROUP_UDATA = "user_data_dir"
SDIR_GROUP_CBOOK = "codebook_data_dir"
SDIR_GROUP_META = "meta_data_dir"

# --- 公开类定义 ---
class IDManager:
    """ID管理器：处理内部ID和原始ID的转换"""
    def __init__(self, id_mapping: Dict[str, int]):
        self._original_to_internal = id_mapping
        self._internal_to_original = {v: k for k, v in id_mapping.items()}
        
    def to_internal_id(self, original_id) -> int:
        """原始ID转内部ID"""
        return self._original_to_internal[str(original_id)]
        
    def to_original_id(self, internal_id) -> str:
        """内部ID转原始ID"""
        return self._internal_to_original[internal_id]

# --- 公开函数 ---
def get_path(key: str) -> str:
    """获取单个文件或目录的路径"""
    global _PROJECT_FILE_DIR
    _ensure_file_dir_initialized()
    if _PROJECT_FILE_DIR is None or not isinstance(_PROJECT_FILE_DIR, dict):
        raise RuntimeError("项目路径配置 _PROJECT_FILE_DIR 未能成功初始化或类型不正确。")
        
    path_value = _PROJECT_FILE_DIR.get(key)
    if path_value is None:
        raise KeyError(f"路径键 '{key}' 在项目路径配置中未找到。可用键示例: 'APP_PATH', 'UI', 'inductive_global_dir'等。")
    if not isinstance(path_value, str):
        raise TypeError(f"路径键 '{key}' 期望获取字符串路径，但得到的是类型 {type(path_value)}。请使用 get_path_list 获取列表型路径，或检查键名是否正确。")
    return path_value

def get_path_list(key: str) -> List[Any]:
    """获取路径列表（如按分类分组的文件路径列表）"""
    global _PROJECT_FILE_DIR
    _ensure_file_dir_initialized()
    if _PROJECT_FILE_DIR is None or not isinstance(_PROJECT_FILE_DIR, dict):
        raise RuntimeError("项目路径配置 _PROJECT_FILE_DIR 未能成功初始化或类型不正确。")

    path_value = _PROJECT_FILE_DIR.get(key)
    if path_value is None:
        raise KeyError(f"路径列表键 '{key}' 在项目路径配置中未找到。可用键示例: 'grouped_user_g_txts', 'grouped_inductive_q_jsons'等。")
    if not isinstance(path_value, list):
        raise TypeError(f"路径列表键 '{key}' 期望获取列表，但得到的是类型 {type(path_value)}。请使用 get_path 获取单一字符串路径，或检查键名是否正确。")
    return path_value

def get_category_specific_path(category_name: str, sub_dir_type_constant: str, file_name: Optional[str] = None) -> str:
    """获取特定分类下的路径"""
    global _PROJECT_FILE_DIR
    _ensure_file_dir_initialized()
    if _PROJECT_FILE_DIR is None or not isinstance(_PROJECT_FILE_DIR, dict):
         raise RuntimeError("项目路径配置 _PROJECT_FILE_DIR 未能成功初始化或类型不正确。")

    valid_sub_dir_keys = {SDIR_GROUP_QDATA, SDIR_GROUP_UDATA, SDIR_GROUP_CBOOK, SDIR_GROUP_META}
    if sub_dir_type_constant not in valid_sub_dir_keys:
        raise ValueError(f"无效的 sub_dir_type_constant: '{sub_dir_type_constant}'. "
                         f"必须是 SDIR_GROUP_QDATA ('{SDIR_GROUP_QDATA}'), "
                         f"SDIR_GROUP_UDATA ('{SDIR_GROUP_UDATA}'), "
                         f"SDIR_GROUP_CBOOK ('{SDIR_GROUP_CBOOK}'), "
                         f"或 SDIR_GROUP_META ('{SDIR_GROUP_META}') 之一。")

    category_base_paths_dict = _PROJECT_FILE_DIR.get('_category_base_paths')
    if not isinstance(category_base_paths_dict, dict):
        raise KeyError("内部错误: '_category_base_paths' 结构未在路径配置中正确初始化。")
        
    specific_category_paths = category_base_paths_dict.get(category_name)
    if not isinstance(specific_category_paths, dict):
        raise KeyError(f"在路径配置中未找到分类 '{category_name}' 的基础路径信息。 "
                       f"请确保该分类存在于您的访谈大纲中并且已被正确解析。 "
                       f"当前已解析的分类: {list(category_base_paths_dict.keys())}")
    
    target_dir_path = specific_category_paths.get(sub_dir_type_constant)
    if not isinstance(target_dir_path, str) or not target_dir_path.endswith(os.sep):
        raise KeyError(f"在分类 '{category_name}' 中未找到或未正确配置子目录类型 '{sub_dir_type_constant}' 的路径。")

    if file_name:
        return os.path.join(target_dir_path.rstrip(os.sep), file_name)
    else:
        return target_dir_path

def get_id_manager() -> IDManager:
    """获取ID管理器实例"""
    if _ID_MANAGER is None:
        return initialize_id_system()
    return _ID_MANAGER


# ===================== 内部实现 (Internal Implementation) =====================

# --- 内部变量 ---
_PROJECT_FILE_DIR: Optional[Dict[str, Any]] = None
_ID_MANAGER: Optional[IDManager] = None

# --- 内部函数 ---
def sanitize_folder_name(name: str) -> str:
    """确保文件夹名称在所有操作系统上都有效，移除或替换非法字符。"""
    invalid_chars_pattern = r'[<>:"/\\|?*\x00-\x1F]' 
    safe_name = re.sub(invalid_chars_pattern, '_', name)
    safe_name = re.sub(r'_+', '_', safe_name)
    safe_name = safe_name.strip('_.')
    if not safe_name: # Handle cases where the name becomes empty after sanitization
        safe_name = "sanitized_folder_name" 
    return safe_name

def validate_file_dir(file_dir: Dict[str, str]) -> bool:
    """验证 file_dir 中的关键路径是否都已正确设置"""
    required_keys = ['APP_PATH', 'UI', 'UI_ol', 'UI_id','UI_utxt', 'UI_qtxt']
    # 检查key是否存在，并且对应的值是字符串（路径通常是字符串）
    return all(key in file_dir and isinstance(file_dir[key], str) for key in required_keys)

# --- @para-categ: 解析访谈大纲 ---
def parse_interview_outline() -> Tuple[Dict[str, List[int]], Set[str]]:
    """
    解析访谈大纲CSV文件，提取分类信息和问题编号映射。
    直接从项目根目录读取大纲文件，避免与 get_path 的循环依赖。
    
    Returns:
        Tuple[Dict[str, List[int]], Set[str]]: 
            - 字典：分类名称到问题编号列表的映射
            - 集合：所有唯一的分类名称
    """
    global QUESTION_MAP, OUTLINE  # 声明所有需要修改的全局变量
    
    temp_outline_dict = defaultdict(list)
    temp_categories = set()
    QUESTION_MAP.clear()  # 清空旧的映射
    
    try:
        # 直接从项目根目录读取大纲文件
        outline_filename = f"{APP_NAME}-outline.csv"
        outline_filepath = os.path.join(PROJECT_ROOT, outline_filename)
        
        if not os.path.exists(outline_filepath):
            # 尝试在 00_rawdata_dir 中查找文件
            raw_data_dir = os.path.join(PROJECT_ROOT, DATA_DIR_BASE_NAME, f"{APP_NAME}_dir", SDIR_00_RAW)
            alternative_path = os.path.join(raw_data_dir, outline_filename)
            
            if os.path.exists(alternative_path):
                outline_filepath = alternative_path
            else:
                print(f"错误: 未找到大纲文件: {outline_filepath} 或 {alternative_path}")
                return {}, set()
        
        with open(outline_filepath, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            
            for row in reader:
                if len(row) < 3:  # 确保至少有问题号、分类名和问题内容三列
                    continue
                    
                q_num_str = row[0].strip()
                category_name = row[1].strip()
                question_content = row[2].strip()
                
                if not q_num_str or not category_name:
                    continue
                    
                try:
                    q_num = int(q_num_str)
                    temp_categories.add(category_name)
                    temp_outline_dict[category_name].append(q_num)
                    
                    # 填充问题映射字典
                    if question_content:
                        QUESTION_MAP[q_num] = question_content
                        
                except ValueError:
                    continue
                    
        return dict(temp_outline_dict), temp_categories
        
    except Exception as e:
        print(f"解析访谈大纲时出错: {e}")
        print(f"详细错误信息: {traceback.format_exc()}")
        return {}, set()

# --- 面向外部的结构解析任务 ---
OUTLINE, UNIQUE_CATEGORIES = parse_interview_outline()  # 更新为同时获取两个返回值

def _build_project_file_dir_internal(
    base_data_dir_for_app_folders: str,
    current_app_name: str,
    categories_list: List[str]
) -> Dict[str, Any]:
    """
    (内部辅助函数) 根据给定的基础路径、应用名称和分类列表，
    构建项目的文件/目录路径配置字典 (file_dir)。

    此函数是所有路径配置的"真理之源"。它的文档字符串详细描述了返回字典的结构。
    所有明确表示目录的路径字符串，都会以特定于操作系统的路径分隔符 (os.sep) 结尾。

    Args:
        base_data_dir_for_app_folders (str): 存放所有应用特定数据文件夹的基础目录路径。
                                            例如: os.path.join(PROJECT_ROOT, DATA_DIR_BASE_NAME)
        current_app_name (str): 当前正在处理的应用/项目名称 (例如: 'myworld')。
        categories_list (List[str]): 包含所有唯一分类名称 (通常是中文) 的字符串列表。
                                   这些名称将用作 '02_interview_outline_dir' 下的子文件夹名。

    Returns:
        Dict[str, Any]: file_dir 字典，包含路径字符串、路径列表或文件名模式。
                        键名和结构示例:
                        - 'APP_PATH': str - 当前应用的项目根目录 (例如: '.../data_dir/myworld_dir/')
                        - 'UI': str - 原始访谈数据CSV文件路径。
                        - 'UI_ol': str - 原始访谈大纲CSV文件路径 (在00_rawdata_dir中)。
                        - 'UI_path': str - '00_rawdata_dir/' 目录本身的路径。
                        - 'UI_utxt': str, 'UI_qtxt': str - 预处理后的文本文件路径。
                        - 'UI_utxt_path': str - '01_preprocessed_for_llm_dir/' 目录本身的路径。
                        - 'inductive_global_dir': str - 归纳编码的全局输出目录。
                        - 'deductive_global_dir': str - 演绎编码的全局输出目录。
                        - '02_outline_parent_dir': str - '02_interview_outline_dir' 的路径。
                        - '_category_base_paths': Dict[str, Dict[str, str]] - 映射原始category名到其功能子目录路径:
                            {
                                "原始Category1名": {
                                    SDIR_GROUP_QDATA: ".../Category1_safe/question_data_dir/",
                                    SDIR_GROUP_UDATA: ".../Category1_safe/user_data_dir/",
                                    SDIR_GROUP_CBOOK: ".../Category1_safe/codebook_data_dir/",
                                    SDIR_GROUP_META:  ".../Category1_safe/meta_data_dir/"
                                }, ...
                            }
                        - 'grouped_user_g_txts': List[str] - 各分类下 'question_data_dir/user_g.txt' 的路径列表。
                        - 'grouped_inductive_q_jsons': List[List[str]] - 各分类下 'question_data_dir/' 中匹配模式的JSON文件路径的嵌套列表。
                        - (更多 'grouped_...' 键，值为 List[str] 或 List[List[str]])
                        - 'pattern_...': str - 文件名匹配模式。
    Raises:
        ValueError: 如果 base_data_dir_for_app_folders 或 current_app_name 为空。
    """
    if not base_data_dir_for_app_folders or not current_app_name:
        raise ValueError("构建路径配置：基础数据目录或应用名称不能为空。")

    file_dir: Dict[str, Any] = {}
    app_folder_name = f"{current_app_name}_dir" # 例如 myworld_dir
    current_app_path = os.path.join(base_data_dir_for_app_folders, app_folder_name)

    file_dir['APP_PATH'] = os.path.join(current_app_path, '')

    # --- 固定路径填充 ---
    raw_data_dir = os.path.join(current_app_path, SDIR_00_RAW)
    file_dir['UI_path'] = os.path.join(raw_data_dir, '') # 目录路径
    file_dir['UI'] = os.path.join(raw_data_dir, f"{current_app_name}.csv")
    file_dir['UI_ol'] = os.path.join(raw_data_dir, f"{current_app_name}-outline.csv")
    file_dir['UI_id'] = os.path.join(raw_data_dir, f"{current_app_name}-id.csv")

    preproc_dir = os.path.join(current_app_path, SDIR_01_PREPROC)
    file_dir['UI_utxt_path'] = os.path.join(preproc_dir, '') # 目录路径
    file_dir['UI_utxt'] = os.path.join(preproc_dir, f"{current_app_name}_user.txt")
    file_dir['UI_qtxt'] = os.path.join(preproc_dir, f"{current_app_name}_question.txt")

    inductive_dir = os.path.join(current_app_path, SDIR_03_INDUCTIVE)
    file_dir['inductive_global_dir'] = os.path.join(inductive_dir, '') # 目录路径
    file_dir['inductive_merged_json'] = os.path.join(inductive_dir, f"{current_app_name}_inductive_codes.json")
    file_dir['inductive_maxqda_opencode'] = os.path.join(inductive_dir, f"{current_app_name}_inductive_maxqda_opencode.txt")
    file_dir['inductive_maxqda_themecode'] = os.path.join(inductive_dir, f"{current_app_name}_inductive_maxqda_themecode.txt")
    file_dir['inductive_global_metadata'] = os.path.join(inductive_dir, f"{current_app_name}_inductive_metadata.json")

    deductive_dir = os.path.join(current_app_path, SDIR_04_DEDUCTIVE)
    file_dir['deductive_global_dir'] = os.path.join(deductive_dir, '') # 目录路径
    file_dir['deductive_llm_raw_output'] = os.path.join(deductive_dir, f"{current_app_name}_deductive_llm_output.json")
    file_dir['deductive_maxqda_text'] = os.path.join(deductive_dir, f"{current_app_name}_deductive_maxqda.txt")
    file_dir['deductive_global_metadata'] = os.path.join(deductive_dir, f"{current_app_name}_deductive_metadata.json")

    # --- 文件名模式 ---
    file_dir['pattern_inductive_q_json'] = 'inductive_questio*[0-9]*.json'
    file_dir['pattern_inductive_q_cbook_json'] = 'inductive_questio*[0-9]*_codebook.json'
    file_dir['pattern_deductive_llm_in_group'] = 'deductive_code_by_LLM.json'

    # --- 动态生成与分组相关的路径 ---
    outline_parent_abs_dir = os.path.join(current_app_path, SDIR_02_OUTLINE)
    file_dir['02_outline_parent_dir'] = os.path.join(outline_parent_abs_dir, '') # 目录路径

    # 为 get_category_specific_path 准备的辅助字典
    file_dir['_category_base_paths'] = {} 
    
    # 初始化用于存储分组路径列表的键
    grouped_keys = [
        'grouped_user_g_txts', 'grouped_inductive_q_jsons',
        'grouped_deductive_llm_jsons_in_group', 'grouped_inductive_q_cbook_jsons',
        'grouped_raw_codebook_txts', 'grouped_final_codebooks_txts',
        'grouped_meta_data_files', 'grouped_user_data_dirs'  # 添加新的键
    ]
    for key in grouped_keys:
        file_dir[key] = []

    # --- 新增：为 get_path_list 测试准备的列表 ---
    all_qdata_category_dirs: List[str] = []
    all_udata_category_dirs: List[str] = []  # 新增：收集所有 user_data_dir 路径

    # 设置所有分类的目录路径
    for original_category_name in categories_list:
            
        safe_category_folder_name = sanitize_folder_name(original_category_name) # 使用中文名需要安全处理
        group_main_abs_dir = os.path.join(outline_parent_abs_dir, safe_category_folder_name)
        
        qdata_abs_dir = os.path.join(group_main_abs_dir, SDIR_GROUP_QDATA, '') # 目录路径
        udata_abs_dir = os.path.join(group_main_abs_dir, SDIR_GROUP_UDATA, '') # 目录路径
        cbook_abs_dir = os.path.join(group_main_abs_dir, SDIR_GROUP_CBOOK, '') # 目录路径
        meta_abs_dir = os.path.join(group_main_abs_dir, SDIR_GROUP_META, '')   # 目录路径

        # 填充 _category_base_paths (使用原始 category 名称作为键)
        file_dir['_category_base_paths'][original_category_name] = {
            SDIR_GROUP_QDATA: qdata_abs_dir,
            SDIR_GROUP_UDATA: udata_abs_dir,
            SDIR_GROUP_CBOOK: cbook_abs_dir,
            SDIR_GROUP_META:  meta_abs_dir
        }

        all_qdata_category_dirs.append(qdata_abs_dir)
        all_udata_category_dirs.append(udata_abs_dir)  # 新增：收集 user_data_dir 路径

        # 填充 grouped_ lists (确保路径的文件部分不含尾部斜杠)
        file_dir['grouped_user_g_txts'].append(os.path.join(qdata_abs_dir.rstrip(os.sep), "user_g.txt"))
        
        # glob.glob 会在调用时查找文件，如果目录此时不存在或无匹配文件，则列表为空
        # 确保传递给 glob 的目录路径存在，或者 glob 能处理不存在的路径（通常返回空列表）
        qdata_for_glob = qdata_abs_dir.rstrip(os.sep)
        if os.path.exists(qdata_for_glob):
            files_ind_q = sorted(glob.glob(os.path.join(qdata_for_glob, file_dir['pattern_inductive_q_json'])))
            if not files_ind_q:
                print(f"警告: 在目录 '{qdata_for_glob}' 中未找到匹配的JSON文件")
        else:
            print(f"警告: 目录不存在: '{qdata_for_glob}'")
            files_ind_q = []
            
        file_dir['grouped_inductive_q_jsons'].append(files_ind_q)
        
        file_dir['grouped_deductive_llm_jsons_in_group'].append(
            os.path.join(qdata_abs_dir.rstrip(os.sep), file_dir['pattern_deductive_llm_in_group'])
        )
        
        cbook_for_glob = cbook_abs_dir.rstrip(os.sep)
        if os.path.exists(cbook_for_glob):
            files_ind_cbook = sorted(glob.glob(os.path.join(cbook_for_glob, file_dir['pattern_inductive_q_cbook_json'])))
        else:
            files_ind_cbook = []
        file_dir['grouped_inductive_q_cbook_jsons'].append(files_ind_cbook)
        file_dir['grouped_raw_codebook_txts'].append(os.path.join(cbook_abs_dir.rstrip(os.sep), "raw_codebooks.txt"))
        file_dir['grouped_final_codebooks_txts'].append(os.path.join(cbook_abs_dir.rstrip(os.sep), "codebook.txt"))
        file_dir['grouped_meta_data_files'].append(os.path.join(meta_abs_dir.rstrip(os.sep), f"{safe_category_folder_name}_metadata.json"))

    file_dir['grouped_qdata_category_dirs'] = all_qdata_category_dirs
    file_dir['grouped_user_data_dirs'] = all_udata_category_dirs  # 新增：存储收集的 user_data_dir 路径
    
    # validate_file_dir 可以在 _ensure_file_dir_initialized 中调用，或由调用者负责
    return file_dir

def _ensure_file_dir_initialized() -> None:
    """(内部辅助函数) 确保 _PROJECT_FILE_DIR 已被初始化。"""
    global _PROJECT_FILE_DIR
    if _PROJECT_FILE_DIR is None:
        # 此处打印信息表明正在进行初始化
        logger.info("首次调用路径获取函数，正在为应用 '{}' 初始化项目路径配置...".format(APP_NAME))
        base_dir = os.path.join(PROJECT_ROOT, DATA_DIR_BASE_NAME)
        try:
            file_dir, outline = get_project_paths(base_dir, APP_NAME, UNIQUE_CATEGORIES)
            if not validate_file_dir(file_dir):
                logger.warning("初始化生成的 file_dir 未通过基本验证（部分关键路径缺失）。")
            _PROJECT_FILE_DIR = file_dir  # 只保存 file_dir 部分
            logger.info("应用 '{}' 的路径配置已成功初始化。".format(APP_NAME))
        except Exception as e:
            _PROJECT_FILE_DIR = {} # 关键：初始化失败也将其设为非None（例如空字典），避免无限重试
            logger.error("初始化项目路径配置失败: {}".format(e))
            logger.error("详细错误信息:\n{}".format(traceback.format_exc()))
            raise RuntimeError("项目路径配置初始化失败: {}".format(e)) from e

def get_project_paths(base_dir_for_apps: str, app_name: str, categories_list: List[str]) -> Tuple[Dict[str, Any], Dict[str, List[int]]]:
    """
    生成项目路径配置和大纲信息。

    Args:
        base_dir_for_apps (str): 存放所有应用特定数据文件夹的基础目录路径。
        app_name (str): 当前正在处理的应用/项目名称。
        categories_list (List[str]): 包含所有唯一分类名称的列表。

    Returns:
        Tuple[Dict[str, Any], Dict[str, List[int]]]: 
            - 项目路径配置字典
            - 大纲字典 (category -> question numbers)
    """
    file_dir = _build_project_file_dir_internal(base_dir_for_apps, app_name, categories_list)
    return file_dir, OUTLINE

# --- 封装创建目录功能 ---

def ensure_dir_exists(directory_path: str) -> None:
    """
    确保单个目录存在，如果不存在则创建。如果创建失败，抛出异常。
    
    Args:
        directory_path (str): 需要检查或创建的目录路径。
        
    Raises:
        ValueError: 当目录路径为空时
        OSError: 当目录创建失败时
    """
    if not directory_path:
        logger.warning("目录路径为空")
        raise ValueError("目录路径不能为空")
        
    try:
        os.makedirs(directory_path, exist_ok=True)
        logger.info("已创建/确认目录: {}".format(directory_path))
    except OSError as e:
        logger.error("创建目录失败: {}".format(e))
        raise  # 直接重新抛出原始异常，保留完整的堆栈信息

def create_project_dir(target_file_dir: Dict[str, Any]) -> bool:
    """
    根据 target_file_dir 字典中定义的路径，创建所有必需的项目目录。
    
    Args:
        target_file_dir: 包含路径的字典
    Returns:
        bool: 表示所有目录是否成功创建
    """
    if not target_file_dir:
        logger.warning("传入的 target_file_dir 为空或None，未尝试创建任何目录。")
        return False

    logger.info("正在检查并按需创建项目目录...")
    all_dirs_to_ensure: Set[str] = set()
    created_dirs: List[str] = []  # 记录新创建的目录，用于出错时回滚
    
    try:
        # 收集并验证所有需要创建的目录
        app_path_val = target_file_dir.get('APP_PATH', '')
        if not app_path_val or not isinstance(app_path_val, str):
            raise ValueError("APP_PATH 未定义或格式不正确")
            
        # 确保所有路径都在项目目录下
        project_root_abs = os.path.abspath(PROJECT_ROOT)
        app_base = os.path.abspath(os.path.dirname(app_path_val.rstrip(os.sep)))
        try:
            common_path = os.path.commonpath([project_root_abs, app_base])
            if common_path != project_root_abs:
                raise ValueError(f"APP_PATH {app_base} 不在项目目录 {project_root_abs} 下")
        except ValueError as e:
            raise ValueError(f"路径验证失败: {str(e)}")
            
        # 收集所有目录路径
        for key, path_value in target_file_dir.items():
            if key.endswith('_pattern'):
                continue
                
            paths = []
            if isinstance(path_value, str):
                paths.append(path_value)
            elif isinstance(path_value, (list, tuple)):
                paths.extend(p for p in path_value if isinstance(p, str))
                
            for path in paths:
                if not path:
                    continue
                    
                dir_path = (
                    path.rstrip(os.sep) if path.endswith(os.sep)
                    else os.path.dirname(path)
                )
                
                if dir_path and dir_path != '.':
                    abs_dir_path = os.path.abspath(dir_path)
                    try:
                        common_path = os.path.commonpath([project_root_abs, abs_dir_path])
                        if common_path != project_root_abs:
                            logger.warning(f"跳过项目外的路径 {abs_dir_path}")
                            continue
                        all_dirs_to_ensure.add(dir_path)
                    except ValueError:
                        logger.warning(f"跳过无效路径 {abs_dir_path}")
                        continue
                    
        # 按层级排序目录
        sorted_dirs = sorted(
            all_dirs_to_ensure,
            key=lambda x: len(os.path.normpath(x).split(os.sep))
        )
        
        # 创建目录
        for dir_path in sorted_dirs:
            if not os.path.exists(dir_path):
                try:
                    os.makedirs(dir_path, exist_ok=True)
                    created_dirs.append(dir_path)
                    logger.info(f"已创建目录: {dir_path}")
                except Exception as e:
                    raise OSError(f"创建目录 {dir_path} 失败: {str(e)}")
                
        logger.info("所有必需的目录已创建完成")
        return True
        
    except Exception as e:
        logger.error(f"创建目录时发生错误: {str(e)}")
        # 回滚：删除本次新建的目录
        for dir_path in reversed(created_dirs):
            try:
                if os.path.exists(dir_path):
                    # 检查目录是否为空或只包含空目录
                    is_empty = True
                    for root, dirs, files in os.walk(dir_path):
                        if files:
                            is_empty = False
                            break
                    if is_empty:
                        shutil.rmtree(dir_path)
                        logger.info(f"已回滚删除目录: {dir_path}")
            except Exception as cleanup_error:
                logger.warning(f"回滚删除目录 {dir_path} 失败: {str(cleanup_error)}")
        return False

# --- ID系统管理 ---
class IDManager:
    """ID管理器：处理内部ID和原始ID的转换"""
    def __init__(self, id_mapping: Dict[str, int]):
        self._original_to_internal = id_mapping
        self._internal_to_original = {v: k for k, v in id_mapping.items()}
        
    def to_internal_id(self, original_id) -> int:
        """原始ID转内部ID"""
        return self._original_to_internal[str(original_id)]
        
    def to_original_id(self, internal_id) -> str:
        """内部ID转原始ID"""
        return self._internal_to_original[internal_id]

# 全局单例
_ID_MANAGER: Optional[IDManager] = None

# --- 初始化ID系统 ---
def initialize_id_system() -> IDManager:
    """
    仅初始化ID系统，不影响项目结构
    """
    global _ID_MANAGER
    
    try:
        # 如果已经初始化过，直接返回
        if _ID_MANAGER is not None:
            return _ID_MANAGER
            
        # 获取原始数据文件路径
        original_file = get_path('UI')
        
        # 读取原始数据
        df = pd.read_csv(original_file)
        
        # 建立ID映射关系
        id_mapping = dict(zip(
            df.iloc[:, 0].astype(str),  # 原始ID（第一列）
            range(1, len(df) + 1)       # 新的内部ID
        ))
        
        # 初始化IDManager
        _ID_MANAGER = IDManager(id_mapping)
        return _ID_MANAGER
        
    except Exception as e:
        raise RuntimeError(f"ID系统初始化失败: {str(e)}")

# --- 移动初始文件函数 --- 
@dataclass
class MoveOperation:
    source: str
    target: str
    description: str

def move_original_data(source_project_root: str, app_name: str, target_file_dir: Dict[str, Any]) -> bool:
    """
    将项目根目录下的原始数据文件移动到目标位置，支持事务性操作。

    Args:
        source_project_root (str): 项目的根目录路径。
        app_name (str): 当前应用的名称。
        target_file_dir (Dict[str, Any]): 已填充的 file_dir 字典，包含目标路径。

    Returns:
        bool: 如果所有文件都成功移动或已在目标位置，则返回 True。
    """
    logger.info("准备移动初始数据文件...")
    moved_files: List[MoveOperation] = []  # 记录已移动的文件

    # 定义源文件和目标文件路径
    source_data_filename = f"{app_name}.csv"
    source_outline_filename = f"{app_name}-outline.csv"
    
    source_data_filepath = os.path.join(source_project_root, source_data_filename)
    source_outline_filepath = os.path.join(source_project_root, source_outline_filename)
    
    dest_data_filepath = target_file_dir.get('UI')
    dest_outline_filepath = target_file_dir.get('UI_ol')

    if not dest_data_filepath or not dest_outline_filepath:
        logger.warning("目标路径 'UI' 或 'UI_ol' 在 file_dir 中未定义")
        return False

    try:
        # 移动数据文件 ([app_name].csv)
        if os.path.exists(source_data_filepath):
            if os.path.abspath(source_data_filepath) == os.path.abspath(dest_data_filepath):
                logger.info(f"数据文件 '{source_data_filename}' 已在目标位置")
            else:
                try:
                    ensure_dir_exists(os.path.dirname(dest_data_filepath))
                    shutil.move(source_data_filepath, dest_data_filepath)
                    moved_files.append(MoveOperation(source_data_filepath, dest_data_filepath, "数据文件"))
                    logger.info(f"已移动 '{source_data_filename}'")
                except (OSError, IOError) as e:
                    raise OSError(f"移动数据文件失败: {e}")
        else:
            if not os.path.exists(dest_data_filepath):
                logger.warning(f"源数据文件 '{source_data_filepath}' 未找到，且目标位置也无此文件")
                return False
            else:
                logger.info(f"数据文件已在目标位置 '{dest_data_filepath}'")

        # 移动大纲文件 ([app_name]-outline.csv)
        if os.path.exists(source_outline_filepath):
            if os.path.abspath(source_outline_filepath) == os.path.abspath(dest_outline_filepath):
                logger.info(f"大纲文件 '{source_outline_filename}' 已在目标位置")
            else:
                try:
                    ensure_dir_exists(os.path.dirname(dest_outline_filepath))
                    shutil.move(source_outline_filepath, dest_outline_filepath)
                    moved_files.append(MoveOperation(source_outline_filepath, dest_outline_filepath, "大纲文件"))
                    logger.info(f"已移动 '{source_outline_filename}'")
                except (OSError, IOError) as e:
                    raise OSError(f"移动大纲文件失败: {e}")
        else:
            if not os.path.exists(dest_outline_filepath):
                logger.warning(f"源大纲文件 '{source_outline_filepath}' 未找到，且目标位置也无此文件")
                if UNIQUE_CATEGORIES:
                    return False
            else:
                logger.info(f"大纲文件已在目标位置 '{dest_outline_filepath}'")

        logger.info("所有文件移动操作已完成")
        return True

    except Exception as e:
        logger.error(f"移动过程中发生错误: {str(e)}")
        # 回滚已移动的文件
        for move_op in reversed(moved_files):
            try:
                shutil.move(move_op.target, move_op.source)
                logger.info(f"已将{move_op.description}移回原位置")
            except Exception as rollback_error:
                logger.warning(f"回滚{move_op.description}失败: {str(rollback_error)}")
        return False

def move_original_data_back(target_project_root: str, app_name: str, source_file_dir: Dict[str, Any]) -> bool:
    """
    (调试功能) 将已移动到 '00_rawdata_dir/' 中的原始数据文件 ([app_name].csv 和 [app_name]-outline.csv)
    移回项目根目录。

    Args:
        target_project_root (str): 项目的根目录路径 (文件将移回此处)。
        app_name (str): 当前应用的名称。
        source_file_dir (Dict[str, Any]): 已填充的 file_dir 字典，包含源文件路径。

    Returns:
        bool: 如果两个文件都成功移回或已在根目录，则返回 True；否则返回 False。
    """
    logger.info(f"准备将初始数据文件移回项目根目录 (还原操作)...")
    files_moved_back_successfully = True

    source_data_filepath = source_file_dir.get('UI')
    source_outline_filepath = source_file_dir.get('UI_ol')

    dest_data_filename = f"{app_name}.csv"
    dest_outline_filename = f"{app_name}-outline.csv"

    dest_data_filepath = os.path.join(target_project_root, dest_data_filename)
    dest_outline_filepath = os.path.join(target_project_root, dest_outline_filename)

    if not source_data_filepath or not source_outline_filepath:
        logger.error("源路径 'UI' 或 'UI_ol' 在 file_dir 中未定义。无法执行移回操作。")
        return False

    # 移回数据文件 ([app_name].csv)
    if os.path.exists(source_data_filepath):
        if os.path.abspath(source_data_filepath) == os.path.abspath(dest_data_filepath):
            logger.info(f"数据文件 '{dest_data_filename}' 已在根目录。")
        else:
            try:
                shutil.move(source_data_filepath, dest_data_filepath)
                logger.info(f"已将数据文件从 '{source_data_filepath}' 移回 '{dest_data_filepath}'")
            except Exception as e:
                logger.error(f"移回数据文件 '{dest_data_filename}' 失败: {e}")
                files_moved_back_successfully = False
    else:
        if not os.path.exists(dest_data_filepath):
            logger.warning(f"数据文件在源位置 '{source_data_filepath}' 和目标根目录均未找到。")
            # files_moved_back_successfully = False # Consider if this state is an error
        else:
             logger.info(f"数据文件 '{dest_data_filename}' 已在根目录，无需从项目结构中移回。")


    # 移回大纲文件 ([app_name]-outline.csv)
    if os.path.exists(source_outline_filepath):
        if os.path.abspath(source_outline_filepath) == os.path.abspath(dest_outline_filepath):
            logger.info(f"大纲文件 '{dest_outline_filename}' 已在根目录。")
        else:
            try:
                shutil.move(source_outline_filepath, dest_outline_filepath)
                logger.info(f"已将大纲文件从 '{source_outline_filepath}' 移回 '{dest_outline_filepath}'")
            except Exception as e:
                logger.error(f"移回大纲文件 '{dest_outline_filename}' 失败: {e}")
                files_moved_back_successfully = False
    else:
        if not os.path.exists(dest_outline_filepath):
            logger.warning(f"大纲文件在源位置 '{source_outline_filepath}' 和目标根目录均未找到。")
            # files_moved_back_successfully = False # Consider if this state is an error
        else:
            logger.info(f"大纲文件 '{dest_outline_filename}' 已在根目录，无需从项目结构中移回。")
            
    if files_moved_back_successfully:
        logger.info("初始文件移回操作检查完成。")
    return files_moved_back_successfully

# --- 处理原始数据 ---

def process_raw_data(raw_df: pd.DataFrame) -> pd.DataFrame:
    """
    处理DataFrame中的多行文本
    
    Args:
        raw_df (pd.DataFrame): 原始数据DataFrame
        
    Returns:
        pd.DataFrame: 处理后的DataFrame
    """
    # 创建一个新的DataFrame来存储处理后的数据
    processed_df = raw_df.copy()
    
    # 对每一列进行处理
    replacements = {
            '\n': ' ', '\r': ' ', '\\n': ' ', '\\r': ' ',
            '\t': ' ', '\\t': ' '
        }
        
    # 对所有文本列应用清理
    for col in processed_df.columns:
        if processed_df[col].dtype == 'object':  # 只处理文本列
            processed_df[col] = processed_df[col].astype(str).replace(replacements, regex=True)
            # 移除多余的空格
            processed_df[col] = processed_df[col].str.strip()
    
    return processed_df

# --- 设置项目 ---
def validate_workflow_config(
    mode: str,
    base_dir_for_apps: str,
    app_to_manage: str,
    initial_files_source_root: str
) -> Tuple[bool, str]:
    """
    验证工作流配置参数
    
    Args:
        mode (str): 操作模式
        base_dir_for_apps (str): 应用数据目录
        app_to_manage (str): 要管理的应用名称
        initial_files_source_root (str): 初始文件根目录
    
    Returns:
        Tuple[bool, str]: (验证是否通过, 错误信息)
    """
    if mode not in ["setup", "reset"]:
        return False, f"无效的模式: {mode}"
        
    if not all([base_dir_for_apps, app_to_manage, initial_files_source_root]):
        return False, "所有参数都不能为空"
        
    if not os.path.isabs(base_dir_for_apps):
        return False, f"base_dir_for_apps 必须是绝对路径: {base_dir_for_apps}"
        
    if not os.path.isabs(initial_files_source_root):
        return False, f"initial_files_source_root 必须是绝对路径: {initial_files_source_root}"
        
    # 验证目录权限
    try:
        if not os.path.exists(base_dir_for_apps):
            os.makedirs(base_dir_for_apps)
        test_file = os.path.join(base_dir_for_apps, ".test_write")
        with open(test_file, 'w') as f:
            f.write("test")
        os.remove(test_file)
    except (OSError, IOError) as e:
        return False, f"目录权限验证失败: {str(e)}"
        
    return True, ""

def manage_project_workflow(
    mode: str,
    base_dir_for_apps: str,
    app_to_manage: str,
    initial_files_source_root: str,
    progress_callback: Optional[Callable[[str, int], None]] = None
) -> bool:
    """
    管理项目环境的主要工作流程函数，支持 "setup" 和 "reset" 模式。

    Args:
        mode (str): 操作模式， "setup" 或 "reset"。
        base_dir_for_apps (str): 将在其中创建 [app_name]_dir 的基础目录。
        app_to_manage (str): 要管理的应用名称。
        initial_files_source_root (str): 初始文件所在的根目录。
        progress_callback (Optional[Callable[[str, int], None]]): 进度回调函数。

    Returns:
        bool: 表示操作是否整体成功。
    """
    total_steps = 3  # 总步骤数
    current_step = 0
    
    def update_progress(description: str):
        nonlocal current_step
        current_step += 1
        if progress_callback:
            progress_callback(description, int(current_step * 100 / total_steps))
        logger.info(f"{description} ({current_step}/{total_steps})")
    
    try:
        logger.info(f"开始执行工作流程: 模式 '{mode.upper()}' for app '{app_to_manage}'")
        
        # 步骤1: 验证配置
        update_progress("验证配置")
        valid, error_msg = validate_workflow_config(mode, base_dir_for_apps, app_to_manage, initial_files_source_root)
        if not valid:
            logger.error(f"配置验证失败: {error_msg}")
            return False
            
        # 步骤2: 创建目录结构
        update_progress("创建目录结构")
        file_dir, outline = get_project_paths(base_dir_for_apps, app_to_manage, UNIQUE_CATEGORIES)
        if not create_project_dir(file_dir):
            logger.error("创建目录结构失败")
            return False
            
        # 步骤3: 移动文件
        update_progress("移动文件")
        success = False
        if mode == "setup":
            success = move_original_data(initial_files_source_root, app_to_manage, file_dir)
        elif mode == "reset":
            success = move_original_data_back(initial_files_source_root, app_to_manage, file_dir)
            
        if success:
            logger.info(f"工作流程 '{mode.upper()}' 执行成功")
        else:
            logger.error(f"工作流程 '{mode.upper()}' 执行失败")
        return success
        
    except Exception as e:
        logger.error(f"工作流执行过程中发生错误: {str(e)}")
        return False

def setup_id_system() -> bool:
    """建立内部ID系统"""
    logger.info("开始建立内部ID系统...")
    
    try:
        # 获取文件路径
        original_file = get_path('UI')
        id_file = get_path('UI_id')
        
        # 读取原始数据
        df = pd.read_csv(original_file)
        logger.info(f"成功读取原始数据，共 {len(df)} 条记录")

        # 处理原始数据中多行文本可能导致的行错乱问题
        df = process_raw_data(df)
        
        # 建立ID系统并获取带ID的数据
        df_with_id = df.copy()
        # 生成从1开始的ID
        df_with_id.insert(0, '_id', range(1, len(df_with_id) + 1))
        logger.info(f"成功生成内部ID，ID范围: 1-{len(df_with_id)}")
        
        # 创建映射关系并初始化IDManager
        global _ID_MANAGER
        id_mapping = dict(zip(
            df.iloc[:, 0].astype(str),  # 原始ID（第一列）
            df_with_id['_id']  # 新的内部ID
        ))
        _ID_MANAGER = IDManager(id_mapping)
        
        # 保存处理后的文件
        df_with_id.to_csv(id_file, index=False)
        logger.info(f"成功保存带ID的文件到: {id_file}")

        # 保存修改多行问题的原始文件
        df.to_csv(original_file, index=False)
        logger.info(f"修改了可能存在格式问题的原始文件: {original_file}")
        
        # 验证ID映射
        sample_id = str(df.iloc[0, 0])  # 取第一个原始ID做测试
        internal_id = _ID_MANAGER.to_internal_id(sample_id)
        restored_id = _ID_MANAGER.to_original_id(internal_id)
        logger.debug(f"ID转换测试 - 原始ID: {sample_id} -> 内部ID: {internal_id} -> 还原ID: {restored_id}")
        
        logger.info("ID系统建立完成")
        return True
        
    except Exception as e:
        logger.error(f"ID系统建立失败: {str(e)}")
        return False

 
def setup_project(mode: str = "setup") -> bool:
    """项目初始化设置"""
    global OUTLINE, UNIQUE_CATEGORIES, QUESTION_MAP
    
    try:
        # 1. 设置基础参数
        param_base_data_dir = os.path.join(PROJECT_ROOT, DATA_DIR_BASE_NAME)
        param_app_name = APP_NAME
        param_initial_files_root = PROJECT_ROOT
        
        # 2. 执行工作流
        workflow_success = manage_project_workflow(
            mode=mode,
            base_dir_for_apps=param_base_data_dir,
            app_to_manage=param_app_name,
            initial_files_source_root=param_initial_files_root
        )
        
        if not workflow_success:
            logger.error("工作流程执行失败")
            return False
            
        # 3. 根据模式输出相应信息
        if mode == "setup":
            logger.info("项目环境已准备就绪")
            logger.info(
                f"确保文件已被移入正确位置: {os.path.join(param_base_data_dir, f'{param_app_name}_dir', SDIR_00_RAW)}")
            
            # 4. 建立ID系统（只在setup模式下执行）
            if not setup_id_system():
                return False
                
        elif mode == "reset":
            logger.info(f"文件已移回项目根目录: {PROJECT_ROOT}")
            
        # 5. 打印重要变量状态
        logger.debug(f"OUTLINE: {OUTLINE}")
        logger.debug(f"QUESTION_MAP: {QUESTION_MAP}")
        
        return True
        
    except Exception as e:
        logger.error(f"项目设置过程出错: {str(e)}")
        return False

def run(mode: str):
    # 执行工作流
    param_base_data_dir = os.path.join(PROJECT_ROOT, DATA_DIR_BASE_NAME)
    param_app_name = APP_NAME
    param_initial_files_root = PROJECT_ROOT

    workflow_success = manage_project_workflow(
        mode=mode,
        base_dir_for_apps=param_base_data_dir,
        app_to_manage=param_app_name,
        initial_files_source_root=param_initial_files_root
    )

    if workflow_success:
        if mode == "setup":
            logger.info("项目环境已准备就绪")
            logger.info(
                f"确保文件已被移入正确位置: {os.path.join(param_base_data_dir, f'{param_app_name}_dir', SDIR_00_RAW)}")
        elif mode == "reset":
            logger.info(f"文件已移回项目根目录: {PROJECT_ROOT}")
    else:
        logger.error("工作流程执行失败，请检查日志文件了解详细信息")

    print(f"OUTLINE: {OUTLINE}")
    print(f"QUESTION_MAP: {QUESTION_MAP}")

# --- 测试函数 --- 

def test_data_access_interfaces():
    """
    专门测试数据访问接口: get_path, get_path_list, get_category_specific_path。
    假定 _PROJECT_FILE_DIR 已经通过 _ensure_file_dir_initialized() 被填充。
    """
    logger.info("\n--- 开始测试数据访问接口 ---")
    
    # 确保 _PROJECT_FILE_DIR 已初始化 (如果尚未初始化，则会在此处初始化)
    # 这一步很重要，因为它会使用全局的 APP_NAME, PROJECT_ROOT, DATA_DIR_BASE_NAME, UNIQUE_CATEGORIES
    try:
        _ensure_file_dir_initialized()
        if not _PROJECT_FILE_DIR: # 检查初始化是否真的成功
            logger.warning("_PROJECT_FILE_DIR 未能初始化，无法进行接口测试。")
            return
    except Exception as e:
        logger.warning(f"_ensure_file_dir_initialized 执行失败: {e}")
        print(f"错误 (测试接口): _ensure_file_dir_initialized 执行失败: {e}")
        print(traceback.format_exc())
        return

    test_passed_count = 0
    test_failed_count = 0

    # 1. 测试 get_path: 获取 APP_PATH 和 UI_path (SDIR_00_RAW 对应的目录)
    print("\n1. 测试 get_path():")
    try:
        app_path = get_path('APP_PATH')
        print(f"  get_path('APP_PATH'): OK -> '{app_path}'")
        test_passed_count += 1
    except Exception as e:
        print(f"  get_path('APP_PATH'): FAILED -> {e}")
        test_failed_count += 1

    try:
        ui_path_dir = get_path('UI_path') # UI_path 是 00_rawdata_dir 目录
        print(f"  get_path('UI_path') (SDIR_00_RAW 目录): OK -> '{ui_path_dir}'")
        test_passed_count += 1
    except Exception as e:
        print(f"  get_path('UI_path'): FAILED -> {e}")
        test_failed_count += 1

    # 2. 测试 get_path_list: 获取所有 PROJECT_GROUP_FOLDERS (UNIQUE_CATEGORIES) 中的 SDIR_GROUP_QDATA 路径
    #    我们将使用新添加的 'grouped_qdata_category_dirs' 键
    print("\n2. 测试 get_path_list():")
    grouped_qdata_key = 'grouped_qdata_category_dirs'
    try:
        qdata_dirs_list = get_path_list(grouped_qdata_key)
        print(f"  get_path_list('{grouped_qdata_key}'): OK (获取到 {len(qdata_dirs_list)} 个路径)")
        if qdata_dirs_list:
            print(f"    示例路径[0]: '{qdata_dirs_list[0]}'")
        elif UNIQUE_CATEGORIES: # 如果有分类但列表为空，可能 glob 未执行或目录未创建
             print(f"    注意: '{grouped_qdata_key}' 返回空列表，但存在 {len(UNIQUE_CATEGORIES)} 个分类。")
        test_passed_count += 1
    except Exception as e:
        print(f"  get_path_list('{grouped_qdata_key}'): FAILED -> {e}")
        test_failed_count += 1
        
    # 也可以测试一个已有的返回嵌套列表的键，例如 'grouped_inductive_q_jsons'
    # (可选，如果需要更全面的 get_path_list 测试)
    # try:
    #     inductive_jsons_list = get_path_list('grouped_inductive_q_jsons')
    #     print(f"  get_path_list('grouped_inductive_q_jsons'): OK (获取到 {len(inductive_jsons_list)} 个外层列表元素)")
    #     test_passed_count += 1
    # except Exception as e:
    #     print(f"  get_path_list('grouped_inductive_q_jsons'): FAILED -> {e}")
    #     test_failed_count += 1


    # 3. 测试 get_category_specific_path: 获取"用户体验" category 路径下的 SDIR_GROUP_QDATA 路径
    print("\n3. 测试 get_category_specific_path():")
    category_to_test = "用户体验" # 假设这是您大纲中的一个中文分类名
                                 # 为了测试的健壮性，最好从 UNIQUE_CATEGORIES 中动态选择一个
    if UNIQUE_CATEGORIES:
        if category_to_test not in UNIQUE_CATEGORIES:
            print(f"  注意: 测试用的分类 '{category_to_test}' 不在 UNIQUE_CATEGORIES 中。将使用第一个可用分类 '{UNIQUE_CATEGORIES[0]}' 进行测试。")
            category_to_test_actual = UNIQUE_CATEGORIES[0]
        else:
            category_to_test_actual = category_to_test
            
        try:
            specific_qdata_path = get_category_specific_path(category_to_test_actual, SDIR_GROUP_QDATA)
            print(f"  get_category_specific_path('{category_to_test_actual}', SDIR_GROUP_QDATA): OK -> '{specific_qdata_path}'")
            test_passed_count += 1
            
            # 测试获取带文件名的路径
            specific_file_path = get_category_specific_path(category_to_test_actual, SDIR_GROUP_QDATA, "sample_file.txt")
            expected_file_path = os.path.join(specific_qdata_path.rstrip(os.sep), "sample_file.txt")
            if specific_file_path == expected_file_path:
                print(f"  get_category_specific_path with filename: OK -> '{specific_file_path}'")
                test_passed_count += 1
            else:
                print(f"  get_category_specific_path with filename: FAILED -> Expected '{expected_file_path}', Got '{specific_file_path}'")
                test_failed_count += 1

        except Exception as e:
            print(f"  get_category_specific_path('{category_to_test_actual}', SDIR_GROUP_QDATA): FAILED -> {e}")
            test_failed_count += 1
    else:
        print(f"  跳过 get_category_specific_path 测试，因为 UNIQUE_CATEGORIES 为空。")
        # test_failed_count += 1 # 或者不计为失败，只是跳过

    print("\n--- 数据访问接口测试总结 ---")
    print(f"  通过测试: {test_passed_count}")
    print(f"  失败测试: {test_failed_count}")
    if test_failed_count == 0:
        print("  所有指定接口测试通过！")
    else:
        print("  部分接口测试失败，请检查错误信息。")
    print("-----------------------------")

if __name__ == "__main__":
    # 使用标准日志系统
    logger.info("开始执行项目设置...")
    setup_project()  # 使用默认的setup模式