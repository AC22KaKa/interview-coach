# 面试陪练 Agent

基于真实简历与岗位 JD 的中文文字面试工具。每次一个问题，支持追问、提前结束、有原文依据的复盘与记录下载。独立于原简历项目，不修改原压缩包。

## 快速开始（Windows PowerShell）

建议使用 Python 3.11 或 3.12；代码使用 Python 3.10+ 语法，新版 Python 的第三方依赖兼容性需按实际安装确认。

在本目录打开终端：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
# 用编辑器在 .env 中填写自己的 API Key，不要提交密钥
.\.venv\Scripts\python.exe -m streamlit run app.py
```

默认接口是智谱，模型是 `glm-4-flash`。可用环境变量 `OPENAI_API_KEY`、`OPENAI_BASE_URL`、`MODEL_NAME` 更换支持 JSON 输出的兼容接口。模型可用性与额度以提供商账户为准。

打开页面 → 载入示例或输入自己的材料 → 核实 → 开始面试 → 每轮提交回答 → 结束后生成报告。提交失败时保留原问题与输入，点击提交即可重试。结束按钮只使用已提交的回答，未提交草稿不进入报告。

## 导入与导出

支持原简历项目的 `ResumeResult` JSON：`project_name`、`matched_keywords`、`bullets`（`star`、`metric`）、`interview_questions`、`needs_clarification`、`clarifying_questions`。JSON 需满足原项目数量约束，最大 1 MB。

原项目页面的“查看原始 JSON”可以复制保存成 UTF-8 `.json` 后上传。原页面只提供 Markdown 下载，因此这里没有假定它已经有 JSON 下载按钮。导入会覆盖当前简历编辑框，但不会开始面试；请核实指标占位符。原有面试题不当作已发生的对话。

下载的完整会话 JSON 包含简历、JD、问答和报告，属于个人资料，请自行妥善保管。此版本提供导出，不支持恢复会话；会话 JSON 也不是 ResumeResult 导入格式。

## 架构与设计

```text
页面输入 / ResumeResult JSON
       ↓
输入校验 → Session（材料、问题、历史、状态）
                   ↓
            面试控制 service
                   ↓
       Gateway → 兼容接口 → Pydantic + 业务校验
                   ↓
          成功后提交新 Session
                   ↓
           复盘 → Markdown / JSON
```

- `agent/inputs.py` 负责原项目兼容；`agent/schemas.py` 定义类型。
- `agent/llm.py` 管理接口和一次输出修复，不进行隐藏的网络重试。
- `agent/service.py` 管理首问、追问上限、结束、引用校验和状态提交。
- `agent/export.py` 负责导出；`app.py` 只组织页面交互。

状态为 `active → review → complete`。默认八轮，可设 1–20 轮；同一主题最多追问两次。每次发送全部材料和已有记录，优点是简单可解释，代价是对话越长消耗越高；本版没有摘要或检索。

## 验证

离线测试不需要密钥、网络、Streamlit 或 OpenAI SDK，只需 Pydantic：

```powershell
python -m unittest discover -s tests -v
```

真实接口检查需要安装全部依赖并填写 `.env`，正常情况下调用两次，有输出修复时最多四次：

```powershell
python tests/live_smoke.py --confirm-api
```

人工质量评估使用 `evals/cases.json` 的四组材料，JD 可统一使用“Python AI 应用实习生”。按检查点判断相关性、事实依据、追问质量，记录模型名、日期、是否通过和失败原文。不要将测试中的模拟响应当作模型能力证据。

页面验收：示例载入、合法与非法导入、空材料、首问、失败后输入保留、追问、提前结束、空面试结束、到达轮数、报告失败后重试、两种下载、新面试清空历史。

## 本次验证状态与限制

10 项离线自动测试通过，覆盖完整流程、默认八轮结束、追问上限、输出修复、原子提交、重试、证据校验、导入、导出、空材料和空回答。代码可编译。

开发环境的依赖安装受到文件访问错误阻碍，尚未完成 Streamlit 页面运行验证；也没有配置真实 API 密钥，因此没有完成真实接口验证。以上两项需在正常安装环境完成，不能视为已通过。

目前没有语音、PDF/DOCX 解析、RAG、账号、数据库或持久化。刷新、断开连接或重启可能丢失会话。材料会发送给所配置的模型提供商。

引用检查只证明引文存在，不能保证所有结论正确；主题名字由模型生成，语义近似主题仍需人工判断。提示词降低注入风险但不是绝对隔离。复盘是练习反馈，不是招聘结论。

详细教学见 [学习手册](LEARNING.md)。
