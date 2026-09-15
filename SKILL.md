---
name: ai-workflow-optimizer
description: "在用户明确要求检查、精简或优化智能体指令、Skill 或提示词时，读取 OpenAI 官方建议并给出或实施最小必要改动。"
---

# 智能体配置优化

当用户明确要求检查、精简或优化智能体的指令、Skill 或提示词时使用。普通编码、写作和研究任务不要触发本 Skill。

先打开并阅读当前 OpenAI 官方文章：<https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra>。不要复制文章全文，也不要预设一套长工作流。只读取当前问题相关的 `AGENTS.md`、提示词、Skill 或配置；根据文章找出真正需要改的冗余、重复、过宽触发和不必要停顿。

用户只要求分析时保持只读；用户明确要求修改时，只做最小、可回退的改动，保留业务约束和权限边界，并说明改了什么、如何验证、哪些效果尚未测量。不要擅自创建工作流、状态文件、脚本、参考资料、角色或新的 Skill。

联网失败就直说，不能假装读过文章。这个社区 Skill 不是 OpenAI 官方产品。

启动示例：

`使用 $ai-workflow-optimizer 按 OpenAI 官方文章检查我的智能体配置，只做必要改动。`
