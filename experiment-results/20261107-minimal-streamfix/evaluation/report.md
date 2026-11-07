# Benchmark Evaluation Report

> Derived from canonical Evaluation artifacts. This report does not execute LLM requests.

## Executive Summary

| Metric | Value |
| --- | --- |
| Report version | 0.2 |
| Benchmark version | v1 |
| Repositories | 23 |
| Ground Truth findings | 42 |
| Predictions | 92 |
| Total matched predictions | 8 |
| Total matched weight | 4.4500 |
| Pooled soft precision | 0.0484 |
| Pooled soft recall | 0.1060 |
| Macro soft F1 | 0.0614 |
| Pooled soft F1 | 0.0664 |

## Evaluation Configuration

| Field | Value |
| --- | --- |
| Matching strategy | greedy |
| Threshold | 0.5000 |
| Weight profile | end-to-end-v2 |
| Judge model | gpt-5.6-luna |
| Judge prompt version | benchmark-judge-v3 |
| Detector version | gptscan-price-minimal-upstream7-v3 |
| Detector model | openai-codex/gpt-5.6-luna |
| Manifest SHA-256 | e88ce520f7a19668638329548caae81969e985c0dc7544c21bf6a685d32adac9 |

## Repository Summary

| Repository | Ground Truth | Predictions | Matched Predictions | Matched weight | Precision | Recall | Soft F1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `2021-04-marginswap` | 1 | 2 | 1 | 0.5500 | 0.2750 | 0.5500 | 0.3667 |
| `2021-07-spartan` | 3 | 5 | 2 | 1.2000 | 0.2400 | 0.4000 | 0.3000 |
| `2021-08-notional` | 2 | 3 | 0 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `2021-11-malt` | 3 | 1 | 0 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `2021-12-vader` | 4 | 5 | 1 | 0.5500 | 0.1100 | 0.1375 | 0.1222 |
| `2022-01-behodler` | 2 | 10 | 0 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `2022-01-sandclock` | 2 | 0 | 0 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `2022-08-sentiment` | 2 | 0 | 0 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `2022-09-notional` | 1 | 4 | 0 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `2022-11-paraspace` | 4 | 0 | 0 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `2022-11-telcoin` | 1 | 0 | 0 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `2023-03-olympus` | 1 | 1 | 0 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `2023-04-blueberry` | 1 | 4 | 1 | 0.5000 | 0.1250 | 0.5000 | 0.2000 |
| `2023-05-ussd` | 2 | 0 | 0 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `2023-06-lybra` | 1 | 3 | 0 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `2023-06-real-wagmi` | 1 | 6 | 1 | 0.5500 | 0.0917 | 0.5500 | 0.1571 |
| `2023-06-tokemak` | 1 | 9 | 1 | 0.5500 | 0.0611 | 0.5500 | 0.1100 |
| `2023-08-dopex` | 2 | 1 | 0 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `2024-03-abracadabra-money` | 2 | 5 | 1 | 0.5500 | 0.1100 | 0.2750 | 0.1571 |
| `2024-03-revert-lend` | 1 | 13 | 0 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `2024-03-woofi-swap` | 1 | 11 | 0 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `2024-04-panoptic` | 1 | 3 | 0 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| `2025-12-panoptic` | 3 | 6 | 0 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |

## Repository Details

### `2021-04-marginswap`

| Metric | Value |
| --- | --- |
| Ground Truth findings | 1 |
| Predictions | 2 |
| Matched weight | 0.5500 |
| Soft precision | 0.2750 |
| Soft recall | 0.5500 |
| Soft F1 | 0.3667 |

#### Matched Findings

| Ground Truth | Prediction | R | L | I | M | Weighted |
| --- | --- | --- | --- | --- | --- | --- |
| H-03 — [H-03] Price feed can be manipulated | GPTSCAN-9775da266872fbd6 — MWE-200: Insecure LP Token Value Calculation | 2/4 | 3/4 | 2/4 | 2/4 | 0.5500 |

<details>
<summary>Pair 1: H-03 — [H-03] Price feed can be manipulated ↔ GPTSCAN-9775da266872fbd6 — MWE-200: Insecure LP Token Value Calculation</summary>

- **Ground Truth:** `H-03`
- **Prediction:** `GPTSCAN-9775da266872fbd6`

#### Ground Truth locations

| File | Contract | Function | Lines |
| --- | --- | --- | --- |
| contracts/PriceAware.sol | PriceAware | getCurrentPriceInPeg(address,uint256,bool) | 60–87 |
| contracts/PriceAware.sol | PriceAware | getPriceFromAMM(address,uint256) | 111–137 |

#### Prediction locations

| File | Contract | Function | Lines |
| --- | --- | --- | --- |
| contracts/PriceAware.sol | PriceAware | getCurrentPriceInPeg(address,uint256,bool) | 60–87 |

#### Judge rationale

```text
R: Correctly identifies flash-loan manipulation of an AMM-derived price, but frames it specifically as LP-token valuation rather than the broader current spot token-price feed and reserve distortion. L: Correctly identifies PriceAware.getCurrentPriceInPeg, though it omits the related getPriceFromAMM operation. I: Captures mispricing and distorted financial outcomes, but does not specifically identify the protocol’s borrowing, margin, or liquidation consequences and narrows the scope to liquidity positions. M: Avoiding AMM-based valuation is directionally relevant, but it is vague and does not specify replacing the manipulable spot quote with a cumulative-price TWAP across the affected path.
```

</details>

#### Unmatched Ground Truth

No unmatched Ground Truth findings.

#### Unmatched Predictions

- GPTSCAN-1820dda09211b749 — MWE-209: Wrong Order for Interest or ExchangeRate

### `2021-07-spartan`

| Metric | Value |
| --- | --- |
| Ground Truth findings | 3 |
| Predictions | 5 |
| Matched weight | 1.2000 |
| Soft precision | 0.2400 |
| Soft recall | 0.4000 |
| Soft F1 | 0.3000 |

#### Matched Findings

| Ground Truth | Prediction | R | L | I | M | Weighted |
| --- | --- | --- | --- | --- | --- | --- |
| H-05 — [H-05] Synth realise is vulnerable to flash loan attacks | GPTSCAN-b6c928f4096b1f12 — MWE-200: Insecure LP Token Value Calculation | 3/4 | 4/4 | 2/4 | 2/4 | 0.7000 |
| M-14 — [M-14] BondVault `BASE` incentive can be gamed | GPTSCAN-a0e995bb024a4c0a — MWE-200: Insecure LP Token Value Calculation | 2/4 | 2/4 | 2/4 | 2/4 | 0.5000 |

<details>
<summary>Pair 1: H-05 — [H-05] Synth realise is vulnerable to flash loan attacks ↔ GPTSCAN-b6c928f4096b1f12 — MWE-200: Insecure LP Token Value Calculation</summary>

- **Ground Truth:** `H-05`
- **Prediction:** `GPTSCAN-b6c928f4096b1f12`

#### Ground Truth locations

| File | Contract | Function | Lines |
| --- | --- | --- | --- |
| contracts/Synth.sol | Synth | realise(address) | 187–199 |
| contracts/Utils.sol | Utils | calcLiquidityHoldings(uint,address,address) | 114–125 |
| contracts/Utils.sol | Utils | calcActualSynthUnits(uint,address) | 210–216 |

#### Prediction locations

| File | Contract | Function | Lines |
| --- | --- | --- | --- |
| contracts/Utils.sol | Utils | calcLiquidityHoldings(uint256,address,address) | 114–125 |

#### Judge rationale

```text
R: Correctly identifies manipulation of the liquidity-holdings valuation used in the vulnerability, with minor omission of the synth-value comparison and resulting burn. L: Correctly identifies Utils.calcLiquidityHoldings(), one of the ground-truth vulnerable valuation operations. I: Describes general mispricing and potential loss, but omits the concrete attacker capability and value extraction from other pool LP holders. M: Avoiding spot/custom AMM valuation is relevant, but the mitigation lacks a concrete manipulation-resistant replacement.
```

</details>

<details>
<summary>Pair 2: M-14 — [M-14] BondVault \`BASE\` incentive can be gamed ↔ GPTSCAN-a0e995bb024a4c0a — MWE-200: Insecure LP Token Value Calculation</summary>

- **Ground Truth:** `M-14`
- **Prediction:** `GPTSCAN-a0e995bb024a4c0a`

#### Ground Truth locations

| File | Contract | Function | Lines |
| --- | --- | --- | --- |
| contracts/Dao.sol | Dao | bond(address,uint256) | 239–253 |
| contracts/Utils.sol | Utils | calcSwapValueInBase(address,uint) | 170–173 |
| contracts/Utils.sol | Utils | calcSwapValueInBaseWithPool(address,uint) | 198–202 |

#### Prediction locations

| File | Contract | Function | Lines |
| --- | --- | --- | --- |
| contracts/Utils.sol | Utils | calcAsymmetricValueToken(address,uint256) | 142–148 |

#### Judge rationale

```text
R: Recognizes manipulable pool-based token valuation, but misstates the specific mechanism and affected calculation; the ground truth concerns BASE value computed for bonding. L: Utils and a pricing-related function are adjacent to the vulnerable area, but calcAsymmetricValueToken() is not calcSwapValueInBase() or its pool helper. I: Describes general manipulated pricing causing incorrect payouts/loss, but not theft of DAO bond allocation through manipulated BASE incentives and reversal. M: Removing manipulable AMM/custom pricing could address the issue in principle, but the proposal is incomplete and does not explicitly secure the bond calculation with TWAP or another manipulation-resistant reference.
```

</details>

#### Unmatched Ground Truth

- H-06 — [H-06] SynthVault rewards can be gamed

#### Unmatched Predictions

- GPTSCAN-99003c027580631c — MWE-201: Insecure Vote Calculation
- GPTSCAN-4967e8b89e9c8dbc — MWE-200: Insecure LP Token Value Calculation
- GPTSCAN-fdcd9144516a3cd0 — MWE-200: Insecure LP Token Value Calculation

### `2021-08-notional`

| Metric | Value |
| --- | --- |
| Ground Truth findings | 2 |
| Predictions | 3 |
| Matched weight | 0.0000 |
| Soft precision | 0.0000 |
| Soft recall | 0.0000 |
| Soft F1 | 0.0000 |

#### Matched Findings

| Ground Truth | Prediction | R | L | I | M | Weighted |
| --- | --- | --- | --- | --- | --- | --- |
| No matched findings. | | | | | | |

#### Unmatched Ground Truth

- H-10 — [H-10] Liquidity token value can be manipulated
- M-07 — [M-07] Attackers can force liquidations by borrowing large amounts of an asset.

#### Unmatched Predictions

- GPTSCAN-3903369141c197df — MWE-200: Insecure LP Token Value Calculation
- GPTSCAN-9e7ab9eda5fa09b6 — MWE-200: Insecure LP Token Value Calculation
- GPTSCAN-e05a9a69808b4ea8 — MWE-200: Insecure LP Token Value Calculation

### `2021-11-malt`

| Metric | Value |
| --- | --- |
| Ground Truth findings | 3 |
| Predictions | 1 |
| Matched weight | 0.0000 |
| Soft precision | 0.0000 |
| Soft recall | 0.0000 |
| Soft F1 | 0.0000 |

#### Matched Findings

| Ground Truth | Prediction | R | L | I | M | Weighted |
| --- | --- | --- | --- | --- | --- | --- |
| No matched findings. | | | | | | |

#### Unmatched Ground Truth

- M-22 — [M-22] `_calculateMaltRequiredForExit` Uses Spot Price To Calculate Malt Quantity In `exitEarly`
- M-25 — [M-25] AMM Pool Can Be Drained Using a Flash Loan and Calling `stabilize`
- M-30 — [M-30] Malt Protocol Uses Stale Results From `MaltDataLab` Which Can Be Abused By Users

#### Unmatched Predictions

- GPTSCAN-a80f7033b5ae1369 — MWE-202: Insecure Token Buying Behavior

### `2021-12-vader`

| Metric | Value |
| --- | --- |
| Ground Truth findings | 4 |
| Predictions | 5 |
| Matched weight | 0.5500 |
| Soft precision | 0.1100 |
| Soft recall | 0.1375 |
| Soft F1 | 0.1222 |

#### Matched Findings

| Ground Truth | Prediction | R | L | I | M | Weighted |
| --- | --- | --- | --- | --- | --- | --- |
| H-06 — [H-06] LPs of VaderPoolV2 can manipulate pool reserves to extract funds from the reserve. | GPTSCAN-e835e95570d044ee — MWE-200: Insecure LP Token Value Calculation | 2/4 | 4/4 | 1/4 | 2/4 | 0.5500 |

<details>
<summary>Pair 1: H-06 — [H-06] LPs of VaderPoolV2 can manipulate pool reserves to extract funds from the reserve. ↔ GPTSCAN-e835e95570d044ee — MWE-200: Insecure LP Token Value Calculation</summary>

- **Ground Truth:** `H-06`
- **Prediction:** `GPTSCAN-e835e95570d044ee`

#### Ground Truth locations

| File | Contract | Function | Lines |
| --- | --- | --- | --- |
| contracts/dex-v2/pool/BasePoolV2.sol | BasePoolV2 | _burn(uint256,address) | 203–246 |
| contracts/dex-v2/pool/VaderPoolV2.sol | VaderPoolV2 | burn(uint256,address) | 265–296 |
| contracts/dex/math/VaderMath.sol | VaderMath | calculateLoss(uint256,uint256,uint256,uint256) | 72–92 |
| contracts/dex-v2/router/VaderRouterV2.sol | VaderRouterV2 | removeLiquidity(address,address,uint256,uint256,uint256,address,uint256) | 173–221 |

#### Prediction locations

| File | Contract | Function | Lines |
| --- | --- | --- | --- |
| contracts/dex-v2/pool/BasePoolV2.sol | BasePoolV2 | _burn(uint256,address) | 203–246 |

#### Judge rationale

```text
R: Correctly recognizes that manipulable pool-derived LP valuation inputs can be abused, but omits the specific artificial impermanent-loss calculation and reserve reimbursement mechanism. L: Correctly identifies BasePoolV2._burn(), which is one of the vulnerable code paths. I: Mentions possible incorrect payouts or loss only generically and does not identify VADER compensation or profitable reserve extraction. M: Avoiding AMM/custom spot-based valuation is directionally relevant, but it does not specify a manipulation-resistant oracle such as a TWAP and is incomplete.
```

</details>

#### Unmatched Ground Truth

- H-04 — [H-04] Vader TWAP weights can be corrupted and price queries can be forced to revert.
- H-07 — [H-07] Synth minting and redemption use manipulable pool reserves to drain native assets.
- M-06 — [M-06] Manipulated pool reserves can make the oracle rely on a single pair.

#### Unmatched Predictions

- GPTSCAN-d514b130be66a381 — MWE-200: Insecure LP Token Value Calculation
- GPTSCAN-a46119f216a2358d — MWE-205: Front Running
- GPTSCAN-538393dbc277a91a — MWE-200: Insecure LP Token Value Calculation
- GPTSCAN-652f633117693a5e — MWE-200: Insecure LP Token Value Calculation

### `2022-01-behodler`

| Metric | Value |
| --- | --- |
| Ground Truth findings | 2 |
| Predictions | 10 |
| Matched weight | 0.0000 |
| Soft precision | 0.0000 |
| Soft recall | 0.0000 |
| Soft F1 | 0.0000 |

#### Matched Findings

| Ground Truth | Prediction | R | L | I | M | Weighted |
| --- | --- | --- | --- | --- | --- | --- |
| No matched findings. | | | | | | |

#### Unmatched Ground Truth

- H-05 — [H-05] Flash loan price manipulation in purchasePyroFlan()
- H-07 — [H-07] LP pricing formula is vulnerable to flashloan manipulation

#### Unmatched Predictions

- GPTSCAN-44f19166cd311af9 — MWE-200: Insecure LP Token Value Calculation
- GPTSCAN-126f03bedae44d8a — MWE-200: Insecure LP Token Value Calculation
- GPTSCAN-0bb4d2266441241d — MWE-205: Front Running
- GPTSCAN-d92febfa742840ca — MWE-200: Insecure LP Token Value Calculation
- GPTSCAN-0617c9b39ec079d4 — MWE-200: Insecure LP Token Value Calculation
- GPTSCAN-4e1a9f2d61f32f2c — MWE-200: Insecure LP Token Value Calculation
- GPTSCAN-a317e65c93a90d86 — MWE-200: Insecure LP Token Value Calculation
- GPTSCAN-5d5010861b052c87 — MWE-200: Insecure LP Token Value Calculation
- GPTSCAN-d19a6a3bcad28995 — MWE-205: Front Running
- GPTSCAN-0965d6555d45d32e — MWE-200: Insecure LP Token Value Calculation

### `2022-01-sandclock`

| Metric | Value |
| --- | --- |
| Ground Truth findings | 2 |
| Predictions | 0 |
| Matched weight | 0.0000 |
| Soft precision | 0.0000 |
| Soft recall | 0.0000 |
| Soft F1 | 0.0000 |

#### Matched Findings

| Ground Truth | Prediction | R | L | I | M | Weighted |
| --- | --- | --- | --- | --- | --- | --- |
| No matched findings. | | | | | | |

#### Unmatched Ground Truth

- H-03 — [H-03] Vaults with non-UST underlying asset vulnerable to flash loan attack on curve pool
- M-11 — [M-11] Changing a strategy can be bricked

#### Unmatched Predictions

No unmatched predictions.

### `2022-08-sentiment`

| Metric | Value |
| --- | --- |
| Ground Truth findings | 2 |
| Predictions | 0 |
| Matched weight | 0.0000 |
| Soft precision | 0.0000 |
| Soft recall | 0.0000 |
| Soft F1 | 0.0000 |

#### Matched Findings

| Ground Truth | Prediction | R | L | I | M | Weighted |
| --- | --- | --- | --- | --- | --- | --- |
| No matched findings. | | | | | | |

#### Unmatched Ground Truth

- M-10 — M-10: ERC4626Oracle Vulnerable To Price Manipulation
- H-1 — H-1: LToken pricePerShare can be manipulated by an early depositor

#### Unmatched Predictions

No unmatched predictions.

### `2022-09-notional`

| Metric | Value |
| --- | --- |
| Ground Truth findings | 1 |
| Predictions | 4 |
| Matched weight | 0.0000 |
| Soft precision | 0.0000 |
| Soft recall | 0.0000 |
| Soft F1 | 0.0000 |

#### Matched Findings

| Ground Truth | Prediction | R | L | I | M | Weighted |
| --- | --- | --- | --- | --- | --- | --- |
| No matched findings. | | | | | | |

#### Unmatched Ground Truth

- M-7 — [M-7] Gain From Balancer Vaults Can Be Stolen

#### Unmatched Predictions

- GPTSCAN-43f0a81a675a2359 — MWE-200: Insecure LP Token Value Calculation
- GPTSCAN-ed3b6e73c5e0b8bd — MWE-200: Insecure LP Token Value Calculation
- GPTSCAN-5d8c1eaa05a06c27 — MWE-200: Insecure LP Token Value Calculation
- GPTSCAN-0a7cb324eae3a5a4 — MWE-204: Unsafe First Deposit

### `2022-11-paraspace`

| Metric | Value |
| --- | --- |
| Ground Truth findings | 4 |
| Predictions | 0 |
| Matched weight | 0.0000 |
| Soft precision | 0.0000 |
| Soft recall | 0.0000 |
| Soft F1 | 0.0000 |

#### Matched Findings

| Ground Truth | Prediction | R | L | I | M | Weighted |
| --- | --- | --- | --- | --- | --- | --- |
| No matched findings. | | | | | | |

#### Unmatched Ground Truth

- H-05 — [H-05] Attacker can manipulate low TVL Uniswap V3 pool to borrow and swap to make Lending Pool in loss
- M-04 — [M-04] Fallback oracle is using spot price in Uniswap liquidity pool, which is very vulnerable to flashloan price manipulation
- M-05 — [M-05] Front-running admin setPrice call allows a single compromised oracle to set any price, allowing the oracle manipulator to drain all protocol funds
- M-22 — [M-22] Price can deviate by much more than maxDeviationRate

#### Unmatched Predictions

No unmatched predictions.

### `2022-11-telcoin`

| Metric | Value |
| --- | --- |
| Ground Truth findings | 1 |
| Predictions | 0 |
| Matched weight | 0.0000 |
| Soft precision | 0.0000 |
| Soft recall | 0.0000 |
| Soft F1 | 0.0000 |

#### Matched Findings

| Ground Truth | Prediction | R | L | I | M | Weighted |
| --- | --- | --- | --- | --- | --- | --- |
| No matched findings. | | | | | | |

#### Unmatched Ground Truth

- H-1 — H-1: Flashloan `TEL` tokens to stake and exit in the same block can fake a huge amount of stake with minimal material cost

#### Unmatched Predictions

No unmatched predictions.

### `2023-03-olympus`

| Metric | Value |
| --- | --- |
| Ground Truth findings | 1 |
| Predictions | 1 |
| Matched weight | 0.0000 |
| Soft precision | 0.0000 |
| Soft recall | 0.0000 |
| Soft F1 | 0.0000 |

#### Matched Findings

| Ground Truth | Prediction | R | L | I | M | Weighted |
| --- | --- | --- | --- | --- | --- | --- |
| No matched findings. | | | | | | |

#### Unmatched Ground Truth

- H-1 — H-1: Adversary can sandwich oracle updates to exploit vault

#### Unmatched Predictions

- GPTSCAN-b035cbf99646dbf4 — MWE-200: Insecure LP Token Value Calculation

### `2023-04-blueberry`

| Metric | Value |
| --- | --- |
| Ground Truth findings | 1 |
| Predictions | 4 |
| Matched weight | 0.5000 |
| Soft precision | 0.1250 |
| Soft recall | 0.5000 |
| Soft F1 | 0.2000 |

#### Matched Findings

| Ground Truth | Prediction | R | L | I | M | Weighted |
| --- | --- | --- | --- | --- | --- | --- |
| H-4 — H-4: Potential flash loan attack vulnerability in `getPrice` function of CurveOracle | GPTSCAN-645d0c4c1d33e497 — MWE-200: Insecure LP Token Value Calculation | 1/4 | 4/4 | 2/4 | 2/4 | 0.5000 |

<details>
<summary>Pair 1: H-4 — H-4: Potential flash loan attack vulnerability in \`getPrice\` function of CurveOracle ↔ GPTSCAN-645d0c4c1d33e497 — MWE-200: Insecure LP Token Value Calculation</summary>

- **Ground Truth:** `H-4`
- **Prediction:** `GPTSCAN-645d0c4c1d33e497`

#### Ground Truth locations

| File | Contract | Function | Lines |
| --- | --- | --- | --- |
| blueberry-core/contracts/oracle/CurveOracle.sol | CurveOracle | getPrice(address) | 122–134 |

#### Prediction locations

| File | Contract | Function | Lines |
| --- | --- | --- | --- |
| blueberry-core/contracts/oracle/CurveOracle.sol | CurveOracle | getPrice(address) | 122–134 |

#### Judge rationale

```text
R: Identifies manipulable LP-token valuation, a related symptom/category, but does not identify the specific causal flaw of using manipulable underlying-token prices and a minimum-price calculation. L: Correctly localizes CurveOracle.getPrice at the same lines and function. I: Recognizes mispricing and possible losses or incorrect payouts, but omits the specific attacker profit-at-others'-expense consequence and relevant exploit conditions. M: Avoiding AMM/custom LP calculations is directionally related, but is vague and does not specify a sound replacement such as TWAP underlying-asset prices.
```

</details>

#### Unmatched Ground Truth

No unmatched Ground Truth findings.

#### Unmatched Predictions

- GPTSCAN-dc8246d6a7bfa6c2 — MWE-200: Insecure LP Token Value Calculation
- GPTSCAN-3d073c52e85135c8 — MWE-200: Insecure LP Token Value Calculation
- GPTSCAN-20a71a684d2235f9 — MWE-200: Insecure LP Token Value Calculation

### `2023-05-ussd`

| Metric | Value |
| --- | --- |
| Ground Truth findings | 2 |
| Predictions | 0 |
| Matched weight | 0.0000 |
| Soft precision | 0.0000 |
| Soft recall | 0.0000 |
| Soft F1 | 0.0000 |

#### Matched Findings

| Ground Truth | Prediction | R | L | I | M | Weighted |
| --- | --- | --- | --- | --- | --- | --- |
| No matched findings. | | | | | | |

#### Unmatched Ground Truth

- H-9 — H-9: Uniswap v3 pool token balance proportion does not necessarily correspond to the price, and it is easy to manipulate.
- H-5 — H-5: Price calculation susceptible to flashloan exploits

#### Unmatched Predictions

No unmatched predictions.

### `2023-06-lybra`

| Metric | Value |
| --- | --- |
| Ground Truth findings | 1 |
| Predictions | 3 |
| Matched weight | 0.0000 |
| Soft precision | 0.0000 |
| Soft recall | 0.0000 |
| Soft F1 | 0.0000 |

#### Matched Findings

| Ground Truth | Prediction | R | L | I | M | Weighted |
| --- | --- | --- | --- | --- | --- | --- |
| No matched findings. | | | | | | |

#### Unmatched Ground Truth

- M-13 — [M-13] It is possible to manipulate WETH/LBR pair to claim reward of the users which shouldn't be claimed

#### Unmatched Predictions

- GPTSCAN-8ed0baa5b4fa45c7 — MWE-200: Insecure LP Token Value Calculation
- GPTSCAN-d81333ef57a79c35 — MWE-200: Insecure LP Token Value Calculation
- GPTSCAN-ebbecd6f5d0b9765 — MWE-200: Insecure LP Token Value Calculation

### `2023-06-real-wagmi`

| Metric | Value |
| --- | --- |
| Ground Truth findings | 1 |
| Predictions | 6 |
| Matched weight | 0.5500 |
| Soft precision | 0.0917 |
| Soft recall | 0.5500 |
| Soft F1 | 0.1571 |

#### Matched Findings

| Ground Truth | Prediction | R | L | I | M | Weighted |
| --- | --- | --- | --- | --- | --- | --- |
| H-3 — H-3: Usage of `slot0` is extremely easy to manipulate | GPTSCAN-9cffc57b2c082703 — MWE-200: Insecure LP Token Value Calculation | 2/4 | 3/4 | 2/4 | 2/4 | 0.5500 |

<details>
<summary>Pair 1: H-3 — H-3: Usage of \`slot0\` is extremely easy to manipulate ↔ GPTSCAN-9cffc57b2c082703 — MWE-200: Insecure LP Token Value Calculation</summary>

- **Ground Truth:** `H-3`
- **Prediction:** `GPTSCAN-9cffc57b2c082703`

#### Ground Truth locations

| File | Contract | Function | Lines |
| --- | --- | --- | --- |
| concentrator/contracts/Multipool.sol | Multipool | deposit(uint256,uint256,uint256,uint256) | 433–486 |
| concentrator/contracts/Multipool.sol | Multipool | getSlots() | 589–602 |
| concentrator/contracts/Multipool.sol | Multipool | _getReserves(Slot0Data[]) | 693–768 |

#### Prediction locations

| File | Contract | Function | Lines |
| --- | --- | --- | --- |
| concentrator/contracts/Multipool.sol | Multipool | _getReserves(Multipool.Slot0Data[]) | 693–768 |
| concentrator/contracts/Multipool.sol | Multipool | deposit(uint256,uint256,uint256,uint256) | 433–486 |

#### Judge rationale

```text
R: Identifies manipulable liquidity/LP valuation inputs, but omits the specific transaction-local Uniswap V3 slot0 price mechanism and incorrectly frames it primarily as a flashloan attack. L: Correctly identifies _getReserves() and the deposit path, but omits getSlots(), the operation that directly reads manipulable slot0 data. I: Recognizes mispricing and potentially incorrect financial outcomes, but does not identify incorrect LP issuance, dilution, or the affected provider share. M: Avoiding AMM/custom valuation is directionally relevant, but it does not specifically require a manipulation-resistant TWAP or validated deviation checks.
```

</details>

#### Unmatched Ground Truth

No unmatched Ground Truth findings.

#### Unmatched Predictions

- GPTSCAN-68a9598fb13e961c — MWE-200: Insecure LP Token Value Calculation
- GPTSCAN-3f67639f970465c7 — MWE-200: Insecure LP Token Value Calculation
- GPTSCAN-1ced5dfc71327f07 — MWE-200: Insecure LP Token Value Calculation
- GPTSCAN-a17eb2dd82159c82 — MWE-200: Insecure LP Token Value Calculation
- GPTSCAN-3b5f53a161171e7b — MWE-200: Insecure LP Token Value Calculation

### `2023-06-tokemak`

| Metric | Value |
| --- | --- |
| Ground Truth findings | 1 |
| Predictions | 9 |
| Matched weight | 0.5500 |
| Soft precision | 0.0611 |
| Soft recall | 0.5500 |
| Soft F1 | 0.1100 |

#### Matched Findings

| Ground Truth | Prediction | R | L | I | M | Weighted |
| --- | --- | --- | --- | --- | --- | --- |
| H-15 — H-15: Maverick oracle can be manipulated | GPTSCAN-569f38a742554c9a — MWE-200: Insecure LP Token Value Calculation | 2/4 | 2/4 | 2/4 | 3/4 | 0.5500 |

<details>
<summary>Pair 1: H-15 — H-15: Maverick oracle can be manipulated ↔ GPTSCAN-569f38a742554c9a — MWE-200: Insecure LP Token Value Calculation</summary>

- **Ground Truth:** `H-15`
- **Prediction:** `GPTSCAN-569f38a742554c9a`

#### Ground Truth locations

| File | Contract | Function | Lines |
| --- | --- | --- | --- |
| v2-core-audit-2023-07-14/src/oracles/providers/MavEthOracle.sol | MavEthOracle | getPriceInEth(address) | 58–75 |

#### Prediction locations

| File | Contract | Function | Lines |
| --- | --- | --- | --- |
| v2-core-audit-2023-07-14/src/oracles/providers/BalancerLPMetaStableEthOracle.sol | BalancerLPMetaStableEthOracle | getPriceInEth(address) | 35–81 |

#### Judge rationale

```text
R: Correctly identifies manipulable LP-token valuation and flash-loan-based price manipulation, but omits the specific Maverick reserve-reading mechanism. L: Locates an analogous oracle getPriceInEth operation, but names the wrong oracle contract and implementation. I: Identifies mispricing and potentially incorrect payouts/losses, but omits the specific debt/share and withdrawal outcomes. M: Avoiding AMM spot-reserve/custom valuation is directionally effective, though it does not specify the required fair-reserve/invariant calculation.
```

</details>

#### Unmatched Ground Truth

No unmatched Ground Truth findings.

#### Unmatched Predictions

- GPTSCAN-f38e9cd856979d68 — MWE-200: Insecure LP Token Value Calculation
- GPTSCAN-db8619b502a85479 — MWE-200: Insecure LP Token Value Calculation
- GPTSCAN-4bc99df51718ecb7 — MWE-200: Insecure LP Token Value Calculation
- GPTSCAN-f4696a0a66e606c9 — MWE-200: Insecure LP Token Value Calculation
- GPTSCAN-061002d555a4c409 — MWE-200: Insecure LP Token Value Calculation
- GPTSCAN-58e4fa6baee36f65 — MWE-200: Insecure LP Token Value Calculation
- GPTSCAN-ecf27bb58ab3a084 — MWE-200: Insecure LP Token Value Calculation
- GPTSCAN-91a2f6c0c1d19a40 — MWE-200: Insecure LP Token Value Calculation

### `2023-08-dopex`

| Metric | Value |
| --- | --- |
| Ground Truth findings | 2 |
| Predictions | 1 |
| Matched weight | 0.0000 |
| Soft precision | 0.0000 |
| Soft recall | 0.0000 |
| Soft F1 | 0.0000 |

#### Matched Findings

| Ground Truth | Prediction | R | L | I | M | Weighted |
| --- | --- | --- | --- | --- | --- | --- |
| No matched findings. | | | | | | |

#### Unmatched Ground Truth

- M-08 — [M-08] `reLPContract.reLP()` is susceptible to sandwich attack due to user control over `bond()`
- M-09 — [M-09] A malicious early depositor can manipulate the LP-Token price per share to take an unfair share of future user deposits

#### Unmatched Predictions

- GPTSCAN-6c2ddfd4c5627bce — MWE-200: Insecure LP Token Value Calculation

### `2024-03-abracadabra-money`

| Metric | Value |
| --- | --- |
| Ground Truth findings | 2 |
| Predictions | 5 |
| Matched weight | 0.5500 |
| Soft precision | 0.1100 |
| Soft recall | 0.2750 |
| Soft F1 | 0.1571 |

#### Matched Findings

| Ground Truth | Prediction | R | L | I | M | Weighted |
| --- | --- | --- | --- | --- | --- | --- |
| H-04 — [H-04] Oracle price can be manipulated | GPTSCAN-62fdcad2e97ab960 — MWE-200: Insecure LP Token Value Calculation | 2/4 | 2/4 | 2/4 | 3/4 | 0.5500 |

<details>
<summary>Pair 1: H-04 — [H-04] Oracle price can be manipulated ↔ GPTSCAN-62fdcad2e97ab960 — MWE-200: Insecure LP Token Value Calculation</summary>

- **Ground Truth:** `H-04`
- **Prediction:** `GPTSCAN-62fdcad2e97ab960`

#### Ground Truth locations

| File | Contract | Function | Lines |
| --- | --- | --- | --- |
| src/oracles/aggregators/MagicLpAggregator.sol | MagicLpAggregator | _getReserves() | 33–35 |
| src/oracles/aggregators/MagicLpAggregator.sol | MagicLpAggregator | latestAnswer() | 37–46 |

#### Prediction locations

| File | Contract | Function | Lines |
| --- | --- | --- | --- |
| src/libraries/CauldronLib.sol | CauldronLib | getUserCollateral(ICauldronV2,address) | 56–62 |

#### Judge rationale

```text
R: Identifies flash-loan manipulation of an LP-token price/value calculation, but omits the specific reserve-based MagicLP oracle mechanism and inflated oracle price. L: CauldronLib.getUserCollateral is at most an adjacent collateral-valuation/caller path; it does not identify MagicLpAggregator._getReserves or latestAnswer. I: Captures flash-loan-driven LP mispricing and potential financial loss, but not the specific one-transaction inflation of the MagicLP oracle valuation. M: Avoiding AMM/custom reserve-based LP valuation would prevent the flaw in principle, though it lacks the ground-truth Chainlink deviation check or replacement details.
```

</details>

#### Unmatched Ground Truth

- H-01 — [H-01] Anyone making use of the MagicLP's TWAP to determine token prices will be exploitable.

#### Unmatched Predictions

- GPTSCAN-99cae3b75277c1d7 — MWE-200: Insecure LP Token Value Calculation
- GPTSCAN-10a55b5415a23007 — MWE-209: Wrong Order for Interest or ExchangeRate
- GPTSCAN-af76751b6ce0d827 — MWE-200: Insecure LP Token Value Calculation
- GPTSCAN-bc0739f2fa77da70 — MWE-200: Insecure LP Token Value Calculation

### `2024-03-revert-lend`

| Metric | Value |
| --- | --- |
| Ground Truth findings | 1 |
| Predictions | 13 |
| Matched weight | 0.0000 |
| Soft precision | 0.0000 |
| Soft recall | 0.0000 |
| Soft F1 | 0.0000 |

#### Matched Findings

| Ground Truth | Prediction | R | L | I | M | Weighted |
| --- | --- | --- | --- | --- | --- | --- |
| No matched findings. | | | | | | |

#### Unmatched Ground Truth

- M-19 — [M-19] `V3Oracle` susceptible to price manipulation

#### Unmatched Predictions

- GPTSCAN-ca079b6bd978cc2f — MWE-200: Insecure LP Token Value Calculation
- GPTSCAN-80947d7a6bc388a6 — MWE-200: Insecure LP Token Value Calculation
- GPTSCAN-865c4784984f0612 — MWE-200: Insecure LP Token Value Calculation
- GPTSCAN-e1b8305cfaa78523 — MWE-209: Wrong Order for Interest or ExchangeRate
- GPTSCAN-b8e7e03952aeb8f4 — MWE-200: Insecure LP Token Value Calculation
- GPTSCAN-2a8b3bb2c91bcef7 — MWE-200: Insecure LP Token Value Calculation
- GPTSCAN-a47b0b73934241f2 — MWE-200: Insecure LP Token Value Calculation
- GPTSCAN-6d322c8dec9c569d — MWE-209: Wrong Order for Interest or ExchangeRate
- GPTSCAN-be319d2bc2418441 — MWE-200: Insecure LP Token Value Calculation
- GPTSCAN-9630ac569a47753b — MWE-200: Insecure LP Token Value Calculation
- GPTSCAN-04f9cf900db655cf — MWE-200: Insecure LP Token Value Calculation
- GPTSCAN-f80d1a860e87aa79 — MWE-200: Insecure LP Token Value Calculation
- GPTSCAN-124c2838684279cc — MWE-200: Insecure LP Token Value Calculation

### `2024-03-woofi-swap`

| Metric | Value |
| --- | --- |
| Ground Truth findings | 1 |
| Predictions | 11 |
| Matched weight | 0.0000 |
| Soft precision | 0.0000 |
| Soft recall | 0.0000 |
| Soft F1 | 0.0000 |

#### Matched Findings

| Ground Truth | Prediction | R | L | I | M | Weighted |
| --- | --- | --- | --- | --- | --- | --- |
| No matched findings. | | | | | | |

#### Unmatched Ground Truth

- H-1 — H-1: Pool can be drained

#### Unmatched Predictions

- GPTSCAN-be9f5c337aab625d — MWE-209: Wrong Order for Interest or ExchangeRate
- GPTSCAN-9dfc9c0ec559fbad — MWE-209: Wrong Order for Interest or ExchangeRate
- GPTSCAN-6e56d1fe63186b13 — MWE-209: Wrong Order for Interest or ExchangeRate
- GPTSCAN-1ef920d14a028f2f — MWE-200: Insecure LP Token Value Calculation
- GPTSCAN-cd71eb127ab7b8a9 — MWE-200: Insecure LP Token Value Calculation
- GPTSCAN-9f9a1f00b82e8690 — MWE-200: Insecure LP Token Value Calculation
- GPTSCAN-aaec72cd68f75f49 — MWE-209: Wrong Order for Interest or ExchangeRate
- GPTSCAN-5c2209fb0ef81867 — MWE-200: Insecure LP Token Value Calculation
- GPTSCAN-a396f1f746569e50 — MWE-200: Insecure LP Token Value Calculation
- GPTSCAN-377dc8a6d81bf158 — MWE-200: Insecure LP Token Value Calculation
- GPTSCAN-2f10b172b45da69e — MWE-209: Wrong Order for Interest or ExchangeRate

### `2024-04-panoptic`

| Metric | Value |
| --- | --- |
| Ground Truth findings | 1 |
| Predictions | 3 |
| Matched weight | 0.0000 |
| Soft precision | 0.0000 |
| Soft recall | 0.0000 |
| Soft F1 | 0.0000 |

#### Matched Findings

| Ground Truth | Prediction | R | L | I | M | Weighted |
| --- | --- | --- | --- | --- | --- | --- |
| No matched findings. | | | | | | |

#### Unmatched Ground Truth

- M-01 — [M-01] `PanopticFactory` uses spot price when deploying new pools, resulting in liquidity manipulation when minting

#### Unmatched Predictions

- GPTSCAN-dc3d2cbf41d2ef66 — MWE-200: Insecure LP Token Value Calculation
- GPTSCAN-0e325ebc160a2586 — MWE-200: Insecure LP Token Value Calculation
- GPTSCAN-7841397ca1d60bce — MWE-200: Insecure LP Token Value Calculation

### `2025-12-panoptic`

| Metric | Value |
| --- | --- |
| Ground Truth findings | 3 |
| Predictions | 6 |
| Matched weight | 0.0000 |
| Soft precision | 0.0000 |
| Soft recall | 0.0000 |
| Soft F1 | 0.0000 |

#### Matched Findings

| Ground Truth | Prediction | R | L | I | M | Weighted |
| --- | --- | --- | --- | --- | --- | --- |
| No matched findings. | | | | | | |

#### Unmatched Ground Truth

- M-11 — [M-11] An attacker can manipulate oracle easily
- M-03 — [M-03] TWAP misweights EMAs in RiskEngine, anchoring liquidation price to slow EMA and letting insolvent accounts dodge liquidation
- M-15 — [M-15] Commission share-burn distribution is JIT-capturable when `builderCode == 0` (default)

#### Unmatched Predictions

- GPTSCAN-2688180308d90412 — MWE-200: Insecure LP Token Value Calculation
- GPTSCAN-03163a5552a7b0d3 — MWE-200: Insecure LP Token Value Calculation
- GPTSCAN-201e782f15e5c9f9 — MWE-200: Insecure LP Token Value Calculation
- GPTSCAN-85825f34183d2e2e — MWE-200: Insecure LP Token Value Calculation
- GPTSCAN-a357ffd6a4f9bf3c — MWE-200: Insecure LP Token Value Calculation
- GPTSCAN-e49f4e7f930bab54 — MWE-200: Insecure LP Token Value Calculation


## Artifacts

- [manifest.json](manifest.json)
- [judge_artifact.json](judge_artifact.json)
- [report.json](report.json)
