from .schemas import Session, Question, Turn, Report


def context(session):
    return session.model_dump(exclude={"report"})


def next_question(gateway, session):
    def check(q):
        if not session.turns:
            if q.action != "new_topic":
                raise ValueError("首问必须是新主题")
            return
        previous = session.turns[-1].question
        if q.action == "follow_up":
            if session.followups >= 2 or q.topic != previous.topic:
                raise ValueError("追问超过上限或主题不一致")
        elif q.topic in {t.question.topic for t in session.turns}:
            raise ValueError("新主题不能重复")
        if q.text in {t.question.text for t in session.turns}:
            raise ValueError("问题重复")
    return gateway.generate(Question, "生成下一个问题。首问 action=new_topic；追问沿用 topic。同一主题最多连续追问两次，之后必须选择未问过的新主题。", context(session), check)


def start(gateway, resume, jd, max_turns=8):
    session = Session(resume=resume, jd=jd, max_turns=max_turns)
    session.current = next_question(gateway, session)
    return session


def answer(gateway, session, text):
    if session.status != "active" or session.current is None:
        raise ValueError("当前没有待回答的问题")
    # Copy-on-write: an API failure cannot partly commit a submitted answer.
    draft = session.model_copy(deep=True)
    draft.turns.append(Turn(question=draft.current, answer=text))
    draft.current = None
    if len(draft.turns) >= draft.max_turns:
        draft.status = "review"
        return draft
    draft.current = next_question(gateway, draft)
    draft.followups = draft.followups + 1 if draft.current.action == "follow_up" else 0
    return draft


def finish(session):
    draft = session.model_copy(deep=True)
    draft.status = "review"
    draft.current = None
    return draft


def review(gateway, session):
    if session.status != "review" or not session.turns:
        raise ValueError("至少回答一个问题并结束面试后才能复盘")
    def check(report):
        if len({f.dimension for f in report.feedback}) != 4:
            raise ValueError("必须覆盖四个不同维度")
        for feedback in report.feedback:
            for evidence in feedback.evidence:
                if evidence.turn > len(session.turns) or evidence.quote not in session.turns[evidence.turn - 1].answer:
                    raise ValueError("引用必须来自对应回答原文")
        if any(not q.strip() for q in report.practice_questions):
            raise ValueError("重练问题不能为空")
    report = gateway.generate(Report, "复盘已有回答：四个维度各一条，引用原文并标注从1开始的回答轮数；提供亮点、待补充事实、可操作改进和三个重练问题。不得补造事实。", context(session), check)
    draft = session.model_copy(deep=True)
    draft.report = report
    draft.status = "complete"
    return draft
