# 文件收件箱

将需要让 agent 分析的文件直接放到对应子目录，
程序启动或点击"扫描新文件"后自动加载。

| 子目录 | 放什么文件 |
|--------|-----------|
| `problems/` | 赛题 PDF（支持子文件夹） |
| `papers/` | 获奖论文 PDF |
| `references/` | 参考文献 PDF |
| `knowledge/` | 数学建模领域知识库 PDF |
| `web_ai/` | 从 AI 网页版复制并保存的回复（.md 或 .txt） |

> 支持格式：PDF（自动 OCR）、Markdown、纯文本
> 已处理文件记录在 `.processed_files.json`，不会重复加载
