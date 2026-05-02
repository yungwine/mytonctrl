# lst_restricted_wallet integration audit and runbook

Branch: `feat/lst-restricted-wallet-integration`

## What changed

### 1. `new_controllers` switches behavior only for `lst_restricted_wallet`
File: `modules/controller.py`

- non-`lst_restricted_wallet` wallets keep the old path:
  - wallet -> pool `deploy_controller{0,1}.boc`
- `lst_restricted_wallet` uses the new path:
  - fetch pool deploy data
  - build controller `StateInit` locally
  - compare locally computed controller address with pool `get_controller_address_legacy`
  - direct-deploy controller with `top-up.boc` + `StateInit`

This is the intended minimal blast-radius change.

### 2. Existing signing architecture is reused
Files:
- `mytoncore/mytoncore.py`
- `modules/wallet.py`

`lst_restricted_wallet` is treated as `wallet.fif`-compatible for:
- `SignBocWithWallet(...)`
- `move_coins`

`SignBocWithWallet(...)` was extended with:
- `init_boc_path` -> appends `-I <state_init.boc>`
- `extra_flags` -> used for `-n`

No new send architecture was introduced.

### 3. Pool deploy metadata is read via THA
File: `mytoncore/mytoncore.py`

Added:
- `RunTonHttpGetMethod(...)`
- `GetLiquidPoolDeployData(...)`

Data source:
- `get_pool_full_data_raw`

Extracted values:
- `governor`
- `halter`
- `approver`
- `controller_code`

### 4. Local controller `StateInit` builder
File: `mytoncore/contracts/lst-restricted-wallet/build-controller-init.fif`

This helper builds controller `static_data`, `init_data`, and final `StateInit`, then saves:
- `<file-base>-init.boc`
- `<file-base>.addr`

It prints the bounceable controller address, which is then compared with pool-derived address.

## Audit summary

## Good parts

1. **Minimal invasive patching**
   - only a small branch in `new_controllers`
   - existing send/sign flow reused
   - ordinary wallets keep current behavior untouched

2. **Off-chain sanity check is correct in spirit**
   - direct deploy does not trust local `StateInit` blindly
   - it checks computed address against pool `get_controller_address_legacy`

3. **Good alignment with restricted wallet design**
   - deployment uses `top_up` body
   - direct deploy path is activated only for the restricted wallet type

4. **THA use is appropriate here**
   - current code already depends on THA for loan calculation
   - using it for pool raw data avoids building a more fragile lite-client parser for cell-heavy responses

## Known runtime edge-cases / risks

### A. THA is now a hard requirement for restricted-wallet `new_controllers`
If ton-http-api is not enabled or not reachable, restricted-wallet controller deployment will fail.

Expected operator prerequisite:
- `installer -> enable THA`

Recommendation:
- before running `new_controllers`, verify THA is healthy.

### B. `get_pool_full_data_raw` stack index coupling is brittle
Current extraction assumes the output layout remains stable, especially indexes:
- `20` -> governor
- `23` -> halter
- `24` -> approver
- `25` -> controller_code

If pool wrapper / get-method layout changes, this branch can silently break.

Recommendation:
- treat this integration as tied to the current liquid-staking pool implementation
- validate on the target pool version before production use

### C. BOC/address parser only supports standard addresses
`AddressFromSliceBoc(...)` assumes:
- `addr_std`
- no anycast
- one root cell
- no refs in the address slice

That is fine for normal pool role addresses today, but it is intentionally narrow.

### D. Fift helper correctness depends on exact legacy controller init layout
`build-controller-init.fif` reproduces the legacy controller layout from liquid-staking source.

This is good, but it means:
- if deployed pool uses a different controller code/storage layout version,
- local `StateInit` may no longer match pool expectations.

Recommendation:
- verify against the actual pool/controller version in the target environment
- especially if the pool repo or controller code was updated independently

### E. `create_wallet` is intentionally not patched
Current integration does **not** make `mytonctrl nw ...` create `lst_restricted_wallet`.

Current expected flow:
1. deploy restricted wallet separately
2. point validator to that wallet
3. set wallet version manually to `lst_restricted_wallet`

This keeps the patch smaller, but should be documented for operators.

### F. `wallet.version` must be set exactly
The direct deploy branch activates only for:
- `wallet.version == "lst_restricted_wallet"`

If operator forgets to set it, `new_controllers` will use the old pool deploy path.

### G. No added support yet for config/elector body-aware permissioning
This branch only integrates controller deployment assumptions.
It does **not** add any extra mytonctrl support for proposal/complaint governance flows related to the restricted wallet policy.

That is expected for current scope.

## Real-world verification runbook

## Preconditions

1. `lst-restricted-wallet` repo already built/tested
2. restricted wallet deployed on-chain
3. validator uses that wallet address
4. wallet version set to `lst_restricted_wallet`
5. THA enabled and healthy
6. liquid pool address configured in mytonctrl
7. wallet funded with enough TON for:
   - 2 controller deploys
   - future controller top-ups / operations

## Suggested command sequence

### 1. Verify current wallet metadata
- check validator wallet address
- verify wallet version is exactly `lst_restricted_wallet`
- verify wallet has positive seqno/balance visibility

### 2. Verify THA
Use any existing THA-backed command first, or test `calculate_annual_controller_percentage` / loan-related read path.
If THA is unavailable, fix that first.

### 3. Verify liquid staking config
- `enable_mode liquid-staking`
- `set stake null`
- `set liquid_pool_addr <pool>`
- `set min_loan ...`
- `set max_loan ...`
- `set max_interest_percent ...`

### 4. Dry sanity checks before live deploy
Recommended manual checks:
- confirm target pool is the expected one
- confirm restricted wallet on-chain config matches intended `liquid_pool`
- confirm restricted wallet stored `controller_code_hash` matches pool controller code hash

### 5. Run controller creation
- `new_controllers`

Expected restricted-wallet behavior:
- mytonctrl fetches pool deploy data via THA
- builds controller0/1 init locally
- compares computed address with pool-derived address
- sends direct deploys with attached `StateInit`

### 6. Inspect results
- `controllers_list`
- verify both controller addresses exist and are active/inactive as expected immediately after deploy
- verify the addresses match the pool-derived legacy addresses

### 7. Verify wallet policy actually accepted the deploys
Since restricted wallet only auto-whitelists valid deploys, successful deploy itself is a strong sign.
Then verify normal controller operation still works:
- `deposit_to_controller <addr> <amount>`
- or other harmless controller command path

If deposit/top-up to controller fails from the restricted wallet, the likely causes are:
- controller was not whitelisted during deploy
- wrong pool/controller code hash assumptions
- wrong wallet version selected

## Best immediate follow-up checks

1. run `new_controllers` on a non-production validator first
2. compare the locally built controller address with pool output for both controller ids
3. do one deposit/top-up through the restricted wallet
4. only then move on to the rest of the liquid-staking cycle

## Recommended next improvements

1. add a small explicit preflight command in mytonctrl for restricted-wallet deployments
   - show THA status
   - show pool role addresses
   - show local computed controller addresses
   - compare them against pool-derived addresses without sending anything

2. optionally add wallet creation/deploy UX later
   - keep out of this branch unless really needed

3. later add governance/config/elector integration once restricted wallet policy for those destinations is finalized
