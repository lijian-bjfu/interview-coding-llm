# interview-coding-llm

> 与 LLM 协作做深度访谈定性编码的最小化脚手架。
> **研究者全程主导**编码节奏与方向；脚本只负责把数据预处理好、把 LLM
> 产物自动归档。LLM 在两份方法论模板（归纳 / 编码本）的约束下，按
> 你下达的"任务口令"逐步推进，每一步都停下来等你审阅。

---

## 0. 设计哲学

- **研究者是总设计师**：所有方向性判断、主题聚焦、边界裁定、版本
  存档都由你决定；LLM 只负责按工艺执行 + 在每个关键节点停下报告。
- **协作通过"任务口令"流转**：你给「编码预览」LLM 才会出预览；
  你给「正式输出」LLM 才会出最终文件；这套口令在两份模板中**完全
  一致**（见第 2 节）。
- **用户唯一手动接触点是 `_inbox/`**：把 LLM 生成的产物（JSON / CSV /
  TXT）一律丢进去，dispatch 脚本会按文件内容签名自动归位。
- **脚本编号 = 工作流时间线**：按 `00 → 01 → 02 → …` 顺序使用脚本就是
  一次完整的研究流程。dispatch 脚本穿插在 prompt 生成脚本之后。
- **零配置**：每个脚本只做一件事，无强制命令行参数。VSCode 中
  "Run Python File" 双击即可，命令行 `python 0X_xxx.py` 也可。
- **单一全局变量**：`parameters.py` 只暴露 `APP_NAME`，每个脚本支持
  `--app <name>` 临时覆盖。

---

## 1. 协作哲学：你的工作权限

这套工具的核心不是 prompt 模板，而是**"研究者主导 + LLM 辅助"的
协作权限分工**。在你与 LLM 的每一次对话中：

| 角色 | 权限 / 职责 |
|---|---|
| **研究者（你）** | 战略导航（设研究目标 / 聚焦主题）、智慧核心（注入理论视角与意义诠释）、质量守门（审计编码本完备性）、节奏掌控（决定推进 / 深化 / 存档）、最终裁决 |
| **LLM** | 检索引擎（语义扫描）、信息处理器（结构化分类归纳）、灵感催化剂（提供多视角参考）、高效文书（按你的决策生成结构化文档与日志） |

LLM **不会**自作主张推进流程。它默认在每个步骤完成后停下来，等
你下达下一个口令。这意味着：编码质量的天花板由你决定，不由 LLM
决定；LLM 不会"一口气把活干完然后给你一份你只能照单全收的结果"。

**"对话优于指令"**：你可以反复追问、引导 LLM 重新审视、要求它
补全规则、给出未决项的边界判断——这都是协作流程的一部分，不是
"出错重来"。

---

## 2. 任务口令体系（两份模板共享）

不论是归纳编码（`02_make_inductive_prompt.py` 生成的 prompt），还是
编码本精炼（`07_make_codebook_prompt.py` 生成的 prompt），LLM 都会
等你下达以下口令才推进。**口令由你直接在对话窗口里打出来**——
比如直接发"编码预览"或"请进入编码预览阶段"。

| 口令 | 你想要什么 | LLM 的反应 |
|---|---|---|
| **`阅览报告`** | 让 LLM 通读材料后给你一份概览 + 提出方向性问题 | 输出阅览报告，**不开始编码**，停下等你回应 |
| **`编码预览`** | 让 LLM 内部完整跑一遍编码工艺，但**只展示预览** | 在对话窗口里输出预览（带表格、未决项、边界提示），停下等你审阅 |
| **`深度探索`** | 你对当前预览不满意，或想换一个主题 / 在主题内深挖 | 抛弃当前预览，回到「阅览报告」或「编码预览」阶段重做 |
| **`正式输出`** | 你已经在所有关键点上跟 LLM 对齐，要最终交付物 | 生成最终的 JSON（归纳阶段）或 CSV（编码本阶段） |
| **`编码日志`** | 你要把当前编码本的内容、思路、规范存档（**仅归纳阶段**） | 输出可拷贝粘贴的 Markdown 编码日志 |

> 编码本阶段不提供「编码日志」口令——按 refactor.md 的明确决策，
> 精炼阶段不再做对话总结存档。

### 协作节奏的典型样貌

下面是一次"归纳编码某一题"的对话节奏示例（以你下达的口令为
锚点）：

```
研究者：[复制粘贴 02_make_inductive_prompt.py 生成的 prompt]
LLM   ：（自动进入步骤 1）阅览报告 + 方向性问题
研究者：聚焦在 XX 主题，注意把 Y 类回答归到一起。请编码预览。
LLM   ：编码预览（表格 + 未决项 + 边界提示）
研究者：编码 A 太粗，拆成 A1/A2；评论 U023 应归 B 不是 A。请深度探索。
LLM   ：（按要求重做）新一轮编码预览
研究者：可以了。正式输出。
LLM   ：[完整 JSON]
研究者：编码日志。
LLM   ：[Markdown 格式的当前编码本快照]
```

编码本精炼的节奏类似，但循环可能更多——通常你会在每个聚焦主题
（社交、成就感、创造性 ……）上各跑一次"阅览报告 → 编码预览 →
深度探索（按需）"，等所有主题都闭环后再下「正式输出」。

---

## 3. 目录结构

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
- 用户**永远只在 `00_rawdata/` 下放原始数据**（实际操作中可放在项目
  根目录由 `00_init_project.py` 自动归位）。
- 其他所有目录由脚本自动创建和写入。

---

## 4. 项目执行流程（按脚本编号顺序）

### 准备阶段

1. 修改根目录 `parameters.py` 里的 `APP_NAME = '<你的产品名>'`。
2. 把 `<APP>.csv`、`<APP>-outline.csv`、`<APP>_user_var.csv`（可选）
   放在项目根目录。
3. 运行 `00_init_project.py` —— 创建目录树，把 csv 归位到
   `00_rawdata/`，生成内部 ID 文件。
4. 运行 `01_prepare_data.py` —— 生成横/纵向 txt 与各分类下的子文件。

### 归纳编码循环（每题一次）

5. 运行 `02_make_inductive_prompt.py`，按提示选题号 → prompt 自动复制
   到剪贴板。
6. 把 prompt 粘贴到 LLM 对话窗口。LLM 进入**步骤 1（阅览报告）**自动
   输出概览 + 方向性问题，停下等你回应。
7. 你与 LLM 按第 2 节的口令体系来回推进：
   - 「编码预览」→ 看预览
   - 「深度探索」→ 让 LLM 重新走一轮
   - 「正式输出」→ LLM 输出完整 JSON
   - 「编码日志」→ LLM 输出可存档的 Markdown 快照（按需）
8. 把 LLM 输出的 JSON 文件保存到 `_inbox/`（文件名随意）。
9. 运行 `03_dispatch_inductive.py` —— JSON 自动归位到
   `02_outline/{category}/question/inductive_q{NN}.json`。

### 阶段性总结（按需使用）

10. 在归纳对话进行到节点时，运行 `04_make_summary_prompt.py` —— 复制
    总结指令给 LLM。
11. LLM 输出总结 .txt（首行必须包含 `# category=xxx, stage=ind`），
    保存到 `_inbox/`。
12. 运行 `05_dispatch_summary.py` —— TXT 自动归位到
    `02_outline/{category}/recorder/sum_ind_{NN}.txt`。

### 编码本精炼

13. 当某分类所有题归纳完成后，运行 `06_create_raw_codebook.py` —— 合并
    所有 JSON、生成各分类 raw_codebook.csv。
14. 运行 `07_make_codebook_prompt.py`，按提示选 category → prompt 自动
    复制。
15. 把 prompt 粘贴到 LLM 对话窗口。LLM 进入**步骤 1（阅览报告）**输出
    raw codebook 概览 + 方向性问题。
16. 你与 LLM 按口令体系**多轮循环**——通常每个聚焦主题各做一次
    「阅览报告 → 编码预览 → 深度探索（按需）」，所有主题闭环后再下
    「正式输出」让 LLM 出最终 CSV。
17. 把 LLM 输出的精炼编码本 CSV（首行必须是 `# category=xxx`）保存到
    `_inbox/`。
18. 运行 `08_dispatch_codebook.py` —— CSV 自动归位到
    `02_outline/{category}/codebook/codebook_{category}.csv`。

### 受访者变量提取

19. 运行 `09_make_variable_prompt.py`，按提示输入 ID 列表（标准 1 个，
    数据短时 3-4 个）→ prompt 自动复制。
20. LLM 输出变量 CSV（表头第一列必须是 `文件名`），保存到 `_inbox/`。
21. 运行 `10_dispatch_variables.py` —— CSV 自动归位到
    `03_variables/raw/var_{NN}.csv`。
22. 全部受访者处理完后，运行 `11_merge_variables.py` —— 合并为最终
    `03_variables/user_var.csv`。

### 任意时刻

- 运行 `status.py` —— 查看项目当前进度报告，并对 `_inbox/` 中的文件
  给出"建议跑哪个 dispatch"提示。

---

## 5. dispatch 脚本统一规则表

| 脚本 | 处理扩展名 | 内容签名 | 身份字段 | 归位目标 |
|---|---|---|---|---|
| 03_dispatch_inductive | `.json` | 顶层数组 + 元素含 `initial_codes` | 元素的 `category` | `02_outline/{category}/question/inductive_q{NN}.json` |
| 05_dispatch_summary | `.txt` | 首行以 `# stage=` 开头 | 首行 `# category=xxx, stage=ind` | `02_outline/{category}/recorder/sum_{stage}_{NN}.txt` |
| 08_dispatch_codebook | `.csv` | 首行 `# category=` + 第二行表头第一列 `Theme` | 首行 `# category=xxx` | `02_outline/{category}/codebook/codebook_{category}.csv` |
| 10_dispatch_variables | `.csv` | 表头第一列 `文件名` | 无 | `03_variables/raw/var_{NN}.csv` |

dispatch 脚本通用行为：

- 不符合本脚本签名的文件**留在 inbox**，不报错（其他 dispatch 会处理）。
- 每个脚本结束时 print 处理结果汇总（成功 / 跳过 / 错误）。
- 残留无法被任何 dispatch 识别的文件由 `status.py` 报告。

---

## 6. Prompt 模板说明

`prompts/` 下 4 个模板由各 `make_prompt` 脚本读入，注释行（`#` 开头）
会被自动剔除，模板正文中的 `{{XXX}}` 占位符会被脚本替换：

| 模板 | 占位符 | 任务口令 |
|---|---|---|
| `inductive_template.txt` | `{{CATEGORY}}`, `{{QUESTION_DATA}}` | 阅览报告 / 编码预览 / 深度探索 / 正式输出 / 编码日志 |
| `codebook_template.txt` | `{{CATEGORY}}`, `{{RAW_CODEBOOK_CSV}}` | 阅览报告 / 编码预览 / 深度探索 / 正式输出 |
| `summary_template.txt` | （无） | 一次性指令，无口令体系 |
| `variable_template.txt` | `{{VARIABLE_DEFINITIONS}}`, `{{VARIABLE_COLUMNS}}`, `{{USER_INTERVIEW_DATA}}` | 一次性提取，无口令体系 |

模板内核心方法论内容（编码工艺 A→B→C→D、口令体系、输出格式硬性
要求等）请勿轻易改动；仅可在指定占位符处由脚本动态填入研究内容。

---

## 7. 切换不同产品

```
# 方式 A：修改 parameters.py 里的 APP_NAME
APP_NAME = '另一个产品'

# 方式 B：临时使用命令行覆盖
python 02_make_inductive_prompt.py --app 另一个产品
```

`--app` 是所有脚本共有的可选参数。

---

## 8. 旧版本去哪了

老版本脚本与 prompt 已移到 `_legacy/`，仅作历史参考。不再维护，
新流程不依赖它们。
