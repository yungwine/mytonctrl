# `lst_restricted_wallet` Guide

## What this guide covers

This guide explains how to use `lst_restricted_wallet` with `mytonctrl` for liquid staking controller mode.

The goal of this wallet is simple:

- validator operations should keep working as usual
- controller deployment should work from `mytonctrl`
- funds should **not** be freely movable to arbitrary destinations
- outside controller operations, the wallet may send coins only to a designated `treasury`

This guide is operator-facing and focuses on setup and daily use.

---

## How `lst_restricted_wallet` differs from a normal validator wallet

A normal validator wallet can send funds anywhere.

`lst_restricted_wallet` is more restrictive:

- it may send freely to `treasury`
- it may send only approved controller operations to known controller contracts
- it may direct-deploy new controllers when the deployment matches the configured liquid pool and controller code hash
- `treasury` has an internal emergency `proxy` path

In practice this means:

- validator/operator automation can still work with controllers
- controller funds cannot be casually drained to arbitrary addresses
- if coins return to the wallet, they can be moved only to `treasury`

---

## Current scope and limitations

At the time of writing, this branch supports the liquid-staking controller workflow, but **does not yet add body-aware permissions for config/elector governance paths**.

That means:

- controller creation and controller operations are the supported target flow
- proposal voting / complaint voting / complaint submission should be treated as **not integrated yet** unless verified separately

Other important notes:

- `ton-http-api` (**THA**) is required for restricted-wallet controller deployment and wallet creation
- for controller creation, the branch uses the command `create_controllers`
  - older docs or older discussions may say `new_controllers`
- wallet version must be exactly `lst_restricted_wallet`

---

## Prerequisites

Before using `lst_restricted_wallet`, make sure:

1. your validator node is installed and synchronized
2. `mytonctrl` is installed on the branch with restricted-wallet support
3. `ton-http-api` is enabled
4. you know:
   - the target `treasury` address
   - the target liquid pool address
5. you have enough TON to:
   - initialize the wallet
   - create two controllers
   - top up controllers for operation

Enable THA if needed:

```text
mytonctrl -> installer -> enable THA
```

Exit installer mode with `Ctrl+D`.

---

## Launching a validator in controller mode with `lst_restricted_wallet`

### 1. Create the restricted wallet

Create the wallet with explicit treasury and pool parameters:

```bash
nw 0 <wallet_name> lst_restricted_wallet <treasury_addr> <liquid_pool_addr>
```

Example:

```bash
nw 0 validator_wallet lst_restricted_wallet EQ...TREASURY EQ...POOL
```

Notes:

- `wallet_name` is the local name inside `mytonctrl`
- `treasury_addr` is the only arbitrary destination the wallet may send funds to
- `liquid_pool_addr` is stored inside the wallet state and used to constrain controller deployment

### 2. Check the wallet list

```bash
wl
```

Find the new wallet and note its address.

### 3. Fund the wallet and activate it

Send at least `1 TON` to the wallet initialization address shown by `wl`, then activate it:

```bash
aw <wallet_name>
```

Example:

```bash
aw validator_wallet
```

After activation, fund the wallet with enough TON for controller creation and future operations.

### 4. Make it the validator wallet

Set the newly created wallet as the main validator wallet:

```bash
set validatorWalletName <wallet_name>
```

Example:

```bash
set validatorWalletName validator_wallet
```

Then check `wl` again and verify you are using the expected wallet.

### 5. Enable liquid-staking mode

```bash
enable_mode liquid-staking
set stake null
```

If you were using nominator pools before, disable them first:

```bash
disable_mode nominator-pool
```

### 6. Configure the liquid pool and lending parameters

Even though the pool address was passed to `nw`, you still need to configure it for the liquid-staking runtime flow:

```bash
set liquid_pool_addr <liquid_pool_addr>
set min_loan 41000
set max_loan 43000
set max_interest_percent 1.5
```

You may also check the annualized percentage:

```bash
calculate_annual_controller_percentage
```

### 7. Create controllers

Use:

```bash
create_controllers
```

On this branch, if the validator wallet version is `lst_restricted_wallet`, `mytonctrl` will:

1. fetch pool deploy data through THA
2. build controller `StateInit` locally
3. compare the locally computed address with the pool-derived controller address
4. direct-deploy the controller with `StateInit` attached

If the wallet version is not `lst_restricted_wallet`, `mytonctrl` will fall back to the old pool-based controller deployment path.

### 8. Verify controllers

```bash
controllers_list
```

You should see two controller addresses.

### 9. Deposit validator stake to controllers

Example:

```bash
deposit_to_controller <controller_addr_0> 10000
deposit_to_controller <controller_addr_1> 10000
```

### 10. Get controller approval

Each pool may have its own approval process. Obtain approval according to the pool operator’s policy.

---

## Daily operations

Once controllers are deployed and approved, regular controller operations should continue through the restricted wallet path.

Useful commands:

```bash
controllers_list
deposit_to_controller <controller_addr> <amount>
withdraw_from_controller <controller_addr> [amount]
stop_controller <controller_addr>
stop_and_withdraw_controller <controller_addr> [amount]
controller_update_validator_set <controller_addr>
check_liquid_pool
```

---

## Switching an existing validator to `lst_restricted_wallet`

If you already operate a validator and want to migrate to `lst_restricted_wallet`:

### 1. Stop participating in elections

```bash
set stake 0
```

### 2. Wait until deposits/stakes are safely returned

Do not switch in the middle of an unsafe state if you can avoid it.

### 3. Create and activate the restricted wallet

```bash
nw 0 <wallet_name> lst_restricted_wallet <treasury_addr> <liquid_pool_addr>
aw <wallet_name>
```

### 4. Set it as the validator wallet

```bash
set validatorWalletName <wallet_name>
```

### 5. Re-enable controller-mode liquid staking

```bash
enable_mode liquid-staking
set stake null
set liquid_pool_addr <liquid_pool_addr>
set min_loan <...>
set max_loan <...>
set max_interest_percent <...>
create_controllers
```

### 6. Fund and approve the new controllers

Use `deposit_to_controller` and then obtain pool approval.

---

## Moving funds to treasury

If coins accumulate on the restricted wallet itself, they can be moved to `treasury`, but not to arbitrary destinations.

Use the standard move command:

```bash
mg <wallet_name> <treasury_addr> <amount>
```

Examples:

```bash
mg validator_wallet EQ...TREASURY 10
mg validator_wallet EQ...TREASURY all
```

---

## If you deployed the wallet outside `mytonctrl`

If the wallet was created or imported outside the built-in `nw` flow, make sure `mytonctrl` knows its version:

```bash
swv <wallet_addr> lst_restricted_wallet
```

If the version is not set correctly, `create_controllers` will not activate the restricted-wallet direct deploy path.

---

## Troubleshooting

### `create_controllers` fails immediately

Check:

- THA is enabled
- the wallet version is exactly `lst_restricted_wallet`
- the configured `liquid_pool_addr` is correct
- the restricted wallet was created with the intended `treasury` and `liquid_pool`

### Controllers were not deployed or do not appear in `controllers_list`

Possible reasons:

- THA could not return pool deploy data
- the locally built controller address did not match the pool-derived address
- the liquid pool/controller code version differs from what the integration expects
- the wallet version was wrong, so the old path was used instead

### `deposit_to_controller` fails after controller creation

Possible reasons:

- the controller deployment did not pass wallet validation, so the controller was not added to the allowlist
- the wrong pool was used during wallet creation
- the wrong pool is currently configured in `set liquid_pool_addr`

### Wallet creation fails

Check:

- THA is enabled and reachable
- both addresses are valid:
  - `<treasury_addr>`
  - `<liquid_pool_addr>`
- the branch really includes `lst_restricted_wallet` support

---

## Recommended first smoke test

For a first non-production check:

1. create the restricted wallet
2. activate it
3. set it as validator wallet
4. configure liquid staking
5. run `create_controllers`
6. run `controllers_list`
7. run one small `deposit_to_controller`
8. verify the wallet can still send to treasury with `mg`

Only after that should you move to the full production cycle.
