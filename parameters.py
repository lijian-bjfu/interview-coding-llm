# parameters.py 

import os
import csv
import glob # For file pattern matching
import re   # For sanitize_folder_name
from collections import defaultdict
import traceback # For detailed error reporting in parse_interview_outline
from typing import Dict, List, Tuple, Optional, Any, Set, Callable
import shutil # <--- @para-move: 新增导入
import sys    # <--- @para-move: 新增导入，用于命令行参数处理
from dataclasses import dataclass
from datetime import datetime

# --- 工具类定义 ---
@dataclass
class OperationLog:
    timestamp: datetime
    operation: str
    status: str
    details: str

class WorkflowLogger:
    def __init__(self, log_file: Optional[str] = None):
        self.log_file = log_file
        self.logs: List[OperationLog] = []
        
    def log(self, operation: str, status: str, details: str):
        log_entry = OperationLog(
            timestamp=datetime.now(),
            operation=operation,
            status=status,
            details=details
        )
        self.logs.append(log_entry)
        print(f"{log_entry.timestamp.isoformat()} - {status}: {operation} - {details}")
        if self.log_file:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(f"{log_entry.timestamp.isoformat()} - {status}: {operation} - {details}\n")

# 全局日志器实例
logger = WorkflowLogger()

# --- 模块级变量 ---
_PROJECT_FILE_DIR: Optional[Dict[str, Any]] = None

# --- 项目核心配置 ---
# APP_NAME is now a mock for testing; will be a parameter for get_project_paths
APP_NAME = 'myworld' # Mock app name for testing parse_interview_outline on import

# --- 调试打印配置 ---
P_DBUG_RESPONDENT_ID = "9"
P_DBUG_QUESTION_TEXT_RAW = "最吸引你的玩法是什么/为什么喜欢这种玩法?"

# --- 全局数据结构 ---
OUTLINE: Dict[str, List[int]] = {}  # Will store {"中文Category名称": [问题号列表]}
QUESTION_MAP: Dict[int, str] = {}   # 问题编号到问题文本的映射
UNIQUE_CATEGORIES: List[str] = []   # 所有分类名称列表

# --- 基础路径组件定义  ---
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR_BASE_NAME = "data_dir" # Top-level data folder name

# 各阶段子目录的固定名称 (SDIR constants )
SDIR_00_RAW = "00_rawdata_dir"
SDIR_01_PREPROC = "01_preprocessed_for_llm_dir"
SDIR_02_OUTLINE = "02_interview_outline_dir"
SDIR_03_INDUCTIVE = "03_inductive_coding_dir"
SDIR_04_DEDUCTIVE = "04_deductive_coding_dir"

# 分组内部功能性子文件夹名称 (SDIR_GROUP constants)
SDIR_GROUP_QDATA = "question_data_dir"
SDIR_GROUP_CBOOK = "codebook_data_dir"
SDIR_GROUP_META = "meta_data_dir"

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
    required_keys = ['APP_PATH', 'UI', 'UI_ol', 'UI_utxt', 'UI_qtxt']
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

# --- 执行解析任务 ---
OUTLINE, UNIQUE_CATEGORIES = parse_interview_outline()  # 更新为同时获取两个返回值

# --- @para-load: 封装 file_dir 生成功能 ---
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
        'grouped_meta_data_files'
    ]
    for key in grouped_keys:
        file_dir[key] = []

    # --- 新增：为 get_path_list 测试准备的列表 ---
    all_qdata_category_dirs: List[str] = []

    # 确保按照大纲文件中的顺序处理分类
    expected_categories = ['用户身份', '用户特征', '游戏体验', '创造性体验', '创造性设计']
    for original_category_name in categories_list:
        if original_category_name not in expected_categories:
            print(f"警告: 发现未预期的分类名称: {original_category_name}")
            continue
            
        safe_category_folder_name = sanitize_folder_name(original_category_name) # 使用中文名需要安全处理
        group_main_abs_dir = os.path.join(outline_parent_abs_dir, safe_category_folder_name)
        
        qdata_abs_dir = os.path.join(group_main_abs_dir, SDIR_GROUP_QDATA, '') # 目录路径
        cbook_abs_dir = os.path.join(group_main_abs_dir, SDIR_GROUP_CBOOK, '') # 目录路径
        meta_abs_dir = os.path.join(group_main_abs_dir, SDIR_GROUP_META, '')   # 目录路径

        # 填充 _category_base_paths (使用原始 category 名称作为键)
        file_dir['_category_base_paths'][original_category_name] = {
            SDIR_GROUP_QDATA: qdata_abs_dir,
            SDIR_GROUP_CBOOK: cbook_abs_dir,
            SDIR_GROUP_META:  meta_abs_dir
        }

        all_qdata_category_dirs.append(qdata_abs_dir) # <--- 新增：收集 qdata 目录路径

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

    file_dir['grouped_qdata_category_dirs'] = all_qdata_category_dirs # <--- 新增：将收集的列表存入 file_dir
    
    # validate_file_dir 可以在 _ensure_file_dir_initialized 中调用，或由调用者负责
    return file_dir

def _ensure_file_dir_initialized() -> None:
    """(内部辅助函数) 确保 _PROJECT_FILE_DIR 已被初始化。"""
    global _PROJECT_FILE_DIR
    if _PROJECT_FILE_DIR is None:
        # 此处打印信息表明正在进行初始化
        logger.log("初始化", "信息", f"首次调用路径获取函数，正在为应用 '{APP_NAME}' 初始化项目路径配置...")
        base_dir = os.path.join(PROJECT_ROOT, DATA_DIR_BASE_NAME)
        try:
            file_dir, outline = get_project_paths(base_dir, APP_NAME, UNIQUE_CATEGORIES)
            if not validate_file_dir(file_dir):
                logger.log("初始化", "警告", "初始化生成的 file_dir 未通过基本验证（部分关键路径缺失）。")
            _PROJECT_FILE_DIR = file_dir  # 只保存 file_dir 部分
            logger.log("初始化", "信息", f"应用 '{APP_NAME}' 的路径配置已成功初始化。")
        except Exception as e:
            _PROJECT_FILE_DIR = {} # 关键：初始化失败也将其设为非None（例如空字典），避免无限重试
            logger.log("初始化", "严重错误", f"初始化项目路径配置失败: {e}")
            logger.log("初始化", "严重错误", f"详细错误信息:\n{traceback.format_exc()}")
            raise RuntimeError(f"项目路径配置初始化失败: {e}") from e


def get_path(key: str) -> str:
    """
    从项目配置中获取单个文件或目录的**字符串路径**。

    此函数用于获取在 `_build_project_file_dir_internal` 中定义的、值为单个字符串的路径。
    例如：获取原始数据文件的路径，或某个主要输出目录的路径。

    Args:
        key (str): 要获取的路径的键名。
                   所有可用键及其含义定义在 `_build_project_file_dir_internal` 函数的文档字符串中。

    Returns:
        str: 对应的文件或目录的完整路径字符串。

    Raises:
        RuntimeError: 如果项目路径配置未能成功初始化。
        KeyError: 如果键在路径配置中不存在。
        TypeError: 如果键对应的值不是一个字符串路径 (例如，它是一个列表)。
    """
    global _PROJECT_FILE_DIR
    _ensure_file_dir_initialized()
    if _PROJECT_FILE_DIR is None or not isinstance(_PROJECT_FILE_DIR, dict): # 增加对 _PROJECT_FILE_DIR 类型的检查
        raise RuntimeError("项目路径配置 _PROJECT_FILE_DIR 未能成功初始化或类型不正确。")
        
    path_value = _PROJECT_FILE_DIR.get(key)
    if path_value is None:
        raise KeyError(f"路径键 '{key}' 在项目路径配置中未找到。可用键示例: 'APP_PATH', 'UI', 'inductive_global_dir'等。")
    if not isinstance(path_value, str):
        raise TypeError(f"路径键 '{key}' 期望获取字符串路径，但得到的是类型 {type(path_value)}。请使用 get_path_list 获取列表型路径，或检查键名是否正确。")
    return path_value

def get_path_list(key: str) -> List[Any]:
    """
    从项目配置中获取**路径列表** (例如，按分类分组的文件路径列表)。

    此函数用于获取在 `_build_project_file_dir_internal` 中定义的、值为列表的路径集合。
    列表元素可以是字符串路径，也可能是嵌套的路径列表（例如 'grouped_inductive_q_jsons'）。

    Args:
        key (str): 要获取的路径列表的键名。
                   所有可用键及其含义定义在 `_build_project_file_dir_internal` 函数的文档字符串中。

    Returns:
        List[Any]: 对应的路径列表。

    Raises:
        RuntimeError: 如果项目路径配置未能成功初始化。
        KeyError: 如果键在路径配置中不存在。
        TypeError: 如果键对应的值不是一个列表。
    """
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
    """
    动态构建特定原始分类名称下、特定功能子目录内某个文件或该功能子目录本身的路径。

    Args:
        category_name (str): 原始的分类名称 (例如，中文名，如 '用户体验')。
                             此名称应与访谈大纲CSV中定义的分类名称一致。
        sub_dir_type_constant (str): 指定功能子目录的常量，必须是以下之一:
                                     SDIR_GROUP_QDATA (来自parameters模块)
                                     SDIR_GROUP_CBOOK (来自parameters模块)
                                     SDIR_GROUP_META  (来自parameters模块)
        file_name (Optional[str], optional): 如果提供，则构建到该文件的完整路径。
                                             如果为 None，则返回功能子目录本身的路径 (已确保以os.sep结尾)。
                                             Defaults to None.
    Returns:
        str: 构建完成的路径字符串。

    Raises:
        RuntimeError: 如果项目路径配置未能成功初始化。
        KeyError: 如果 category_name 或 sub_dir_type_constant 无效或未在配置中找到。
        ValueError: 如果 sub_dir_type_constant 不是预定义的有效常量之一。
    """
    global _PROJECT_FILE_DIR
    _ensure_file_dir_initialized()
    if _PROJECT_FILE_DIR is None or not isinstance(_PROJECT_FILE_DIR, dict):
         raise RuntimeError("项目路径配置 _PROJECT_FILE_DIR 未能成功初始化或类型不正确。")

    valid_sub_dir_keys = {SDIR_GROUP_QDATA, SDIR_GROUP_CBOOK, SDIR_GROUP_META}
    if sub_dir_type_constant not in valid_sub_dir_keys:
        raise ValueError(f"无效的 sub_dir_type_constant: '{sub_dir_type_constant}'. "
                         f"必须是 SDIR_GROUP_QDATA ('{SDIR_GROUP_QDATA}'), "
                         f"SDIR_GROUP_CBOOK ('{SDIR_GROUP_CBOOK}'), "
                         f"或 SDIR_GROUP_META ('{SDIR_GROUP_META}') 之一。")

    category_base_paths_dict = _PROJECT_FILE_DIR.get('_category_base_paths')
    if not isinstance(category_base_paths_dict, dict): # Should be a dict
        raise KeyError("内部错误: '_category_base_paths' 结构未在路径配置中正确初始化。")
        
    specific_category_paths = category_base_paths_dict.get(category_name)
    if not isinstance(specific_category_paths, dict): # Value for a category should be a dict
        raise KeyError(f"在路径配置中未找到分类 '{category_name}' 的基础路径信息。 "
                       f"请确保该分类存在于您的访谈大纲中并且已被正确解析。 "
                       f"当前已解析的分类: {list(category_base_paths_dict.keys())}")
    
    target_dir_path = specific_category_paths.get(sub_dir_type_constant)
    if not isinstance(target_dir_path, str) or not target_dir_path.endswith(os.sep): # Should be a string dir path
        raise KeyError(f"在分类 '{category_name}' 中未找到或未正确配置子目录类型 '{sub_dir_type_constant}' 的路径。")

    if file_name:
        # target_dir_path 已经以 os.sep 结尾
        return os.path.join(target_dir_path.rstrip(os.sep), file_name)
    else:
        return target_dir_path # 返回目录路径，已包含结尾的 os.sep

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
        logger.log("创建目录", "失败", "目录路径为空")
        raise ValueError("目录路径不能为空")
        
    try:
        os.makedirs(directory_path, exist_ok=True)
        logger.log("创建目录", "成功", f"已创建/确认目录: {directory_path}")
    except OSError as e:
        logger.log("创建目录", "失败", f"创建目录 '{directory_path}' 失败: {e}")
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
        logger.log("创建目录", "警告", "传入的 target_file_dir 为空或None，未尝试创建任何目录。")
        return False

    logger.log("创建目录", "信息", "正在检查并按需创建项目目录...")
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
                            logger.log("创建目录", "警告", f"跳过项目外的路径 {abs_dir_path}")
                            continue
                        all_dirs_to_ensure.add(dir_path)
                    except ValueError:
                        logger.log("创建目录", "警告", f"跳过无效路径 {abs_dir_path}")
                        continue
                    
        # 按层级排序目录
        sorted_dirs = sorted(
            all_dirs_to_ensure,
            key=lambda x: len(os.path.normpath(x).split(os.sep))
        )
        
        # 创建目录
        for dir_path in sorted_dirs:
            if not os.path.exists(dir_path):
                ensure_dir_exists(dir_path)  # 如果失败会自动抛出异常
                created_dirs.append(dir_path)
                
        logger.log("创建目录", "成功", "所有必需的目录已创建完成")
        return True
        
    except Exception as e:
        logger.log("创建目录", "错误", f"创建目录时发生错误: {e}")
        # 回滚：删除本次新建的目录
        for dir_path in reversed(created_dirs):
            try:
                if os.path.exists(dir_path) and not os.listdir(dir_path):
                    os.rmdir(dir_path)
                    logger.log("创建目录", "信息", f"已回滚删除空目录: {dir_path}")
            except Exception as cleanup_error:
                logger.log("创建目录", "警告", f"回滚删除目录 {dir_path} 失败: {cleanup_error}")
        return False

# --- @para-move: 新增移动初始文件函数 --- (新代码插入位置开始)
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
    logger.log("移动文件", "开始", "准备移动初始数据文件...")
    moved_files: List[MoveOperation] = []  # 记录已移动的文件

    # 定义源文件和目标文件路径
    source_data_filename = f"{app_name}.csv"
    source_outline_filename = f"{app_name}-outline.csv"
    
    source_data_filepath = os.path.join(source_project_root, source_data_filename)
    source_outline_filepath = os.path.join(source_project_root, source_outline_filename)
    
    dest_data_filepath = target_file_dir.get('UI')
    dest_outline_filepath = target_file_dir.get('UI_ol')

    if not dest_data_filepath or not dest_outline_filepath:
        logger.log("移动文件", "失败", "目标路径 'UI' 或 'UI_ol' 在 file_dir 中未定义")
        return False

    try:
        # 移动数据文件 ([app_name].csv)
        if os.path.exists(source_data_filepath):
            if os.path.abspath(source_data_filepath) == os.path.abspath(dest_data_filepath):
                logger.log("移动文件", "跳过", f"数据文件 '{source_data_filename}' 已在目标位置")
            else:
                try:
                    ensure_dir_exists(os.path.dirname(dest_data_filepath))
                    shutil.move(source_data_filepath, dest_data_filepath)
                    moved_files.append(MoveOperation(source_data_filepath, dest_data_filepath, "数据文件"))
                    logger.log("移动文件", "成功", f"已移动 '{source_data_filename}'")
                except (OSError, IOError) as e:
                    raise OSError(f"移动数据文件失败: {e}")
        else:
            if not os.path.exists(dest_data_filepath):
                logger.log("移动文件", "警告", f"源数据文件 '{source_data_filepath}' 未找到，且目标位置也无此文件")
                return False
            else:
                logger.log("移动文件", "信息", f"数据文件已在目标位置 '{dest_data_filepath}'")

        # 移动大纲文件 ([app_name]-outline.csv)
        if os.path.exists(source_outline_filepath):
            if os.path.abspath(source_outline_filepath) == os.path.abspath(dest_outline_filepath):
                logger.log("移动文件", "跳过", f"大纲文件 '{source_outline_filename}' 已在目标位置")
            else:
                try:
                    ensure_dir_exists(os.path.dirname(dest_outline_filepath))
                    shutil.move(source_outline_filepath, dest_outline_filepath)
                    moved_files.append(MoveOperation(source_outline_filepath, dest_outline_filepath, "大纲文件"))
                    logger.log("移动文件", "成功", f"已移动 '{source_outline_filename}'")
                except (OSError, IOError) as e:
                    raise OSError(f"移动大纲文件失败: {e}")
        else:
            if not os.path.exists(dest_outline_filepath):
                logger.log("移动文件", "警告", f"源大纲文件 '{source_outline_filepath}' 未找到，且目标位置也无此文件")
                if UNIQUE_CATEGORIES:
                    return False
            else:
                logger.log("移动文件", "信息", f"大纲文件已在目标位置 '{dest_outline_filepath}'")

        logger.log("移动文件", "完成", "所有文件移动操作已完成")
        return True

    except Exception as e:
        logger.log("移动文件", "错误", f"移动过程中发生错误: {str(e)}")
        # 回滚已移动的文件
        for move_op in reversed(moved_files):
            try:
                shutil.move(move_op.target, move_op.source)
                logger.log("移动文件回滚", "成功", f"已将{move_op.description}移回原位置")
            except Exception as rollback_error:
                logger.log("移动文件回滚", "失败", f"回滚{move_op.description}失败: {str(rollback_error)}")
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
    logger.log("移动文件", "信息", f"准备将初始数据文件移回项目根目录 (还原操作)...")
    files_moved_back_successfully = True

    source_data_filepath = source_file_dir.get('UI')
    source_outline_filepath = source_file_dir.get('UI_ol')

    dest_data_filename = f"{app_name}.csv"
    dest_outline_filename = f"{app_name}-outline.csv"

    dest_data_filepath = os.path.join(target_project_root, dest_data_filename)
    dest_outline_filepath = os.path.join(target_project_root, dest_outline_filename)

    if not source_data_filepath or not source_outline_filepath:
        logger.log("移动文件", "错误", "源路径 'UI' 或 'UI_ol' 在 file_dir 中未定义。无法执行移回操作。")
        return False

    # 移回数据文件 ([app_name].csv)
    if os.path.exists(source_data_filepath):
        if os.path.abspath(source_data_filepath) == os.path.abspath(dest_data_filepath):
            logger.log("移动文件", "信息", f"数据文件 '{dest_data_filename}' 已在根目录。")
        else:
            try:
                shutil.move(source_data_filepath, dest_data_filepath)
                logger.log("移动文件", "信息", f"已将数据文件从 '{source_data_filepath}' 移回 '{dest_data_filepath}'")
            except Exception as e:
                logger.log("移动文件", "错误", f"移回数据文件 '{dest_data_filename}' 失败: {e}")
                files_moved_back_successfully = False
    else:
        if not os.path.exists(dest_data_filepath):
            logger.log("移动文件", "警告", f"数据文件在源位置 '{source_data_filepath}' 和目标根目录均未找到。")
            # files_moved_back_successfully = False # Consider if this state is an error
        else:
             logger.log("移动文件", "信息", f"数据文件 '{dest_data_filename}' 已在根目录，无需从项目结构中移回。")


    # 移回大纲文件 ([app_name]-outline.csv)
    if os.path.exists(source_outline_filepath):
        if os.path.abspath(source_outline_filepath) == os.path.abspath(dest_outline_filepath):
            logger.log("移动文件", "信息", f"大纲文件 '{dest_outline_filename}' 已在根目录。")
        else:
            try:
                shutil.move(source_outline_filepath, dest_outline_filepath)
                logger.log("移动文件", "信息", f"已将大纲文件从 '{source_outline_filepath}' 移回 '{dest_outline_filepath}'")
            except Exception as e:
                logger.log("移动文件", "错误", f"移回大纲文件 '{dest_outline_filename}' 失败: {e}")
                files_moved_back_successfully = False
    else:
        if not os.path.exists(dest_outline_filepath):
            logger.log("移动文件", "警告", f"大纲文件在源位置 '{source_outline_filepath}' 和目标根目录均未找到。")
            # files_moved_back_successfully = False # Consider if this state is an error
        else:
            logger.log("移动文件", "信息", f"大纲文件 '{dest_outline_filename}' 已在根目录，无需从项目结构中移回。")
            
    if files_moved_back_successfully:
        logger.log("移动文件", "信息", "初始文件移回操作检查完成。")
    return files_moved_back_successfully

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
        logger.log("进度", "信息", f"{description} ({current_step}/{total_steps})")
    
    try:
        logger.log("工作流", "开始", f"开始执行工作流程: 模式 '{mode.upper()}' for app '{app_to_manage}'")
        
        # 步骤1: 验证配置
        update_progress("验证配置")
        valid, error_msg = validate_workflow_config(mode, base_dir_for_apps, app_to_manage, initial_files_source_root)
        if not valid:
            logger.log("工作流", "失败", f"配置验证失败: {error_msg}")
            return False
            
        # 步骤2: 创建目录结构
        update_progress("创建目录结构")
        file_dir, outline = get_project_paths(base_dir_for_apps, app_to_manage, UNIQUE_CATEGORIES)
        if not create_project_dir(file_dir):
            logger.log("工作流", "失败", "创建目录结构失败")
            return False
            
        # 步骤3: 移动文件
        update_progress("移动文件")
        success = False
        if mode == "setup":
            success = move_original_data(initial_files_source_root, app_to_manage, file_dir)
        elif mode == "reset":
            success = move_original_data_back(initial_files_source_root, app_to_manage, file_dir)
            
        if success:
            logger.log("工作流", "完成", f"工作流程 '{mode.upper()}' 执行成功")
        else:
            logger.log("工作流", "失败", f"工作流程 '{mode.upper()}' 执行失败")
        return success
        
    except Exception as e:
        logger.log("工作流", "错误", f"工作流执行过程中发生错误: {str(e)}")
        return False

def run_tests():
    """运行所有测试用例"""
    test_cases = [
        ("setup", "正常设置测试"),
        ("reset", "正常重置测试"),
        ("invalid", "无效模式测试"),
    ]
    
    results = []
    for mode, description in test_cases:
        logger.log("测试", "开始", f"执行测试: {description}")
        result = manage_project_workflow(
            mode=mode,
            base_dir_for_apps=os.path.join(PROJECT_ROOT, DATA_DIR_BASE_NAME),
            app_to_manage=APP_NAME,
            initial_files_source_root=PROJECT_ROOT
        )
        results.append((description, result))
        logger.log("测试", "结果", f"{description}: {'成功' if result else '失败'}")
    
    # 打印测试总结
    logger.log("测试", "总结", "\n=== 测试结果总结 ===")
    for desc, res in results:
        logger.log("测试", "总结", f"{desc}: {'成功' if res else '失败'}")

# --- 测试函数：test_data_access_interfaces --- (新代码插入位置开始)

def test_data_access_interfaces():
    """
    专门测试数据访问接口: get_path, get_path_list, get_category_specific_path。
    假定 _PROJECT_FILE_DIR 已经通过 _ensure_file_dir_initialized() 被填充。
    """
    logger.log("测试", "开始", "\n--- 开始测试数据访问接口 ---")
    
    # 确保 _PROJECT_FILE_DIR 已初始化 (如果尚未初始化，则会在此处初始化)
    # 这一步很重要，因为它会使用全局的 APP_NAME, PROJECT_ROOT, DATA_DIR_BASE_NAME, UNIQUE_CATEGORIES
    try:
        _ensure_file_dir_initialized()
        if not _PROJECT_FILE_DIR: # 检查初始化是否真的成功
            logger.log("测试接口", "错误", "_PROJECT_FILE_DIR 未能初始化，无法进行接口测试。")
            return
    except Exception as e:
        logger.log("测试接口", "错误", f"_ensure_file_dir_initialized 执行失败: {e}")
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
    # 设置日志文件
    logger = WorkflowLogger(os.path.join(PROJECT_ROOT, "workflow.log"))
    
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        run_tests()
    else:
        # 正常的工作流执行
        default_mode = "setup"
        current_mode = default_mode

        if len(sys.argv) > 1:
            arg_mode = sys.argv[1].lower()
            if arg_mode in ["setup", "reset"]:
                current_mode = arg_mode
            else:
                logger.log("参数", "警告", f"未知模式参数 '{sys.argv[1]}'，使用默认模式 '{default_mode}'")

        # 执行工作流
        param_base_data_dir = os.path.join(PROJECT_ROOT, DATA_DIR_BASE_NAME)
        param_app_name = APP_NAME
        param_initial_files_root = PROJECT_ROOT

        workflow_success = manage_project_workflow(
            mode=current_mode,
            base_dir_for_apps=param_base_data_dir,
            app_to_manage=param_app_name,
            initial_files_source_root=param_initial_files_root
        )

        if workflow_success:
            if current_mode == "setup":
                logger.log("完成", "成功", "项目环境已准备就绪")
                logger.log("提示", "信息", 
                    f"确保文件已被移入正确位置: {os.path.join(param_base_data_dir, f'{param_app_name}_dir', SDIR_00_RAW)}")
            elif current_mode == "reset":
                logger.log("完成", "成功", f"文件已移回项目根目录: {PROJECT_ROOT}")
        else:
            logger.log("完成", "失败", "工作流程执行失败，请检查日志文件了解详细信息")

        print(f"OUTLINE: {OUTLINE}")
        print(f"QUESTION_MAP: {QUESTION_MAP}")

        # test_data_access_interfaces()