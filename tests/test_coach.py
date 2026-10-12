import json
import unittest
from types import SimpleNamespace
from agent.schemas import Question, Report, Session
from agent.service import start, answer, finish, review
from agent.llm import Gateway, CoachError
from agent.inputs import import_resume
from agent.export import markdown


def question(topic="贡献", action="new_topic"):
    return {"text": f"请具体解释你的{topic}是什么？", "topic": topic, "action": action}


def report(quote="我实现了校验"):
    return {"feedback": [{"dimension": d, "assessment": "提供了实现细节，但证据仍有限", "evidence": [{"turn": 1, "quote": quote}], "suggestion": "解释一个实际失败案例"} for d in ["相关性", "具体性", "技术解释", "表达结构"]], "strengths": ["提到了实际实现"], "missing_facts": ["测试结果待补充"], "practice_questions": ["你负责什么？", "为什么用校验？", "失败时如何处理？"]}


class FakeClient:
    def __init__(self, outputs):
        self.outputs = iter(outputs)
        self.calls = []
        self.chat = SimpleNamespace(completions=self)

    def create(self, **kwargs):
        self.calls.append(kwargs)
        output = next(self.outputs)
        if isinstance(output, Exception):
            raise output
        content = output if isinstance(output, str) else json.dumps(output, ensure_ascii=False)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


def gateway(*outputs):
    return Gateway(FakeClient(outputs), "fake")


class CoachTests(unittest.TestCase):
    def test_default_eight_rounds(self):
        s = start(gateway(question("主题0")), "项目", "岗位")
        for i in range(8):
            s = answer(gateway(question(f"主题{i + 1}")), s, "我实现了校验")
        self.assertEqual(len(s.turns), 8)
        self.assertEqual(s.status, "review")
        self.assertIsNone(s.current)
        with self.assertRaises(ValueError):
            answer(gateway(), s, "重复提交")

    def test_materials_required_and_error_sanitized(self):
        with self.assertRaises(ValueError):
            start(gateway(), "  ", "岗位")
        with self.assertRaises(ValueError):
            start(gateway(), "项目", "  ")
        with self.assertRaises(CoachError) as caught:
            start(gateway(RuntimeError("secret-key")), "项目", "岗位")
        self.assertNotIn("secret-key", str(caught.exception))

    def test_full_interview_and_exports(self):
        g = gateway(question(), report())
        s = start(g, "真实项目", "Python岗位", 1)
        s = answer(g, s, "我实现了校验")
        self.assertEqual(s.status, "review")
        s = review(g, s)
        self.assertEqual(s.status, "complete")
        self.assertIn("我实现了校验", markdown(s))
        self.assertEqual(Session.model_validate_json(s.model_dump_json()), s)

    def test_failed_answer_is_atomic_and_retryable(self):
        s = start(gateway(question()), "项目", "岗位")
        with self.assertRaises(CoachError):
            answer(gateway(RuntimeError("secret")), s, "我实现了校验")
        self.assertEqual(len(s.turns), 0)
        self.assertIsNotNone(s.current)
        result = answer(gateway(question("选型")), s, "我实现了校验")
        self.assertEqual(len(result.turns), 1)

    def test_repair_and_exhaustion(self):
        g = gateway("invalid", question())
        self.assertIsInstance(g.generate(Question, "问题", {}), Question)
        self.assertEqual(len(g.client.calls), 2)
        with self.assertRaises(CoachError):
            gateway("bad", "bad").generate(Question, "问题", {})

    def test_followup_limit(self):
        s = start(gateway(question()), "项目", "岗位")
        for i in range(2):
            q = question(action="follow_up")
            q["text"] = f"请详细补充个人贡献的第{i}项细节？"
            s = answer(gateway(q), s, "我的贡献")
        forbidden = question(action="follow_up")
        result = answer(gateway(forbidden, question("技术选择")), s, "我的贡献")
        self.assertEqual(result.followups, 0)
        with self.assertRaises(CoachError):
            answer(gateway(forbidden, forbidden), s, "我的贡献")

    def test_report_evidence_and_retry(self):
        s = finish(answer(gateway(), start(gateway(question()), "项目", "岗位", 1), "我实现了校验"))
        with self.assertRaises(CoachError):
            review(gateway(report("编造内容"), report("编造内容")), s)
        self.assertIsNone(s.report)
        self.assertEqual(review(gateway(report()), s).status, "complete")

    def test_empty_and_early_finish(self):
        s = start(gateway(question()), "项目", "岗位")
        with self.assertRaises(ValueError):
            answer(gateway(), s, "  ")
        with self.assertRaises(ValueError):
            review(gateway(), finish(s))
        s = answer(gateway(question("选型")), s, "我实现了校验")
        self.assertEqual(review(gateway(report()), finish(s)).status, "complete")

    def test_resume_import(self):
        data = {"project_name": "Resume Agent", "bullets": [{"star": "使用Python实现结构化输出校验", "metric": "[Add metric]"}] * 2, "interview_questions": ["为什么？"] * 3}
        self.assertIn("[Add metric]", import_resume(json.dumps(data).encode()))
        for invalid in [b"{}", b"not json", b"x" * 1_000_001]:
            with self.assertRaises(ValueError):
                import_resume(invalid)

    def test_dimensions_unique(self):
        s = answer(gateway(), start(gateway(question()), "项目", "岗位", 1), "我实现了校验")
        bad = report()
        bad["feedback"][1]["dimension"] = "相关性"
        with self.assertRaises(CoachError):
            review(gateway(bad, bad), s)


if __name__ == "__main__":
    unittest.main()
