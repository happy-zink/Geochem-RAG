# 全量语料扩容交付报告（公开版）

日期：2026-09-29。私有来源清单和逐文件报告仅保存在本地 `data/private/full_corpus/`。

## 范围与命令

- `scripts/import_all_pdfs.py`：从本地 `PDF/` 逐份抽取、页内分块、按 SHA-256 去重并续跑。
- `scripts/build_full_index.py`：使用 SiliconFlow embedding API 建立可续跑向量缓存。
- `src/geochem_rag/retrieval.py`：增加常用中英地学术语查询扩展。
- `src/geochem_rag/answering.py`：界面 top-k 与证据数量对齐、支持部分证据回答；无有效引用时仅显示中性证据不足提示。
- `src/geochem_rag/app.py`：默认选择现有全量库，提供扩展解释开关，明确在线数据流。

```powershell
.\.venv\Scripts\python.exe scripts\import_all_pdfs.py
.\.venv\Scripts\python.exe scripts\import_all_pdfs.py --report-only
.\.venv\Scripts\python.exe scripts\build_full_index.py
.\.venv\Scripts\python.exe scripts\run_streamlit_online.py
```

## 本机语料结果

| 指标 | 数值 |
| --- | ---: |
| PDF 文件 | 87 |
| 唯一 SHA-256 / 入库来源 | 85 |
| 重复文件 | 2 |
| 证据块 | 6322 |
| 唯一文件 PDF 总页数 | 1889 |
| ok / empty / scanned / garbled 页 | 1588 / 18 / 21 / 262 |
| 导入硬失败 | 0 |

页数与质量分类均按唯一 SHA-256 统计，四类页合计为 1889。旧版报告的 1921 页按文件路径计数，包含两份重复文件；旧版质量分类漏计续跑文件。

本机已建立 `data/index/embeddings_full.json`，历史运行记录显示 6322 个向量。其他机器需要自行配置密钥并重新建索引。建索引时，文本证据块送往 SiliconFlow；在线问答时，问题和命中证据块送往 DeepSeek。原始 PDF 文件不上传，也不进入 Git。

## 验证边界

全量导入和索引并不等于回答质量已获验证。固定题集上的真实模型同条件检索对照、人工引用正确率和答案支持性标注仍待完成；不报告准确率或提升百分比。扫描页和乱码页没有 OCR 修复，可能影响检索。私有逐文件路径、原文片段、向量和 API 调用记录不随仓库发布。
