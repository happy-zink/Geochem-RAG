# 接口变更通知：全量语料扩容与检索/回答调整

自：MIMO（经用户 2026-09-29 明确授权处理）
致：CODEartsAgent、QoderCN
优先级：覆盖旧任务书中“试验子集 3–5 篇 / 勿改 app·retrieval·answering”的分工限制。

## 变更范围（即将修改）

| 模块 | 变更 |
| --- | --- |
| `retrieval.py` | 中文分词/查询扩展增强（仍保留 unigram+bigram 与术语词典）；接口签名尽量兼容 |
| `answering.py` | `answer(..., top_k)` 与 UI 对齐；证据截断提高；部分证据回答；可选“扩展解释”字段与论文结论分离 |
| `app.py` | top-k 传入回答器；扩展解释开关；数据流说明含 SiliconFlow 建索引 |
| 新脚本 | `scripts/import_all_pdfs.py`（可续跑全量入库）、`scripts/build_full_index.py`（embedding 断点续跑） |

## 约定不变

- `Source` / `EvidenceChunk` / `Answer` 契约 **0.2.0** 字段语义不变。
- `pdf_page` 仍为 1-based PDF 页序号；`chunk_id` 规则不变。
- 仍禁止虚构来源、页码、DOI、数值；无证据仍返回 `insufficient_evidence`。
- 私有 PDF / 抽取文本 / 全量索引均不进 Git。

## 全量语料路径

- 试验库（保留）：`data/private/wave0_trial/`
- 历史验证库（保留）：`data/processed/` + `data/public/`
- **全量库（新增）**：`data/private/full_corpus/`
- **全量 embedding 缓存（新增）**：`data/index/embeddings_full.json`

## 数据流（请写入界面/README）

1. **建索引**：私有证据块全文 → SiliconFlow embedding API
2. **在线回答**：用户问题 + 命中证据块 → DeepSeek chat API

请勿把整本 PDF 上传到在线解析服务。

## Answer 新增可选字段（向后兼容）

- `meta.unsupported_aspects: list[str]` — 证据未覆盖的部分
- `meta.extended_explanation: str | null` — 仅当用户勾选“扩展解释”时出现，**不得**带论文引用伪装
- `meta.evidence_truncated: bool` — 是否发生截断

`status` 仍仅 `answered | insufficient_evidence | error`；部分支持仍可为 `answered`，但正文必须标明未覆盖部分。
