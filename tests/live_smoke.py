"""Explicit opt-in integration check. Makes two paid/provider API requests."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agent.llm import Gateway
from agent.service import start, answer, review

if __name__ == "__main__":
    if "--confirm-api" not in sys.argv:
        raise SystemExit("该检查消耗 API。配置 .env 后运行：python tests/live_smoke.py --confirm-api")
    gateway = Gateway()
    session = start(gateway, "我使用Python和Pydantic开发简历工具，负责JSON校验和失败重试，没有测量用户数量。", "Python AI应用实习生", 1)
    print("首问：", session.current.text)
    session = answer(gateway, session, "我负责Pydantic模型和失败重试，JSON不合法时再请求一次。我还没有统计成功率。")
    session = review(gateway, session)
    print("完成：", session.status)
    print(session.report.model_dump_json(indent=2))
