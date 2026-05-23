# Designer handoff: hardware-check screen

**Status:** spec only — no JSX yet, designer to deliver.
**Where it lives in the flow:** new wizard step, runs **before** Step 1 Identity. Same chrome as the existing 5 steps (sovereign dark theme, header, footer).
**Why:** operator boots the ISO on the wrong hardware → wizard limps along → nobody knows why. A clear pre-flight gate refuses the install (or surfaces a strong warning) before any config work happens.

## What the screen reports

Detected vs. required, four rows. Each row carries a status: `ok` (green), `warn` (amber — below recommended, above minimum), `fail` (red — below minimum).

| Row | Detected from | Minimum | Recommended |
|---|---|---|---|
| CPU cores | `nproc` | 8 | 16 |
| RAM | `/proc/meminfo MemTotal` | 32 GB | 64 GB |
| Disk | `df -B1 /` (root partition) | 256 GB | 1 TB |
| NIC link speed | `ethtool $(ip route | awk '/default/ {print $5}')` | 1 Gbps | 10 Gbps |

`ok` if `detected >= recommended`, `warn` if `recommended > detected >= minimum`, `fail` if `detected < minimum`.

## Backend contract

New endpoint, same wire convention as identity:

```
GET /setup/hardware
→ 200 application/json
{
  "cores":     { "detected": 8,  "min": 8,  "recommended": 16, "status": "ok" },
  "ramBytes":  { "detected": 34359738368, "min": 34359738368, "recommended": 68719476736, "status": "ok" },
  "diskBytes": { "detected": 274877906944, "min": 274877906944, "recommended": 1099511627776, "status": "ok" },
  "nicMbps":   { "detected": 1000, "min": 1000, "recommended": 10000, "status": "ok" },
  "overallStatus": "ok"  // worst of the four
}
```

`overallStatus = "fail"` if any row is `fail`. `"warn"` if any `warn` and none `fail`. `"ok"` otherwise.

## Wizard flow gates

- `overallStatus = "ok"` → proceed button enabled, "Begin setup"
- `overallStatus = "warn"` → proceed button enabled but secondary styling, copy reads "Continue anyway" + an inline note: "Your hardware is below recommended specs. The system will run but may struggle under load."
- `overallStatus = "fail"` → proceed button **disabled**, copy reads "Hardware does not meet minimum requirements." Operator's only paths: (a) back out of the installer, (b) override with a separately-documented escape hatch (out of scope for v1; designer doesn't need to surface)

## Visual treatment — design questions for you

These are the choices I have an opinion on but want you to own:

1. **Single screen vs. row-at-a-time reveal?** I'd lean single screen with all 4 rows visible — fast, scannable. But a row-at-a-time reveal with a brief "checking..." beat per row would feel more like the system is actually doing work, which builds trust. Your call.

2. **Status indicator shape?** Existing wizard uses circles/checks for the step rail. For hardware status I'd reach for a different vocabulary so the operator doesn't confuse "row status" with "step completion." A colored chip with a small icon (✓ / ⚠ / ✕) feels right. Match the theme.

3. **Detected values — show units always or computed unit?** "34.4 GB" not "34359738368 bytes". Same for disk. NIC: "1 Gbps" not "1000 Mbps". You decide whether to surface the raw values somewhere (tooltip on hover?) for the kind of operator who wants to see the exact reading.

4. **Where the row sits on the step rail** — does this become "Step 0" displayed in the rail, or does it skip the rail entirely and sit before the step-counted flow? I'd skip the rail (it's a precondition, not a step in the *setup*) but you may have stronger UX intuition.

## Out of scope for v1

- GPU detection (no GPU required for the EMS stack on CPU-only inference paths)
- Network reachability checks (the ISO is air-gapped by intent — no internet test)
- Disk type detection (NVMe vs. SATA vs. HDD) — the GB count is the only thing the operator can fix without buying new hardware

## Reference data we have

If you want to mock realistic values for the prototype:
- 8c / 32 GB / 512 GB SSD / 1 Gbps → all green
- 8c / 16 GB / 256 GB SSD / 1 Gbps → RAM warn (above 16 GB min if we set one, below 32 GB rec)
- 4c / 32 GB / 256 GB SSD / 1 Gbps → cores fail

## Deliverable

Same as Step 1-5: JSX dropped at `wizard/static/hardware-check.jsx`, exposing `window.HardwareCheckBody` for the Jinja mount.
