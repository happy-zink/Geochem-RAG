# Source 契约 0.2.0 交接说明

为支持用户把已有 PDF 手动放入 `PDF/`，`Source` 从 0.1.0 升级到 0.2.0。其他对象的字段未变。

- 私有来源的 `authors` 可以是空列表；`year`、`doi_or_url`、`license`、`license_url`、`download_date` 可以是 `null`。不要补造未知作者、出版年或 DOI。
- 新字段 `title_is_filename: bool` 表示 `title` 仅由文件名暂代。界面展示时应区分“文件名”与已核实论文标题。
- 公开来源仍须提供作者、年份、DOI/URL、下载日期和许可证明链接，且标题不能仅由文件名暂代。
- 旧 0.1.0 的公开来源 JSON 可以由新版 `Source.from_dict()` 读取，新字段默认为 `false`。
- 不带 `--meta` 的 `import_pdf` 命令按 `private` 导入，`source_id` 由文件的解析后绝对路径生成；同一路径替换 PDF 后重导入会删除旧块。重复内容返回 `already_exists`，只补充书目信息返回 `metadata_updated`。
- `scripts/run_import_check.py` 现使用独立临时存储，不会清空默认的 `data/processed/`。

手动导入命令见根目录 `README.md`。CODEartsAgent 和 QoderCN 在读取 `Source` 元数据时应处理 `null`，不能假设 `source.authors[0]`、`source.year` 或 `source.doi_or_url` 一定存在。
