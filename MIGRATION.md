# Repository Migration Notes

## Origin and reconstructed history

This project was migrated from the final source export of GitBook, according to the repository owner's account. The original platform's successive source snapshots and Git-format commit history were not exported.

The first 32 commits were reconstructed locally from the exported source, in functional dependency order. Intermediate implementations were assembled and validated as independent snapshots. They represent a documented reconstruction, not recovered original commits or exact original platform snapshots.

Their dates, from September 8 through October 7, 2026, are owner-approved suggested reconstruction times, not independently recovered original timestamps. The 33rd migration commit uses the actual execution time for both author and committer, in America/Los_Angeles. Its Git metadata records that real time.

The previous local repository contained 10 commits. Its old local Git history was cleared and the repository reinitialized with the owner's approval before this reconstruction.

## Minimal test corrections

迁移时对两个测试文件各做了一行最小修正，使其与现有业务代码一致；这两项测试修正未改动业务代码：

- `tests/test_llm_structured.py`: added `thinking=True` to the test double's function signature because the existing model function already accepts and receives that parameter.
- `tests/test_observability_api.py`: changed the expected `in_sync` value from `False` to `"conservative"`. The existing business implementation returns that string when the active threshold exceeds the recommendation; this test uses 0.5 versus 0.26.

Against the saved pre-reconstruction comparison baseline of 305 eligible files, 303 files remain byte-for-byte identical and the two test files differ by exactly one line each. This document is newly added. Before that baseline was saved, owner-approved credential hygiene changes had already removed embedded database URL credentials, replaced `.env.example` examples with obvious placeholders, and updated ignore rules. The byte-for-byte comparison refers to that saved baseline, not an untouched original export.

## Documents and datasets

Original document filenames and contents are retained, including the 20 files under `docs/superpowers/` whose names contain July 2026 dates. Filename dates are not used as commit timestamps.

Both datasets are retained without additional redaction, as explicitly approved by the owner:

| Dataset location | train.jsonl | val.jsonl | test.jsonl | Total records |
| --- | ---: | ---: | ---: | ---: |
| `data/ch10/dataset/` | 34 | 0 | 0 | 34 |
| `mewhelp-ch10-dataset/` | 2,594 | 161 | 161 | 2,916 |

The external dataset was copied into the repository from the sibling `mewhelp-ch10-dataset/` directory; the two empty internal validation/test files are retained.

## Excluded local files

Real `.env` files and their variants are excluded, with only `.env.example` allowed. `docker-compose.yml.bak`, virtual environments, caches, logs, runtime databases, PID files, generated reports, and generated model/ONNX artifacts are excluded according to the approved `.gitignore`. Local development credentials in the original Docker, Makefile, and documentation examples remain as previously approved.

## Validation and publication

All 32 reconstructed snapshots passed their recorded local tests after the two approved test corrections. Snapshot 32 completed with 480 passed, 7 skipped, and no failures. Validation used the existing project virtual environment; clean installation of every historical dependency set was not demonstrated.

SQLite substitutes and a persistence-only Milvus test double cover the recorded local behavior. Real MySQL-specific DDL, Milvus/BM25 behavior, external model quality, model training/ONNX export, and browser visual rendering were not marked as verified. Two MCP integration cases were separately verified using real local HTTP service subprocesses at snapshot 24; unchanged server files were retained afterward.

The migration was performed locally. No Git remote was configured and no push was performed during migration. Publication requires the owner's separate approval.
