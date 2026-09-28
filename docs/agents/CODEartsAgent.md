# CODEartsAgent 执行任务书

状态：按用户后续开发指令执行。先读根目录 `AGENTS.md`、设计、执行计划和 `docs/CONTRACT_MIGRATION_0.2.md`。本地私有语料的新版 `domain.py` 契约已就绪；不得自行在线下载文献。

## 负责范围

负责 Wave 1–2：SiliconFlow 调用适配、dense/BM25/RRF 检索、证据约束回答与引用校验、离线替身测试、固定评估与实验报告。主要文件：`src/geochem_rag/providers.py`、`retrieval.py`、`answering.py`、`evaluation.py`、`.env.example`、对应测试与 `docs/EVALUATION.md`。不要接管 PDF 解析或 Streamlit 页面。

## 实施要求

1. 通过配置使用 SiliconFlow 的 chat 和 embedding API。实际模型 ID 以开发时平台可用模型为准，记录名称、版本、调用参数和费用估算；不得依赖曾经存在但现已下线的模型。API 密钥仅来自环境变量。
2. `retrieve(question, mode)` 至少支持 `dense_only` 与 `hybrid`，返回可追溯 `SearchHit`。查询扩展词典应保留原查询，不覆盖用户输入；RRF 的参数写入评估记录。
3. `answer(question, hits)` 的输出遵循 `Answer` 契约：所有可见引用都必须来自本次 hits；无证据时拒答。模型输出错误引用时明确处理，不能直接把模型字符串显示给用户。禁止 `eval`、`exec` 或动态执行模型生成代码。
4. 使用 mock provider 测试成功和错误路径。在线集成测试受配额限制可以单独标记，但交付前至少完成一次真实 SiliconFlow 端到端请求并记录结果，不保存密钥或私有证据全文。
5. 评估把检索指标、引用指标与答案支持性分开；比较策略时保持相同语料、问题、聊天模型和配置。Ragas 只是补充，不代替人工核对。

## 验收与交接

提交运行命令、离线测试结果、一次匿名化在线调用记录、评估结果文件和失败案例。将对 QoderCN 暴露的调用签名与返回示例写进 `docs/EVALUATION.md` 或接口说明；接口变更先通知协调者。
