MIN_COVERAGE_SCORE = 0.35


def _render_sim_block(sim_results, scores, label, min_score=MIN_COVERAGE_SCORE):
    has_scores = scores and len(scores) > 0
    if has_scores:
        items = [(sim_results[i][:400], scores[i]) for i in range(min(3, len(scores))) if scores[i] >= min_score]
    else:
        items = [(sim_results[i][:400], 0) for i in range(min(3, len(sim_results)))]

    if not items:
        return f"""
{label}：
（数据库中未检索到足够相关的历史资料，相似度均低于 {min_score}。
请完全依据题目本身和数学原理进行分析，不要强行套用无关历史案例。）
"""
    lines = []
    for text, score in items[:3]:
        score_str = f"[相似度 {score:.2f}]" if has_scores and score > 0 else ""
        lines.append(f"{score_str} {text}")
    return f"{label}：\n" + "\n".join(lines)


def get_topic_selection_prompt(topics, sims_list):
    topics_text = "\n".join([f"选题{i+1}: {t[:2000]}" for i, t in enumerate(topics)])
    sims_descriptions = []
    for i, sims in enumerate(sims_list):
        q_count = len([s for s in sims.get("sim_question_scores", []) if s >= MIN_COVERAGE_SCORE])
        p_count = len([s for s in sims.get("sim_paper_scores", []) if s >= MIN_COVERAGE_SCORE])
        r_count = len(sims.get("sim_question_scores", []))

        has_cov = sims.get("has_coverage", q_count > 0)
        if has_cov:
            sims_descriptions.append(
                f"选题{i+1}: 匹配到{q_count}道相似历史赛题(相似度>{MIN_COVERAGE_SCORE}), {p_count}篇相关论文, 共{r_count}条历史记录"
            )
        else:
            sims_descriptions.append(
                f"选题{i+1}: 数据库中无足够相似的历史资料(所有相似度均<{MIN_COVERAGE_SCORE})"
            )
    sims_text = "\n".join(sims_descriptions)

    return f"""你是APMCM数学建模竞赛特等奖教练,精通选题策略。

当前三个备选赛题:
{topics_text}

各选题的数据库匹配情况:
{sims_text}

请从以下维度分析每个选题并给出推荐排名:
1. 获奖难度(是否有成熟方法可借鉴)
2. 完成可行性(建模-编码-论文路径是否清晰)
3. 数据与文献支撑(数据库匹配是否充分)

输出格式:
## 选题分析

### 选题1分析
- 获奖难度: (评分/10) 分析...
- 完成可行性: (评分/10) 分析...
- 文献支撑: (评分/10) 分析...

### 选题2分析
(同上)

### 选题3分析
(同上)

## 最终推荐
- 首选: 选题X (综合理由)
- 备选: 选题Y (理由)
- 不推荐: 选题Z (理由)
"""


def get_modeling_prompt(question, sims, selected_approach=""):
    q_block = _render_sim_block(
        sims.get("sim_questions", []),
        sims.get("sim_question_scores", []),
        "相似历史赛题（可借鉴方法）"
    )
    p_block = _render_sim_block(
        sims.get("sim_papers", []),
        sims.get("sim_paper_scores", []),
        "优秀论文参考"
    )

    return f"""你是APMCM数学建模竞赛教练,擅长数学建模方案设计。
【think 约束 - 先设计再实现】
输出建模方案前，先在内部完成以下思考（不需要输出思考过程）：
① 这道题最本质的数学结构是什么（优化/预测/分类/模拟）
② 历史参考资料里哪些方法真正适用，哪些只是表面相似
③ 推荐方案最可能在哪个环节失败
完成思考后，再按结构输出建模方案。

当前赛题:
{question[:3000]}

{q_block}

{p_block}

用户选择的方法方向: {selected_approach if selected_approach else "请自主推荐最优方法"}

请输出完整的数学建模方案:

## 1. 问题分析
- 问题类型归类
- 核心变量识别
- 约束条件分析

## 2. 符号说明
(列出所有数学符号及含义)

## 3. 模型假设
(列出合理的模型假设)

## 4. 建模方案(推荐3种,每种包含)
- 方法名称
- 数学原理与公式
- 优缺点对比
- 适用性分析

## 5. 推荐方案详细推导
- 目标函数
- 约束条件数学表达
- 求解思路

## 6. 创新点说明
"""


def get_coding_prompt(question, modeling_plan, sims):
    return f"""你是APMCM数学建模编程教练,擅长将数学模型转化为高效Python代码。

赛题背景:
{question}

建模方案:
{modeling_plan}

请生成完整的Python代码实现:

## 1. 数据处理模块
- 数据读取与预处理
- 数据探索性分析(EDA)

## 2. 模型实现
- 使用Pyomo/Scipy/GEKKO实现优化模型
- 或使用sklearn/scipy实现统计/机器学习模型
- 代码需包含完整注释

## 3. 求解与结果输出
- 求解器配置与调用
- 结果提取与整理

## 4. 敏感性分析
- 关键参数变化对结果的影响

【TDD 约束 - 必须遵守】
第一步（先写验证）：在代码最顶部定义 validate_output(result) 函数，
  明确规定期望输出的类型、范围、格式，用 assert 断言，最后打印 "✅ PASS" 或 "❌ FAIL: 原因"
第二步（再写设计）：在 validate_output 之后，用注释块写明设计决策：
  # === 设计决策 ===
  # 求解器选择: <为什么用 Pyomo/Scipy/GEKKO>
  # 核心假设: <列出 2-3 条>
  # 最可能出错的地方: <列出 1-2 条>
  # ================
第三步（再写实现）：按 数据处理 → 模型实现 → 求解输出 → 敏感性分析 顺序实现
第四步（调用验证）：main() 最后一行调用 validate_output(result)

其他要求: 可直接运行 / 中文注释 / 错误处理用 try-except 并打印具体错误信息 / 格式化输出
"""


def get_figure_prompt(question, modeling_result, coding_result):
    return f"""你是科学可视化专家,擅长为数学建模论文设计专业图表。

赛题: {question}

建模结果摘要: {modeling_result[:2000]}

代码运行结果: {coding_result[:2000]}

请设计图表方案:

## 图表清单
对每个图表说明:
1. 图表类型(折线图/柱状图/热力图/散点图/箱线图等)
2. 展示目的
3. 数据来源
4. 推荐配色方案
5. 图表尺寸与分辨率建议

## 推荐图表
- 使用Nature期刊风格
- 中英文标题
- 清晰的图例和轴标签
"""


def get_paper_writing_prompt(question, modeling_plan, coding_result, figure_descriptions):
    return f"""你是APMCM数学建模论文写作教练,擅长撰写竞赛获奖级别论文。

赛题: {question}

建模方案: {modeling_plan[:3000]}

代码实现要点: {coding_result[:2000]}

图表方案: {figure_descriptions[:2000]}

请撰写论文初稿,按以下结构:

## 摘要
(200-300字,包含:问题背景、建模方法、主要结论、创新点)

## 1. 问题重述
## 2. 问题分析
## 3. 模型假设与符号说明
## 4. 模型建立与求解
### 4.1 模型一
### 4.2 模型二
### 4.3 模型三
## 5. 模型检验与敏感性分析
## 6. 模型评价与推广
## 7. 参考文献

## 附录: 核心代码

要求:
- 学术写作风格
- 公式使用LaTeX格式
- 图表引用标记清晰
- 逻辑连贯,论证充分

【check 自审清单 - 输出论文前逐条检查】
□ 摘要是否在 200-300 字之间，是否包含核心结论和量化结果
□ 每个模型章节是否有对应的数学公式（LaTeX 格式）
□ 是否引用了图表（图1/表1 等标记）
□ 参考文献格式是否统一（APA 或 GB/T 7714）
□ 逻辑链是否完整：问题重述→假设→建模→求解→验证→结论
未通过的项目，在输出论文时主动补全，不要跳过。
"""


def get_polish_prompt(paper_content, polish_type="润色"):
    return f"""你是学术论文编辑,请对以下论文初稿进行{polish_type}。

论文内容:
{paper_content}

要求:
- 保持学术写作风格
- 修正语法和表达问题
- 增强逻辑连贯性
- 保持原意不变
- 标注主要修改处
"""


def get_pressure_test_prompt(solution_plan, test_dimensions=None):
    dims = test_dimensions or ["可行性", "创新性", "完整性", "可操作性", "数学严谨性"]
    dims_text = "\n".join([f"- {d}" for d in dims])

    return f"""你是数学建模评审专家,请对以下建模方案进行压力测试。

建模方案:
{solution_plan}

请从以下维度进行评估:
{dims_text}

每个维度请给出:
1. 评分(1-10)
2. 优点
3. 潜在漏洞或不足
4. 改进建议

最后给出:
- 总体评分
- 主要风险点
- 优先级改进清单
"""


def get_grill_me_prompt(plan, user_expectation):
    return f"""你是数学建模项目评估专家。用户的期望是: {user_expectation}

当前方案:
{plan}

请评估此方案是否符合用户期望,从以下角度:
1. 目标对齐度: 方案是否解决了用户关心的问题?
2. 方法匹配度: 使用的方法是否适合问题?
3. 预期产出: 预计能否达到用户期望的结果?
4. 差距分析: 方案与期望之间有哪些差距?
5. 调整建议: 如何调整方案以更好地满足期望?

请给出"A.方案符合预期,可以继续"或"B.需要调整,具体建议如下"的明确判断。
"""
