// Relay — control plane for Slack → OpenRouter → Jira
// Single hi-fi dashboard. Linear-leaning minimal aesthetic.

const { useState, useEffect, useMemo } = React;

// ─── Sample data ──────────────────────────────────────────────────────────
const NAV = [
  { id: "overview",     label: "Overview",       icon: "i-overview", kbd: "G O", active: true },
  { id: "integrations", label: "Integrations",   icon: "i-link",     kbd: "G I" },
  { id: "analytics",    label: "Analytics",      icon: "i-chart",    kbd: "G A" },
  { id: "rules",        label: "Rules & prompts",icon: "i-rules",    kbd: "G R" },
  { id: "logs",         label: "Activity log",   icon: "i-log",      dot: true },
];
const NAV_2 = [
  { id: "team",     label: "Team",     icon: "i-team" },
  { id: "keys",     label: "API keys", icon: "i-key" },
  { id: "settings", label: "Settings", icon: "i-gear" },
];

// 28 days of usage, grouped by source channel
const USAGE = Array.from({ length: 28 }, (_, i) => {
  const seed = (n) => Math.sin((i + n) * 1.7) * 0.5 + 0.5;
  const a = Math.round(40 + seed(1) * 90);
  const b = Math.round(20 + seed(3) * 60);
  const c = Math.round(8  + seed(5) * 30);
  return { d: i, a, b, c, total: a + b + c };
});
const USAGE_MAX = Math.max(...USAGE.map(u => u.total));

const MODELS = [
  { name: "claude-sonnet-4.5",  vendor: "Anthropic", pct: 52, calls: "8,142", cost: "$184.20" },
  { name: "gpt-5-mini",         vendor: "OpenAI",    pct: 24, calls: "3,757", cost: "$42.10"  },
  { name: "llama-3.3-70b",      vendor: "Meta",      pct: 14, calls: "2,191", cost: "$11.84"  },
  { name: "gemini-2.5-flash",   vendor: "Google",    pct:  7, calls: "1,096", cost: "$6.42"   },
  { name: "deepseek-v3",        vendor: "DeepSeek",  pct:  3, calls: "470",   cost: "$0.94"   },
];

const COMMANDS = [
  { cmd: 'create issue "fix login redirect on safari"',         from: "#eng-bugs",     count: 42, ms: 1240, ok: 100 },
  { cmd: "list my open tickets due this week",                  from: "@aria",         count: 38, ms: 640,  ok: 100 },
  { cmd: "move PROJ-1284 to in-progress and assign to dani",    from: "#sprint-23",    count: 31, ms: 980,  ok: 96  },
  { cmd: "summarize all P0 incidents from last 7 days",         from: "#oncall",       count: 24, ms: 2210, ok: 100 },
  { cmd: "close stale tickets in BACKEND, untouched 60d+",      from: "@marcus",       count: 18, ms: 3140, ok: 88  },
  { cmd: "add comment + attach figma to DESIGN-441",            from: "#design",       count: 14, ms: 760,  ok: 100 },
];

// ─── Tiny components ──────────────────────────────────────────────────────
const Icon = ({ id, className = "ico", style }) => (
  <svg className={className} width="14" height="14" style={style} aria-hidden="true">
    <use href={`#${id}`} />
  </svg>
);

const NavItem = ({ item }) => (
  <div className={`nav-item${item.active ? " active" : ""}`}>
    <Icon id={item.icon} />
    <span>{item.label}</span>
    {item.dot ? <span className="dot" /> : item.kbd ? <span className="kbd">{item.kbd}</span> : null}
  </div>
);

const Sidebar = () => (
  <aside className="side">
    <div className="brand">
      <div className="brand-mark" aria-hidden="true" />
      <div className="brand-name">Relay</div>
      <div className="brand-tag mono">v0.4</div>
    </div>

    <div className="nav-group">
      {NAV.map(n => <NavItem key={n.id} item={n} />)}
    </div>

    <div className="nav-group">
      <div className="nav-h">Workspace</div>
      {NAV_2.map(n => <NavItem key={n.id} item={n} />)}
    </div>

    <div className="side-foot">
      <div className="who">
        <div className="ava">A</div>
        <div style={{ minWidth: 0, flex: 1 }}>
          <div className="who-name">Aria Chen</div>
          <div className="who-org">Northwind · Admin</div>
        </div>
        <Icon id="i-gear" style={{ color: "var(--ink-3)" }} />
      </div>
    </div>
  </aside>
);

const Topbar = () => (
  <div className="topbar">
    <div className="crumbs">
      <span>Northwind</span>
      <span className="crumb-sep">/</span>
      <b>Overview</b>
    </div>
    <div className="topbar-spacer" />
    <div className="search">
      <Icon id="i-search" />
      <span>Search commands, models, rules…</span>
      <span className="kbd">⌘K</span>
    </div>
    <button className="icon-btn" title="Notifications"><Icon id="i-bell" /></button>
    <button className="icon-btn" title="Help"><Icon id="i-help" /></button>
  </div>
);

const PipelineNode = ({ lm, name, meta, align = "left" }) => (
  <div className={`pipe-node ${align}`}>
    <div className={`lm ${lm.cls}`}>{lm.label}</div>
    <div>
      <div className="pn-name">{name}</div>
      <div className="pn-meta"><span className="ok">{meta}</span></div>
    </div>
  </div>
);

const PipelineStrip = () => (
  <div className="card pipeline">
    <PipelineNode
      lm={{ cls: "lm-slack", label: "S" }}
      name="Slack workspace"
      meta="Listening · 14 channels"
      align="left"
    />
    <div className="pipe-arrow"><span className="pkt" /><span className="pkt b" /></div>
    <PipelineNode
      lm={{ cls: "lm-or", label: "OR" }}
      name="OpenRouter"
      meta="Routing · 5 models active"
      align="center"
    />
    <div className="pipe-arrow"><span className="pkt" /><span className="pkt b" /></div>
    <PipelineNode
      lm={{ cls: "lm-jira", label: "J" }}
      name="Jira Cloud"
      meta="Connected · 6 projects"
      align="right"
    />
  </div>
);

// ─── Integration cards ────────────────────────────────────────────────────
const IntegrationCard = ({ lm, title, sub, status, rows, primary, secondary }) => (
  <div className="card ig">
    <div className="ig-h">
      <div className={`lm ${lm.cls}`}>{lm.label}</div>
      <div style={{ minWidth: 0 }}>
        <div className="ttl">{title}</div>
        <div className="sub">{sub}</div>
      </div>
      <div className={`ig-status${status.warn ? " warn" : ""}`}>
        <span className="d" />{status.label}
      </div>
    </div>
    <dl className="ig-rows">
      {rows.map((r, i) => (
        <div key={i} className="ig-r">
          <dt>{r.k}</dt>
          <dd>{r.v}</dd>
        </div>
      ))}
    </dl>
    <div className="ig-foot">
      {primary && <button className="btn">{primary}</button>}
      {secondary && (
        <button className="btn ghost">
          {secondary} <Icon id="i-ext" style={{ width: 12, height: 12 }} />
        </button>
      )}
    </div>
  </div>
);

const Integrations = () => (
  <div className="grid-3">
    <IntegrationCard
      lm={{ cls: "lm-slack", label: "S" }}
      title="Slack"
      sub="Source — listens for /relay commands"
      status={{ label: "Connected" }}
      rows={[
        { k: "Workspace", v: <span className="mono">northwind.slack.com</span> },
        { k: "Channels",  v: "14 listening · 3 muted" },
        { k: "Trigger",   v: <span className="mono">/relay</span> },
        { k: "Last event",v: "12 seconds ago" },
      ]}
      primary="Manage channels"
      secondary="Open in Slack"
    />
    <IntegrationCard
      lm={{ cls: "lm-or", label: "OR" }}
      title="OpenRouter"
      sub="Routing — selects best model per task"
      status={{ label: "5 models" }}
      rows={[
        { k: "API key",   v: <span className="mono">sk-or-v1·••••a92f</span> },
        { k: "Default",   v: <span className="mono">claude-sonnet-4.5</span> },
        { k: "Fallback",  v: <span className="mono">gpt-5-mini → llama-3.3</span> },
        { k: "Spend cap", v: "$500 / month · 49% used" },
      ]}
      primary="Edit routing"
      secondary="OpenRouter dashboard"
    />
    <IntegrationCard
      lm={{ cls: "lm-jira", label: "J" }}
      title="Jira Cloud"
      sub="Target — executes the resolved action"
      status={{ label: "Connected" }}
      rows={[
        { k: "Site",      v: <span className="mono">northwind.atlassian.net</span> },
        { k: "Projects",  v: "6 enabled · ENG, DESIGN, OPS, +3" },
        { k: "Auth",      v: "OAuth 2.0 · scoped to issue:write" },
        { k: "Webhook",   v: <span style={{ color: "var(--ok)" }}>Active</span> },
      ]}
      primary="Manage projects"
      secondary="Open Jira"
    />
  </div>
);

// ─── KPI cards ────────────────────────────────────────────────────────────
const KPI = ({ label, value, unit, delta, deltaDir = "up", lblSuffix = "vs last 7d", spark }) => (
  <div className="card kpi">
    <div className="kpi-h"><span>{label}</span></div>
    <div className="kpi-v">
      <span className="num">{value}</span>
      {unit && <span className="u">{unit}</span>}
    </div>
    <div className="kpi-d">
      <span className={`delta ${deltaDir}`}>{delta}</span>
      <span className="lbl">{lblSuffix}</span>
    </div>
    <div className="spark" aria-hidden="true">
      {spark.map((h, i) => (
        <span key={i} className={i === spark.length - 1 ? "hi" : ""} style={{ height: `${h}%` }} />
      ))}
    </div>
  </div>
);

const sparkA = [22, 30, 26, 38, 34, 44, 52, 48, 56, 62, 58, 70];
const sparkB = [60, 52, 58, 50, 44, 48, 40, 38, 42, 36, 30, 28];
const sparkC = [42, 38, 44, 40, 48, 46, 50, 52, 48, 54, 56, 58];
const sparkD = [62, 70, 66, 72, 68, 74, 78, 72, 80, 76, 82, 84];

const KPIs = () => (
  <div className="grid-4">
    <KPI label="Commands routed"   value="15,656" delta="+18.4%" deltaDir="up"   spark={sparkA} />
    <KPI label="Avg. latency"      value="1,184" unit="ms" delta="-7.1%"  deltaDir="up"   spark={sparkB} lblSuffix="faster than last week" />
    <KPI label="Spend (this mo.)"  value="$245.50" delta="+12%"   deltaDir="flat" spark={sparkC} />
    <KPI label="Success rate"      value="98.6" unit="%" delta="+0.4pp" deltaDir="up"   spark={sparkD} />
  </div>
);

// ─── Usage chart ──────────────────────────────────────────────────────────
const UsageChart = () => (
  <div className="card usage">
    <div className="usage-h">
      <div>
        <div className="t">Commands by source · 28 days</div>
        <div className="s">Hourly aggregates · UTC</div>
      </div>
      <div style={{ textAlign: "right" }}>
        <div className="n num">15,656</div>
        <div className="legend">
          <span><i style={{ background: "var(--accent)" }} />DM</span>
          <span><i style={{ background: "color-mix(in oklab, var(--accent) 55%, var(--bg-elev))" }} />Channel</span>
          <span><i style={{ background: "color-mix(in oklab, var(--accent) 25%, var(--bg-elev))" }} />Mention</span>
        </div>
      </div>
    </div>
    <div className="chart">
      {USAGE.map(u => {
        const total = u.total / USAGE_MAX * 100;
        const a = (u.a / u.total) * total;
        const b = (u.b / u.total) * total;
        const c = (u.c / u.total) * total;
        return (
          <div key={u.d} className="bar">
            <i className="s1" style={{ height: `${a}%` }} />
            <i className="s2" style={{ height: `${b}%` }} />
            <i className="s3" style={{ height: `${c}%` }} />
          </div>
        );
      })}
    </div>
    <div className="x-ax">
      <span>Apr 11</span><span>Apr 15</span><span>Apr 19</span><span>Apr 23</span>
      <span>Apr 27</span><span>May 1</span><span>May 8</span>
    </div>
  </div>
);

// ─── Model breakdown ──────────────────────────────────────────────────────
const ModelBreakdown = () => (
  <div className="card mb">
    <h3>Model routing · last 30 days</h3>
    {MODELS.map(m => (
      <div key={m.name} className="mb-row">
        <div className={`lm sm ${m.vendor === "Anthropic" ? "lm-slack" : m.vendor === "OpenAI" ? "lm-jira" : "lm-or"}`}>
          {m.vendor[0]}
        </div>
        <div>
          <div className="nm mono">{m.name}</div>
          <div className="pv">{m.vendor}</div>
        </div>
        <div className="mb-bar"><i style={{ width: `${m.pct}%` }} /></div>
        <div className="ct mono">{m.calls}</div>
        <div className="pp">{m.cost}</div>
      </div>
    ))}
  </div>
);

// ─── Top commands table ───────────────────────────────────────────────────
const TopCommands = () => (
  <div className="card">
    <div className="tbl-h">
      <span>Command pattern</span>
      <span>Calls / 7d</span>
      <span>Avg ms</span>
      <span>Success</span>
    </div>
    <div className="tbl-wrap">
      {COMMANDS.map((c, i) => (
        <div key={i} className="tbl-r">
          <div style={{ minWidth: 0 }}>
            <div className="cmd">{c.cmd}</div>
            <div className="from">from {c.from}</div>
          </div>
          <span className="ct num">{c.count}</span>
          <span className="ms num">{c.ms.toLocaleString()}</span>
          <span className={c.ok < 95 ? "meh-pct" : "ok-pct"}>{c.ok}%</span>
        </div>
      ))}
    </div>
  </div>
);

// ─── Page header ──────────────────────────────────────────────────────────
const PageHeader = () => {
  const [range, setRange] = useState("7d");
  return (
    <div className="page-h">
      <div>
        <h1 className="page-title">Overview</h1>
        <p className="page-sub">Live status of the Slack → OpenRouter → Jira pipeline, and how it's been used.</p>
      </div>
      <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
        <div className="seg" role="tablist">
          {["24h", "7d", "30d", "90d"].map(r => (
            <button key={r} className={range === r ? "on" : ""} onClick={() => setRange(r)}>{r}</button>
          ))}
        </div>
        <button className="btn"><Icon id="i-refresh" style={{ width: 12, height: 12 }} /> Refresh</button>
        <button className="btn primary"><Icon id="i-plus" style={{ width: 12, height: 12 }} /> New rule</button>
      </div>
    </div>
  );
};

// ─── App ──────────────────────────────────────────────────────────────────
function App() {
  const [t, setTweak] = useTweaks(window.TWEAK_DEFAULTS);

  // Apply tweaks at the html level (so CSS vars cascade everywhere)
  useEffect(() => {
    const html = document.documentElement;
    html.dataset.theme   = t.theme;
    html.dataset.density = t.density;
    html.dataset.sidebar = t.showSidebar ? "on" : "off";
    html.style.setProperty("--accent", t.accent);
  }, [t.theme, t.density, t.showSidebar, t.accent]);

  return (
    <>
      <div className="app">
        {t.showSidebar && <Sidebar />}
        <main className="main">
          <Topbar />
          <div className="page">
            <PageHeader />

            <section className="section">
              <div className="section-h">
                <h2>Pipeline</h2>
                <span className="meta mono">last event · 12s ago</span>
              </div>
              <PipelineStrip />
            </section>

            <section className="section">
              <div className="section-h">
                <h2>Connected services</h2>
                <a href="#" className="doc-link">Read the integration guide ↗</a>
              </div>
              <Integrations />
            </section>

            <section className="section">
              <div className="section-h">
                <h2>Analytics · last 7 days</h2>
              </div>
              <KPIs />
            </section>

            <section className="section">
              <div className="grid-2">
                <UsageChart />
                <ModelBreakdown />
              </div>
            </section>

            <section className="section">
              <div className="section-h">
                <h2>Top commands</h2>
                <span className="meta">Showing 6 of 134 distinct patterns</span>
              </div>
              <TopCommands />
            </section>
          </div>
        </main>
      </div>

      <TweaksPanel>
        <TweakSection label="Appearance" />
        <TweakRadio
          label="Theme"
          value={t.theme}
          options={["light", "dark"]}
          onChange={v => setTweak("theme", v)}
        />
        <TweakColor
          label="Accent"
          value={t.accent}
          options={["#C26E4F", "#5B6BD9", "#3F8F6E", "#A95FB6"]}
          onChange={v => setTweak("accent", v)}
        />
        <TweakRadio
          label="Density"
          value={t.density}
          options={["compact", "regular", "comfy"]}
          onChange={v => setTweak("density", v)}
        />
        <TweakSection label="Layout" />
        <TweakToggle
          label="Show sidebar"
          value={t.showSidebar}
          onChange={v => setTweak("showSidebar", v)}
        />
      </TweaksPanel>
    </>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
