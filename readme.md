# interview-coding-llm

> 与 LLM 协作做深度访谈定性编码的最小化脚手架。
> 用户只关注与 LLM 在对话窗口中编码，文件全部由脚本自动管理。

---

## 0. 设计哲学

- **用户唯一手动接触点是 `_inbox/`**：把 LLM 生成的产物（JSON / CSV / TXT）一律丢进去，dispatch 脚本会按文件内容签名自动归位。
- **脚本编号 = 工作流时间线**：按 `00 → 01 → 02 → …` 顺序使用脚本就是一次完整的研究流程。dispatch 脚本穿插在 prompt 生成脚本之后。
- **零配置**：每个脚本只做一件事，无强制命令行参数。VSCode 中"Run Python File"双击即可，命令行 `python 0X_xxx.py` 也可。
- **单一全局变量**：`parameters.py` 只暴露 `APP_NAME`，每个脚本支持 `--app <name>` 临时覆盖。

---

## 1. 目录结构

### 项目根目录

```
项目根目录/
├── parameters.py                ← 仅含 APP_NAME = '<产品名>'
├── 00_init_project.py
├── 01_prepare_data.py
├── 02_make_inductive_prompt.py
├── 03_dispatch_inductive.py
├── 04_make_summary_prompt.py
├── 05_dispatch_summary.py
├── 06_create_raw_codebook.py
├── 07_make_codebook_prompt.py
├── 08_dispatch_codebook.py
├── 09_make_variable_prompt.py
├── 10_dispatch_variables.py
├── 11_merge_variables.py
├── status.py
├── prompts/
│   ├── inductive_template.txt
│   ├── summary_template.txt
│   ├── codebook_template.txt
│   └── variable_template.txt
├── _legacy/                     ← 旧版脚本与 prompt 备份（参考用）
└── data_dir/
    └── {appname}_dir/           ← 每个产品一个工作目录（见下）
```

### 单个产品的工作目录 `data_dir/{appname}_dir/`

```
{appname}_dir/
├── _inbox/                      ← 用户唯一接触点；4 类文件混合放
├── 00_rawdata/
│   ├── {appname}.csv                # 原始访谈数据（用户提供）
│   ├── {appname}-id.csv             # 加内部 ID 后的版本（脚本生成）
│   ├── {appname}-outline.csv        # 大纲定义（用户提供）
│   └── {appname}_user_var.csv       # 变量定义（用户提供，可选）
├── 01_preprocessed/
│   ├── {appname}_question.txt       # 横向：按问题组织
│   ├── {appname}_user.txt           # 纵向：按用户组织
│   ├── {appname}_inductive_merged.json  # 06 合并后的归纳编码
│   └── _prompts/                    # 各脚本生成的 prompt 文本（仅供参考）
├── 02_outline/
│   └── {category}/                  # 大纲分类，每分类一个子目录
│       ├── question/                # 该分类的横向数据 + 归纳编码 JSON
│       │   ├── {appname}_question_{category}.txt
│       │   └── inductive_q{NN}.json
│       ├── user/
│       │   └── {appname}_user_{category}.txt
│       ├── codebook/
│       │   ├── raw_codebook_{category}.csv
│       │   └── codebook_{category}.csv
│       └── recorder/
│           └── sum_ind_{NN}.txt     # 对话总结，全局递增编号
└── 03_variables/
    ├── raw/
    │   └── var_{NN}.csv             # 10_dispatch 后归位的零散变量 CSV
    └── user_var.csv                 # 11 合并后的变量大表
```

**关键约定**：

- 用户**永远只把 LLM 产物丢进 `_inbox/`**，不直接操作其他目录。
- 用户**永远只在 `00_rawdata/` 下放原始数据**（实际操作中可放在项目根目录由 `00_init_project.py` 自动归位）。
- 其他所有目录由脚本自动创建和写入。

---

## 2. 用户工作流（按脚本编号顺序）

### 准备阶段

1. 修改根目录 `parameters.py` 里的 `APP_NAME = '<你的产品名>'`。
2. 把 `<APP>.csv`、`<APP>-outline.csv`、`<APP>_user_var.csv`（可选）放在项目根目录。
3. 运行 `00_init_project.py` —— 创建目录树，把 csv 归位到 `00_rawdata/`，生成内部 ID 文件。
4. 运行 `01_prepare_data.py` —— 生成横/纵向 txt 与各分类下的子文件。

### 归纳编码循环（每题一次）

5. 运行 `02_make_inductive_prompt.py`，按提示选题号 → prompt 自动复制到剪贴板。
6. 在你常用的 LLM 对话窗口粘贴该 prompt，按对话往复直到本题编码完成。
7. 让 LLM 输出最终 JSON，把 JSON 文件保存到 `_inbox/`（文件名随意）。
8. 运行 `03_dispatch_inductive.py` —— JSON 自动归位到 `02_outline/{category}/question/inductive_q{NN}.json`。

### 阶段性总结（按需使用）

9. 在归纳对话进行到节点时，运行 `04_make_summary_prompt.py` —— 复制总结指令给 LLM。
10. LLM 输出总结 .txt（首行必须包含 `# category=xxx, stage=ind`），保存到 `_inbox/`。
11. 运行 `05_dispatch_summary.py` —— TXT 自动归位到 `02_outline/{category}/recorder/sum_ind_{NN}.txt`。

### 编码本精炼

12. 当某分类所有题归纳完成后，运行 `06_create_raw_codebook.py` —— 合并所有 JSON、生成各分类 raw_codebook.csv。
13. 运行 `07_make_codebook_prompt.py`，按提示选 category → prompt 自动复制。
14. LLM 与你协作产出精炼编码本 CSV（首行必须是 `# category=xxx`），保存到 `_inbox/`。
15. 运行 `08_dispatch_codebook.py` —— CSV 自动归位到 `02_outline/{category}/codebook/codebook_{category}.csv`。

### 受访者变量提取

16. 运行 `09_make_variable_prompt.py`，按提示输入 ID 列表（标准 1 个，数据短时 3-4 个）→ prompt 自动复制。
17. LLM 输出变量 CSV（表头第一列必须是 `文件名`），保存到 `_inbox/`。
18. 运行 `10_dispatch_variables.py` —— CSV 自动归位到 `03_variables/raw/var_{NN}.csv`。
19. 全部受访者处理完后，运行 `11_merge_variables.py` —— 合并为最终 `03_variables/user_var.csv`。

### 任意时刻

- 运行 `status.py` —— 查看项目当前进度报告，并对 `_inbox/` 中的文件给出"建议跑哪个 dispatch"提示。

---

## 3. dispatch 脚本统一规则表

| 脚本 | 处理扩展名 | 内容签名 | 身份字段 | 归位目标 |
|---|---|---|---|---|
| 03_dispatch_inductive | `.json` | 顶层数组 + 元素含 `initial_codes` | 元素的 `category` | `02_outline/{category}/question/inductive_q{NN}.json` |
| 05_dispatch_summary | `.txt` | 首行以 `# stage=` 开头 | 首行 `# category=xxx, stage=ind` | `02_outline/{category}/recorder/sum_{stage}_{NN}.txt` |
| 08_dispatch_codebook | `.csv` | 首行 `# category=` + 第二行表头第一列 `Theme` | 首行 `# category=xxx` | `02_outline/{category}/codebook/codebook_{category}.csv` |
| 10_dispatch_variables | `.csv` | 表头第一列 `文件名` | 无 | `03_variables/raw/var_{NN}.csv` |

dispatch 脚本通用行为：

- 不符合本脚本签名的文件**留在 inbox**，不报错（其他 dispatch 会处理）。
- 每个脚本结束时 print 处理结果汇总（成功/跳过/错误）。
- 残留无法被任何 dispatch 识别的文件由 `status.py` 报告。

---

## 4. Prompt 模板说明

`prompts/` 下 4 个模板由各 `make_prompt` 脚本读入，注释行（`#` 开头）会被自动剔除，模板正文中的 `{{XXX}}` 占位符会被脚本替换：

| 模板 | 占位符 |
|---|---|
| `inductive_template.txt` | `{{CATEGORY}}`, `{{QUESTION_DATA}}` |
| `summary_template.txt` | （无） |
| `codebook_template.txt` | `{{CATEGORY}}`, `{{RAW_CODEBOOK_CSV}}` |
| `variable_template.txt` | `{{VARIABLE_DEFINITIONS}}`, `{{VARIABLE_COLUMNS}}`, `{{USER_INTERVIEW_DATA}}` |

模板内核心方法论内容（编码原则、输出格式硬性要求等）请勿轻易改动；仅可在指定占位符处由脚本动态填入研究内容。

---

## 5. 切换不同产品

```
# 方式 A：修改 parameters.py 里的 APP_NAME
APP_NAME = '另一个产品'

# 方式 B：临时使用命令行覆盖
python 02_make_inductive_prompt.py --app 另一个产品
```

`--app` 是所有脚本共有的可选参数。

---

## 6. 旧版本去哪了

老版本脚本与 prompt 已移到 `_legacy/`，仅作历史参考。不再维护，新流程不依赖它们。
