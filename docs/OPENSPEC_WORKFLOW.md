# OpenSpec 工作流程說明

更新：2026-10-04（P5）。本案採用 [OpenSpec](https://github.com/Fission-AI/OpenSpec) 管理本批（D44）工程變更規格。

## 版本與安裝（局部，非全域）

- CLI 版本：**1.14.0**（`@fission-ai/openspec`；npm 11.13.0 / node v24.16.0）
- 局部安裝於 `tools/openspec/`（`package.json`＋`node_modules/`；後者不入 Git）
- 執行前設 `OPENSPEC_TELEMETRY=0`
- CLI 路徑：`./tools/openspec/node_modules/.bin/openspec`

## 初始化紀錄（2026-10-04）

```
openspec init --tools none --language zh-TW   # 非互動；不覆寫既有 AGENTS 設定
```

產出 `openspec/`（config.yaml：schema spec-driven、zh-TW）、`openspec/changes/`、`openspec/specs/`。

## 本批 change：`prepare-tw01-proposal-package`

結構（4/4 artifacts complete，validate --strict 通過）：

| 檔案 | 內容 |
| --- | --- |
| `proposal.md` | Why/What/Capabilities（research-evidence、proposal-delivery） |
| `design.md` | 本批變更設計（文件批次、不動程式；舊 FINAL 文件保留歷史） |
| `specs/research-evidence/spec.md` | 主張可追溯（WHEN/THEN：成績可重算、UNKNOWN 不當否定、負向保留、B 標待驗證） |
| `specs/proposal-delivery/spec.md` | 跨文件一致、PPTX/PDF 實檔逐頁檢查、講者備註、範圍誠實 |
| `tasks.md` | P1–P6 對應勾選（7/11；6.x 投影片與 5.2 完成時回填） |

## 常用命令（Git Bash；PowerShell 用 `tools\\openspec\\node_modules\\.bin\\openspec`）

```
export OPENSPEC_TELEMETRY=0
./tools/openspec/node_modules/.bin/openspec list
./tools/openspec/node_modules/.bin/openspec status --change prepare-tw01-proposal-package
./tools/openspec/node_modules/.bin/openspec validate prepare-tw01-proposal-package --strict --no-interactive
```

真實輸出證據：`outputs/proposal_delivery/run1_20261004/openspec_cli_evidence.txt`。

## 流程與維護

需求→change（proposal/design/specs/tasks）→交付→`validate --strict`→（全部逐項驗收後才考慮 archive；本批保留可審閱狀態，不 archive、不用 `--no-validate`）。後續新批次：`openspec/changes/<新change>/`，根目錄 design.md 仍是正式藍圖，change 的 design 只記該批變更。

## 邊界

OpenSpec 管理工程變更規格，不取代學術 [PROPOSAL_REPORT](PROPOSAL_REPORT.md)；CLI 格式通過不代表系統功能驗收。
