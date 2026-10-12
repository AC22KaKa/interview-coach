from pathlib import Path
import streamlit as st
from agent.inputs import import_resume
from agent.llm import Gateway
from agent.service import start, answer, finish, review
from agent.export import markdown

st.set_page_config(page_title="面试陪练 Agent", page_icon="💬")
st.title("面试陪练 Agent")
st.caption("围绕你的真实项目经历，逐题回答、深入追问、复盘练习。")
gateway = Gateway()
for key in ("resume", "jd"):
    st.session_state.setdefault(key, "")


def perform(operation):
    try:
        with st.spinner("正在处理…"):
            result = operation()
        st.session_state.session = result
        st.rerun()
    except Exception as exc:
        st.error(str(exc))


session = st.session_state.get("session")
if session is None:
    with st.expander("导入第二个项目的结果 JSON"):
        uploaded = st.file_uploader("ResumeResult JSON", type="json")
        if st.button("导入到简历编辑框", disabled=uploaded is None):
            try:
                st.session_state.resume = import_resume(uploaded.getvalue())
                st.success("已导入，请核实指标与经历后开始。")
            except ValueError:
                st.error("文件不符合原简历项目的 ResumeResult 格式，或超过 1 MB。")
    if st.button("载入示例"):
        import json
        data = json.loads((Path(__file__).parent / "examples/materials.json").read_text(encoding="utf-8"))
        st.session_state.resume, st.session_state.jd = data["resume"], data["jd"]
    st.text_area("简历 / 项目经历（请核实导入内容）", key="resume", height=220)
    st.text_area("目标岗位 JD", key="jd", height=140)
    rounds = st.number_input("回答轮数", min_value=1, max_value=20, value=8)
    if st.button("开始面试", type="primary"):
        if not st.session_state.resume.strip() or not st.session_state.jd.strip():
            st.error("请同时填写简历和 JD。")
        else:
            perform(lambda: start(gateway, st.session_state.resume, st.session_state.jd, rounds))
else:
    st.caption(f"已完成 {len(session.turns)} / {session.max_turns} 轮 · 记录仅保存在当前会话，请及时下载。")
    for i, turn in enumerate(session.turns, 1):
        with st.chat_message("assistant"):
            st.write(f"第 {i} 问：{turn.question.text}")
        with st.chat_message("user"):
            st.write(turn.answer)
    if session.status == "active":
        with st.chat_message("assistant"):
            st.write(session.current.text)
        # A per-turn widget key retains failed submissions and clears only after success.
        answer_key = f"answer_{len(session.turns)}"
        text = st.text_area("你的回答", key=answer_key, height=180)
        if st.button("提交回答", type="primary"):
            if not text.strip():
                st.error("请先输入回答。")
            else:
                perform(lambda: answer(gateway, session, text))
        if st.button("结束面试（仅复盘已提交回答）"):
            perform(lambda: finish(session))
    elif session.status == "review":
        if not session.turns:
            st.info("尚无已提交回答，不生成能力评价。可以重新开始。")
        elif st.button("生成 / 重试复盘报告", type="primary"):
            perform(lambda: review(gateway, session))
    if session.report:
        st.markdown(markdown(session).rsplit("## 复盘", 1)[1])
    st.download_button("下载 Markdown", markdown(session), "interview.md", "text/markdown")
    st.download_button("下载完整 JSON（含简历和回答）", session.model_dump_json(indent=2), "interview.json", "application/json")
    if st.button("清空记录，开始新面试"):
        del st.session_state.session
        for key in list(st.session_state):
            if key.startswith("answer_"):
                del st.session_state[key]
        st.rerun()
