# 智能体配置体检与优化

一个根据 OpenAI 关于技能与提示词的提醒整理的社区 Skill。帮助检查指令过多、技能误触发、不必要流程和任务提前停止，并完成可恢复的修改。不是 OpenAI 官方产品，也不保证节省多少 token。

## 安装到 Codex

解压后，将整个 `ai-workflow-optimizer` 文件夹放入自己的 Codex 技能目录，默认是 `~/.codex/skills/`；设置过 CODEX_HOME 时用该目录下的 `skills/`。

如果已经有同名技能，先备份并比较差异，选择合并或替换，不要直接覆盖。打开一个新任务，检查技能是否被发现；若客户端使用不同目录，以其实际设置为准。

## 用法

只看问题，不修改：

> 使用 $ai-workflow-optimizer 对我的智能体配置做只读体检，解释问题和建议。

直接优化：

> 使用 $ai-workflow-optimizer 优化我的全局指令和本地技能。先备份，修复有证据的问题，保留业务边界，完成验证并给我差异与回退说明。

制作分享包：

> 使用 $ai-workflow-optimizer 把通用优化方法整理成可分享的 Skill，排除个人数据，并验证压缩包。

## 本地只读脚本

需要 Python 3.9 或以上，无第三方依赖。将占位路径替换为实际路径，路径有空格时加引号。

```bash
python3 scripts/audit.py --root /path/to/skills --root /path/to/AGENTS.md
python3 -m unittest discover -s tests -v
```

脚本只输出 JSON，不改配置、不安装依赖、不联网。它报告的是磁盘文件及候选问题，不是实际活跃技能、历史使用率或完整 YAML 验证。输出可能含私人路径和描述，请留在本机。

## 分享给别人

分享本技能文件夹或 ZIP 即可。不要打包自己的 .codex 目录、审计输出、配置和备份。收件人用自己的资料运行；本包没有预置任何个人项目。

原文与本方法的区别见 references/sources.md。优化是否有效，用相同材料的新任务对照观察，不以字数减少代替质量验证。
