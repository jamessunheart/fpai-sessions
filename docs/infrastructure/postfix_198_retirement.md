# Postfix Retirement On 198

Spec: `SPEC_d145_self-audit-infra-retire-postfix`

Decision: `d145`

Target: `198.54.123.234`

Service: `postfix`

## Action

`core/BUILD/activate/SPEC_d145_self-audit-infra-retire-postfix.sh` runs:

```bash
python3 -B -m tools.infra.retire_postfix_198 --execute
```

The helper first checks repo evidence that outbound mail is covered by Brevo in
`core/STATE/RESOURCE_INVENTORY.md`. It only runs `systemctl disable --now
postfix` when the local host IP list includes `198.54.123.234`.

If the activation runs on a non-target host, it appends a skipped proof row and
takes no service action.

## Rollback

On `198.54.123.234`:

```bash
systemctl enable --now postfix
systemctl is-active postfix
systemctl is-enabled postfix
```

## Proof

The helper appends one JSONL row to `/opt/fpai-build/ops_ledger.jsonl` with:

- `spec_id=SPEC_d145_self-audit-infra-retire-postfix`
- `decision_id=d145`
- `service=postfix`
- before/after `systemctl is-active` and `systemctl is-enabled`
- `rollback=systemctl enable --now postfix`
- Brevo evidence lines from `core/STATE/RESOURCE_INVENTORY.md`
