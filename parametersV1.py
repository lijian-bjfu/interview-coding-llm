# parameters.py
# ==============================================================================
# 项目参数和路径配置文件 (parameters.py) - 使用指南
# ==============================================================================
#
# == 概述 ==
# 本文件是整个LLM辅助访谈数据分析项目的中央配置枢纽。它定义了：
#   1. 项目级别的核心参数，例如当前正在分析的应用/游戏名称 ('app')。
#   2. 一个标准化的、分阶段的项目文件和目录结构。
#   3. 一个名为 'file_dir' 的Python字典，它包含了所有预定义文件和目录的
#      完整路径。其他Python脚本通过导入这个 'file_dir' 来获取所需路径。
#   4. 自动目录创建功能：当本文件被任何脚本第一次导入时，它会自动检查
#      'file_dir' 中定义的所有必需目录是否存在，如果不存在则尝试创建它们。
#   5. 全局调试打印控制变量 (P_DBUG_...)，用于控制其他脚本在处理特定
#      被访者或特定问题时是否输出详细的调试日志。
#
# == 如何在其他Python脚本中使用本文件 ==
#
# 1. **导入配置**:
#    在其他Python脚本（例如 `build_codebook_raw.py`, `convert_to_maxqda_tc.py`）
#    的开头，按如下方式导入本文件中的核心配置变量：
#    ```python
#       from parameters import file_dir, app, P_DBUG_RESPONDENT_ID, P_DBUG_QUESTION_TEXT_RAW
#    ```
#
# 2. **获取文件/目录路径**:
#    所有必需的文件和目录路径都预先定义在 `file_dir` 字典中。脚本应该通过
#    `file_dir['键名']` 的方式来获取这些路径，而不是在脚本中硬编码路径字符串。
#    这样，如果将来项目结构或文件名需要调整，只需要修改 `parameters.py`
#    这一个文件即可。
#
#    **示例 - 获取原始CSV文件路径:**
#    `original_csv_path = file_dir['UI']`
#
#    **示例 - 获取全局合并的归纳编码JSON文件路径:**
#    `merged_inductive_json = file_dir['inductive_merged_json']`
#
#    **示例 - 获取第一个分组 (player_states) 的原始编码本素材TXT输出路径:**
#    `# PROJECT_GROUPS_CONFIG 在 parameters.py 中定义了分组文件夹名和描述`
#    `# file_dir['grouped_raw_codebook_txts'] 是一个列表，按 PROJECT_GROUPS_CONFIG 的顺序排列`
#    `# 假设我们知道 player_states 是第一个分组 (索引0)`
#    `raw_codebook_g1_path = file_dir['grouped_raw_codebook_txts'][0]`
#
#    **示例 - 获取特定分组 (例如 'player_states') 的 'inductive_questionN.json' 文件列表:**
#    ```python
#    # from parameters import PROJECT_GROUPS_CONFIG, file_dir # 已导入
#    group_folder_to_find = "player_states"
#    group_index = -1
#    for i, (folder_name, desc) in enumerate(PROJECT_GROUPS_CONFIG):
#        if folder_name == group_folder_to_find:
#            group_index = i
#            break
#    
#    if group_index != -1:
#        inductive_q_jsons_for_group = file_dir['grouped_inductive_q_jsons'][group_index]
#        if inductive_q_jsons_for_group:
#            print(f"找到分组 '{group_folder_to_find}' 的归纳编码JSON文件: {inductive_q_jsons_for_group}")
#            # 然后可以遍历 inductive_q_jsons_for_group 来处理每个文件
#        else:
#            print(f"分组 '{group_folder_to_find}' 内没有找到归纳编码JSON文件。")
#    else:
#        print(f"未在 PROJECT_GROUPS_CONFIG 中找到分组文件夹 '{group_folder_to_find}'。")
#    ```
#
# 3. **文件名模式的使用**:
#    `file_dir` 中包含了一些文件名模式，例如：
#    - `file_dir['pattern_inductive_q_json']` (值为: 'inductive_question[0-9]*.json')
#    - `file_dir['pattern_inductive_q_cbook_json']`
#    - `file_dir['pattern_deductive_llm_in_group']`
#    当脚本需要在特定分组目录下查找这些类型的文件时，应结合分组目录路径和这些模式。
#    例如，在 `build_codebook_raw.py` 中，当处理一个分组的 `question_data_dir` 时：
#    ```python
#    # group_qdata_dir_path = file_dir[...某个分组的question_data_dir路径...]
#    # pattern = file_dir['pattern_inductive_q_json']
#    # import glob, os
#    # json_files = glob.glob(os.path.join(group_qdata_dir_path, pattern))
#    ```
#    (实际上，`parameters.py` 自身在构建 `file_dir['grouped_inductive_q_jsons']` 等列表时，
#    内部已经使用了 `glob` 和这些模式，所以调用脚本通常可以直接使用这些预先填充好的文件路径列表。)
#
# 4. **目录自动创建**:
#    无需在其他脚本中显式创建 `file_dir` 中定义的目录。`parameters.py` 在被
#    首次导入时，其末尾的目录创建逻辑会自动执行，确保所有必需的文件夹结构都已就绪。
#    它会打印出实际创建的目录，如果目录已存在则不会重复打印。
#
# 5. **使用调试打印控制**:
#    `parameters.py` 定义了全局变量 `P_DBUG_RESPONDENT_ID` 和 `P_DBUG_QUESTION_TEXT_RAW`。
#    在其他脚本中，可以通过导入这些变量，并在主处理循环（例如 `run_maxqda_conversion`）
#    的开头，根据当前正在处理的被访者ID和问题文本（清理后）是否与这些调试目标匹配，
#    来设置一个全局的布尔标志 `PRINT_CURRENT_ITEM_DETAILS`。
#    然后，在各个辅助函数内部，所有详细的 `print` 语句都由 `if PRINT_CURRENT_ITEM_DETAILS:` 控制。
#
#    **主脚本中的设置示例 (在 run_maxqda_conversion 内，遍历问题之前):**
#    ```python
#    # global PRINT_CURRENT_ITEM_DETAILS # 在函数开头声明
#    # TARGET_ID = str(P_DBUG_RESPONDENT_ID).strip() if P_DBUG_RESPONDENT_ID is not None else None
#    # TARGET_Q_CLEANED = clean_text_for_maxqda(P_DBUG_QUESTION_TEXT_RAW, True) if P_DBUG_QUESTION_TEXT_RAW is not None else None
#    #
#    # respondent_matches = (TARGET_ID is None or current_respondent_id == TARGET_ID)
#    # question_matches = (TARGET_Q_CLEANED is None or current_q_cleaned == TARGET_Q_CLEANED)
#    # PRINT_CURRENT_ITEM_DETAILS = respondent_matches and question_matches
#    ```
#    **辅助函数中的使用示例:**
#    ```python
#    # global PRINT_CURRENT_ITEM_DETAILS
#    # if PRINT_CURRENT_ITEM_DETAILS:
#    #     print("这是一条详细的调试日志...")
#    ```
#
# == file_dir 字典中主要键的含义与对应文件/目录 ==
#
# --- 顶级和应用特定目录 ---
# 'root_data_dir': "data_dir/" 
# 'app_root_dir': "data_dir/[app]_dir/" (例如 "data_dir/myworld_dir/")
#
# --- 00_rawdata_dir ---
# 'UI': "data_dir/[app]_dir/00_rawdata_dir/[app].csv" (原始CSV数据)
#
# --- 01_preprocessed_for_llm_dir ---
# 'UI_utxt': "data_dir/[app]_dir/01_preprocessed_for_llm_dir/[app]_user.txt" (纵向文本)
# 'UI_qtxt': "data_dir/[app]_dir/01_preprocessed_for_llm_dir/[app]_question.txt" (横向文本)
#
# --- 02_interview_outline_dir ---
# 'interview_outline_base_dir': "data_dir/[app]_dir/02_interview_outline_dir/" (所有分组的父目录)
#
#   对于每个分组 (例如，通过遍历 parameters.PROJECT_GROUP_FOLDERS 获得 group_folder_name):
#     分组主目录: os.path.join(file_dir['interview_outline_base_dir'], group_folder_name) + os.sep
#     分组下的 question_data_dir: os.path.join(..., "question_data_dir") + os.sep
#     分组下的 codebook_data_dir: os.path.join(..., "codebook_data_dir") + os.sep
#     分组下的 meta_data_dir: os.path.join(..., "meta_data_dir") + os.sep
#
#   动态生成的列表键 (由 parameters.py 内部逻辑填充):
#   'groups_config_list': parameters.PROJECT_GROUP_FOLDERS (方便其他脚本迭代分组)
#   'grouped_user_g_txts': 列表，每个元素是对应分组的 user_g.txt 的完整路径。
#                           例如: file_dir['grouped_user_g_txts'][0] 是第一个分组的user_g.txt路径。
#   'grouped_inductive_q_jsons': 嵌套列表，外层列表对应分组，内层列表是该组所有 inductive_questionN.json 的路径。
#                                例如: file_dir['grouped_inductive_q_jsons'][0] 是第一个分组的JSON文件路径列表。
#   'grouped_deductive_llm_jsons_in_group': 列表，每个元素是对应分组的 deductive_code_by_LLM.json 的路径。
#   'grouped_inductive_q_cbook_jsons': 嵌套列表，类似 'grouped_inductive_q_jsons'，但针对 _codebook.json 文件。
#   'grouped_raw_codebook_txts': 列表，每个元素是对应分组的 raw_codebooks.txt 的路径。
#   'grouped_final_codebooks_txts': 列表，每个元素是对应分组的 codebook.txt 的路径。
#   'grouped_meta_data_files': 列表，每个元素是对应分组的元数据文件路径。
#
# --- 03_inductive_coding_dir ---
# 'inductive_dir_path': "data_dir/[app]_dir/03_inductive_coding_dir/"
# 'inductive_merged_json': ".../[app]_inductive_codes.json" (全局合并的归纳编码JSON)
# 'inductive_maxqda_opencode': ".../[app]_inductive_maxqda_opencode.txt"
# 'inductive_maxqda_themecode': ".../[app]_inductive_maxqda_themecode.txt"
# 'inductive_global_metadata': ".../[app]_inductive_metadata.json"
#
# --- 04_deductive_coding_dir ---
# 'deductive_dir_path': "data_dir/[app]_dir/04_deductive_coding_dir/"
# 'deductive_llm_raw_output': ".../[app]_deductive_llm_output.json" (全局演绎编码LLM输出)
# 'deductive_maxqda_text': ".../[app]_deductive_maxqda.txt"
# 'deductive_global_metadata': ".../[app]_deductive_metadata.json"
#
# --- 文件名模式 (常量，非路径) ---
# 'pattern_inductive_q_json': 'inductive_question[0-9]*.json'
# 'pattern_inductive_q_cbook_json': 'inductive_question[0-9]*_codebook.json'
# 'pattern_deductive_llm_in_group': 'deductive_code_by_LLM.json'
#
# == 重要维护点 ==
# 1. **`app` 变量**: 在本文件顶部设置，用于构建项目特定的文件名和路径。
# 2. **`PROJECT_GROUPS_CONFIG` 列表**: 这是研究者定义访谈大纲分组的地方。
#    增加、删除或重命名分组文件夹时，主要修改此列表。
#    脚本会基于此列表动态生成 `file_dir` 中与分组相关的路径和文件列表。
# 3. **文件名模式**: 如果LLM输出的独立JSON文件名约定有变，需修改对应的模式常量。
# 4. **基础目录结构常量**: 如 `DATA_ROOT_DIR_NAME`, `SDIR_00_RAW` 等，如果项目整体结构调整，需修改这些。
#
# 通过以上约定，其他脚本应该能够以统一和简洁的方式与本项目的文件系统进行交互。
#
# ----------------------------------------------------------------------------------

# ... (parameters.py 的其余代码：ensure_dir_exists, file_dir 初始化, 动态填充, 目录创建, P_DBUG 定义) ...


import os
import glob
import re

# --- 项目核心配置 ---
app = 'myworld'
is_steam = False
parameters_dict = { # parameters 字典
    'top_n': 300,
    'min_df': 0.2,
    'ngram': 1,
    'ngram_range': (1,1),
}

# --- 辅助函数：确保目录存在 ---
def ensure_dir_exists(directory_path):
    """确保目录存在，如果不存在则创建，并打印创建信息。"""
    if not directory_path: return
    if not os.path.exists(directory_path):
        try:
            os.makedirs(directory_path, exist_ok=True)
            print(f"INFO (parameters.py): 已创建目录: {directory_path}")
        except OSError as e:
            print(f"错误 (parameters.py): 创建目录 '{directory_path}' 失败: {e}")

# --- 【核心修改】基础路径组件定义 ---
# 因为 parameters.py 在项目根目录，所以 PROJECT_ROOT 就是当前文件所在的目录
# 或者，所有路径可以直接以 "data_dir" 或 "scripts_dir" 开头，因为它们是相对于根的
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__)) # 项目根目录就是 parameters.py 所在的目录

DATA_DIR_BASE_NAME = "data_dir" # 顶级数据文件夹名
SCRIPTS_DIR_BASE_NAME = "scripts_dir" # 顶级脚本文件夹名
APP_FOLDER_NAME = f"{app}_dir"   # 例如 myworld_dir

# 构建基础路径 (这些现在是相对于项目根目录的)
BASE_DATA_PATH = os.path.join(PROJECT_ROOT, DATA_DIR_BASE_NAME) # data_dir
APP_PATH = os.path.join(BASE_DATA_PATH, APP_FOLDER_NAME)       # data_dir/myworld_dir

# 各阶段子目录的固定名称 
SDIR_00_RAW = "00_rawdata_dir"
SDIR_01_PREPROC = "01_preprocessed_for_llm_dir"
SDIR_02_OUTLINE = "02_interview_outline_dir"
SDIR_03_INDUCTIVE = "03_inductive_coding_dir"
SDIR_04_DEDUCTIVE = "04_deductive_coding_dir"

# 分组内部功能性子文件夹名称
SDIR_GROUP_QDATA = "question_data_dir"
SDIR_GROUP_CBOOK = "codebook_data_dir"
SDIR_GROUP_META = "meta_data_dir"

# --- 此处自定义访谈大纲的分组文件夹名称 ---
PROJECT_GROUP_FOLDERS = [
    "player_states", "player_experiences",
    "creativity_experiences", "creativity_features",
]

# --- 初始化 file_dir 字典 ---
file_dir = {}

# --- 固定路径填充 ---
file_dir['UI'] = os.path.join(APP_PATH, SDIR_00_RAW, f"{app}.csv")
file_dir['UI_utxt'] = os.path.join(APP_PATH, SDIR_01_PREPROC, f"{app}_user.txt")
file_dir['UI_qtxt'] = os.path.join(APP_PATH, SDIR_01_PREPROC, f"{app}_question.txt")

file_dir['inductive_global_dir'] = os.path.join(APP_PATH, SDIR_03_INDUCTIVE) + os.sep
file_dir['inductive_merged_json'] = os.path.join(APP_PATH, SDIR_03_INDUCTIVE, f"{app}_inductive_codes.json")
file_dir['inductive_maxqda_opencode'] = os.path.join(APP_PATH, SDIR_03_INDUCTIVE, f"{app}_inductive_maxqda_opencode.txt")
file_dir['inductive_maxqda_themecode'] = os.path.join(APP_PATH, SDIR_03_INDUCTIVE, f"{app}_inductive_maxqda_themecode.txt")
file_dir['inductive_global_metadata'] = os.path.join(APP_PATH, SDIR_03_INDUCTIVE, f"{app}_inductive_metadata.json")

file_dir['deductive_global_dir'] = os.path.join(APP_PATH, SDIR_04_DEDUCTIVE) + os.sep
file_dir['deductive_llm_raw_output'] = os.path.join(APP_PATH, SDIR_04_DEDUCTIVE, f"{app}_deductive_llm_output.json")
file_dir['deductive_maxqda_text'] = os.path.join(APP_PATH, SDIR_04_DEDUCTIVE, f"{app}_deductive_maxqda.txt")
file_dir['deductive_global_metadata'] = os.path.join(APP_PATH, SDIR_04_DEDUCTIVE, f"{app}_deductive_metadata.json")


# --- 文件名模式 ---
file_dir['pattern_inductive_q_json'] = 'inductive_question[0-9]*.json'
file_dir['pattern_inductive_q_cbook_json'] = 'inductive_question[0-9]*_codebook.json'
file_dir['pattern_deductive_llm_in_group'] = 'deductive_code_by_LLM.json'


# --- 动态生成与分组相关的路径和文件列表 ---
grouped_keys_to_init = [
    'grouped_user_g_txts', 'grouped_inductive_q_jsons',
    'grouped_deductive_llm_jsons_in_group', 'grouped_inductive_q_cbook_jsons',
    'grouped_raw_codebook_txts', 'grouped_final_codebooks_txts',
    'grouped_meta_data_files'
]
for key in grouped_keys_to_init:
    file_dir[key] = []

outline_parent_abs_dir = os.path.join(APP_PATH, SDIR_02_OUTLINE)

for group_folder_name in PROJECT_GROUP_FOLDERS:
    group_main_abs_dir = os.path.join(outline_parent_abs_dir, group_folder_name)
    
    qdata_abs_dir = os.path.join(group_main_abs_dir, SDIR_GROUP_QDATA)
    cbook_abs_dir = os.path.join(group_main_abs_dir, SDIR_GROUP_CBOOK)
    meta_abs_dir = os.path.join(group_main_abs_dir, SDIR_GROUP_META)

    file_dir['grouped_user_g_txts'].append(os.path.join(qdata_abs_dir, "user_g.txt"))
    
    pattern_ind_q = file_dir['pattern_inductive_q_json']
    files_ind_q = sorted(glob.glob(os.path.join(qdata_abs_dir, pattern_ind_q)))
    file_dir['grouped_inductive_q_jsons'].append(files_ind_q)
    
    deductive_llm_file_this_group = os.path.join(qdata_abs_dir, file_dir['pattern_deductive_llm_in_group'])
    file_dir['grouped_deductive_llm_jsons_in_group'].append(deductive_llm_file_this_group)

    pattern_ind_cbook = file_dir['pattern_inductive_q_cbook_json']
    files_this_group_ind_cbook = sorted(glob.glob(os.path.join(cbook_abs_dir, pattern_ind_cbook)))
    file_dir['grouped_inductive_q_cbook_jsons'].append(files_this_group_ind_cbook)
    
    file_dir['grouped_raw_codebook_txts'].append(os.path.join(cbook_abs_dir, "raw_codebooks.txt"))
    file_dir['grouped_final_codebooks_txts'].append(os.path.join(cbook_abs_dir, "codebook.txt"))
    file_dir['grouped_meta_data_files'].append(os.path.join(meta_abs_dir, f"{group_folder_name}_metadata.json"))


# --- 自动确保所有在 file_dir 中定义的目录都存在 ---
print(f"INFO (parameters.py): 正在为应用 '{app}' 检查并按需创建所有已定义的目录...")
all_dirs_to_ensure = set()

# 1. 添加所有明确是目录的路径 (这些路径已经都以 os.sep 结尾了，或者本身就是父目录)
#    确保所有在 file_dir 中定义的、以斜杠结尾的路径都被加入
#    以及所有文件路径的父目录都被加入。

# 首先确保最顶层的 data_dir 和 app_dir 存在
ensure_dir_exists(os.path.join(PROJECT_ROOT, DATA_DIR_BASE_NAME))
ensure_dir_exists(APP_PATH) # APP_PATH 本身是一个目录

# 然后遍历 file_dir 中的所有值
for key, path_value in file_dir.items():
    if isinstance(path_value, str): 
        if key.endswith('_pattern') or key == 'Qjson': 
            continue 
        
        # 检查路径是否明确表示为目录 (以分隔符结尾)
        # 或者其键名是否暗示它是一个目录 (例如，包含 '_dir' 但不以 _pattern 结尾)
        # 一个更简单的方法是，只要值是一个字符串，就尝试获取其目录部分并确保存在
        # 对于本身就是目录的路径，os.path.dirname 会返回其父目录，我们需要确保这个目录本身也被创建
        
        if path_value.endswith(os.sep): # 如果值本身以分隔符结尾，它是一个目录
            all_dirs_to_ensure.add(path_value)
        else: # 否则认为是文件路径，取其父目录
            parent = os.path.dirname(path_value)
            if parent: # 确保父目录非空
                all_dirs_to_ensure.add(parent + os.sep) # 确保父目录也以分隔符结尾加入set

    elif isinstance(path_value, list): # 如果是路径列表
        for item_path_or_list in path_value:
            if isinstance(item_path_or_list, str):
                parent = os.path.dirname(item_path_or_list)
                if parent: all_dirs_to_ensure.add(parent + os.sep)
            elif isinstance(item_path_or_list, list): # 如果是嵌套列表
                for sub_item_path in item_path_or_list:
                    if isinstance(sub_item_path, str):
                        parent = os.path.dirname(sub_item_path)
                        if parent: all_dirs_to_ensure.add(parent + os.sep)

# 创建所有收集到的目录
for dir_to_create in sorted(list(all_dirs_to_ensure)):
    ensure_dir_exists(dir_to_create.rstrip(os.sep))

print("INFO (parameters.py): 所有必需的目录检查和创建完成。")
        
# --- 调试打印配置 ---
P_DBUG_RESPONDENT_ID = "9" 
P_DBUG_QUESTION_TEXT_RAW = "最吸引你的玩法是什么/为什么喜欢这种玩法?"