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


# 开放编码

## 全局变量定义

在parameters.py中定义全局变量

- app名称，所调研的产品名称
- 路径名称：02_interview_outline_dir下的子文件夹按照访谈大纲设定。在parameters.py中找到下面代码修改

```
# --- 研究者在此处定义访谈大纲的分组文件夹名称 ---
PROJECT_GROUP_FOLDERS = [
	"player_states", "player_experiences",
	"creativity_experiences", "creativity_features",
]
```

- 一键生成所有项目路径

## 归位文件

将原始csv访谈文件以产品名命名。名称需要与parameters.py中的app名称一致。

## 生成数据文本

使用01create_user_and_question_data.py基于原始csv数据生成纵向（以用户为轴, {app}_user.txt）和横向（以问题为轴, {app}_question.txt）两个txt数据文本。app为在parameters.py中设置的产品名。

生成文件的位置在01_preprocessed_for_llm_dir/下

## LLM生成

使用prompts_inductive_coding.txt文件中的提示语引导LLM逐步生成每个问题的json文件。第一次建议喂给LLM一个问题(使用{app}_question.txt里的问题)。生成时检查编码质量。

将生成结果拷贝到名为"inductive_questionN.json"的文件中, N为问题序号

inductive_questionN.json根据问题在大纲中的所属模块，放入02_interview_outline_dir/下相应的分组文件夹/question_data_dir/中

## 合并json

使用02inductive_merge_json.py文件将上一步所有的问题编码json文件整合为一个json

该文件位于03_inductive_coding_dir/{app}_inductive_codes.json

## 转换maxqda结构本文

使用03inductive_create_maxqda_themecode.py进行识别并解析json文件中的信息，转换为maxqda结构文本

生成文件保存在03_inductive_coding_dir/{app}_inductive_maxqda_themecode.txt

## 导入maxqda

在MaxQDA中导入{app}_inductive_maxqda_themecode.txt即可。

# 制作编码本

## 使用LLM生成编码

生成每个问题的初步编码本的提示语在interview-prompts.txt中。生成的文件命名为Q1c.py, Q2c.py的格式...

将生成的数据根据parameter.py里的路径标注，放入相应的项目文件夹
