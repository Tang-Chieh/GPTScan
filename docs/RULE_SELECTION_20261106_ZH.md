# 規則調整：保留七條原版規則（2026-11-06）

目前 `price` profile 載入下列七個 upstream 規則：

| 檔案 | 原版標題 | 新增 impact 的重點 |
|---|---|---|
| Flashloan_Price.yml | MWE-200: Insecure LP Token Value Calculation | LP 估值被操縱，影響金融操作金額 |
| FirstDeposit.yml | MWE-204: Unsafe First Deposit | 首次存款影響後續 share issuance，可能使存戶損失 |
| Flashloan_Buy.yml | MWE-202: Insecure Token Buying Behavior | 操縱交易執行價格，造成 sandwich／不利成交 |
| Flashloan_Vote.yml | MWE-201: Insecure Vote Calculation | 暫借 token 膨脹投票權，影響治理 |
| FrontRun.yml | MWE-205: Front Running | 搶跑分離的資產轉入／mint 或領取流程，重導收款權益 |
| WrongOrder_Checkpoint.yml | MWE-208: Wrong Order for Checkpoint | checkpoint 順序造成錯誤權益或帳務歸屬 |
| WrongOrder_Interest.yml | MWE-209: Wrong Order for Interest or ExchangeRate | 利息／匯率更新順序造成 stale accounting |

## 本次修改邊界

- 刪除我們新增的 `src/rules/OraclePrice.yml`。
- 七條規則以原版內容為準，僅在 `output` 加上 `impact`，不修改 `recommendation`（包含原文措辭）、`description`、properties、篩選條件、prompt 或 static checker。
- Flashloan_Price 的 recommendation 恢復 upstream 原文；先前較長的 recommendation 不再使用。
- `impact` 是開發時補充的保守規則模板，不是模型逐筆生成、不是 ground truth，也不是已確認的實際攻擊後果。
- `src/profiles.py` 的 price selection 改為上表七條。general 仍讀取所有現存原版規則。
- 模型 system prompt 仍保留先前的 price focus；本次沒有修改模型連接、adapter、compiler 或 Judge。
- 七條規則含治理、first deposit 與 order-of-operations 等類型，不表示它們每條都嚴格等同 price manipulation。這是使用者指定的規則組，實際結果仍受到既有 price-focused system prompt 影響。

## 驗證與歷史資料

已以本機 upstream commit `29a174773bd526c32ab7d6a8c78a63870330ccc7` 逐條比對：移除新增的 `output.impact` 後，七條 YAML 結構均與原版相同。回歸測試保存 canonical baseline hashes，保護原 recommendation 與偵測欄位不被修改。

`tests/runtime_smoke.py` 的 synthetic positive fixture 改用既有 LP rule 可辨識的函式名稱，不再依賴已刪除的 OraclePrice rule；這只是測試 fixture，不修改 dataset 原始碼。

之前 23 repo 的 204 findings 與 Judge 報告，仍屬於舊的「Flashloan_Price + OraclePrice」設定。本次只改程式／測試，不重新執行 dataset 或 Judge，不重寫既有結果，也沒有 commit／push。歷史文件內的兩條規則說明仍描述舊實驗，不能視為目前設定。
