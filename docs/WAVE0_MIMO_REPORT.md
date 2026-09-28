# Wave 0 交付报告（MIMO）

> 后续用户补充（2026-09-28）：不需要在线下载文献；用户已有资料位于 `PDF/`。本报告记录此前流水线验证的历史状态；后续工作按根目录 `AGENTS.md` 与 `docs/agents/MIMO.md` 的本地语料规则执行。现有 `data/public/` 样本保留但不自动作为正式公开演示数据。

> 后续接口更新：`Source` 已升级到 0.2.0，私有 PDF 可不填书目信息直接导入。当前契约以 `docs/CONTRACT_MIGRATION_0.2.md` 和代码为准；下文 0.1.0 是 MIMO 当时交付的历史版本。

状态：数据契约、导入/去重模块、离线测试与评估题初稿已完成。正式公开语料以用户后续提供的 PDF 为准；当前 `data/public/` 中 4 篇 Frontiers 样本仅用于打通与验证流水线，许可均已逐篇核对为 CC BY 4.0。

**数据契约版本**：`0.1.0`（见 `src/geochem_rag/domain.py` 的 `CONTRACT_VERSION`）

## 修改文件

| 路径 | 说明 |
| --- | --- |
| `pyproject.toml` | 包元数据、pytest 配置 |
| `src/geochem_rag/__init__.py` | 包入口 |
| `src/geochem_rag/domain.py` | Source / EvidenceChunk / SearchHit / Answer / Citation 与稳定 ID |
| `src/geochem_rag/ingest.py` | PDF 逐页抽取、质量标记、页内分块 |
| `src/geochem_rag/store.py` | 本地 JSONL 存储、SHA-256 去重、可见性过滤 |
| `src/geochem_rag/import_pdf.py` | 单文件导入 CLI |
| `tests/test_domain.py` | 契约离线测试 |
| `tests/test_ingest.py` | 页码/分块/质量离线测试 |
| `tests/test_store.py` | 去重/替换/删除离线测试 |
| `data/sources.json` | 公开样本来源清单（含许可证明） |
| `docs/schemas/contract_samples.json` | 跨模块样例 JSON |
| `eval/questions.jsonl` | 40 道评估题初稿（待用户地学审核） |
| `scripts/run_import_check.py` | 一次导入 + 重复导入核对脚本 |

## 数据契约摘要

- **Source**：`source_id`, `title`, `authors`, `year`, `doi_or_url`, `license`, `license_url`, `sha256`, `visibility`, `download_date`；公开源必须有 http(s) `license_url`。
- **EvidenceChunk**：`chunk_id`, `source_id`, `pdf_page`（从 1 开始）, `text`, `section`, `quality`, `chunk_index`, `sha256`。块不跨页；`chunk_id = chk_<sha16>_p<page>_c<index>`，同一 PDF 字节 + 同一分块规则可复现。
- **SearchHit**：`chunk_id`, `score`, `rank`, `retrievers`（含 dense/bm25 分数）。
- **Answer**：`status` ∈ `answered|insufficient_evidence|error`，`citations ⊆ evidence`；`answered` 至少 1 条引用。

样例见 `docs/schemas/contract_samples.json`。

## 运行与测试命令

```powershell
# 环境（已建 .venv）
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install pypdf pytest

# 离线测试
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -m pytest tests -q

# 导入单篇（示例）
.\.venv\Scripts\python.exe -m geochem_rag.import_pdf --pdf data/public/feart_2022_845763.pdf --meta data/sources.json --store data/processed

# 批量导入 + 重复导入去重核对
.\.venv\Scripts\python.exe scripts\run_import_check.py
```

测试结果：**22 passed**（`tests/test_domain.py`, `test_ingest.py`, `test_store.py`），不依赖在线 API。

## 页统计（当前 4 篇样本）

| source_id | 文件 | 页数 | 成功(quality=ok) | 失败页 | 块数 | 重复导入 |
| --- | --- | ---: | ---: | --- | ---: | --- |
| src_feart_2022_845763 | feart_2022_845763.pdf | 17 | 17 | 无 | 74 | already_exists，块数不变 |
| src_feart_2021_665610 | feart_2021_665610.pdf | 15 | 15 | 无 | 51 | already_exists，块数不变 |
| src_feart_2022_927695 | feart_2022_927695.pdf | 17 | 17 | 无 | 64 | already_exists，块数不变 |
| src_feart_2024_1497913 | feart_2024_1497913.pdf | 21 | 21 | 无 | 73 | already_exists，块数不变 |

合计：70 页，262 块。4 篇均为 born-digital，当前无扫描页/空页。扫描页或抽取失败页会在 `IngestReport.failed_pages` 与 `warnings` 中显式列出（单元测试覆盖 blank PDF → `empty` 页）。

## 重复导入验证

`scripts/run_import_check.py` 对每篇连续 `import_document` 两次：

- 第一次：`imported`，写入 N 块
- 第二次：`already_exists`（按 SHA-256 去重），`count_chunks(source_id)` 仍为 N

SHA 变更场景由测试 `test_sha_change_invalidates_old_chunks` 覆盖：同一 `source_id` 新 PDF 字节 → `replaced`，旧块失效，仅保留新集合。

## 人工核对记录（chunk_id → PDF 页 → 原文）

以下三条用 `extract_pages` 回读 PDF 第 N 页，确认块文本来自该页：

1. `chk_6ee572d18962b49b_p0012_c004` → **feart_2022_845763.pdf 第 12 页**  
   页内原文含：`The Mogetong adakitic quartz monzonite porphyries have high Mg # values (Mg # =4 7 – 55; ...`（页字符数 4702，quality=ok）

2. `chk_9bb22fb9be3b7cf8_p0009_c000` → **feart_2021_665610.pdf 第 9 页**  
   页内原文含：`FIGURE 8 | Rayleigh fractionation modal calculations for trace elements (A) Cr-Ni, (B) Nb-Ta.`（页字符数 2203，quality=ok）

3. `chk_f07c2e962e9992e9_p0011_c002` → **feart_2024_1497913.pdf 第 11 页**  
   页内原文含：`Incremental heating plateau ages are according to the definition of Fleck et al. (1977)`（页字符数 3190，quality=ok）

复核方法：`geochem_rag.ingest.extract_pages(pdf)` 取 `pdf_page`（1-based）全文，确认关键短语落在该页。

## 评估题初稿

`eval/questions.jsonl` 共 40 题：

- 术语/缩写 10（q01–q10）
- 跨中英检索 10（q11–q20）
- 跨文献比较 10（q21–q30）
- 不可回答/证据冲突/防幻觉 10（q31–q40）

所有题的 `status = draft_pending_user_science_review`。`answer_points` 仅为草案，**不作为已锁定科学标准答案**；`expected_pages` 待用户替换语料并审核后填写。q31–q40 覆盖证据不足拒答、范围外计算、伪造页码、虚构 DOI 等场景。

## 已知限制

1. **表格/图件**：单元格级定位与 OCR 不在第一版；仅能引用页内可提取文本。
2. **字体编码**：部分 Frontiers PDF 的 CFF 字体缺 fontTools 时 pypdf 会告警；已把 pypdf logger 降到 ERROR，文本抽取仍可用。若后续出现乱码页，会标记 `garbled` 并进 `failed_pages`。
3. **分块边界**：按段落/句内粘合，`max_chars` 默认 1200；同一 PDF 重复导入 ID 稳定，但若改分块参数会产生新 `chunk_index` 从而新 ID。
4. **语料范围**：当前 4 篇为流水线验证样本；用户提供的正式 PDF 需重新：许可逐篇确认 → 写入 `data/sources.json` → `run_import_check.py`。
5. **私有资料**：`data/private/` 由用户稍后放入；不提交 Git、不上传在线解析服务。

## 交接给 CODEartsAgent / QoderCN

- 字段语义以 `domain.py` + `docs/schemas/contract_samples.json` 为准；改契约需先写迁移说明。
- 检索/回答/前端请只依赖上述对象，不要改动 `ingest.py` / `store.py` 的页码与 ID 规则。
- 存储位置：`data/processed/sources.jsonl` 与 `chunks.jsonl`（已在 `.gitignore`）。
