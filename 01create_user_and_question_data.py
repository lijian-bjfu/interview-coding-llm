import csv
import re
import os
from parameters import file_dir, app

# --- 辅助函数：查找ID列索引 (供格式二使用) ---
def find_respondent_id_column_index(header_list, id_column_name="序号"):
    if not header_list:
        print("错误: 表头列表为空，无法查找ID列。")
        return -1
    try:
        return header_list.index(id_column_name)
    except ValueError:
        print(f"警告: 在表头中未找到指定的ID列 '{id_column_name}'。将默认使用第一列 (索引 0) 作为ID。")
        return 0

# --- 格式一：按被访者组织数据的转换函数 ---
def convert_to_respondent_format(csv_filepath, txt_filepath):
    """
    将CSV格式的用户访谈数据转换为TXT格式 (按被访者组织)。
    问题放在【】中，回答紧跟其后。不同被访者数据用---分隔。
    回答中的多行会合并为一行，并处理多余空白。
    """
    try:
        all_data_rows = []
        header = []
        with open(csv_filepath, 'r', encoding='utf-8-sig') as csvfile:
            reader = csv.reader(csvfile)
            try:
                header = next(reader)
                if not header:
                    print(f"错误 (格式一): CSV文件 {csv_filepath} 的表头为空行。")
                    return False
            except StopIteration:
                print(f"错误 (格式一): CSV文件 {csv_filepath} 为空或无法读取表头。")
                return False
            
            for row in reader:
                if any(field.strip() for field in row):
                    all_data_rows.append(row)

        if not all_data_rows:
            print(f"提示 (格式一): CSV文件 {csv_filepath} 中没有数据行 (在表头之后)。")
            # 即使没有数据行，也可能希望生成一个包含表头（如果适用）的空文件或特定标记的文件
            # 此处我们选择不生成文件或生成空文件，取决于后续写入逻辑

        with open(txt_filepath, 'w', encoding='utf-8') as txtfile:
            total_data_rows = len(all_data_rows)
            for row_index, row_data in enumerate(all_data_rows):
                if row_index > 0:
                    txtfile.write("---\n")

                for col_index, question in enumerate(header):
                    answer_raw = ""
                    if col_index < len(row_data):
                        answer_raw = row_data[col_index]
                    
                    temp_answer = answer_raw.replace('\n', '').replace('\r', '')
                    temp_answer = temp_answer.replace('\\n', '').replace('\\r', '')
                    processed_answer = re.sub(r'\s+', ' ', temp_answer).strip()

                    txtfile.write(f"【{question}】\n")
                    txtfile.write(f"{processed_answer}\n")

                if row_index < total_data_rows - 1: # 在每个被访者数据块后加空行，使得---更突出
                     txtfile.write("\n")


        print(f"格式一：数据已成功按被访者聚合格式导出到: {txt_filepath}")
        return True

    except FileNotFoundError:
        print(f"错误 (格式一): CSV文件 {csv_filepath} 未找到，请检查路径。")
        return False
    except Exception as e:
        print(f"处理过程中发生未预料的错误 (格式一): {e}")
        # import traceback
        # traceback.print_exc()
        return False

# --- 格式二：按问题组织数据的转换函数 ---
def find_respondent_id_column_index(header_list, id_column_name="序号"):
    """
    在表头列表中查找指定ID列的索引。
    """
    if not header_list:
        print(f"错误: 表头列表为空，无法查找ID列 '{id_column_name}'。")
        return -1
    try:
        return header_list.index(id_column_name)
    except ValueError:
        print(f"警告: 在表头中未找到指定的ID列 '{id_column_name}'。将默认使用第一列 (索引 0) 作为ID。")
        return 0

def convert_to_question_format(csv_filepath, txt_filepath, id_column_name="序号"):
    """
    将CSV数据转换为TXT格式 (按问题组织 - 方案B)。
    格式为：
    问题：【问题文本】

    被访者 {ID} 说：
    {回答}

    ...
    同时处理回答文本中多余的空白。
    """
    try:
        all_data_rows = []
        header = []
        # 使用 'utf-8-sig' 来处理可能由Excel等软件保存时添加的BOM (Byte Order Mark)
        with open(csv_filepath, 'r', encoding='utf-8-sig') as csvfile:
            reader = csv.reader(csvfile)
            try:
                header = next(reader) # 获取表头
                if not header: # 处理表头是空行的情况
                    print(f"错误 (方案B格式): CSV文件 {csv_filepath} 的表头为空行。")
                    return False
            except StopIteration: # CSV文件为空或只有BOM
                print(f"错误 (方案B格式): CSV文件 {csv_filepath} 为空或无法读取表头。")
                return False
            
            # 读取所有有效数据行
            for row in reader:
                # 跳过数据区域中的空行（如果一行所有字段都为空或只含空格）
                if any(field.strip() for field in row):
                    all_data_rows.append(row)

        id_col_idx = find_respondent_id_column_index(header, id_column_name)
        if id_col_idx == -1: # 错误信息已在辅助函数中打印
            return False

        with open(txt_filepath, 'w', encoding='utf-8') as txtfile:
            # 遍历表头中的每一个问题 (每一列)
            for q_col_idx, question_text in enumerate(header):
                # 写入问题标题，并增加一个空行
                txtfile.write(f"问题：【{question_text}】\n\n")

                # 对于当前问题，遍历所有被访者 (每一行数据)
                for row_data in all_data_rows:
                    respondent_id_str = "UNKNOWN_ID" # 默认ID
                    if id_col_idx < len(row_data): # 确保行长度足够获取ID列
                        raw_id = row_data[id_col_idx].strip()
                        if raw_id: # 如果ID不是空字符串
                            respondent_id_str = raw_id
                        else:
                            respondent_id_str = "EMPTY_ID" # ID单元格为空
                    else:
                        # 此情况表示行数据比预期的ID列索引还要短
                        # 可以选择记录日志或忽略
                        pass 

                    current_answer_raw = ""
                    if q_col_idx < len(row_data): # 确保行长度足够获取当前问题的答案
                        current_answer_raw = row_data[q_col_idx]
                    
                    # 清理回答文本：移除内部换行符，确保为单行，并处理多余空白
                    temp_answer = current_answer_raw.replace('\n', '').replace('\r', '')
                    temp_answer = temp_answer.replace('\\n', '').replace('\\r', '')
                    processed_answer = re.sub(r'\s+', ' ', temp_answer).strip()

                    # 写入被访者标识和回答
                    txtfile.write(f"被访者 {respondent_id_str} 说：\n")
                    txtfile.write(f"{processed_answer}\n")
                    
                    # 在每个被访者的回答后添加一个空行，以分隔下一个被访者的回答
                    txtfile.write("\n")

                # 在一个问题的所有回答结束后，如果不是最后一个问题，则再添加一个空行
                # 这使得不同【问题】模块之间有两个空行（一个来自上面回答后的空行，一个来自这里）
                # 如果只需要一个空行分隔问题，可以移除这里的 if 语句，或者调整上面回答后的空行
                if q_col_idx < len(header) - 1:
                    txtfile.write("\n") 

        print(f"方案B格式：数据已成功按问题聚合（自然语言格式）导出到: {txt_filepath}")
        return True

    except FileNotFoundError:
        print(f"错误 (方案B格式): CSV文件 {csv_filepath} 未找到，请检查路径。")
        return False
    except Exception as e:
        print(f"处理过程中发生未预料的错误 (方案B格式): {e}")
        # 如果需要更详细的错误追踪，可以取消下面两行的注释
        # import traceback
        # traceback.print_exc()
        return False

# --- 主程序执行 ---
if __name__ == "__main__":
    input_csv_file = file_dir['UI']  # <--- 请替换为您的CSV文件名

    # 为两种格式定义不同的输出文件名
    output_format1_file = file_dir['UI_utxt']
    output_format2_file = file_dir['UI_qtxt']
    
    id_column_name_for_format2 = '序号'  # “格式二”中用于提取被访者ID的列名

    print(f"开始处理文件: {input_csv_file}")
    print("-" * 30)

    success1 = convert_to_respondent_format(input_csv_file, output_format1_file)
    print("-" * 30)
    success2 = convert_to_question_format(input_csv_file, output_format2_file, id_column_name_for_format2)
    print("-" * 30)

    if success1 and success2:
        print("所有转换任务完成！")
    elif success1:
        print("格式一转换完成，但格式二转换失败。")
    elif success2:
        print("格式二转换完成，但格式一转换失败。")
    else:
        print("两个转换任务均失败。请检查错误信息。")