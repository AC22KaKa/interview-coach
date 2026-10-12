def markdown(session):
    lines = ["# 面试练习记录", "", "## 简历", session.resume, "", "## 目标岗位", session.jd, "", "## 问答"]
    for i, turn in enumerate(session.turns, 1):
        lines.extend([f"### 第 {i} 轮", turn.question.text, "", turn.answer, ""])
    if session.report:
        lines.extend(["## 复盘", "以下评价仅用于练习，不是客观能力测量。"])
        for item in session.report.feedback:
            lines.extend([f"### {item.dimension}", item.assessment])
            for evidence in item.evidence:
                lines.append(f"- 第 {evidence.turn} 轮原文：{evidence.quote}")
            lines.append("改进建议：" + item.suggestion)
        for title, items in [("亮点", session.report.strengths), ("待补充事实", session.report.missing_facts), ("优先重练", session.report.practice_questions)]:
            lines.extend([f"### {title}", *[f"- {item}" for item in items]])
    return "\n\n".join(lines)
