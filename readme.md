# 项目文件夹结构
```
📁 data_dir/
├── 📁 myworld_dir/  
│   ├── 📁 00_rawdata_dir/
│   │   └── 📄 myworld.csv  -->key('UI')
│   ├── 📁 01_preprocessed_for_llm_dir/
│   │   ├── 📄 myworld_user.txt  -->key('UI_utxt')
│   │   └── 📄 myworld_question.txt  -->key('UI_qtxt')
│   ├── 📁 02_interview_outline_dir/  -->key('interview_outline_base_dir')
│   │   ├── 📁 player_states/
│   │   │   ├── 📁 question_data_dir/
│   │   │   │   ├── 📄 user_g.txt
│   │   │   │   └── 📄 inductive_questionN.json
│   │   │   │   └── 📄 deductive_code_by_LLM.json
│   │   │   ├── 📁 codebook_data/
│   │   │   │   ├── 📄 inductive_questionN_codebook.json  -->key('grouped_inductive_q_jsons')
│   │   │   │   ├── 📄 raw_codebooks.txt  -->key('grouped_raw_codebook_txts')
│   │   │   │   └── 📄 codebook.tx
│   │   │   └── 📁 meta_data_dir/
│   │   │       └── 📄 编码位置元数据.xx
│   │   ├── 📁 player_experiences/
│   │   │   └── 📂 ... // 项目结构与player_states相同
│   │   ├── 📁 creativity_experiences/
│   │   │   └── 📂 ... // 项目结构与player_states相同
│   │   └── 📁 creativity_features/
│   │       └── 📂 ... // 项目结构与player_states相同
│   ├── 📁 03_inductive_coding_dir/  --> key('inductive_dir_path')
│   │   ├── 📄 myworld_inductive_codes.json  -->key('inductive_codes_merged_json')
│   │   ├── 📄 myworld_inductive_maxqda_opencode.txt  -->key('inductive_maxqda_opencode') 
│   │   ├── 📄 myworld_inductive_maxqda_themecode.txt ）  -->key('inductive_maxqda_themecode')
│   │   └── 📄 myworld_inductive_metadata.xx  -->key('inductive_metadata_file')  
│   └── 📁 04_deductive_coding_dir/  --> key('deductive_dir_path') 
│       ├── 📄 myworld_deductive_maxqda.txt  -->key('deductive_maxqda_text')
│       └── 📄 myworld_deductive_metadata.xx  -->key('deductive_metadata_file')
├── 📁 lol_dir/
│   └── 📂 ...
└── 📂 python scripts
```

# 操作流程概要

- 建立项目环境，包括项目路径、文件夹以及原始文件
- 使用原始文件生成基于访谈题目的数据结构，以便后续喂给LLM
- 使用LLM进行编码，改编码的结果为对每个访谈题目数据的开放编码（归纳编码-inductive coding）
- 鉴于LLM的上下文能力，每次只处理一个访谈题目数据，并以json格式保存编码信息。
- 让LLM对所有访谈题目数据编码后，将编码结果（多个json）文件合并为整体数据（json格式）
- 根据maxqda的结构文本的格式要求，将合并数据转换为带编码格式的txt文件，导入maxqda
- 根据大纲生成初步编码本raw_codebook_{大纲分类}


# 开放编码

## 准备文件

准备2个文件

- 原始访谈数据文件csv文件。第一列为用户“序号”，以数字方式编排。文件名称使用”调研产品名称.csv“的方式命名，如"lol.csv"
- 访谈大纲文件，包含三列，分别为问题号、大纲类别、访谈问题。列名称可自定义。文件名称为“调研产品名称-outline.csv"方式命名，例如"lol-outline.csv"

## 全局变量定义

在parameters.py中定义全局变量

- 修改 APP_NAME = ”调研的产品名称“
- 运行后，该脚本会执行以下任务
	- 一键生成所有项目路径
	- 归位文件，将访谈数据与访谈大纲放入指定文件夹


## 生成数据文本

- 使用01create_user_and_question_data.py基于原始csv数据生成纵向（以用户为轴, {APP_NAME}_user.txt）和横向（以问题为轴, {APP_NAME}_question.txt）两个txt数据文本。APP_NAME 为在parameters.py中设置的产品名。
- 生成文件的位置在01_preprocessed_for_llm_dir/下

## LLM生成

- 使用prompts_inductive_coding-simple.txt文件中的提示语引导LLM逐步生成每个问题的json文件。第一次建议喂给LLM一个问题(使用{APP_NAME}_question.txt里的问题)。生成时检查编码质量。
- 将生成结果拷贝到名为"inductive_questionN.json"的文件中, N为问题序号
- inductive_questionN.json根据问题在大纲中的所属模块，放入02_interview_outline_dir/下相应的分组文件夹/question_data_dir/中

## 合并json

- 使用02inductive_merge_json.py文件将上一步所有的问题编码json文件整合为一个json
- 生成文件位于03_inductive_coding_dir/{APP_NAME}_inductive_codes.json

## 转换maxqda结构本文

- 使用03inductive_create_maxqda_themecode.py进行识别并解析json文件中的信息，转换为maxqda结构文本
- 生成文件保存在03_inductive_coding_dir/{APP_NAME}_inductive_maxqda_themecode.txt

## 导入maxqda

- 在MaxQDA中”导入-->结构化文本“命令导入{APP_NAME}_inductive_maxqda_themecode.txt即可。
- 📢 未编码的问题数据会以问题作为每个问题数据的主编码。编码的问题数据，问题编码下则为空，解决此问题可参考以下方法：

	1. 将原始访谈数据.csv改为excel文件，导入maxqda。该数据能保证初始数据均在问题大编码下。保存为”excelinput.mx“
	2. 使用”开始-->团队合作-->导出团队合作文件“，将文件另存为“excelinput-merge.mex"文件
	3. 建立新的maxqda文件，导入之前生成的结构文本。保存为“txtinput.mx”
	4. 确保“txtinput.mx”中的数据在组名、文件名、问题编码名等于”excelinput.mx“相同
	5. 使用”开始-->团队合作-->导入团队合作文件“命令，将“excelinput-merge.mex"导入到“txtinput.mx”

# 制作编码本

## 生成初步编码本

- 使用04create_raw_codebook.py提取inductive_questionN.json中的信息，生成基于大纲的初步编码本
- 编码本存默认放在02_interview_outline_dir/下相应的分组文件夹/codebook_data_dir/中

## 使用LLM生成编码

- 此过程是一个漫长的过程，需要精心调教LLM生成编码本
- 建议每次按照一个大纲模块生成编码本
- 参考prompts_create_codebook-simple.txt设计提示语
- 编码本建议生成一版本maxqda字典格式，提示语可参考以下形式：
	1. 请将编码本整理为以下格式
	|分类|检索词|

	|编码名字1|引文1|

	|编码名字1|引文2|

	|编码名字1|引文N|

	|编码名字2|引文1|

	|编码名字2|引文2|

	|编码名字2|引文N|

	|编码名字N|引文1|

	|编码名字N|引文2|

	|编码名字N|引文N|
	...

	2. “索引词”列中的文本，去除所有前后的标点符号

# 演绎编码与分析

## 在MAXQDA中生成归纳编码

- 将LLM生成的编码本导入MAXQDA的词典
- 使用”基于词典内容进行分析“功能，将词典转化为编码
- 生成code map，关掉网格，显示连线频次

## 结合LLM进行分析

- 将code map、原始访谈数据喂给大模型，让大模型帮助解析结果


