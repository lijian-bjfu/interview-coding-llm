# 项目重构工作要求 (for Codex)

> 本文档是项目重构的完整说明书。请按章节顺序阅读，按"任务清单"章节执行。所有设计决策已锁定，**不要自行偏离**。如遇文档未覆盖的边界情况，**保守处理 + 在代码注释中标注 TODO**，不要自行扩展功能。

---

## 0. 改造目标与核心原则

### 0.1 目标

把当前项目从"用户高度参与文件管理"重构为"用户只关注与 LLM 编码对话，文件全部由脚本自动管理"。

### 0.2 核心原则（按重要性排序）

1. **用户唯一手动接触点是 `_inbox/`**：用户把 LLM 输出的所有产物丢进 `_inbox/`，dispatch 脚本自动归位。用户不需要记任何路径、不需要起任何文件名（命名冲突由浏览器/系统提示，不在脚本职责范围）。
2. **脚本单功能、零配置**：每个脚本只做一件事，无命令行参数（除可选的 `--app` 覆盖外），双击 VSCode 运行 OR 命令行直接执行均可。
3. **脚本编号 = 用户工作流时间线**：研究者按 00→01→02→... 的顺序使用脚本就是一次完整的研究流程。dispatch 脚本穿插在生成脚本之后。
4. **简化目录结构**：data 下每个项目只有 `_inbox/` + 4 个数字编号目录，名字短、层次浅。
5. **临时文件识别只用内容签名（策略 A）**，不靠用户起名、不靠扩展名硬绑（CSV 用列名签名、JSON 用字段签名、TXT 用首行注释）。

### 0.3 技术约束

- Python 3.x，标准库优先；CSV 处理用 `csv` 或 `pandas`（已有依赖延续）
- 所有脚本必须在 VSCode "Run Python File" 双击可执行（即使没有命令行参数也能跑）
- 命令行执行作为可选项支持（用 `argparse` 或 `sys.argv`）
- 所有脚本读取 `parameters.py` 的 `APP_NAME` 作为默认产品名
- 脚本输出全部用中文 print，方便用户阅读

---

## 1. 新目录结构

### 1.1 项目根目录

```
项目根目录/
├── _legacy/                              ← 旧脚本备份（删除已废弃数据，仅保留废弃脚本）
│   ├── 03inductive_create_maxqda.py
│   └── prompts_deductive_coding.txt
├── parameters.py                         ← 保留，含 APP_NAME 全局变量
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
├── prompts/                              ← prompt 模板（脚本读取用）
│   ├── inductive_template.txt
│   ├── summary_template.txt
│   ├── codebook_template.txt
│   └── variable_template.txt
├── data_dir/
│   └── {appname}_dir/                    ← 见 1.2
└── README.md
```

### 1.2 data_dir 下每个项目的目录

```
data_dir/{appname}_dir/
├── _inbox/                               ← 用户唯一接触点，4 类文件混合放
├── 00_rawdata/
│   ├── {appname}.csv                     ← 原始访谈数据（用户提供）
│   ├── {appname}-id.csv                  ← 加内部 ID 后的版本（脚本生成）
│   ├── {appname}-outline.csv             ← 大纲定义（用户提供）
│   └── {appname}_user_var.csv            ← 变量定义（用户提供）
├── 01_preprocessed/
│   ├── {appname}_question.txt            ← 横向：按问题组织
│   ├── {appname}_user.txt                ← 纵向：按用户组织
│   └── {appname}_inductive_merged.json   ← 合并后的归纳编码（06 脚本产出，中间档案）
├── 02_outline/
│   └── {category}/                       ← 大纲分类，每分类一个子目录
│       ├── question/                     ← 该分类的横向数据 + 归纳编码 JSON
│       │   ├── {appname}_question_{category}.txt
│       │   └── inductive_q{NN}.json      ← dispatch 后归位
│       ├── user/                         ← 该分类的纵向数据
│       │   └── {appname}_user_{category}.txt
│       ├── codebook/
│       │   ├── raw_codebook_{category}.csv      ← 06 脚本产出
│       │   └── codebook_{category}.csv          ← 08 dispatch 后归位（LLM 产出）
│       └── recorder/
│           ├── sum_ind_01.txt            ← 对话总结，全局递增编号
│           └── sum_ind_02.txt
└── 03_variables/
    ├── raw/                              ← 10 dispatch 后归位的零散变量 CSV
    │   ├── var_01.csv
    │   └── var_02.csv
    └── user_var.csv                      ← 11 合并后的变量大表
```

**关键点**：
- 用户**永远只在 `_inbox/` 下放文件**，不直接操作其他目录
- 用户**永远只在 `00_rawdata/` 下放原始数据**（产品 csv、outline、变量定义）
- 其他所有目录由脚本自动创建和写入

---

## 2. 文件类型与身份字段规范

### 2.1 进入 `_inbox/` 的 4 类文件

| 类型 | 扩展名 | 内容签名（策略 A） | 身份字段位置 |
|---|---|---|---|
| 归纳编码 JSON | `.json` | 顶层是数组，元素含 `initial_codes` 字段 | 数组每元素含 `category` 字段 |
| 精炼编码本 CSV | `.csv` | 表头第一列是 `Theme` | 第一行注释 `# category=xxx` |
| 对话总结 TXT | `.txt` | 首行以 `# stage=` 开头 | 首行 `# category=xxx, stage=ind` |
| 用户变量 CSV | `.csv` | 表头第一列是 `文件名` | 无需身份字段，全局只有一类 |

### 2.2 归纳编码 JSON 结构

```json
[
  {
    "category": "player_states",
    "question_text": "你最初为什么开始玩这个游戏？",
    "initial_codes": [...],
    "codes": [...],
    "themes": [...]
  }
]
```

**说明**：
- 顶层保持数组（兼容现有 prompt 不大改）
- 每个数组元素加 `category` 字段（侵入性最小）
- 每个题目一个 JSON 文件，数组通常只有 1 个元素，但保留数组结构

### 2.3 精炼编码本 CSV 结构

```
# category=player_states
Theme,Code_Name,Merged_Original_Codes,Total_Original_Frequency,Definition,Application_Rules
玩家体验与心理,自主体验,"[...]",31,"...","..."
...
```

**说明**：
- 第一行为注释行（以 `#` 开头），dispatch 脚本读这行获取 category
- 第二行才是真正表头
- 读 CSV 的脚本要跳过 `#` 开头的行
- LLM 生成时 prompt 会指示它必须以这一行注释开头

### 2.4 对话总结 TXT 结构

```
# category=player_states, stage=ind

【问题焦点的变化过程】
...

【编码结构变化】
...

【编码进程位置】
当前位于：player_states 第 3 题（"你最初为什么开始玩这个游戏？"）

【重大事件】
...
```

**说明**：
- 首行为身份注释（必须）
- 后续四个固定章节，对应总结模板要求（见 5.2）
- `stage=ind` 字段保留（即便目前只有归纳阶段使用），为未来扩展留接口

### 2.5 用户变量 CSV 结构

```
文件名,游戏经验年限,主要游戏类型,...
U001,8,MOBA,...
U002,3,沙盒,...
```

**说明**：
- 第一列必须是 `文件名`（这是 MaxQDA 文件变量导入的硬性要求，对应用户 ID）
- 后续列由用户在 `{appname}_user_var.csv` 变量定义文件中决定
- LLM 输出时一次可能 1 行（标准）或 3-4 行（数据短时合并），dispatch 后落地为 `var_NN.csv`，最终由 11 脚本合并

---

## 3. 脚本清单

每个脚本的格式：**功能 / 输入 / 输出 / 关键行为 / 边界处理**

### 3.0 共通要求

- 所有脚本头部 `from parameters import APP_NAME`
- 所有脚本支持 `--app <name>` 可选参数覆盖默认 APP_NAME
- 所有脚本 print 中文、报错提示明确、对用户友好
- 路径用 `pathlib.Path`，不要拼字符串

### 3.1 `parameters.py`（保留，简化）

仅保留 `APP_NAME = 'D5'` 这一行（或类似）。把当前 parameters.py 里的所有路径生成逻辑**移到 `00_init_project.py`** 里。

### 3.2 `00_init_project.py`

**功能**：初始化项目目录结构，归位用户预先放在根目录的原始文件。

**输入**：
- 用户已在项目根目录放置 `{appname}.csv`、`{appname}-outline.csv`、`{appname}_user_var.csv`（变量定义可选）
- `parameters.py` 的 APP_NAME

**输出**：
- 创建 `data_dir/{appname}_dir/` 完整目录树（含 `_inbox/`, `00_rawdata/`, `01_preprocessed/`, `02_outline/`, `03_variables/raw/`）
- 把根目录的 csv 移动到 `00_rawdata/`
- 生成 `{appname}-id.csv`（加内部 ID 列）

**关键行为**：
- `02_outline/` 下的 category 子目录在这一步**不创建**（因为还没读 outline.csv），留给 01_prepare_data.py 创建
- 如果目录已存在，不报错，跳过创建（幂等）
- 如果根目录找不到 `{appname}.csv`，报错并提示用户

**边界处理**：
- `{appname}_user_var.csv` 不存在时不报错（变量提取是可选功能）
- 如果原始 csv 已经在 00_rawdata/，不重复移动

### 3.3 `01_prepare_data.py`

**功能**：从原始数据生成 LLM 用的 txt 文件，按大纲拆分成各 category 的子文件。

**输入**：
- `00_rawdata/{appname}-id.csv`
- `00_rawdata/{appname}-outline.csv`

**输出**：
- `01_preprocessed/{appname}_question.txt`（横向，所有问题）
- `01_preprocessed/{appname}_user.txt`（纵向，所有用户）
- `02_outline/{category}/`（每个 category 创建子目录树：question/, user/, codebook/, recorder/）
- `02_outline/{category}/question/{appname}_question_{category}.txt`
- `02_outline/{category}/user/{appname}_user_{category}.txt`

**关键行为**：
- outline.csv 三列：问题号、大纲类别、访谈问题文本
- 同一 category 下所有问题数据合到一个 question_{category}.txt 里
- 同一 category 下每个用户的回答合到 user_{category}.txt 里（按用户组织）
- 数据格式延续现有 prompt 文件中的约定：`[ID:X] 回答内容`

**边界处理**：
- 如果某 category 的子目录已存在，不报错
- 如果 outline 中有问题在原始数据中找不到对应列，警告但继续

### 3.4 `02_make_inductive_prompt.py`

**功能**：生成归纳编码用的完整 prompt（角色设定 + 数据 + 输出要求 + 身份字段说明），用户复制即可粘到 LLM 对话窗口。

**输入**：
- `prompts/inductive_template.txt`（模板文件，见 5.1）
- 用户输入：要为哪个题目生成？（命令行参数或运行时交互输入）

**输出**：
- `01_preprocessed/_prompts/inductive_q{NN}_prompt.txt`（输出 + 自动复制到剪贴板，如可用）

**关键行为**：
- 询问用户：想为哪一题生成 prompt？显示 outline.csv 中的题目列表让用户选号
- 拼装 prompt：模板 + 该题目的所有回答数据 + JSON 输出格式（包含 category 字段）
- 把 category 信息硬写进 prompt（让 LLM 在输出 JSON 时填对 category）

**边界处理**：
- 如果用户输入的题号在 outline 里不存在，报错让重新输入
- 如果剪贴板复制失败（环境无 GUI），降级为只写文件，提示用户手动打开

### 3.5 `03_dispatch_inductive.py`

**功能**：扫描 `_inbox/`，识别归纳编码 JSON，自动归位。

**输入**：
- `_inbox/` 下所有 `.json` 文件

**输出**：
- 符合签名的 JSON 移动到 `02_outline/{category}/question/inductive_q{NN}.json`
- 不符合签名的 JSON 留在 inbox，print 警告

**关键行为**：
- 识别签名：JSON 顶层是数组 + 数组元素含 `initial_codes` 字段
- 从数组元素读 `category` 字段决定归位的 category 目录
- 题号 NN 怎么定？读 JSON 的 `question_text`，反查 outline.csv 找对应问题号；如果反查不到，按 inbox 中此 category 已归位文件数 +1 编号
- 题号用两位数（q03、q15）

**边界处理**：
- 同一题号文件已存在：覆盖 + 警告（用户应该明确知道自己在重做某题）
- JSON 解析失败：留在 inbox，报错指明原因
- 找不到 category 字段：留在 inbox，报错

### 3.6 `04_make_summary_prompt.py`

**功能**：生成"让 LLM 总结当前对话"的提示词。用户在归纳编码对话进行到某个节点时，复制这段 prompt 让 LLM 输出阶段性总结。

**输入**：
- `prompts/summary_template.txt`

**输出**：
- 直接 print 到终端 + 写入 `01_preprocessed/_prompts/summary_prompt.txt` + 自动复制剪贴板

**关键行为**：
- 这个 prompt 不需要拼接数据，是一段纯指令性 prompt（让 LLM 按固定模板总结自己刚才的对话历史）
- 模板要求 LLM 生成的总结**首行必须包含 `# category=xxx, stage=ind`**

**边界处理**：无（极简脚本）

### 3.7 `05_dispatch_summary.py`

**功能**：扫描 `_inbox/`，识别对话总结 TXT，归位。

**输入**：
- `_inbox/` 下所有 `.txt` 文件

**输出**：
- 符合签名的 TXT 移动到 `02_outline/{category}/recorder/sum_{stage}_{NN}.txt`
- NN 是全局递增编号

**关键行为**：
- 识别签名：首行以 `# stage=` 开头（同时含 category 字段）
- 解析首行获取 category 和 stage
- NN 编号怎么算：扫描所有 category 的 recorder/ 下已有的 sum_{stage}_*.txt，取最大 NN +1（全局递增，跨 category）
- 文件名：`sum_ind_01.txt`、`sum_ind_02.txt`...

**边界处理**：
- 首行解析失败：留在 inbox，报错
- category 在 02_outline/ 下不存在：报错（说明 outline 没这个分类，用户拼错了）

### 3.8 `06_create_raw_codebook.py`

**功能**：合并所有归纳编码 JSON + 生成各 category 的 raw_codebook（合并原 06+07）。

**输入**：
- `02_outline/{category}/question/inductive_q*.json`（所有 category 所有题）

**输出**：
- `01_preprocessed/{appname}_inductive_merged.json`（合并大档案）
- `02_outline/{category}/codebook/raw_codebook_{category}.csv`（每 category 一份）

**关键行为**：
- 扫描所有 category 下的 inductive_q*.json，按 question_id 排序合并
- 生成 raw_codebook 的列：`code_name`, `definition`, `theme`, `source_question`, `frequency_in_question`, `representative_quotes`
  - 这些字段从 JSON 的 `initial_codes` + `codes` + `themes` 整合
  - 同一 code_name 在同 category 下出现多次的合并 frequency 计数
- raw_codebook 不加 `# category=xxx` 注释行（这是程序产物，不进 inbox 流程，无需身份字段）

**边界处理**：
- 某 category 下没有任何 JSON：跳过该 category，警告
- JSON 缺字段：尽力解析，缺失字段填默认值

### 3.9 `07_make_codebook_prompt.py`

**功能**：生成精炼编码本用的 prompt（整合 raw_codebook + 模板）。

**输入**：
- `prompts/codebook_template.txt`
- 用户输入：要为哪个 category 生成？

**输出**：
- `01_preprocessed/_prompts/codebook_{category}_prompt.txt` + 复制剪贴板

**关键行为**：
- 询问用户选 category（列出所有有 raw_codebook 的 category）
- 拼装：模板 + raw_codebook_{category}.csv 的内容 + 输出格式要求（包含首行 `# category=xxx`）
- 提示词必须明确告诉 LLM：输出的 CSV 第一行必须是 `# category={category}` 注释，第二行开始才是表头

**边界处理**：
- 用户选的 category 没有 raw_codebook：报错让先跑 06

### 3.10 `08_dispatch_codebook.py`

**功能**：扫描 `_inbox/`，识别精炼编码本 CSV，归位。

**输入**：
- `_inbox/` 下所有 `.csv` 文件

**输出**：
- 符合签名的 CSV 移动到 `02_outline/{category}/codebook/codebook_{category}.csv`

**关键行为**：
- 识别签名：CSV 第一行是 `# category=xxx` + 第二行表头第一列是 `Theme`
- 从首行注释解析 category
- **不去重、直接覆盖**：如果该 category 已有 codebook_{category}.csv，覆盖（用户在精炼阶段一次对话产出一份完整编码本，重做就该覆盖）

**边界处理**：
- 首行不是 `#` 开头：留在 inbox，报错（提示用户检查 LLM 输出）
- 表头第一列不是 Theme：可能是用户变量 CSV，跳过不处理

### 3.11 `09_make_variable_prompt.py`

**功能**：生成变量提取用的 prompt（整合用户的访谈数据 + 变量定义）。

**输入**：
- `prompts/variable_template.txt`
- `00_rawdata/{appname}_user_var.csv`（变量定义）
- `01_preprocessed/{appname}_user.txt`（按用户组织的纵向数据）
- 用户输入：要为哪些用户 ID 生成？（多选，标准 1 个，数据短时 3-4 个）

**输出**：
- `01_preprocessed/_prompts/variable_u{IDs}_prompt.txt` + 复制剪贴板

**关键行为**：
- 询问用户选 ID（输入逗号分隔的 ID 列表）
- 把 user_var.csv 的变量定义转成 prompt 的"提取要求"部分
- 把指定 ID 的访谈数据从 user.txt 中提取出来嵌入 prompt
- 提示词要求 LLM 输出 CSV，**第一列必须是 `文件名`**，列名严格按变量定义文件中的"变量名"列

**边界处理**：
- 变量定义文件不存在：报错提示用户先在 00_rawdata/ 下放
- 用户输入的 ID 不存在：报错

### 3.12 `10_dispatch_variables.py`

**功能**：扫描 `_inbox/`，识别用户变量 CSV，归位。

**输入**：
- `_inbox/` 下所有 `.csv` 文件

**输出**：
- 符合签名的 CSV 移动到 `03_variables/raw/var_{NN}.csv`

**关键行为**：
- 识别签名：CSV 表头第一列是 `文件名`
- NN 编号：扫描 03_variables/raw/ 已有的 var_*.csv，取最大 NN +1
- **不需要 category，因为变量是受访者级别的**

**边界处理**：
- 表头不符：留在 inbox，跳过

### 3.13 `11_merge_variables.py`

**功能**：合并 03_variables/raw/ 下所有 var_NN.csv 为最终的 user_var.csv。

**输入**：
- `03_variables/raw/var_*.csv`

**输出**：
- `03_variables/user_var.csv`

**关键行为**：
- 按文件名顺序读取所有 var_*.csv
- 合并所有行（每个文件可能 1-N 行）
- 列对齐：以变量定义文件 `00_rawdata/{appname}_user_var.csv` 中的变量列表为准

**边界处理**：
- 某 var_NN.csv 缺列：填空值，警告
- 某 var_NN.csv 多列：丢弃多余列，警告
- 出现重复"文件名"（同 ID 多行）：报错提示用户检查（按用户决策这种情况不该出现）

### 3.14 `status.py`

**功能**：扫描项目当前状态，print 进度报告。零状态文件，每次运行重新扫描。

**输出**（print 到终端）：

```
=== {appname} 项目状态 ===

📂 原始数据
  ✓ {appname}.csv (33 行)
  ✓ {appname}-outline.csv (15 题)
  ✓ {appname}_user_var.csv (定义了 8 个变量)

📂 归纳编码进度
  player_states:    [████████░░] 8/10 题完成
    未完成: q07, q09
  player_experiences: [██████████] 5/5 题完成
  creativity_features: [░░░░░░░░░░] 0/12 题完成
  
📂 编码本
  player_states:       raw ✓ | refined ✗
  player_experiences:  raw ✓ | refined ✓
  creativity_features: raw ✗ | refined ✗
  
📂 对话总结
  player_states:       3 份
  player_experiences:  1 份

📂 用户变量
  raw 文件: 12/33
  user_var.csv: 未生成

📂 _inbox/ 待处理
  3 个文件:
    - inductive_codes.json (归纳编码？建议跑 03_dispatch_inductive.py)
    - codebook_v2.csv (精炼编码本？建议跑 08_dispatch_codebook.py)
    - 一个无法识别的文件: notes.txt
```

**关键行为**：
- 完全只读，不写任何文件
- 对 inbox 里的文件做识别预判，给出"建议跑哪个 dispatch"提示

---

## 4. dispatch 脚本统一规则表

| 脚本 | 处理扩展名 | 内容签名 | 身份字段位置 | 归位目标 |
|---|---|---|---|---|
| 03_dispatch_inductive | .json | 顶层数组 + 元素含 `initial_codes` | 数组元素的 `category` 字段 | `02_outline/{category}/question/inductive_q{NN}.json` |
| 05_dispatch_summary | .txt | 首行以 `# stage=` 开头 | 首行 `# category=xxx, stage=ind` | `02_outline/{category}/recorder/sum_{stage}_{NN}.txt` |
| 08_dispatch_codebook | .csv | 首行 `# category=` + 第二行表头第一列 `Theme` | 首行 `# category=xxx` | `02_outline/{category}/codebook/codebook_{category}.csv` |
| 10_dispatch_variables | .csv | 表头第一列 `文件名` | 无（不需 category） | `03_variables/raw/var_{NN}.csv` |

**dispatch 脚本通用行为约定**：
- 扫描 `_inbox/` 目录，逐文件判断
- 不符合本脚本签名的文件**留在 inbox**，不报错也不警告（其他 dispatch 脚本会处理）
- 每个脚本结束时 print 处理结果：成功归位几个、跳过几个、错误几个
- 如果 inbox 中有无法被任何 dispatch 识别的"残留"文件，由 status.py 统一报告

---

## 5. Prompt 模板规格

> 这一节定义 4 个 prompt 模板的内容要求。Codex 需要创建这 4 个模板文件放在 `prompts/` 下。模板内容可以参考现有的 `prompts_inductive_coding-simple.txt` 和 `prompts_create_codebook-simple.txt`，但需要按下述要求修改和精简。

### 5.1 `prompts/inductive_template.txt`

**用途**：归纳编码每题用一次。

**模板包含的章节**：
1. 角色设定（专业定性编码专家）
2. 任务说明（开放式编码 + 主题提取）
3. 编码要求：
   - **明确要求 LLM 在编码前先做"意义单元切分"**（meaning unit segmentation），把每条回答切分为表达独立想法的最小文本段，再对每个单元独立判断是否编码
   - 每个编码至少 3 个引文（统一阈值，删掉旧文件中 5 个引文的不一致）
   - 同一引文可被多编码引用
   - **命名约束**：创建新编码前先扫描已生成编码，语义重叠 60% 以上时复用已有编码名（避免 synonym fragmentation）
4. 输出格式：
   - **删除 quote_range 字段**（之前讨论过的索引位置不可靠问题）
   - JSON 顶层数组，每元素含 `category`, `question_text`, `initial_codes`, `codes`, `themes`
5. 模板末尾留置位 `{{CATEGORY}}` 和 `{{QUESTION_DATA}}`，由 02 脚本拼装时填入

**模板拼装规则**（02 脚本读模板后做的事）：
- 把 `{{CATEGORY}}` 替换为该题所在的大纲分类名
- 把 `{{QUESTION_DATA}}` 替换为该题的访谈问题 + 所有用户回答数据

### 5.2 `prompts/summary_template.txt`

**用途**：让 LLM 把当前对话总结成一份结构化记录。

**模板内容**（这是发给 LLM 的指令，不需要拼装数据）：

```
请你按照以下固定模板，对我们当前对话进行总结。

总结目的：将本段对话浓缩为可作为后续对话起点的结构化记录，避免依赖累积式长上下文。

【输出格式硬性要求】
1. 总结输出的第一行必须是这样的注释行（**不要修改格式**）：
   # category={当前讨论涉及的大纲分类名}, stage=ind
   
2. 注释行后必须包含以下四个章节，章节标题严格使用方括号格式：

【问题焦点的变化过程】
- 记录研究问题的演化轨迹（从模糊→聚焦→转向→回归...）
- 每次焦点切换的契机：用户明确表达了原因则记录原因，未表达则标注"用户要求"

【编码结构变化】
- 起点：本段对话开始时（或上一轮总结结束时）的编码状态
- 终点：本段对话当前的编码状态
- 仅记录起点和终点之间发生变化的编码（修改/合并/删除/编码升为主题/概念边界变化等）
- 当前确定的编码列表中，标注每个编码的来源（"修改自XX"或"新增"）

【编码进程位置】
- 当前编到哪个大纲分类、第几号题
- 不确定时填 N/A

【重大事件】
- 本轮值得记下的事件（围绕某编码的多轮讨论、某引文归属的详细辩论、方法论决策等）

【收尾】
请直接输出总结，不要前导寒暄。category 字段请基于对话内容判断后填写。
```

### 5.3 `prompts/codebook_template.txt`

**用途**：精炼编码本（从 raw_codebook 重构为带定义+规则的方法论编码本）。

**模板包含的章节**：
1. 角色设定 + 任务目标（参考现有 prompts_create_codebook-simple.txt 内容）
2. 核心概念说明（聚焦研究主题、自下而上重构、跨编码语义复用）
3. 指导原则（语义互斥、信息全覆盖、操作明确）
4. 引导过程的描述（宏观理解→聚焦主题→深入挖掘→确认结果→下一主题→优化→完善）
5. 输出格式硬性要求：
   - **第一行必须是 `# category={{CATEGORY}}` 注释行**
   - 第二行起为 CSV 表头：`Theme,Code_Name,Merged_Original_Codes,Total_Original_Frequency,Definition,Application_Rules`
   - **Application_Rules 字段必须包含三部分**：纳入标准、排除标准、边界案例（处理两个编码意义重叠时的判定）
6. 留置位：`{{CATEGORY}}`、`{{RAW_CODEBOOK_CSV}}`

### 5.4 `prompts/variable_template.txt`

**用途**：从访谈纵向数据中提取受访者级变量。

**模板包含的章节**：
1. 角色设定（用户研究分析师）
2. 任务：从给定访谈数据中识别指定变量的值
3. 变量提取规则（由 09 脚本根据 `{appname}_user_var.csv` 动态生成）：
   - 文本型：直接提取
   - 数字型：基于范围给定具体数值，无明确提及填 "未提及"
4. 输出格式硬性要求：
   - CSV 格式
   - **第一列列名必须是 `文件名`**，对应用户 ID
   - 后续列严格按变量定义文件中的"变量名"列顺序
   - 一个用户一行
5. 留置位：`{{VARIABLE_DEFINITIONS}}`、`{{USER_INTERVIEW_DATA}}`

---

## 6. Legacy 处理

### 6.1 移到 `_legacy/` 的文件（项目根目录下创建 `_legacy/`）

- `03inductive_create_maxqda.py`（旧脚本）
- `prompts_deductive_coding.txt`（旧 prompt 文件）
- 任何当前项目根目录下与 MaxQDA 结构化文本相关的脚本和文档

### 6.2 直接物理删除

- `data_dir/{appname}_dir/` 下任何已生成的旧产物（如 `*_maxqda_themecode.txt`、`*_maxqda_opencode.txt`、`*_inductive_metadata.*`）
- 旧的 `03_inductive_coding_dir/`、`04_deductive_coding_dir/` 整个目录（如存在）
- 旧的 `02_interview_outline_dir/`（重命名为 `02_outline/`，旧的删除）

### 6.3 简化命名

- `02_interview_outline_dir/` → `02_outline/`
- `question_data_dir/` → `question/`
- `user_data_dir/` → `user/`
- `codebook_data_dir/` → `codebook/`
- `meta_data_dir/` → 删除（不再需要）
- `00_rawdata_dir/` → `00_rawdata/`
- `01_preprocessed_for_llm_dir/` → `01_preprocessed/`

---

## 7. 验收清单

Codex 改完后请按以下清单自查并报告：

### 7.1 目录结构验收

- [ ] 项目根目录下 11 个数字编号脚本 + status.py + parameters.py + prompts/ + _legacy/ + data_dir/ + README.md
- [ ] data_dir/{appname}_dir/ 下只有 `_inbox/`, `00_rawdata/`, `01_preprocessed/`, `02_outline/`, `03_variables/` 五个目录
- [ ] 没有任何带 "_dir" 后缀的子目录（统一去掉旧命名）
- [ ] `_legacy/` 在项目根目录，不在 data_dir 下

### 7.2 脚本独立性验收

- [ ] 每个脚本可在 VSCode 中"Run Python File"双击运行
- [ ] 每个脚本可在命令行 `python 0X_xxx.py` 直接运行
- [ ] 每个脚本最多有 1 个可选的命令行参数 `--app`，其他配置全部从 parameters.py 读取
- [ ] 没有需要用户编辑配置文件才能跑的脚本

### 7.3 dispatch 行为验收

写一个简单测试：手动构造 4 类文件（一个归纳 JSON、一个精炼 codebook CSV、一个总结 TXT、一个变量 CSV）放到 inbox，依次跑 4 个 dispatch 脚本，确认：

- [ ] 每个 dispatch 脚本只处理自己负责的文件类型，其他文件留在 inbox
- [ ] 归位路径符合本文档第 4 节表格
- [ ] 序列号编号正确（sum_ind_NN, var_NN 全局递增）

### 7.4 Prompt 模板验收

- [ ] 4 个模板文件存在于 `prompts/` 下
- [ ] 02、04、07、09 脚本能读取对应模板并完成拼装
- [ ] 拼装后的 prompt 包含必须的身份字段说明（让 LLM 输出时带 category 等）

### 7.5 Status 验收

- [ ] status.py 能正确报告进度，不写任何文件
- [ ] 对 inbox 中的文件能给出"建议跑哪个 dispatch"提示

---

## 8. 不在本次改造范围内的事项（不要做）

为了避免 Codex 自行扩展，明确以下**不要做**：

- **不要**为编码做信度（intercoder reliability）相关功能
- **不要**自动调用 LLM API（本项目坚持人工对话窗口模式）
- **不要**为饱和度做曲线绘图（status 文字报告完成度即可，不画图）
- **不要**做项目级 git hook、自动备份等基础设施
- **不要**做跨项目的文件同步、模板复用机制
- **不要**改 prompts/ 模板的核心方法论内容（尤其是编码原则、输出格式），只在指定位置加身份字段相关说明
- **不要**做精炼编码本阶段的对话总结功能（已明确砍掉）

---

## 9. 改造执行顺序建议

1. 先备份当前项目（git commit）
2. 创建 `_legacy/`，移走废弃脚本
3. 删除 data_dir 下旧产物和旧目录
4. 创建新 `prompts/` 模板（4 个文件）
5. 重写 `parameters.py`（精简为常量）
6. 实现 `00_init_project.py`
7. 实现 `01_prepare_data.py`（生成新目录结构）
8. 实现 4 个 dispatch 脚本（03/05/08/10）和 4 个 make_prompt 脚本（02/04/07/09）
9. 实现 06、11 合并脚本
10. 实现 status.py
11. 写新 README.md（替换旧的，参考第 1 节目录结构 + 用户工作流时间线说明）
12. 用一个测试项目跑通端到端流程，验收

---

## 10. 报告要求

完成后请在 PR/commit message 中说明：

- 哪些文件新增、哪些文件删除、哪些文件移到 `_legacy/`
- 第 7 节验收清单的勾选情况
- 任何 TODO 或暂未实现的边界情况
- 用户开始用新流程前需要知道的注意事项