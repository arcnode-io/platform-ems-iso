// hardware-check.jsx — Pre-flight hardware gate.
// Runs BEFORE step 1; not numbered in the step rail.
// Polls GET /setup/hardware (mocked here). Gates the next button.

const { useState: useStateHC, useEffect: useEffectHC } = React;

// ─── Mock scenarios (mirrors the platform-engineer reference data) ───
const HW_SCENARIOS = {
  ok: {
    cores:     { detected: 16, min: 8,  recommended: 16, status: 'ok' },
    ramBytes:  { detected: 68719476736,  min: 34359738368,  recommended: 68719476736, status: 'ok' },
    diskBytes: { detected: 1099511627776, min: 274877906944, recommended: 1099511627776, status: 'ok' },
    nicMbps:   { detected: 10000, min: 1000, recommended: 10000, status: 'ok' },
    overallStatus: 'ok',
  },
  warn: {
    cores:     { detected: 8,  min: 8,  recommended: 16, status: 'warn' },
    ramBytes:  { detected: 34359738368, min: 34359738368, recommended: 68719476736, status: 'warn' },
    diskBytes: { detected: 549755813888, min: 274877906944, recommended: 1099511627776, status: 'warn' },
    nicMbps:   { detected: 1000, min: 1000, recommended: 10000, status: 'warn' },
    overallStatus: 'warn',
  },
  fail: {
    cores:     { detected: 4,  min: 8,  recommended: 16, status: 'fail' },
    ramBytes:  { detected: 17179869184, min: 34359738368, recommended: 68719476736, status: 'fail' },
    diskBytes: { detected: 274877906944, min: 274877906944, recommended: 1099511627776, status: 'warn' },
    nicMbps:   { detected: 1000, min: 1000, recommended: 10000, status: 'warn' },
    overallStatus: 'fail',
  },
};

// ─── Unit formatting ────────────────────────────────────────────────
function fmtBytes(n) {
  const TB = 1024 ** 4, GB = 1024 ** 3;
  if (n >= TB) return `${(n / TB).toFixed(n % TB ? 1 : 0)} TB`;
  return `${(n / GB).toFixed(0)} GB`;
}
function fmtMbps(n) {
  if (n >= 1000) return `${(n / 1000).toFixed(0)} Gbps`;
  return `${n} Mbps`;
}

// ─── Icons ───────────────────────────────────────────────────────────
function HCCpuIcon({ color }) {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={color}
         strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <rect x="6" y="6" width="12" height="12" rx="1.5"/>
      <rect x="9" y="9" width="6" height="6"/>
      <path d="M9 2 V5 M15 2 V5 M9 19 V22 M15 19 V22 M2 9 H5 M2 15 H5 M19 9 H22 M19 15 H22"/>
    </svg>
  );
}
function HCRamIcon({ color }) {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={color}
         strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="7" width="20" height="10" rx="1"/>
      <path d="M6 7 V17 M10 7 V17 M14 7 V17 M18 7 V17"/>
      <path d="M5 17 V20 M19 17 V20"/>
    </svg>
  );
}
function HCDiskIcon({ color }) {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={color}
         strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <ellipse cx="12" cy="6" rx="9" ry="3"/>
      <path d="M3 6 V18 a 9 3 0 0 0 18 0 V6"/>
      <path d="M3 12 a 9 3 0 0 0 18 0"/>
    </svg>
  );
}
function HCNetIcon({ color }) {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={color}
         strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <path d="M2 17 L7 17 L7 14 L12 14 L12 17 L17 17 L17 14 L22 14"/>
      <path d="M12 14 V7"/>
      <rect x="9" y="3" width="6" height="4" rx="1"/>
    </svg>
  );
}
function HCCheck({ color, size = 14 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color}
         strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
      <path d="M5 12 L10 17 L19 7"/>
    </svg>
  );
}
function HCWarn({ color, size = 14 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24">
      <path d="M12 3 L22 20 L2 20 Z" fill={color}/>
      <rect x="11.2" y="9.5" width="1.6" height="5.5" rx="0.5" fill="#000" fillOpacity="0.7"/>
      <circle cx="12" cy="17.4" r="0.95" fill="#000" fillOpacity="0.7"/>
    </svg>
  );
}
function HCFail({ color, size = 14 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color}
         strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
      <path d="M6 6 L18 18 M18 6 L6 18"/>
    </svg>
  );
}
function HCSpinner({ color, size = 14 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color}
         strokeWidth="2.5" strokeLinecap="round"
         style={{ animation: 'wizSpin 0.9s linear infinite' }}>
      <path d="M12 3 a9 9 0 0 1 9 9"/>
    </svg>
  );
}
function HCRefresh({ color, size = 12 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color}
         strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 12 a9 9 0 0 1 15.5 -6.2 L21 8"/>
      <path d="M21 3 V8 H16"/>
      <path d="M21 12 a9 9 0 0 1 -15.5 6.2 L3 16"/>
      <path d="M3 21 V16 H8"/>
    </svg>
  );
}

// ─── Status pill (distinct from step circles) ────────────────────────
function HCStatusChip({ t, status }) {
  const map = {
    ok:   { fg: t.statusOk,    label: 'OK',   Icon: HCCheck },
    warn: { fg: t.statusWarn,  label: 'WARN', Icon: HCWarn },
    fail: { fg: t.statusAlarm, label: 'FAIL', Icon: HCFail },
  };
  const m = map[status];
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 6,
      height: 24, padding: '0 10px',
      borderRadius: 999,
      background: m.fg + '22',
      border: `1px solid ${m.fg}60`,
      fontFamily: t.fontLabel, fontSize: 10, fontWeight: 700, letterSpacing: 0.22,
      color: m.fg, textTransform: 'uppercase',
    }}>
      <m.Icon color={m.fg} size={11}/>
      {m.label}
    </span>
  );
}

// ─── A row in the requirements list ──────────────────────────────────
function HCRow({ t, Icon, label, detected, rawDetected, min, recommended, status, isLast, isLoading }) {
  return (
    <div title={rawDetected || ''} style={{
      display: 'grid',
      gridTemplateColumns: '36px 160px 1fr auto',
      gap: SPACE[4],
      alignItems: 'center',
      padding: `${SPACE[4]}px ${SPACE[4]}px`,
      borderBottom: isLast ? 'none' : `1px solid ${t.border}`,
    }}>
      <Icon color={t.textMid}/>
      <div>
        <div style={{
          fontFamily: t.fontBody, fontSize: 13, fontWeight: 600, color: t.text,
        }}>{label}</div>
        <div style={{
          fontFamily: t.fontLabel, fontSize: 10,
          color: t.textSoft, marginTop: 2, letterSpacing: 0.05,
        }}>min {min} · recommended {recommended}</div>
      </div>
      <div style={{
        display: 'flex', alignItems: 'baseline', gap: 8,
      }}>
        <span style={{
          fontFamily: t.fontLabel, fontSize: 9, fontWeight: 700, letterSpacing: 0.22,
          color: t.textFaint, textTransform: 'uppercase',
        }}>Detected</span>
        {isLoading ? (
          <span style={{
            fontFamily: t.fontLabel, fontSize: 16, color: t.textSoft,
            fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: 8,
          }}>
            <HCSpinner color={t.textSoft} size={13}/>
            <span style={{ letterSpacing: 0.1 }}>checking…</span>
          </span>
        ) : (
          <span style={{
            fontFamily: t.fontLabel, fontSize: 18, color: t.text,
            fontWeight: 600, letterSpacing: -0.3,
          }}>{detected}</span>
        )}
      </div>
      {isLoading ? (
        <span style={{
          width: 60, height: 24, borderRadius: 999,
          background: t.surface,
          border: `1px dashed ${t.border}`,
        }}/>
      ) : (
        <HCStatusChip t={t} status={status}/>
      )}
    </div>
  );
}

// ─── Overall banner above the rows ───────────────────────────────────
function HCOverallBanner({ t, status, isLoading }) {
  const map = {
    ok:   {
      fg: t.statusOk,
      title: 'Hardware passes preflight checks',
      sub:   'Detected configuration meets or exceeds recommended specs. You can begin setup.',
      Icon: HCCheck,
    },
    warn: {
      fg: t.statusWarn,
      title: 'Hardware below recommended specs',
      sub:   'Your hardware meets the minimum requirements. The system will run but may struggle under sustained load — large fleets, dense forecasting, or many concurrent agents.',
      Icon: HCWarn,
    },
    fail: {
      fg: t.statusAlarm,
      title: 'Hardware does not meet minimum requirements',
      sub:   'One or more checks are below the supported floor. Setup cannot continue on this hardware. Move the ISO to a machine that meets the minimums.',
      Icon: HCFail,
    },
    loading: {
      fg: t.accent,
      title: 'Inspecting hardware…',
      sub:   'Reading CPU, memory, root disk, and primary NIC. Takes about a second.',
      Icon: HCSpinner,
    },
  };
  const m = isLoading ? map.loading : map[status];
  return (
    <div style={{
      background: m.fg + '12',
      border: `1px solid ${m.fg}40`,
      borderRadius: RADIUS[3],
      padding: `${SPACE[4]}px ${SPACE[5]}px`,
      display: 'flex', alignItems: 'flex-start', gap: SPACE[4],
    }}>
      <div style={{
        width: 32, height: 32, borderRadius: '50%',
        background: m.fg + '20',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        flexShrink: 0,
      }}>
        <m.Icon color={m.fg} size={18}/>
      </div>
      <div>
        <div style={{
          fontFamily: t.fontBody, fontSize: 14, fontWeight: 600,
          color: m.fg, lineHeight: 1.3,
        }}>{m.title}</div>
        <div style={{
          fontFamily: t.fontBody, fontSize: 12, color: t.textMid,
          marginTop: 4, lineHeight: 1.5, maxWidth: 620,
        }}>{m.sub}</div>
      </div>
    </div>
  );
}

// ─── Body ────────────────────────────────────────────────────────────
function HardwareCheckBody({ t, scenario = 'ok', onProceed, onRecheck }) {
  // WIRING: server inlines real probe results as window.HARDWARE_DATA. The
  // `scenario` prop drives the mock for the designer's standalone preview;
  // window.HARDWARE_DATA wins in production.
  const [data, setData] = useStateHC(
    (typeof window !== 'undefined' && window.HARDWARE_DATA) || HW_SCENARIOS[scenario] || HW_SCENARIOS.ok
  );
  const [loading, setLoading] = useStateHC(true);

  useEffectHC(() => {
    setLoading(true);
    fetch('/setup/hardware')
      .then(r => r.ok ? r.json() : null)
      .then(fresh => {
        if (fresh) setData(fresh);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [scenario]);

  const rows = [
    {
      Icon: HCCpuIcon,
      label: 'CPU cores',
      detected:    `${data.cores.detected}`,
      rawDetected: `${data.cores.detected} cores · from nproc`,
      min:         `${data.cores.min}`,
      recommended: `${data.cores.recommended}`,
      status: data.cores.status,
    },
    {
      Icon: HCRamIcon,
      label: 'Memory',
      detected:    fmtBytes(data.ramBytes.detected),
      rawDetected: `${data.ramBytes.detected.toLocaleString()} bytes · from /proc/meminfo`,
      min:         fmtBytes(data.ramBytes.min),
      recommended: fmtBytes(data.ramBytes.recommended),
      status: data.ramBytes.status,
    },
    {
      Icon: HCDiskIcon,
      label: 'Root disk',
      detected:    fmtBytes(data.diskBytes.detected),
      rawDetected: `${data.diskBytes.detected.toLocaleString()} bytes · from df`,
      min:         fmtBytes(data.diskBytes.min),
      recommended: fmtBytes(data.diskBytes.recommended),
      status: data.diskBytes.status,
    },
    {
      Icon: HCNetIcon,
      label: 'Primary NIC',
      detected:    fmtMbps(data.nicMbps.detected),
      rawDetected: `${data.nicMbps.detected} Mbps · from ethtool on default route iface`,
      min:         fmtMbps(data.nicMbps.min),
      recommended: fmtMbps(data.nicMbps.recommended),
      status: data.nicMbps.status,
    },
  ];

  return (
    <StepShellW t={t} title="Hardware preflight"
      blurb="ARCNODE inspects the box you booted on before we start writing config. Make sure these match the ISO you were shipped.">
      <HCOverallBanner t={t} status={data.overallStatus} isLoading={loading}/>

      <div style={{
        marginTop: SPACE[4],
        background: t.panel,
        border: `1px solid ${t.border}`,
        borderRadius: RADIUS[3],
        overflow: 'hidden',
      }}>
        <div style={{
          padding: `${SPACE[3]}px ${SPACE[4]}px`,
          background: t.surface,
          borderBottom: `1px solid ${t.border}`,
          display: 'flex', alignItems: 'center', gap: SPACE[3],
        }}>
          <span style={{
            fontFamily: t.fontLabel, fontSize: 10, fontWeight: 700, letterSpacing: 0.22,
            color: t.textSoft, textTransform: 'uppercase',
          }}>Detected configuration</span>
          <span style={{ flex: 1 }}/>
          <button onClick={onRecheck} disabled={loading}
            style={{
              appearance: 'none', cursor: loading ? 'wait' : 'pointer',
              padding: '5px 10px', background: 'transparent',
              border: `1px solid ${t.border}`, borderRadius: RADIUS[1],
              fontFamily: t.fontLabel, fontSize: 10, fontWeight: 700, letterSpacing: 0.18,
              color: loading ? t.textFaint : t.text, textTransform: 'uppercase',
              display: 'inline-flex', alignItems: 'center', gap: 6,
            }}>
            <HCRefresh color={loading ? t.textFaint : t.text} size={11}/>
            Re-check
          </button>
        </div>
        {rows.map((r, i) => (
          <HCRow key={r.label} t={t} {...r}
            isLoading={loading}
            isLast={i === rows.length - 1}/>
        ))}
      </div>

      <div style={{
        marginTop: SPACE[3],
        fontFamily: t.fontLabel, fontSize: 10, color: t.textSoft,
        letterSpacing: 0.05, lineHeight: 1.5,
      }}>
        Hover any detected value to see the raw reading.
        GPU detection, network reachability, and disk-type checks are intentionally
        out of scope — the EMS runs CPU-only, and this ISO is air-gapped by design.
      </div>
    </StepShellW>
  );
}

window.HardwareCheckBody = HardwareCheckBody;
window.HW_SCENARIOS = HW_SCENARIOS;
