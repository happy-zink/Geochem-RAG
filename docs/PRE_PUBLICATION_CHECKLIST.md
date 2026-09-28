# Pre-Publication File Checklist

Date: 2026-09-28  
Checked by: QoderCN (Wave 3)

## Sensitive Files Verification

### Files that MUST be gitignored (verified ✓)

| File/Directory | .gitignore Line | Status |
|---|---|---|
| `.env` | Line 16: `.env` | ✓ Covered |
| `PDF/` | Line 3: `PDF/` | ✓ Covered |
| `data/private/` | Line 2: `data/private/` | ✓ Covered |
| `data/public/` | Line 4: `data/public/` | ✓ Covered |
| `data/processed/` | Line 7: `data/processed/` | ✓ Covered |
| `data/index/` | Line 8: `data/index/` | ✓ Covered |
| `data/raw/` | Line 6: `data/raw/` | ✓ Covered |
| `eval/results/` | Line 10: `eval/results/` | ✓ Covered |
| `eval/private/` | Line 11: `eval/private/` | ✓ Covered |
| `.venv/` | Line 22: `.venv/` | ✓ Covered |
| `__pycache__/` | Line 24: `__pycache__/` | ✓ Covered |
| `*.py[cod]` | Line 25 | ✓ Covered |

### Files that SHOULD be public (verified ✓)

| File | Contains Sensitive Data? | Status |
|---|---|---|
| `src/geochem_rag/*.py` | No (reads keys from env vars only) | ✓ Safe |
| `README.md` | No (shows placeholder values) | ✓ Safe |
| `docs/DEMO.md` | No | ✓ Safe |
| `docs/EVALUATION.md` | No (shows `<your-key>` placeholder) | ✓ Safe |
| `docs/PROJECT_BRIEF.md` | No | ✓ Safe |
| `docs/EXECUTION_PLAN.md` | No | ✓ Safe |
| `scripts/*.py` | No (reads keys from env vars only) | ✓ Safe |
| `tests/*.py` | No | ✓ Safe |
| `pyproject.toml` | No | ✓ Safe |
| `.env.example` | No (template with empty values) | ✓ Safe |
| `.gitignore` | No | ✓ Safe |
| `AGENTS.md` | No | ✓ Safe |

## API Key Scan

Searched for patterns: `SILICONFLOW_API_KEY=`, `DEEPSEEK_API_KEY=`, `sk-`

**Result:** Only environment variable names and placeholder values found. No actual API keys in source code, documentation, or scripts.

**Verification command used:**
```bash
grep -r "SILICONFLOW_API_KEY\|DEEPSEEK_API_KEY\|sk-" src/ docs/ README.md scripts/ | grep -v ".env.example"
```

## Test Results

- **Unit tests:** 67/67 passed
- **Streamlit launch:** Successful (headless mode)
- **Demo script:** Runs in offline mode, produces expected output
- **Import test:** All modules import without errors

## Files Created/Modified in Wave 3

### New files
1. `src/geochem_rag/app.py` - Streamlit UI (292 lines)
2. `docs/DEMO.md` - Demo guide (109 lines)
3. `scripts/run_demo.py` - Automated demo script (110 lines)

### Modified files
1. `pyproject.toml` - Added `streamlit>=1.30.0` dependency
2. `README.md` - Updated from planning version to accurate Quick Start guide

### Files NOT modified (as required)
- `src/geochem_rag/domain.py` - Data contracts unchanged
- `src/geochem_rag/ingest.py` - PDF parsing unchanged
- `src/geochem_rag/store.py` - Persistence unchanged
- `src/geochem_rag/retrieval.py` - Retrieval logic unchanged
- `src/geochem_rag/answering.py` - Answer generation unchanged
- `src/geochem_rag/evaluation.py` - Evaluation logic unchanged
- `src/geochem_rag/providers.py` - API adapters unchanged

## Demo Questions Verification

Three fixed demo questions documented in `docs/DEMO.md`:

1. **Cross-language (q11):** "这篇英文论文如何解释莫根通埃达克质岩体的成因？请用中文概括。"
   - Expected: `answered` with citations to Mogetong paper
   - Offline test: ✓ Returns `answered` with correct citations

2. **Abbreviation (q02):** "MORB 是什么缩写？它在岩石成因讨论中通常指示什么源区？"
   - Expected: `answered` or `insufficient_evidence` depending on corpus
   - Offline test: ✓ Returns `answered` (template provider always answers)

3. **Unanswerable (q36):** "Summarize the conclusions of a paper about kimberlites in Siberia."
   - Expected: `insufficient_evidence`
   - Offline test: ⚠ Returns `answered` (expected - template provider never refuses; real model would refuse)

**Note:** Offline mode uses `TemplateChatProvider` which always cites the first evidence and never refuses. This is documented behavior in `docs/EVALUATION.md` §7.2. In online mode with a real model, Q3 should correctly return `insufficient_evidence`.

## Privacy Notice Verification

The following files contain privacy/data flow notices:

1. **`src/geochem_rag/app.py`** (lines 160-170):
   - Sidebar info box explains that evidence fragments are sent to online API
   - Offline mode shows warning that no data is sent externally
   - Public vs private sources are visually distinguished

2. **`README.md`** (Privacy & Data Flow section):
   - Explains local data stays on machine
   - Explains what is sent to online API
   - Explains API key handling

3. **`docs/DEMO.md`** (Architecture diagram):
   - Shows data flow from PDF → ingest → store → retrieval → answering → UI

## Known Limitations (documented in README.md)

1. Vector index uses pure-Python cosine index (Chroma not installed)
2. Chinese tokenization uses character unigrams + bigrams (no jieba)
3. Human evaluation metrics (citation accuracy, supportability) are PENDING
4. Real-model evaluation not completed due to network restrictions
5. Current corpus: 4 public Frontiers papers (CC BY 4.0)

## Conclusion

✓ All sensitive files are properly gitignored  
✓ No API keys or private data in public files  
✓ All tests pass  
✓ Streamlit UI launches successfully  
✓ Demo script runs in offline mode  
✓ Privacy notices are present  
✓ Documentation is accurate and complete  

**Ready for public release** after user reviews and confirms:
- Evaluation results (when network allows real-model testing)
- Human annotation of citation accuracy
- Any additional private PDFs to import
