# parameters.py
"""
项目全局参数（精简版）

经过 refactor.md 重构后，本文件只保留一个常量：
    APP_NAME —— 当前正在处理的产品/项目名称

所有路径生成、目录解析等逻辑已迁移到 00_init_project.py 与各脚本内部。
所有 0X_*.py 脚本顶部统一通过：
    from parameters import APP_NAME
读取默认值，并支持命令行参数 --app <name> 覆盖。
"""

# ---- 当前默认产品名称（必填） ----
# 用户切换产品时只需修改这一行；或在命令行加 `--app <其他名称>` 临时覆盖。
APP_NAME = 'D5'
