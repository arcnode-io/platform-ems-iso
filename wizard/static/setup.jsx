// setup-wizard.jsx — ARCNODE first-boot setup wizard.
// Served by FastAPI at https://<ip>/setup; runs once, then the URL 404s.
// 5 steps: identity → API keys → TLS → admin → review/apply.

const { useState: useStateW, useEffect: useEffectW } = React;

// WIRING: bootstrap script fetches GET /setup/identity before mount and
// stashes the result on window.INSTALL_IDENTITY. Defaults below only
// show if the fetch fails (network/file error) — operator sees they
// booted into a broken state and contacts support.
const INSTALL_IDENTITY = (typeof window !== 'undefined' && window.INSTALL_IDENTITY) || {
  customer:    '— unknown —',
  site:        '— unknown —',
  market:      '— unknown —',
  isoVersion:  '— unknown —',
  isoBuiltAt:  '— unknown —',
  orderId:     '— unknown —',
  rev:         '— unknown —',
};

// ─── Steps definition ────────────────────────────────────────────────
const STEPS = [
  { id: 'identity', n: 1, title: 'Install identity', sub: 'Confirm the right ISO' },
  { id: 'tls',      n: 2, title: 'TLS for HMI',      sub: 'How operators connect' },
  { id: 'admin',    n: 3, title: 'Grafana admin',    sub: 'Observability dashboards' },
  { id: 'review',   n: 4, title: 'Review & apply',   sub: 'Read back and start' },
];

// ─── Inline icons ────────────────────────────────────────────────────
function CheckW({ color, size = 14 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color}
         strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
      <path d="M5 12 L10 17 L19 7"/>
    </svg>
  );
}
function ChevronW({ color, size = 14, dir = 'right' }) {
  const d = dir === 'right' ? 'M9 6 L15 12 L9 18' : 'M15 6 L9 12 L15 18';
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color}
         strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
      <path d={d}/>
    </svg>
  );
}
function LockW({ color, size = 14 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color}
         strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="4" y="11" width="16" height="10" rx="2"/>
      <path d="M8 11 V7 a 4 4 0 0 1 8 0 V11"/>
    </svg>
  );
}
function SpinnerW({ color, size = 14 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color}
         strokeWidth="2.5" strokeLinecap="round"
         style={{ animation: 'wizSpin 0.9s linear infinite' }}>
      <path d="M12 3 a9 9 0 0 1 9 9" />
    </svg>
  );
}
function DotW({ color, size = 8 }) {
  return (
    <span style={{
      display: 'inline-block', width: size, height: size, borderRadius: '50%',
      background: color, boxShadow: `0 0 0 3px ${color}30`,
    }}/>
  );
}

// ─── Step rail (left column) ─────────────────────────────────────────
function StepRailW({ t, current, completed, onJump }) {
  const isSov = t.name === 'sovereign';
  const preflightActive = current === 'preflight';
  const preflightDone = completed.has('preflight');
  return (
    <div style={{
      width: 260, flexShrink: 0,
      padding: `${SPACE[6]}px ${SPACE[5]}px`,
      borderRight: `1px solid ${t.border}`,
      background: t.surface,
      display: 'flex', flexDirection: 'column', gap: SPACE[2],
    }}>
      <div style={{
        fontFamily: t.fontLabel, fontSize: 9, fontWeight: 700,
        letterSpacing: 0.22, color: t.textFaint, textTransform: 'uppercase',
        marginBottom: SPACE[3],
      }}>Setup · 5 steps</div>

      {/* preflight chip — above the numbered list, not part of the count */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: SPACE[3],
        padding: `${SPACE[2]}px ${SPACE[3]}px`,
        marginBottom: SPACE[2],
        borderRadius: RADIUS[2],
        background: preflightActive ? t.accent + '12' : 'transparent',
        borderLeft: `2px solid ${preflightActive ? t.accent : 'transparent'}`,
        cursor: preflightDone ? 'pointer' : 'default',
        opacity: (preflightActive || preflightDone) ? 1 : 0.55,
      }}
      onClick={() => preflightDone && onJump && onJump('preflight')}>
        <span style={{
          width: 22, height: 22, borderRadius: 6,
          border: `1px solid ${preflightDone ? t.statusOk : preflightActive ? t.accent : t.borderSoft}`,
          background: preflightDone ? t.statusOk : preflightActive ? t.accent : 'transparent',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          flexShrink: 0,
        }}>
          {preflightDone
            ? <CheckW color="#fff" size={11}/>
            : <svg width="11" height="11" viewBox="0 0 24 24" fill="none"
                   stroke={preflightActive ? '#fff' : t.textSoft} strokeWidth="2.2"
                   strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 2 L4 6 V12 C4 17 8 20 12 22 C16 20 20 17 20 12 V6 Z"/>
              </svg>}
        </span>
        <div style={{ minWidth: 0 }}>
          <div style={{
            fontFamily: t.fontBody, fontSize: 13, fontWeight: 600,
            color: preflightActive ? t.text : t.textMid,
            lineHeight: 1.2,
          }}>Hardware preflight</div>
          <div style={{
            fontFamily: t.fontLabel, fontSize: 10, color: t.textSoft,
            marginTop: 2, letterSpacing: 0.05,
          }}>Before setup begins</div>
        </div>
      </div>

      {STEPS.map(s => {
        const isActive = current === s.id;
        const isDone   = completed.has(s.id);
        const isUpcoming = !isActive && !isDone;
        const dotBg = isDone ? t.statusOk : isActive ? t.accent : 'transparent';
        const dotBorder = isDone ? t.statusOk : isActive ? t.accent : t.borderSoft;
        const dotFg = isDone || isActive ? '#fff' : t.textSoft;
        return (
          <div key={s.id}
            onClick={() => isDone && onJump && onJump(s.id)}
            style={{
              display: 'flex', alignItems: 'flex-start', gap: SPACE[3],
              padding: `${SPACE[2]}px ${SPACE[3]}px`,
              borderRadius: RADIUS[2],
              background: isActive ? t.accent + '12' : 'transparent',
              borderLeft: `2px solid ${isActive ? t.accent : 'transparent'}`,
              cursor: isDone ? 'pointer' : 'default',
              opacity: isUpcoming ? 0.55 : 1,
            }}>
            <span style={{
              width: 22, height: 22, borderRadius: '50%',
              border: `1px solid ${dotBorder}`,
              background: dotBg,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              flexShrink: 0, marginTop: 1,
              fontFamily: t.fontLabel, fontSize: 10, fontWeight: 700,
              color: dotFg,
            }}>
              {isDone ? <CheckW color="#fff" size={11}/> : s.n}
            </span>
            <div style={{ minWidth: 0 }}>
              <div style={{
                fontFamily: t.fontBody, fontSize: 13, fontWeight: 600,
                color: isActive ? t.text : t.textMid,
                lineHeight: 1.2,
              }}>{s.title}</div>
              <div style={{
                fontFamily: t.fontLabel, fontSize: 10, color: t.textSoft,
                marginTop: 2, letterSpacing: 0.05,
              }}>{s.sub}</div>
            </div>
          </div>
        );
      })}

      <div style={{ flex: 1 }}/>

      {/* address pill (this is the FastAPI bootstrap server) */}
      <div style={{
        padding: `${SPACE[3]}px`,
        background: t.bg,
        border: `1px solid ${t.border}`,
        borderRadius: RADIUS[2],
      }}>
        <div style={{
          display: 'flex', alignItems: 'center', gap: 6,
          fontFamily: t.fontLabel, fontSize: 9, fontWeight: 700,
          letterSpacing: 0.22, color: t.textFaint, textTransform: 'uppercase',
        }}>
          <LockW color={t.statusOk} size={10}/>
          Bootstrap server
        </div>
        <div style={{
          fontFamily: t.fontLabel, fontSize: 11,
          color: t.text, marginTop: 6, lineHeight: 1.4,
          wordBreak: 'break-all',
        }}>https://10.0.1.42/setup</div>
        <div style={{
          fontFamily: t.fontLabel, fontSize: 9, color: t.textSoft,
          marginTop: 4, letterSpacing: 0.05,
        }}>Disappears after apply.</div>
      </div>
    </div>
  );
}

// ─── Shared field primitives ─────────────────────────────────────────
function FieldLabelW({ t, children, optional, required }) {
  return (
    <label style={{
      display: 'flex', alignItems: 'baseline', gap: 6,
      fontFamily: t.fontLabel, fontSize: 10, fontWeight: 700,
      letterSpacing: 0.18, color: t.textSoft, textTransform: 'uppercase',
      marginBottom: 6,
    }}>
      <span>{children}</span>
      {optional && <span style={{ color: t.textFaint, fontWeight: 500 }}>· optional</span>}
      {required && <span style={{ color: t.statusAlarm, fontWeight: 500 }}>· required</span>}
    </label>
  );
}
function TextInputW({ t, value, onChange, placeholder, type = 'text', disabled, mono, error }) {
  return (
    <input
      type={type} value={value} onChange={e => onChange && onChange(e.target.value)}
      placeholder={placeholder} disabled={disabled}
      style={{
        width: '100%', height: 40, padding: '0 12px',
        boxSizing: 'border-box',
        background: disabled ? t.surface : t.bg,
        border: `1px solid ${error ? t.statusAlarm : t.border}`,
        borderRadius: RADIUS[2],
        fontFamily: mono ? t.fontLabel : t.fontBody, fontSize: 13,
        color: disabled ? t.textSoft : t.text,
        outline: 'none',
      }}
    />
  );
}
function HelperW({ t, children, error }) {
  return (
    <div style={{
      fontFamily: t.fontLabel, fontSize: 10,
      color: error ? t.statusAlarm : t.textSoft,
      marginTop: 6, lineHeight: 1.4, letterSpacing: 0.05,
    }}>{children}</div>
  );
}

// ─── Step 1 — Install identity (read-only) ───────────────────────────
function Step1Identity({ t }) {
  const isSov = t.name === 'sovereign';
  const items = [
    { label: 'Customer',       value: INSTALL_IDENTITY.customer },
    { label: 'Site',           value: INSTALL_IDENTITY.site },
    { label: 'Market',         value: INSTALL_IDENTITY.market },
    { label: 'ISO version',    value: INSTALL_IDENTITY.isoVersion, mono: true },
    { label: 'Built',          value: INSTALL_IDENTITY.isoBuiltAt },
    { label: 'Configurator order', value: INSTALL_IDENTITY.orderId, mono: true },
  ];
  return (
    <StepShellW t={t} title="Confirm install identity"
      blurb="Make sure this is the ISO that was built for your site. If anything below is wrong, stop and contact your ARCNODE configurator.">
      <div style={{
        background: t.panel,
        border: `1px solid ${t.border}`,
        borderRadius: RADIUS[3],
        overflow: 'hidden',
      }}>
        {items.map((it, i) => (
          <div key={it.label} style={{
            display: 'grid',
            gridTemplateColumns: '180px 1fr',
            padding: `${SPACE[3]}px ${SPACE[4]}px`,
            borderBottom: i < items.length - 1 ? `1px solid ${t.border}` : 'none',
            alignItems: 'center',
          }}>
            <span style={{
              fontFamily: t.fontLabel, fontSize: 10, fontWeight: 700,
              letterSpacing: 0.18, color: t.textSoft, textTransform: 'uppercase',
            }}>{it.label}</span>
            <span style={{
              fontFamily: it.mono ? t.fontLabel : t.fontBody,
              fontSize: it.mono ? 13 : 14,
              color: t.text, fontWeight: it.mono ? 500 : 600,
            }}>{it.value}</span>
          </div>
        ))}
      </div>
      <div style={{
        marginTop: SPACE[4], padding: `${SPACE[3]}px ${SPACE[4]}px`,
        background: t.accent + '12',
        border: `1px solid ${t.accent}30`,
        borderRadius: RADIUS[2],
        fontFamily: t.fontBody, fontSize: 12, color: t.textMid, lineHeight: 1.5,
      }}>
        This wizard captures only the four things Debian doesn't know about.
        Network, disk, timezone, and root password were set during the Debian installer.
      </div>
    </StepShellW>
  );
}

function ToggleW({ t, on, onChange, label }) {
  return (
    <div onClick={() => onChange(!on)} style={{
      display: 'inline-flex', alignItems: 'center', gap: 8,
      cursor: 'pointer', userSelect: 'none',
    }}>
      <span style={{
        fontFamily: t.fontLabel, fontSize: 10, fontWeight: 700,
        letterSpacing: 0.2, textTransform: 'uppercase',
        color: on ? t.text : t.textSoft,
      }}>{label}</span>
      <span style={{
        width: 32, height: 18, borderRadius: 999,
        background: on ? t.accent : t.borderSoft,
        position: 'relative', transition: 'background 0.15s',
      }}>
        <span style={{
          position: 'absolute', top: 2, left: on ? 16 : 2,
          width: 14, height: 14, borderRadius: '50%',
          background: '#fff', transition: 'left 0.15s',
          boxShadow: '0 1px 2px rgba(0,0,0,0.2)',
        }}/>
      </span>
    </div>
  );
}

// ─── Step 3 — TLS for HMI ────────────────────────────────────────────
function Step3TLS({ t, mode, onMode, certName, keyName, onCert, onKey }) {
  return (
    <StepShellW t={t} title="TLS for the HMI"
      blurb="Choose how operators' browsers will trust this box. Self-signed is fine for initial install; replace from HMI settings later.">
      <div style={{ display: 'flex', flexDirection: 'column', gap: SPACE[3] }}>
        <RadioCardW t={t} active={mode === 'selfsigned'}
          onClick={() => onMode('selfsigned')}
          title="Generate self-signed certificate"
          sub="ARCNODE creates a 4096-bit RSA cert valid for 3 years. Operators will get a one-time browser warning, then can trust the cert per machine."
          badge="Default"/>
        <RadioCardW t={t} active={mode === 'upload'}
          onClick={() => onMode('upload')}
          title="Upload certificate and key"
          sub="Provide a cert + key issued by your own CA. We validate they parse and that the key matches the cert before continuing.">
          {mode === 'upload' && (
            <div style={{
              display: 'grid', gridTemplateColumns: '1fr 1fr', gap: SPACE[3],
              marginTop: SPACE[3],
              paddingTop: SPACE[3],
              borderTop: `1px solid ${t.border}`,
            }}>
              <FileFieldW t={t} label="Certificate" ext=".crt" filename={certName}
                onPick={(name) => onCert(name)}/>
              <FileFieldW t={t} label="Private key" ext=".key" filename={keyName}
                onPick={(name) => onKey(name)}/>
            </div>
          )}
        </RadioCardW>
      </div>
    </StepShellW>
  );
}
function RadioCardW({ t, active, onClick, title, sub, badge, children }) {
  return (
    <div onClick={onClick} style={{
      background: t.panel,
      border: `1px solid ${active ? t.accent : t.border}`,
      borderRadius: RADIUS[3],
      padding: `${SPACE[4]}px`,
      cursor: 'pointer',
      boxShadow: active ? `0 0 0 2px ${t.accent}25` : 'none',
    }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: SPACE[3] }}>
        <span style={{
          width: 18, height: 18, borderRadius: '50%',
          border: `1.5px solid ${active ? t.accent : t.borderSoft}`,
          background: t.bg,
          flexShrink: 0, marginTop: 2,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          {active && <span style={{
            width: 8, height: 8, borderRadius: '50%', background: t.accent,
          }}/>}
        </span>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: SPACE[3] }}>
            <span style={{
              fontFamily: t.fontBody, fontSize: 14, fontWeight: 600, color: t.text,
            }}>{title}</span>
            {badge && (
              <span style={{
                fontFamily: t.fontLabel, fontSize: 9, fontWeight: 700, letterSpacing: 0.22,
                color: t.statusOk,
                background: t.statusOk + '18',
                border: `1px solid ${t.statusOk}40`,
                padding: '1px 6px', borderRadius: RADIUS[1], textTransform: 'uppercase',
              }}>{badge}</span>
            )}
          </div>
          <div style={{
            fontFamily: t.fontBody, fontSize: 12, color: t.textMid,
            marginTop: 4, lineHeight: 1.5,
          }}>{sub}</div>
          {children}
        </div>
      </div>
    </div>
  );
}
function FileFieldW({ t, label, ext, filename, onPick }) {
  return (
    <div>
      <FieldLabelW t={t}>{label}</FieldLabelW>
      <div style={{
        display: 'flex', alignItems: 'center', gap: SPACE[3],
        height: 40, padding: '0 4px 0 12px',
        background: t.bg,
        border: `1px dashed ${t.borderSoft}`,
        borderRadius: RADIUS[2],
      }}>
        <span style={{
          fontFamily: t.fontLabel, fontSize: 11,
          color: filename ? t.text : t.textSoft,
          flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
        }}>{filename || `drop or browse · ${ext}`}</span>
        <button onClick={(e) => {
            e.stopPropagation();
            const fake = label === 'Certificate' ? 'brookside-dc-1.crt' : 'brookside-dc-1.key';
            onPick(filename ? null : fake);
          }} style={{
          appearance: 'none', cursor: 'pointer',
          height: 30, padding: '0 12px',
          background: 'transparent',
          border: `1px solid ${t.border}`,
          borderRadius: RADIUS[1],
          fontFamily: t.fontLabel, fontSize: 10, fontWeight: 700, letterSpacing: 0.18,
          color: t.text, textTransform: 'uppercase',
        }}>{filename ? 'Replace' : 'Browse'}</button>
      </div>
    </div>
  );
}

// ─── Step 4 — Grafana admin password ─────────────────────────────────
function Step4Admin({ t, password, confirm, onP, onC }) {
  const strength = passwordStrength(password);
  const mismatch = confirm.length > 0 && confirm !== password;
  return (
    <StepShellW t={t} title="Grafana admin password"
      blurb="Sign-in for Grafana, the observability dashboards. Username is fixed at admin. Separate from the system root password you set during Debian install — that one stays for SSH and local console only.">
      <div style={{
        background: t.panel,
        border: `1px solid ${t.border}`,
        borderRadius: RADIUS[3],
        padding: SPACE[5],
        display: 'flex', flexDirection: 'column', gap: SPACE[4],
      }}>
        <div>
          <FieldLabelW t={t} required>Password</FieldLabelW>
          <TextInputW t={t} type="password" value={password} onChange={onP} placeholder="at least 12 characters"/>
          <PasswordStrengthW t={t} strength={strength} password={password}/>
        </div>
        <div>
          <FieldLabelW t={t} required>Confirm password</FieldLabelW>
          <TextInputW t={t} type="password" value={confirm} onChange={onC}
            error={mismatch}/>
          {mismatch && <HelperW t={t} error>Passwords don't match.</HelperW>}
        </div>
      </div>
    </StepShellW>
  );
}
function passwordStrength(pw) {
  if (!pw) return 0;
  let s = 0;
  if (pw.length >= 8)  s++;
  if (pw.length >= 12) s++;
  if (/[A-Z]/.test(pw) && /[a-z]/.test(pw)) s++;
  if (/\d/.test(pw))   s++;
  if (/[^A-Za-z0-9]/.test(pw)) s++;
  return Math.min(s, 4);
}
function PasswordStrengthW({ t, strength, password }) {
  const labels = ['Too short', 'Weak', 'Fair', 'Good', 'Strong'];
  const colors = [t.statusAlarm, t.statusAlarm, t.statusWarn, t.colorBess, t.statusOk];
  const label = password ? labels[strength] : '';
  const c = colors[strength];
  return (
    <div style={{ marginTop: 8 }}>
      <div style={{ display: 'flex', gap: 4 }}>
        {[0,1,2,3].map(i => (
          <div key={i} style={{
            flex: 1, height: 4, borderRadius: 2,
            background: i < strength ? c : t.borderSoft,
          }}/>
        ))}
      </div>
      <div style={{
        fontFamily: t.fontLabel, fontSize: 10,
        color: password ? c : t.textSoft,
        marginTop: 6, letterSpacing: 0.1, fontWeight: 600,
      }}>{password ? label : 'Mix length, case, digits, and a symbol.'}</div>
    </div>
  );
}

// ─── Step 5 — Review + apply ─────────────────────────────────────────
function Step5Review({ t, values, applyState, applyEvents, applyError,
                       onApply, onJump }) {
  const isApplying = applyState === 'applying';
  const isDone     = applyState === 'done';
  const isIdle     = applyState === 'idle' && !applyError;
  const titleText = isIdle ? 'Review and apply'
                  : isDone ? 'Airgapped-ready'
                  : applyError ? 'Apply failed — retry below'
                  : 'Applying…';
  const blurbText = isIdle
    ? 'A single POST writes all configuration, pulls AI models, pulls container images, and starts ARCNODE. The /setup endpoint disappears after success.'
    : isDone
      ? 'ARCNODE is running. You can disconnect from the internet now. Redirecting to the HMI shortly.'
      : applyError
        ? 'Network blips during a 20-min pull happen. Pulls are idempotent — retry picks up where it stopped.'
        : 'This takes a while on first install — AI models are 5–17 GB each. Pulls are streamed from ollama + docker.';
  return (
    <StepShellW t={t} title={titleText} blurb={blurbText}>
      {isIdle && <ReviewSummary t={t} values={values} onJump={onJump}/>}
      {!isIdle && <ProgressLog t={t} events={applyEvents}
                               error={applyError} onRetry={onApply}/>}
    </StepShellW>
  );
}
function ReviewSummary({ t, values, onJump }) {
  const tlsSummary = values.tls.mode === 'selfsigned'
    ? 'Self-signed (auto-generated, 3-year)'
    : `Uploaded · ${values.tls.cert || '?'} + ${values.tls.key || '?'}`;
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: SPACE[3] }}>
      <ReviewCard t={t} title="Install identity" onEdit={() => onJump('identity')}
        rows={[
          ['Customer', INSTALL_IDENTITY.customer],
          ['Site',     INSTALL_IDENTITY.site],
          ['Market',   INSTALL_IDENTITY.market],
          ['Order',    INSTALL_IDENTITY.orderId],
        ]}/>
      <ReviewCard t={t} title="TLS" onEdit={() => onJump('tls')}
        rows={[ ['Mode', tlsSummary] ]}/>
      <ReviewCard t={t} title="Grafana admin" onEdit={() => onJump('admin')}
        rows={[
          ['Username', 'admin'],
          ['Password', '•••••••••• (set)'],
        ]}/>
    </div>
  );
}
function ReviewCard({ t, title, rows, onEdit }) {
  return (
    <div style={{
      background: t.panel,
      border: `1px solid ${t.border}`,
      borderRadius: RADIUS[3],
      overflow: 'hidden',
    }}>
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: `${SPACE[3]}px ${SPACE[4]}px`,
        background: t.surface,
        borderBottom: `1px solid ${t.border}`,
      }}>
        <span style={{
          fontFamily: t.fontLabel, fontSize: 10, fontWeight: 700,
          letterSpacing: 0.22, color: t.textSoft, textTransform: 'uppercase',
        }}>{title}</span>
        <button onClick={onEdit} style={{
          appearance: 'none', cursor: 'pointer',
          padding: '4px 10px', background: 'transparent',
          border: `1px solid ${t.border}`, borderRadius: RADIUS[1],
          fontFamily: t.fontLabel, fontSize: 9, fontWeight: 700, letterSpacing: 0.18,
          color: t.text, textTransform: 'uppercase',
        }}>Edit</button>
      </div>
      {rows.map((r, i) => (
        <div key={i} style={{
          display: 'grid', gridTemplateColumns: '140px 1fr',
          padding: `${SPACE[2]}px ${SPACE[4]}px`,
          borderBottom: i < rows.length - 1 ? `1px solid ${t.border}` : 'none',
          alignItems: 'center',
        }}>
          <span style={{
            fontFamily: t.fontLabel, fontSize: 10, fontWeight: 700,
            letterSpacing: 0.18, color: t.textFaint, textTransform: 'uppercase',
          }}>{r[0]}</span>
          <span style={{ fontFamily: t.fontBody, fontSize: 12, color: t.text }}>{r[1]}</span>
        </div>
      ))}
    </div>
  );
}

// Derive per-phase progress from the SSE event stream.
// Phases reach: pending → active → done. Models track per-role byte progress;
// images track a tail of the last log lines.
function derivePhases(events) {
  const phases = {
    config: { status: 'pending' },
    models: { status: 'pending', roles: [] },
    images: { status: 'pending', lastLines: [] },
    done:   false,
  };
  for (const ev of events) {
    if (ev.phase === 'config') {
      phases.config.status = ev.status === 'done' ? 'done' : 'active';
    } else if (ev.phase === 'models') {
      if (ev.status === 'start') {
        phases.models.status = 'active';
        phases.models.roles = ev.roles.map(r => ({
          ...r, completed: 0, total: 0, done: false,
        }));
      } else if (ev.status === 'done') {
        phases.models.status = 'done';
      } else if (ev.status === 'model_progress' && ev.ollama?.total) {
        const r = phases.models.roles.find(x => x.role === ev.role);
        if (r) { r.completed = ev.ollama.completed || 0; r.total = ev.ollama.total; }
      } else if (ev.status === 'model_done') {
        const r = phases.models.roles.find(x => x.role === ev.role);
        if (r) { r.done = true; r.completed = r.total; }
      }
    } else if (ev.phase === 'images') {
      if (ev.status === 'start') phases.images.status = 'active';
      else if (ev.status === 'done') phases.images.status = 'done';
      else if (ev.status === 'log') {
        phases.images.lastLines = [...phases.images.lastLines, ev.line].slice(-5);
      }
    } else if (ev.phase === 'done') {
      phases.done = true;
    }
  }
  return phases;
}

function fmtBytes(n) {
  if (!n || n < 1024) return `${n || 0} B`;
  const units = ['KB', 'MB', 'GB'];
  let v = n / 1024, u = 0;
  while (v >= 1024 && u < units.length - 1) { v /= 1024; u++; }
  return `${v.toFixed(1)} ${units[u]}`;
}

const ROLE_LABEL = { chat: 'Chat model', code: 'Code model', embedder: 'RAG embedder' };

function ProgressLog({ t, events, error, onRetry }) {
  const phases = derivePhases(events);
  return (
    <div style={{
      background: t.panel, border: `1px solid ${t.border}`,
      borderRadius: RADIUS[3], overflow: 'hidden',
    }}>
      <PhaseRow t={t} label="Writing config" state={phases.config.status}/>
      <PhaseRow t={t} label="AI models" state={phases.models.status}>
        {phases.models.roles.map(r => (
          <ModelRow key={r.role} t={t} role={r.role} model={r.model}
                    completed={r.completed} total={r.total} done={r.done}/>
        ))}
      </PhaseRow>
      <PhaseRow t={t} label="Container images" state={phases.images.status}>
        {phases.images.lastLines.length > 0 && (
          <pre style={{
            margin: 0, padding: `${SPACE[2]}px ${SPACE[4]}px`,
            background: t.bg, color: t.textSoft,
            fontFamily: t.fontLabel, fontSize: 11,
            whiteSpace: 'pre-wrap', wordBreak: 'break-word',
            maxHeight: 110, overflow: 'hidden',
          }}>{phases.images.lastLines.join('\n')}</pre>
        )}
      </PhaseRow>
      {phases.done && (
        <div style={{
          padding: `${SPACE[4]}px ${SPACE[4]}px`,
          background: t.bg,
          borderTop: `1px solid ${t.border}`,
          display: 'flex', alignItems: 'center', gap: SPACE[3],
        }}>
          <CheckW color={t.statusOk} size={16}/>
          <div style={{ flex: 1 }}>
            <div style={{
              fontFamily: t.fontBody, fontSize: 14, fontWeight: 600,
              color: t.text,
            }}>Airgapped-ready</div>
            <div style={{
              fontFamily: t.fontBody, fontSize: 12, color: t.textMid,
              marginTop: 2,
            }}>You can disconnect from the internet now. Redirecting to HMI…</div>
          </div>
        </div>
      )}
      {error && (
        <div style={{
          padding: `${SPACE[4]}px ${SPACE[4]}px`,
          background: t.bg, borderTop: `1px solid ${t.border}`,
          display: 'flex', alignItems: 'center', gap: SPACE[3],
        }}>
          <div style={{ flex: 1 }}>
            <div style={{
              fontFamily: t.fontBody, fontSize: 14, fontWeight: 600,
              color: t.statusBad || '#d44',
            }}>Apply failed</div>
            <div style={{
              fontFamily: t.fontLabel, fontSize: 11, color: t.textMid,
              marginTop: 4, wordBreak: 'break-word',
            }}>{error}</div>
          </div>
          <button onClick={onRetry} style={{
            appearance: 'none', cursor: 'pointer',
            height: 36, padding: '0 14px',
            background: t.accent, color: '#fff',
            border: 'none', borderRadius: RADIUS[2],
            fontFamily: t.fontLabel, fontSize: 11, fontWeight: 700,
            letterSpacing: 0.2, textTransform: 'uppercase',
          }}>Retry</button>
        </div>
      )}
    </div>
  );
}

function PhaseRow({ t, label, state, children }) {
  const icon = state === 'done'   ? <CheckW color={t.statusOk} size={14}/>
             : state === 'active' ? <SpinnerW color={t.accent} size={14}/>
             :                      <span style={{
                                      width: 12, height: 12, borderRadius: '50%',
                                      border: `1px solid ${t.border}`,
                                      display: 'inline-block',
                                    }}/>;
  return (
    <div style={{ borderBottom: `1px solid ${t.border}` }}>
      <div style={{
        padding: `${SPACE[3]}px ${SPACE[4]}px`,
        background: t.surface,
        display: 'flex', alignItems: 'center', gap: SPACE[3],
      }}>
        {icon}
        <span style={{
          fontFamily: t.fontLabel, fontSize: 11, fontWeight: 700,
          letterSpacing: 0.18, color: t.text, textTransform: 'uppercase',
        }}>{label}</span>
      </div>
      {children}
    </div>
  );
}

function ModelRow({ t, role, model, completed, total, done }) {
  const pct = total ? Math.min(100, Math.round((completed / total) * 100)) : 0;
  return (
    <div style={{
      padding: `${SPACE[2]}px ${SPACE[4]}px`,
      display: 'grid', gridTemplateColumns: '110px 1fr 90px 90px',
      gap: SPACE[3], alignItems: 'center',
      background: t.bg,
    }}>
      <span style={{
        fontFamily: t.fontLabel, fontSize: 10, fontWeight: 700,
        letterSpacing: 0.18, color: t.textSoft, textTransform: 'uppercase',
      }}>{ROLE_LABEL[role] || role}</span>
      <div>
        <div style={{
          fontFamily: t.fontLabel, fontSize: 11, color: t.textMid,
          marginBottom: 4,
        }}>{model}</div>
        <div style={{
          height: 4, background: t.border, borderRadius: 2,
          overflow: 'hidden',
        }}>
          <div style={{
            height: '100%', width: `${pct}%`,
            background: done ? t.statusOk : t.accent,
            transition: 'width 0.3s ease-out',
          }}/>
        </div>
      </div>
      <span style={{
        fontFamily: t.fontLabel, fontSize: 11, color: t.textSoft,
        textAlign: 'right',
      }}>{done ? '' : `${fmtBytes(completed)} / ${fmtBytes(total)}`}</span>
      <span style={{
        fontFamily: t.fontLabel, fontSize: 11, color: t.textSoft,
        textAlign: 'right',
      }}>{done ? '✓ done' : `${pct}%`}</span>
    </div>
  );
}

// ─── Shared step shell (title + blurb + children) ────────────────────
function StepShellW({ t, title, blurb, children }) {
  const isSov = t.name === 'sovereign';
  return (
    <div>
      <div style={{
        fontFamily: t.fontHeading, fontSize: 32,
        fontWeight: isSov ? 400 : 600,
        letterSpacing: isSov ? 0.8 : -0.3,
        textTransform: isSov ? 'uppercase' : 'none',
        color: t.text, lineHeight: 1.05,
      }}>{title}</div>
      {blurb && (
        <div style={{
          fontFamily: t.fontBody, fontSize: 14, color: t.textMid,
          marginTop: SPACE[3], maxWidth: 640, lineHeight: 1.55,
        }}>{blurb}</div>
      )}
      <div style={{ marginTop: SPACE[5] }}>{children}</div>
    </div>
  );
}

// ─── Theme toggle ───────────────────────────────────────────────────
function ThemeToggleW({ t, isDark, onToggle }) {
  return (
    <button onClick={onToggle}
      title={isDark ? 'Switch to light' : 'Switch to dark'}
      style={{
        appearance: 'none', cursor: 'pointer',
        width: 36, height: 36, padding: 0,
        background: t.surface,
        border: `1px solid ${t.border}`,
        borderRadius: RADIUS[2],
        display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
        color: t.textMid,
      }}>
      {isDark
        ? (
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={t.text}
               strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="4"/>
            <path d="M12 2 V4 M12 20 V22 M4.93 4.93 L6.34 6.34 M17.66 17.66 L19.07 19.07 M2 12 H4 M20 12 H22 M4.93 19.07 L6.34 17.66 M17.66 6.34 L19.07 4.93"/>
          </svg>
        ) : (
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={t.text}
               strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 12.8 A9 9 0 1 1 11.2 3 a7 7 0 0 0 9.8 9.8 Z"/>
          </svg>
        )}
    </button>
  );
}

// ─── Top header ─────────────────────────────────────────────────────
function HeaderW({ t, current, isDark, onToggleTheme }) {
  const isSov = t.name === 'sovereign';
  const idx = STEPS.findIndex(s => s.id === current);
  const isPreflight = current === 'preflight';
  return (
    <div style={{
      padding: `${SPACE[4]}px ${SPACE[6]}px`,
      borderBottom: `1px solid ${t.border}`,
      display: 'flex', alignItems: 'center', gap: SPACE[4],
      background: t.bg,
    }}>
      <div style={{
        width: 36, height: 36, borderRadius: RADIUS[2],
        background: t.accent,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.2">
          <path d="M4 18 L12 4 L20 18 M7 14 H17"/>
        </svg>
      </div>
      <div style={{ flex: 1 }}>
        <div style={{
          fontFamily: t.fontHeading, fontSize: 18,
          fontWeight: isSov ? 400 : 600,
          letterSpacing: isSov ? 1.4 : 0,
          textTransform: isSov ? 'uppercase' : 'none',
          color: t.text, lineHeight: 1,
        }}>ARCNODE</div>
        <div style={{
          fontFamily: t.fontLabel, fontSize: 10,
          letterSpacing: 0.22, textTransform: 'uppercase',
          color: t.textSoft, marginTop: 3, fontWeight: 700,
        }}>First-boot setup</div>
      </div>
      <div style={{
        fontFamily: t.fontLabel, fontSize: 11, fontWeight: 700, letterSpacing: 0.2,
        color: t.textSoft, textTransform: 'uppercase',
      }}>
        {isPreflight
          ? 'Preflight'
          : <>Step <span style={{ color: t.text }}>{idx + 1}</span> of {STEPS.length}</>}
      </div>
      {onToggleTheme && (
        <ThemeToggleW t={t} isDark={isDark} onToggle={onToggleTheme}/>
      )}
    </div>
  );
}

// ─── Footer (Back / Continue) ───────────────────────────────────────
function FooterW({ t, current, applyState, hwScenario, onBack, onNext, onApply }) {
  const idx = STEPS.findIndex(s => s.id === current);
  const isLast = current === 'review';
  const isPreflight = current === 'preflight';
  const isApplying = applyState === 'applying';
  const isDone = applyState === 'done';

  const hwData = (typeof HW_SCENARIOS !== 'undefined') ? HW_SCENARIOS[hwScenario] : null;
  const hwStatus = hwData?.overallStatus || 'ok';
  const hwBlocked = isPreflight && hwStatus === 'fail';
  const hwWarn    = isPreflight && hwStatus === 'warn';

  let nextLabel;
  if (isPreflight)              nextLabel = hwWarn ? 'Continue anyway' : 'Begin setup';
  else if (current === 'identity') nextLabel = 'Continue';
  else                          nextLabel = 'Continue';

  const backDisabled = isPreflight || isApplying || isDone;

  return (
    <div style={{
      padding: `${SPACE[4]}px ${SPACE[6]}px`,
      borderTop: `1px solid ${t.border}`,
      display: 'flex', alignItems: 'center', gap: SPACE[3],
      background: t.bg,
    }}>
      <button onClick={onBack} disabled={backDisabled}
        style={{
          appearance: 'none',
          cursor: backDisabled ? 'not-allowed' : 'pointer',
          height: 40, padding: '0 16px',
          background: 'transparent',
          border: `1px solid ${t.border}`,
          borderRadius: RADIUS[2],
          fontFamily: t.fontLabel, fontSize: 11, fontWeight: 700, letterSpacing: 0.18,
          color: backDisabled ? t.textFaint : t.text,
          textTransform: 'uppercase',
          display: 'inline-flex', alignItems: 'center', gap: 6,
        }}>
        <ChevronW color={backDisabled ? t.textFaint : t.text} size={12} dir="left"/>
        Back
      </button>
      <span style={{ flex: 1 }}/>

      {/* contextual hint */}
      <span style={{
        fontFamily: t.fontLabel, fontSize: 10, color: t.textSoft, letterSpacing: 0.1,
      }}>
        {isApplying  ? 'Do not refresh the page.'
         : isDone    ? 'Redirecting to HMI…'
         : isLast    ? 'Applies all changes in a single transaction.'
         : isPreflight && hwBlocked
                     ? 'Move the ISO to hardware that meets the minimums.'
         : isPreflight && hwWarn
                     ? 'Below recommended — the system will run but may struggle under load.'
         : isPreflight ? 'Next · Install identity'
         : `Next · ${STEPS[idx + 1]?.title}`}
      </span>

      {isLast ? (
        <button onClick={onApply} disabled={isApplying || isDone}
          style={primaryBtnStyle(t, isApplying || isDone)}>
          {isApplying && <SpinnerW color="#fff" size={13}/>}
          {isDone && <CheckW color="#fff" size={13}/>}
          {isApplying ? 'Applying' : isDone ? 'Complete' : 'Apply & start ARCNODE'}
        </button>
      ) : (
        <button onClick={hwBlocked ? undefined : onNext}
          disabled={hwBlocked}
          style={hwWarn
            ? secondaryBtnStyle(t, false)
            : primaryBtnStyle(t, hwBlocked)}>
          {nextLabel}
          <ChevronW color={hwWarn ? t.text : '#fff'} size={12}/>
        </button>
      )}
    </div>
  );
}
function secondaryBtnStyle(t, disabled) {
  return {
    appearance: 'none', cursor: disabled ? 'not-allowed' : 'pointer',
    height: 40, padding: '0 18px',
    background: 'transparent',
    border: `1px solid ${t.statusWarn}`,
    color: t.text,
    borderRadius: RADIUS[2],
    display: 'inline-flex', alignItems: 'center', gap: 8,
    fontFamily: t.fontLabel, fontSize: 11, fontWeight: 700, letterSpacing: 0.18,
    textTransform: 'uppercase',
  };
}
function primaryBtnStyle(t, disabled) {
  return {
    appearance: 'none', cursor: disabled ? 'not-allowed' : 'pointer',
    height: 40, padding: '0 18px',
    background: disabled ? t.accentDim : t.accent,
    border: `1px solid ${disabled ? t.accentDim : t.accent}`,
    color: '#fff',
    borderRadius: RADIUS[2],
    display: 'inline-flex', alignItems: 'center', gap: 8,
    fontFamily: t.fontLabel, fontSize: 11, fontWeight: 700, letterSpacing: 0.18,
    textTransform: 'uppercase',
    opacity: disabled ? 0.85 : 1,
  };
}

// ─── Main wizard body ───────────────────────────────────────────────
function SetupWizardBody({ t, initialStep, initialApply, initialHwScenario, isDark, onToggleTheme }) {
  const [current, setCurrent] = useStateW(initialStep || 'preflight');
  const [completed, setCompleted] = useStateW(new Set());
  const [applyState, setApplyState] = useStateW(initialApply || 'idle');
  const [applyEvents, setApplyEvents] = useStateW([]);
  const [applyError, setApplyError] = useStateW(null);
  const [hwScenario, setHwScenario] = useStateW(initialHwScenario || 'ok');
  const [hwKey, setHwKey] = useStateW(0); // bumps to re-trigger the spinner

  // form values
  const [values, setValues] = useStateW({
    tls: { mode: 'selfsigned', cert: null, key: null },
    admin: { password: 'correct-horse-battery-staple', confirm: 'correct-horse-battery-staple' },
  });

  // react to externally-injected state changes (from tweaks)
  useEffectW(() => {
    if (initialStep && initialStep !== current) setCurrent(initialStep);
  }, [initialStep]);
  useEffectW(() => {
    if (initialApply && initialApply !== applyState) {
      setApplyState(initialApply);
      if (initialApply !== 'idle') setCurrent('review');
    }
  }, [initialApply]);
  useEffectW(() => {
    if (initialHwScenario && initialHwScenario !== hwScenario) {
      setHwScenario(initialHwScenario);
      setHwKey(k => k + 1);
    }
  }, [initialHwScenario]);

  const advance = (nextId) => {
    setCompleted(s => new Set([...s, current]));
    setCurrent(nextId);
  };
  const onNext = () => {
    if (current === 'preflight') {
      setCompleted(s => new Set([...s, 'preflight']));
      setCurrent('identity');
      return;
    }
    const idx = STEPS.findIndex(s => s.id === current);
    if (idx < STEPS.length - 1) advance(STEPS[idx + 1].id);
  };
  const onBack = () => {
    if (current === 'identity') {
      setCurrent('preflight');
      return;
    }
    const idx = STEPS.findIndex(s => s.id === current);
    if (idx > 0) setCurrent(STEPS[idx - 1].id);
  };
  // POST /setup/apply now returns text/event-stream. Read the body
  // incrementally and route events into derivePhases-friendly state.
  // Pulls are idempotent — retry on error re-POSTs same body, backend
  // skips cached models/images quickly.
  const onApply = async () => {
    setApplyState('applying');
    setApplyEvents([]);
    setApplyError(null);
    const body = {
      tls: {
        mode: values.tls.mode === 'selfsigned' ? 'self_signed' : 'upload',
        certPem: values.tls.cert,
        keyPem:  values.tls.key,
      },
      admin: {
        password: values.admin.password,
      },
    };
    try {
      const resp = await fetch('/setup/apply', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!resp.ok) throw new Error(`apply failed: ${resp.status}`);
      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buf = '';
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const frames = buf.split('\n\n');
        buf = frames.pop() || '';
        for (const f of frames) {
          if (!f.startsWith('data: ')) continue;
          let ev;
          try { ev = JSON.parse(f.slice(6)); }
          catch (e) { console.error('bad SSE frame', f); continue; }
          if (ev.phase === 'error') {
            setApplyError(ev.message || 'unknown apply error');
            setApplyState('idle');
            return;
          }
          setApplyEvents(es => [...es, ev]);
          if (ev.phase === 'done') {
            setApplyState('done');
            // 3s pause so the operator sees the "airgapped-ready" message
            // before the HMI takeover bounces them.
            setTimeout(() => {
              window.location.href = ev.redirect || '/';
            }, 3000);
          }
        }
      }
    } catch (e) {
      console.error('apply error', e);
      setApplyError(e.message);
      setApplyState('idle');
    }
  };
  const onJump = (id) => setCurrent(id);
  const onRecheck = () => setHwKey(k => k + 1);

  const setTLSMode  = (m)     => setValues(s => ({ ...s, tls: { ...s.tls, mode: m } }));
  const setCert     = (n)     => setValues(s => ({ ...s, tls: { ...s.tls, cert: n } }));
  const setTLSKey   = (n)     => setValues(s => ({ ...s, tls: { ...s.tls, key: n } }));
  const setPassword = (v)     => setValues(s => ({ ...s, admin: { ...s.admin, password: v } }));
  const setConfirm  = (v)     => setValues(s => ({ ...s, admin: { ...s.admin, confirm: v } }));

  return (
    <div style={{
      display: 'flex', flexDirection: 'column',
      background: t.bg,
      fontFamily: t.fontBody, color: t.text,
      minHeight: '100%',
    }}>
      <HeaderW t={t} current={current} isDark={isDark} onToggleTheme={onToggleTheme}/>
      <div style={{ flex: 1, display: 'flex', minHeight: 0 }}>
        <StepRailW t={t} current={current} completed={completed} onJump={onJump}/>
        <div style={{
          flex: 1,
          padding: `${SPACE[6]}px ${SPACE[8]}px ${SPACE[6]}px`,
          overflowY: 'auto',
          maxWidth: 820,
        }}>
          {current === 'preflight' && <HardwareCheckBody key={hwKey} t={t} scenario={hwScenario} onRecheck={onRecheck}/>}
          {current === 'identity' && <Step1Identity t={t}/>}
          {current === 'tls'      && <Step3TLS      t={t} mode={values.tls.mode} onMode={setTLSMode}
                                                    certName={values.tls.cert} keyName={values.tls.key}
                                                    onCert={setCert} onKey={setTLSKey}/>}
          {current === 'admin'    && <Step4Admin    t={t} password={values.admin.password}
                                                    confirm={values.admin.confirm}
                                                    onP={setPassword} onC={setConfirm}/>}
          {current === 'review'   && <Step5Review   t={t} values={values}
                                                    applyState={applyState}
                                                    applyEvents={applyEvents}
                                                    applyError={applyError}
                                                    onApply={onApply} onJump={onJump}/>}
        </div>
      </div>
      <FooterW t={t} current={current} applyState={applyState}
        hwScenario={hwScenario}
        onBack={onBack} onNext={onNext} onApply={onApply}/>
    </div>
  );
}

window.SetupWizardBody = SetupWizardBody;
