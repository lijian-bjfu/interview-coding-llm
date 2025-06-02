import csv
import json
import os
import re
from fuzzywuzzy import process, fuzz # 用于模糊字符串匹配

# --- 按照 parameters.py 导入 ---
try:
    from parameters import file_dir, app, P_DBUG_RESPONDENT_ID, P_DBUG_QUESTION_TEXT_RAW
    print("INFO (convert-maxqda-tc.py): 成功从 parameters.py 导入 file_dir, app 及 P_DBUG 调试配置。")
except ImportError:
    print("警告 (convert-maxqda-tc.py)：无法从 parameters.py 导入。请确保该文件在Python路径中。")
    print("警告 (convert-maxqda-tc.py): 将使用脚本内定义的最小备用配置（可能无法正常工作）。")
    app = 'myworld_default_app_应急'
    # 这是一个非常基础的备用，实际应提示用户检查 parameters.py
    file_dir = {
        'UI': f'data_dir/{app}_dir/00_rawdata_dir/{app}.csv', # 示例
        'inductive_merged_json': f'data_dir/{app}_dir/03_inductive_coding_dir/{app}_inductive_codes.json', # 示例
        'maxqda_final_import_file': f'data_dir/{app}_dir/06_maxqda_final_import_files/{app}_maxqda_import_ALL.txt' # 示例
    }
    P_DBUG_RESPONDENT_ID = None
    P_DBUG_QUESTION_TEXT_RAW = None

# --- 全局调试打印控制变量 (由 parameters.py 控制) ---
PRINT_CURRENT_ITEM_DETAILS = False
# ------------------------------

# --- 辅助函数 (内部打印受 PRINT_CURRENT_ITEM_DETAILS 控制) ---
def clean_text_for_maxqda(text, is_for_code_name=False):
    global PRINT_CURRENT_ITEM_DETAILS
    if text is None: return ""
    # if PRINT_CURRENT_ITEM_DETAILS: print(f"    文本清理前: '{str(text)[:50]}...'")
    cleaned_text = str(text).replace('\r\n', ' ').replace('\n', ' ').replace('\r', ' ').replace('#', '')
    if is_for_code_name:
        cleaned_text = cleaned_text.replace('\\', '/').replace('"', "'")
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
    # if PRINT_CURRENT_ITEM_DETAILS: print(f"    文本清理后: '{cleaned_text[:50]}...'")
    return cleaned_text

def _find_locations_for_single_quote(text_to_search_in, quote_to_find):
    global PRINT_CURRENT_ITEM_DETAILS
    # ... (保持您提供的V11版本中的完整实现) ...
    if not quote_to_find: return []
    processed_text = re.sub(r'\s+', ' ', text_to_search_in).strip()
    processed_quote = re.sub(r'\s+', ' ', quote_to_find).strip()
    if not processed_quote: return []
    if PRINT_CURRENT_ITEM_DETAILS: print(f"      尝试定位引文: '{processed_quote[:50]}...' 在 '{processed_text[:70]}...' 中")
    locations = []
    current_pos = 0
    while current_pos < len(processed_text):
        idx = processed_text.find(processed_quote, current_pos)
        if idx == -1: break
        locations.append({'start': idx, 'end': idx + len(processed_quote), 
                          'matched_text': processed_text[idx : idx + len(processed_quote)], 
                          'match_type': 'exact'})
        current_pos = idx + len(processed_quote)
    if locations:
        if PRINT_CURRENT_ITEM_DETAILS: print(f"        精确定位: 找到 {len(locations)} 处。")
        return locations
    if PRINT_CURRENT_ITEM_DETAILS: print(f"        精确查找失败，尝试模糊定位引文: '{processed_quote[:50]}...'")
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

# --- 数据加载模块 (内部打印为固定宏观信息) ---
def load_llm_json_data(merged_json_filepath):
    # ... (保持您V11版本的完整实现) ...
    print(f"  辅助流程: 开始加载LLM分析JSON文件 (CMTC版本): {merged_json_filepath}")
    if not os.path.exists(merged_json_filepath):
        print(f"错误: 合并后的JSON文件 '{merged_json_filepath}' 未找到。")
        return None
    try:
        with open(merged_json_filepath, 'r', encoding='utf-8') as f:
            llm_analysis_data = json.load(f)
        print(f"  辅助流程: LLM JSON文件读取成功，包含 {len(llm_analysis_data)} 个问题的分析。")
        llm_data_by_question_map = {}
        for question_analysis in llm_analysis_data:
            q_text_from_json = question_analysis.get("question_text", "")
            if not q_text_from_json:
                print("    警告: JSON中发现一个没有 'question_text' 的问题分析条目，已跳过。")
                continue
            cleaned_q_text_for_key = clean_text_for_maxqda(q_text_from_json, is_for_code_name=True)
            if cleaned_q_text_for_key not in llm_data_by_question_map:
                llm_data_by_question_map[cleaned_q_text_for_key] = {
                    'themes_for_this_question': question_analysis.get("themes", []),
                    'all_initial_code_entries_for_question': question_analysis.get("initial_codes", []),
                    'code_definitions_for_this_question': question_analysis.get("codes", []) 
                }
            else: 
                print(f"    警告: 问题 '{cleaned_q_text_for_key}' 在合并JSON中出现多次...") # 省略部分
                llm_data_by_question_map[cleaned_q_text_for_key]['themes_for_this_question'].extend(question_analysis.get("themes", []))
                llm_data_by_question_map[cleaned_q_text_for_key]['all_initial_code_entries_for_question'].extend(question_analysis.get("initial_codes", []))
                llm_data_by_question_map[cleaned_q_text_for_key]['code_definitions_for_this_question'].extend(question_analysis.get("codes", []))
        print(f"  辅助流程: LLM编码数据已映射到 {len(llm_data_by_question_map)} 个问题。")
        return llm_data_by_question_map
    except Exception as e:
        print(f"错误: 加载或处理LLM JSON '{merged_json_filepath}' 失败: {e}")
        import traceback; traceback.print_exc(); return None

def load_interview_csv_data(original_csv_filepath, respondent_id_csv_column):
    print(f"  辅助流程: 开始加载原始CSV访谈数据: {original_csv_filepath}")
    if not os.path.exists(original_csv_filepath):
        print(f"错误: 原始CSV访谈数据文件 '{original_csv_filepath}' 未找到。")
        return None, None
    original_interviews_data = []
    csv_header_list = []
    try:
        with open(original_csv_filepath, 'r', encoding='utf-8-sig') as csvfile:
            reader = csv.DictReader(csvfile)
            if not reader.fieldnames:
                print(f"错误：CSV文件 '{original_csv_filepath}' 表头为空或无法读取。")
                return None, None
            csv_header_list = reader.fieldnames
            if respondent_id_csv_column not in csv_header_list:
                print(f"错误：指定的被访者ID列 '{respondent_id_csv_column}' 不在CSV表头 {csv_header_list} 中。")
                return None, None
            for row in reader:
                original_interviews_data.append(row)
        print(f"  辅助流程: 原始CSV数据读取成功，共 {len(original_interviews_data)} 条被访者记录。")
        return original_interviews_data, csv_header_list
    except Exception as e:
        print(f"错误: 读取或处理CSV文件 '{original_csv_filepath}' 时发生: {e}")
        return None, None

def load_data(merged_json_path, original_csv_path, respondent_id_col):
    print("\n宏观流程: 步骤一：加载所有数据...")
    llm_data = load_llm_json_data(merged_json_path)
    original_data, csv_headers = load_interview_csv_data(original_csv_path, respondent_id_col)
    if llm_data is not None and original_data is not None and csv_headers is not None:
        print("宏观流程: 步骤一：所有数据加载成功！")
        return llm_data, original_data, csv_headers
    else:
        print("宏观流程: 步骤一：数据加载失败。")
        return None, None, None

# --- CMTC核心编码处理模块 ---
def get_segments_and_codes_for_answer(
    original_answer_processed, 
    current_respondent_id,
    llm_initial_code_entries_for_respondent, 
    themes_for_current_question, 
    parent_question_cleaned
    ):
    global PRINT_CURRENT_ITEM_DETAILS 
    if PRINT_CURRENT_ITEM_DETAILS: print(f"    步骤CMTC-A1 (细化层级): 开始为回答 '{original_answer_processed[:30]}...' 解析LLM编码条目...")
    aggregated_segments_map = {} 
    for llm_entry in llm_initial_code_entries_for_respondent:
        code_names_list = llm_entry.get("code_name", [])
        supporting_quotes_list = llm_entry.get("supporting_quote", [])
        pairs_list = llm_entry.get("pairs", [])
        if not (isinstance(code_names_list, list) and isinstance(supporting_quotes_list, list) and isinstance(pairs_list, list)):
            if PRINT_CURRENT_ITEM_DETAILS: print(f"      警告: initial_code_entry 中的 code_name, supporting_quote 或 pairs 不是列表，跳过。")
            continue
        for pair_str in pairs_list:
            try:
                code_idx_str, quote_idx_str = pair_str.split('-')
                code_idx = int(code_idx_str) - 1
                quote_idx = int(quote_idx_str) - 1
                if not (0 <= code_idx < len(code_names_list) and 0 <= quote_idx < len(supporting_quotes_list)):
                    if PRINT_CURRENT_ITEM_DETAILS: print(f"      警告: pair '{pair_str}' 索引越界...")
                    continue
                raw_initial_code = code_names_list[code_idx]
                raw_supporting_quote = supporting_quotes_list[quote_idx]
                if str(raw_initial_code).upper() == "NULL" or not str(raw_supporting_quote).strip():
                    if PRINT_CURRENT_ITEM_DETAILS: print(f"      跳过单个NULL编码或空引文...")
                    continue
                cleaned_initial_code = clean_text_for_maxqda(raw_initial_code, is_for_code_name=True)
                if not cleaned_initial_code: 
                    if PRINT_CURRENT_ITEM_DETAILS: print(f"      警告: 清理后初始编码为空...")
                    continue
                quote_to_find = clean_text_for_maxqda(raw_supporting_quote, is_for_code_name=False)
                if not quote_to_find:
                    if PRINT_CURRENT_ITEM_DETAILS: print(f"      引文清理后为空...")
                    continue
                found_locations = _find_locations_for_single_quote(original_answer_processed, quote_to_find)
                if not found_locations:
                    if PRINT_CURRENT_ITEM_DETAILS: print(f"      警告: 未能定位引文 '{quote_to_find[:30]}...'")
                    continue
                for loc_data in found_locations:
                    start, end = loc_data['start'], loc_data['end']
                    matched_text_in_answer = loc_data['matched_text']
                    segment_key = (start, end)
                    if segment_key not in aggregated_segments_map:
                        aggregated_segments_map[segment_key] = {'matched_text': matched_text_in_answer, 'codes_to_apply_set': set()}
                    final_hierarchical_code_to_add = None; found_theme_for_this_ic = False
                    for theme_entry in themes_for_current_question:
                        theme_name_raw = theme_entry.get("theme_name")
                        included_ics_in_theme = theme_entry.get("included_initial_codes", [])
                        cleaned_included_ics = [clean_text_for_maxqda(ic, True) for ic in included_ics_in_theme]
                        if cleaned_initial_code in cleaned_included_ics:
                            cleaned_theme_name = clean_text_for_maxqda(theme_name_raw, is_for_code_name=True)
                            if cleaned_theme_name:
                                final_hierarchical_code_to_add = f"{parent_question_cleaned}\\{cleaned_theme_name}\\{cleaned_initial_code}"
                                found_theme_for_this_ic = True
                                if PRINT_CURRENT_ITEM_DETAILS: print(f"        决定应用三级编码...")
                                break 
                    if not found_theme_for_this_ic:
                        final_hierarchical_code_to_add = f"{parent_question_cleaned}\\{cleaned_initial_code}"
                        if PRINT_CURRENT_ITEM_DETAILS: print(f"        决定应用二级编码...")
                    if final_hierarchical_code_to_add:
                        aggregated_segments_map[segment_key]['codes_to_apply_set'].add(final_hierarchical_code_to_add)
            except Exception as e_pair: # 更具体的异常捕获
                 if PRINT_CURRENT_ITEM_DETAILS: print(f"      警告: 解析或处理pair '{pair_str}' 时出错: {e_pair}，跳过。")
                 continue
    final_located_list = []
    for (start, end), data in aggregated_segments_map.items():
        final_located_list.append({
            'start': start, 'end': end, 'matched_text': data['matched_text'],
            'all_applicable_codes_set': data['codes_to_apply_set']
        })
    final_located_list.sort(key=lambda x: x['start'])
    if PRINT_CURRENT_ITEM_DETAILS: print(f"  步骤CMTC-A1 完成: 为当前回答解析并定位了 {len(final_located_list)} 个编码片段。")
    return final_located_list


def resolve_overlaps_and_aggregate_codes(sorted_located_segments, original_answer_for_tagging):
    global PRINT_CURRENT_ITEM_DETAILS
    if PRINT_CURRENT_ITEM_DETAILS: print(f"  步骤CMTC-A2: 开始处理 {len(sorted_located_segments)} 个片段的重叠...")
    if not sorted_located_segments:
        if PRINT_CURRENT_ITEM_DETAILS: print("    详细日志 - 没有片段处理重叠。")
        return []
    final_non_overlapping_segments = []
    current_merged_s = None
    for next_s_data in sorted_located_segments:
        if PRINT_CURRENT_ITEM_DETAILS: print(f"      检查片段: S={next_s_data['start']}, E={next_s_data['end']}, Codes={next_s_data['all_applicable_codes_set']}")
        if current_merged_s is None:
            current_merged_s = {'start': next_s_data['start'], 'end': next_s_data['end'], 'codes_to_apply_set': set(next_s_data['all_applicable_codes_set'])}
            if PRINT_CURRENT_ITEM_DETAILS: print(f"        开始新的合并段...")
        elif next_s_data['start'] < current_merged_s['end']: 
            if PRINT_CURRENT_ITEM_DETAILS: print(f"        片段重叠...")
            current_merged_s['end'] = max(current_merged_s['end'], next_s_data['end'])
            current_merged_s['codes_to_apply_set'].update(next_s_data['all_applicable_codes_set'])
            if PRINT_CURRENT_ITEM_DETAILS: print(f"        更新合并段...")
        else: 
            if PRINT_CURRENT_ITEM_DETAILS: print(f"        片段不重叠。完成前一个。")
            text_for_merged = original_answer_for_tagging[current_merged_s['start']:current_merged_s['end']]
            final_non_overlapping_segments.append({
                'start': current_merged_s['start'], 'end': current_merged_s['end'],
                'text_to_code': text_for_merged,
                'final_combined_codes_str': "&&".join(sorted(list(current_merged_s['codes_to_apply_set'])))
            })
            current_merged_s = {'start': next_s_data['start'], 'end': next_s_data['end'], 'codes_to_apply_set': set(next_s_data['all_applicable_codes_set'])}
            if PRINT_CURRENT_ITEM_DETAILS: print(f"    开始新的合并段...")
    if current_merged_s: 
        if PRINT_CURRENT_ITEM_DETAILS: print(f"    完成最后一个合并段。")
        text_for_merged = original_answer_for_tagging[current_merged_s['start']:current_merged_s['end']]
        final_non_overlapping_segments.append({
            'start': current_merged_s['start'], 'end': current_merged_s['end'],
            'text_to_code': text_for_merged,
            'final_combined_codes_str': "&&".join(sorted(list(current_merged_s['codes_to_apply_set'])))
        })
    if PRINT_CURRENT_ITEM_DETAILS: print(f"  步骤CMTC-A2 完成: 生成了 {len(final_non_overlapping_segments)} 个不重叠段。")
    return final_non_overlapping_segments

def build_tagged_line_from_segments(original_answer_for_tagging, final_non_overlapping_segments):
    global PRINT_CURRENT_ITEM_DETAILS
    if PRINT_CURRENT_ITEM_DETAILS: print(f"  步骤CMTC-B: 为回答 '{original_answer_for_tagging[:50]}...' 构建标签行...")
    if not final_non_overlapping_segments:
        if PRINT_CURRENT_ITEM_DETAILS: print(f"    详细日志 - 无最终编码段，返回原文。")
        return original_answer_for_tagging 
    result_parts = []
    current_pos_in_original = 0
    for segment in final_non_overlapping_segments:
        if segment['start'] > current_pos_in_original:
            uncoded_part = original_answer_for_tagging[current_pos_in_original:segment['start']]
            result_parts.append(uncoded_part)
            if PRINT_CURRENT_ITEM_DETAILS: print(f"    详细日志 - 添加未编码前缀: '{uncoded_part[:30]}...'")
        text_coded_cleaned = clean_text_for_maxqda(segment['text_to_code'], is_for_code_name=False)
        maxqda_tag_segment = f"#CODE {segment['final_combined_codes_str']}#{text_coded_cleaned}#ENDCODE#"
        result_parts.append(maxqda_tag_segment)
        if PRINT_CURRENT_ITEM_DETAILS: print(f"    详细日志 - 添加编码段: (编码: {segment['final_combined_codes_str']}) '{text_coded_cleaned[:30]}...'")
        current_pos_in_original = segment['end']
    if current_pos_in_original < len(original_answer_for_tagging):
        remaining_uncoded_part = original_answer_for_tagging[current_pos_in_original:]
        result_parts.append(remaining_uncoded_part)
        if PRINT_CURRENT_ITEM_DETAILS: print(f"    详细日志 - 添加未编码后缀: '{remaining_uncoded_part[:30]}...'")
    final_line = "".join(result_parts).strip()
    if PRINT_CURRENT_ITEM_DETAILS: print(f"  步骤CMTC-B 完成: 生成行为: '{final_line[:100]}...'")
    return final_line if final_line else original_answer_for_tagging


# --- 主转换流程控制函数 ---
def run_maxqda_conversion(
    # 直接接收加载好的数据
    loaded_llm_data_map,
    loaded_original_interviews,
    loaded_csv_headers,
    output_maxqda_filepath,
    respondent_id_csv_column,
    questions_to_skip_coding=["序号"]
    ):
    global PRINT_CURRENT_ITEM_DETAILS 
    print("--- 开始MaxQDA格式转换主流程 (CMTC版本) ---")
    
    # 直接从全局（由 parameters.py 导入）获取调试目标
    TARGET_ID_FOR_DEBUG = str(P_DBUG_RESPONDENT_ID).strip() if P_DBUG_RESPONDENT_ID is not None else None
    TARGET_Q_CLEANED_FOR_DEBUG = clean_text_for_maxqda(P_DBUG_QUESTION_TEXT_RAW, is_for_code_name=True) \
                               if P_DBUG_QUESTION_TEXT_RAW is not None else None
    
    print(f"INFO: 当前调试目标配置 - 被访者ID: '{TARGET_ID_FOR_DEBUG}', 清理后的目标问题: '{TARGET_Q_CLEANED_FOR_DEBUG}'")

    # 使用传入的已加载数据
    llm_data_map = loaded_llm_data_map
    original_interviews_list = loaded_original_interviews
    csv_headers = loaded_csv_headers

    if not llm_data_map or not original_interviews_list or not csv_headers:
        print("错误：主流程接收到的核心数据不完整，无法继续。")
        return False

    # 确保输出目录存在 (这个逻辑可以保留，或者假设在主程序块中已处理)
    output_dir = os.path.dirname(output_maxqda_filepath)
    if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir); print(f"  已创建输出目录: {output_dir}")

    try:
        with open(output_maxqda_filepath, 'w', encoding='utf-8') as f_out:
            print(f"\n开始生成MaxQDA输出文件: {output_maxqda_filepath}")
            
            for i, respondent_dict_data in enumerate(original_interviews_list):
                current_respondent_id = respondent_dict_data.get(respondent_id_csv_column, "").strip()
                if not current_respondent_id:
                    print(f"警告：第 {i+1} 条CSV数据缺少有效ID，已跳过。")
                    continue

                respondent_matches_target = (TARGET_ID_FOR_DEBUG is None or current_respondent_id == TARGET_ID_FOR_DEBUG)
                
                # 宏观的被访者处理信息，只在匹配目标被访者或不限制时打印
                if respondent_matches_target:
                    print(f"\n处理被访者: {current_respondent_id} ({i+1}/{len(original_interviews_list)})")
                
                f_out.write(f"#TEXT {current_respondent_id}\n\n")

                for question_header_from_csv in csv_headers:
                    if question_header_from_csv == respondent_id_csv_column:
                        continue 

                    original_answer_raw = respondent_dict_data.get(question_header_from_csv, "")
                    current_parent_code_q_cleaned = clean_text_for_maxqda(question_header_from_csv, is_for_code_name=True)

                    # ---- 设置全局打印标志 ----
                    PRINT_CURRENT_ITEM_DETAILS = False 
                    question_matches_target = (TARGET_Q_CLEANED_FOR_DEBUG is None or \
                                               current_parent_code_q_cleaned == TARGET_Q_CLEANED_FOR_DEBUG)
                    if respondent_matches_target and question_matches_target:
                        PRINT_CURRENT_ITEM_DETAILS = True
                    
                    # ---- 打印当前正在处理的问题（受 PRINT_CURRENT_ITEM_DETAILS 或 respondent_matches_target 控制）----
                    if PRINT_CURRENT_ITEM_DETAILS: 
                        print(f"  >> 详细调试 << 处理问题: '{question_header_from_csv}' (父编码: '{current_parent_code_q_cleaned}') 对于被访者 '{current_respondent_id}'")
                    elif respondent_matches_target: # 如果是目标用户，但非目标问题，也打印一个简略提示
                        print(f"  处理问题 (目标用户，非目标问题，简略): '{question_header_from_csv}'")
                    # 对于非目标用户，这里不打印问题处理信息

                    
                    # --- 后续的编码处理逻辑 (与V11版本相同，其内部打印受 PRINT_CURRENT_ITEM_DETAILS 控制) ---
                    if question_header_from_csv in questions_to_skip_coding:
                        if PRINT_CURRENT_ITEM_DETAILS: print(f"    详细日志 - 此问题标记为跳过细分编码。")
                        f_out.write(f"{clean_text_for_maxqda(original_answer_raw, False)}\n\n" if original_answer_raw.strip() else "\n")
                        continue
                    if not original_answer_raw.strip():
                        if PRINT_CURRENT_ITEM_DETAILS: print(f"    详细日志 - 原始回答为空。")
                        f_out.write(f"\n")
                        continue
                    answer_text_for_tagging = clean_text_for_maxqda(original_answer_raw, is_for_code_name=False)
                    if not answer_text_for_tagging:
                        if PRINT_CURRENT_ITEM_DETAILS: print(f"    详细日志 - 清理后回答为空。")
                        f_out.write(f"\n")
                        continue

                    question_specific_llm_data = llm_data_map.get(current_parent_code_q_cleaned, {})
                    all_initial_codes_for_q = question_specific_llm_data.get('all_initial_code_entries_for_question', [])
                    current_respondent_llm_entries = []
                    for entry in all_initial_codes_for_q:
                        if str(entry.get("respondent_id","")).strip() == current_respondent_id:
                            current_respondent_llm_entries.append(entry)
                    themes_for_this_q = question_specific_llm_data.get('themes_for_this_question', [])
                    
                    if PRINT_CURRENT_ITEM_DETAILS: 
                        print(f"    详细日志 - 找到 {len(current_respondent_llm_entries)} 条LLM initial_code 条目。")
                        print(f"    详细日志 - 当前问题有 {len(themes_for_this_q)} 个主题。")
                    
                    located_segments = get_segments_and_codes_for_answer(
                        answer_text_for_tagging, current_respondent_id, 
                        current_respondent_llm_entries, themes_for_this_q,
                        current_parent_code_q_cleaned
                    )
                    final_segments = resolve_overlaps_and_aggregate_codes( 
                        located_segments, answer_text_for_tagging
                    )
                    tagged_line = build_tagged_line_from_segments( 
                        answer_text_for_tagging, final_segments
                    )
                    f_out.write(f"{tagged_line}\n\n")
                
                if respondent_matches_target: # 只在目标用户处理完毕才打印
                    print(f"被访者 {current_respondent_id} 处理完毕。")
                f_out.write("\n") 
            
            print(f"\nMaxQDA结构化文本文件已成功生成到: {output_maxqda_filepath}") # 固定打印
            return True
    except Exception as e:
        print(f"在主转换流程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False

# --- 主程序执行 ---
if __name__ == "__main__":
    print("--- 开始访谈数据转换为MaxQDA格式脚本 (CMTC V12 - 最终版，全局变量打印) ---") # 固定打印
    
    # app 和 file_dir 已在脚本顶部通过 try-except from parameters 加载或设置了默认值
    # P_DBUG_... 变量也已在脚本顶部加载

    # --- 在主执行块中先完成数据加载 ---
    print("\n宏观流程: 步骤一：加载所有数据...") # 固定打印
    
    # 从已初始化的 file_dir 获取路径
    # 使用 .get() 并提供明确的备用路径（尽管顶部的try-except应该处理了）
    # 这些键名需要与 parameters.py 中 file_dir 定义的键名一致
    MERGED_JSON_FILEPATH = file_dir.get('inductive_merged_json', f'data_dir/{app}_dir/03_inductive_coding_dir/{app}_inductive_codes.json')
    ORIGINAL_CSV_FILEPATH = file_dir.get('UI', f'data_dir/{app}_dir/00_rawdata_dir/{app}.csv')
    RESPONDENT_ID_COL_NAME_MAIN = "序号" 

    llm_data_map_main, original_interviews_list_main, csv_headers_main = load_data(
        MERGED_JSON_FILEPATH,
        ORIGINAL_CSV_FILEPATH,
        RESPONDENT_ID_COL_NAME_MAIN
    )

    if not (llm_data_map_main and original_interviews_list_main and csv_headers_main):
        print("宏观流程: 步骤一：数据加载失败，程序将退出。") # 固定打印
        exit()
    print("宏观流程: 步骤一：所有数据加载成功！") # 固定打印
    print("-" * 40) # 固定打印

    # --- 后续的文件路径和参数 ---
    MAXQDA_OUTPUT_FILEPATH = file_dir['inductive_maxqda_themecode'] # 指向最终的合并文件
    QUESTIONS_TO_SKIP_CODING_LIST_MAIN = ["序号"]


    print("\n步骤0 (主程序): 检查并创建输出所需目录...") # 固定打印
    output_dir_for_maxqda = os.path.dirname(MAXQDA_OUTPUT_FILEPATH)
    if output_dir_for_maxqda and not os.path.exists(output_dir_for_maxqda):
        os.makedirs(output_dir_for_maxqda); print(f"  已创建目录: {output_dir_for_maxqda}")
    
    # 再次检查关键输入文件是否存在
    if not os.path.exists(MERGED_JSON_FILEPATH):
        print(f"错误: 已合并的LLM JSON文件 '{MERGED_JSON_FILEPATH}' 未找到。程序无法继续。")
        exit()
    if not os.path.exists(ORIGINAL_CSV_FILEPATH):
        print(f"错误: 原始CSV文件 '{ORIGINAL_CSV_FILEPATH}' 未找到。程序无法继续。")
        exit()

    print("-" * 40) # 固定打印
    print("步骤2 (主程序): 开始将数据转换为MaxQDA格式...") # 固定打印
    print(f"  将使用合并JSON: '{MERGED_JSON_FILEPATH}'") # 固定打印
    print(f"  将使用原始CSV: '{ORIGINAL_CSV_FILEPATH}'")   # 固定打印
    print(f"  输出到MaxQDA文件: '{MAXQDA_OUTPUT_FILEPATH}'") # 固定打印
    
    conversion_success = run_maxqda_conversion(
        llm_data_map_main,                 # 传递已加载的数据
        original_interviews_list_main,     # 传递已加载的数据
        csv_headers_main,                  # 传递已加载的数据
        MAXQDA_OUTPUT_FILEPATH,
        RESPONDENT_ID_COL_NAME_MAIN,
        questions_to_skip_coding=QUESTIONS_TO_SKIP_CODING_LIST_MAIN
    )

    if conversion_success:
        print("\n步骤2完成。MaxQDA导入文件生成成功！") # 固定打印
    else:
        print("\n步骤2失败。MaxQDA导入文件生成失败。") # 固定打印

    print("-" * 40) # 固定打印
    print("所有任务结束。") # 固定打印