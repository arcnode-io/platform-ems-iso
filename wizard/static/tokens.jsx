// tokens.jsx — Sovereign + Solarpunk theme tokens, both first-class.
// All values traced to ems-hmi-design-system.md §1.1 / §1.2.

const SOVEREIGN = {
  name: 'sovereign',
  // Surface
  bg:           '#080808',
  surface:      '#0e0e0e',
  panel:        '#131313',
  border:       '#1f1f1f',
  borderSoft:   '#2a2a2a',
  // Accent
  accent:       '#4a7aaa',
  accentDim:    '#3a6090',
  accentFaint:  '#0a1520',
  // Text
  text:         '#d4d0c8',
  textMid:      '#8a8680',
  textSoft:     '#6b6860',
  textFaint:    '#3a3835',
  // Status (RESERVED)
  statusOk:           '#4a7c5f',
  statusWarn:         '#f5a623',
  statusAlarm:        '#e84040',
  statusFire:         '#ff2020',
  statusLoto:         '#7a6aaa',
  statusMaintenance:  '#7a6aaa', // legacy alias — prefer statusLoto
  statusOffline:      '#3a3835',
  statusSim:          '#4a7aaa',
  // Domain
  colorBess:      '#4a7c5f',
  colorCompute:   '#4a7aaa',
  colorThermal:   '#4a9a9a',
  colorGrid:      '#7a9e87',
  colorPv:        '#d4a849',
  colorRevenue:   '#b89a5e',
  // Chart
  chartGrid:      'rgba(255,255,255,0.06)',
  // Type
  fontHeading:    '"Bebas Neue", sans-serif',
  fontLabel:      '"DM Mono", ui-monospace, monospace',
  fontBody:       '"DM Mono", ui-monospace, monospace',
  // Status-bar / device chrome
  deviceFrame:    '#000',
  statusBarFg:    '#d4d0c8',
};

const SOLARPUNK = {
  name: 'solarpunk',
  bg:           '#f5f0e8',
  surface:      '#ede7d9',
  panel:        '#e8e2d4',
  border:       '#d0c8b8',
  borderSoft:   '#e0d8c8',
  accent:       '#1e3a2f',
  accentDim:    '#2d5a44',
  accentFaint:  '#e0f0e8',
  text:         '#2a2218',
  textMid:      '#5a5248',
  textSoft:     '#8a8278',
  textFaint:    '#b0a898',
  statusOk:           '#2d5a44',
  statusWarn:         '#c8820a',
  statusAlarm:        '#cc2929',
  statusFire:         '#cc0000',
  statusLoto:         '#5a4a8a',
  statusMaintenance:  '#5a4a8a', // legacy alias — prefer statusLoto
  statusOffline:      '#b0a898',
  statusSim:          '#3a5a8a',
  colorBess:      '#2d5a44',
  colorCompute:   '#3a5a8a',
  colorThermal:   '#2d7a7a',
  colorGrid:      '#4a7c5f',
  colorPv:        '#a87818',
  colorRevenue:   '#7a5e2a',
  chartGrid:      'rgba(0,0,0,0.08)',
  fontHeading:    '"Cormorant Garamond", serif',
  fontLabel:      '"Space Mono", ui-monospace, monospace',
  fontBody:       '"Plus Jakarta Sans", system-ui, sans-serif',
  deviceFrame:    '#3a3835',
  statusBarFg:    '#2a2218',
};

// Spacing scale, base 4
const SPACE = { 1: 4, 2: 8, 3: 12, 4: 16, 5: 24, 6: 32, 8: 48 };

// Radius
const RADIUS = { 1: 2, 2: 4, 3: 6, 4: 8, full: 9999 };

window.SOVEREIGN = SOVEREIGN;
window.SOLARPUNK = SOLARPUNK;
window.SPACE = SPACE;
window.RADIUS = RADIUS;
