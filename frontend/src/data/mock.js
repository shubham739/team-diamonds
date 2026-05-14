// Dummy data mirroring exact API response shapes from the Jira service.
//
// Issue shape (from _issue_to_dict in jira_service/main.py):
//   { id, title, desc, status, members, due_date }
//   status: "todo" | "in_progress" | "complete" | "cancelled"
//   members: string[]  (email addresses)
//   due_date: "YYYY-MM-DD" | null
//
// Chat shape (from POST /chat):
//   { reply: string, actions: Array<{ tool, args, result }> }
//   tool: "list_issues" | "get_issue" | "create_issue" | "update_issue" | "delete_issue"

// ─── Auth / session ────────────────────────────────────────────────────────

export const SESSION = {
  status: "authenticated",
  user_id: "5dd9c3b4a6c4e50e3da8c8a1",
  email: "aria.chen@northwind.io",
  name: "Aria Chen",
  access_token: "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
};

export const JIRA_CONNECTION = {
  connected: true,
  site: "northwind.atlassian.net",
  projects: ["ENG", "DESIGN", "OPS", "QA", "BACKEND"],
  scope: "read:jira-work write:jira-work",
  last_event: "8s ago",
};

// ─── Issues (matches GET /issues → { issues: [...], count: N }) ────────────

export const ISSUES = [
  {
    id: "ENG-2284",
    title: "Fix login redirect loop on Safari 17",
    desc: "Users on Safari 17 get stuck in a redirect loop after successful OAuth. The `location.replace` call fires before the session cookie is written. Reproducible 100% of the time on macOS 14.4.",
    status: "in_progress",
    members: ["aria.chen@northwind.io", "dani.okafor@northwind.io"],
    due_date: "2026-05-14",
  },
  {
    id: "ENG-2283",
    title: "Add rate-limit headers to all API responses",
    desc: "Expose X-RateLimit-Limit, X-RateLimit-Remaining, and X-RateLimit-Reset on every response so clients can back off gracefully. FastAPI middleware is the right place.",
    status: "todo",
    members: ["priya.shah@northwind.io"],
    due_date: "2026-05-20",
  },
  {
    id: "ENG-2281",
    title: "Migrate auth tokens from localStorage to httpOnly cookies",
    desc: "Current localStorage approach is XSS-vulnerable. Switch to httpOnly SameSite=Strict cookies and update the refresh flow accordingly.",
    status: "in_progress",
    members: ["aria.chen@northwind.io"],
    due_date: "2026-05-12",
  },
  {
    id: "ENG-2278",
    title: "Implement retry with exponential backoff for Jira API calls",
    desc: "Jira Cloud throttles at 300 req/min. Add a tenacity-based retry decorator to `_get` and `_post` in JiraClient. Max 3 retries, 1s base, factor 2.",
    status: "todo",
    members: ["marcus.liu@northwind.io"],
    due_date: "2026-05-28",
  },
  {
    id: "ENG-2274",
    title: "Fix JQL injection in get_issues() when filtering by title",
    desc: "The title filter is not passed through sanitize_input(). An attacker can break out of the JQL string with a double quote. Fix: wrap in sanitize_input() before interpolation.",
    status: "complete",
    members: ["aria.chen@northwind.io"],
    due_date: "2026-05-08",
  },
  {
    id: "ENG-2270",
    title: "Add pagination support to GET /issues",
    desc: "Current endpoint fetches all issues in one shot. Add startAt and maxResults query params. Return total in response envelope.",
    status: "todo",
    members: ["sam.patel@northwind.io", "lena.park@northwind.io"],
    due_date: "2026-06-02",
  },
  {
    id: "ENG-2265",
    title: "Replace in-memory user_sessions with Redis",
    desc: "Sessions are lost on server restart. Use redis-py with TTL equal to token expiry. Keep the same dict-like interface so callers don't change.",
    status: "todo",
    members: ["marcus.liu@northwind.io"],
    due_date: "2026-06-10",
  },
  {
    id: "ENG-2240",
    title: "Epic: Q3 mobile rewrite",
    desc: "Full rewrite of the iOS and Android apps using React Native. All existing REST endpoints must remain stable. Coordinate with DESIGN team for new component library.",
    status: "in_progress",
    members: ["dani.okafor@northwind.io", "theo.vasquez@northwind.io", "lena.park@northwind.io"],
    due_date: "2026-09-30",
  },
  {
    id: "DESIGN-441",
    title: "Create component library for Q3 mobile rewrite",
    desc: "Design tokens, button variants, form controls, and navigation patterns. Export to Figma and Storybook. Hand off to ENG by end of sprint.",
    status: "in_progress",
    members: ["theo.vasquez@northwind.io"],
    due_date: "2026-05-22",
  },
  {
    id: "DESIGN-438",
    title: "Redesign onboarding flow — reduce drop-off at step 3",
    desc: "Analytics show 42% drop-off at the Jira connection step. Simplify to a single OAuth button. Add progress indicator. A/B test against current flow.",
    status: "todo",
    members: ["theo.vasquez@northwind.io", "lena.park@northwind.io"],
    due_date: "2026-05-30",
  },
  {
    id: "OPS-198",
    title: "Set up CircleCI integration test context for staging",
    desc: "The jira-client context only works in production. Create a jira-client-staging context with staging credentials and wire up the integration_test job.",
    status: "complete",
    members: ["marcus.liu@northwind.io"],
    due_date: "2026-05-05",
  },
  {
    id: "OPS-195",
    title: "Configure Render autoscaling — min 1 / max 3 instances",
    desc: "Current single-instance setup can't handle traffic spikes. Set minInstances=1, maxInstances=3. Test failover with load generator before enabling.",
    status: "complete",
    members: ["marcus.liu@northwind.io", "aria.chen@northwind.io"],
    due_date: "2026-05-01",
  },
  {
    id: "QA-112",
    title: "Write e2e tests for /chat endpoint tool-call loop",
    desc: "Cover: single tool call, chained tool calls (create → update), tool error propagation, max-step guard (3 iterations). Use pytest-httpx to mock OpenRouter.",
    status: "in_progress",
    members: ["sam.patel@northwind.io"],
    due_date: "2026-05-18",
  },
  {
    id: "QA-109",
    title: "Regression suite for OAuth2 callback edge cases",
    desc: "Test: expired code, wrong state, missing scopes, Atlassian 503, duplicate callback. Ensure all return 400 with a clear detail message.",
    status: "todo",
    members: ["sam.patel@northwind.io"],
    due_date: "2026-05-25",
  },
  {
    id: "BACKEND-87",
    title: "Close stale issues untouched for 60+ days",
    desc: "Run JQL query: project in (BACKEND) AND updated <= -60d AND status != Done. Transition to Cancelled. Requires issue:write scope — confirm with team lead before running.",
    status: "cancelled",
    members: ["marcus.liu@northwind.io"],
    due_date: null,
  },
];

// ─── Chat command history (matches POST /chat responses) ───────────────────

export const CHAT_HISTORY = [
  {
    id: "cmd-001",
    ts: "just now",
    message: 'create issue "fix login redirect loop on safari" in ENG',
    status: "running",
    model: "anthropic/claude-sonnet-4-6",
    latency_ms: null,
    reply: null,
    actions: [],
  },
  {
    id: "cmd-002",
    ts: "38s ago",
    message: "move ENG-2283 to in-progress and assign to dani.okafor@northwind.io",
    status: "ok",
    model: "anthropic/claude-sonnet-4-6",
    latency_ms: 1240,
    reply: "Done — ENG-2283 is now In Progress and assigned to Dani Okafor.",
    actions: [
      {
        tool: "get_issue",
        args: { issue_id: "ENG-2283" },
        result: { id: "ENG-2283", title: "Add rate-limit headers to all API responses", desc: "...", status: "todo", members: ["priya.shah@northwind.io"], due_date: "2026-05-20" },
      },
      {
        tool: "update_issue",
        args: { issue_id: "ENG-2283", status: "in_progress", members: ["priya.shah@northwind.io", "dani.okafor@northwind.io"] },
        result: { id: "ENG-2283", title: "Add rate-limit headers to all API responses", desc: "...", status: "in_progress", members: ["priya.shah@northwind.io", "dani.okafor@northwind.io"], due_date: "2026-05-20" },
      },
    ],
  },
  {
    id: "cmd-003",
    ts: "2m ago",
    message: "list my open tickets due this week",
    status: "ok",
    model: "anthropic/claude-haiku-4-5",
    latency_ms: 640,
    reply: "You have 4 open issues due this week: ENG-2281 (due May 12), ENG-2284 (due May 14), DESIGN-441 (due May 22), QA-112 (due May 18).",
    actions: [
      {
        tool: "list_issues",
        args: { members: ["aria.chen@northwind.io"], status: "in_progress", max_results: 20 },
        result: [
          { id: "ENG-2281", title: "Migrate auth tokens from localStorage to httpOnly cookies", status: "in_progress", members: ["aria.chen@northwind.io"], due_date: "2026-05-12" },
          { id: "ENG-2284", title: "Fix login redirect loop on Safari 17", status: "in_progress", members: ["aria.chen@northwind.io", "dani.okafor@northwind.io"], due_date: "2026-05-14" },
        ],
      },
    ],
  },
  {
    id: "cmd-004",
    ts: "5m ago",
    message: "summarize all P0 issues from the last 7 days",
    status: "ok",
    model: "anthropic/claude-sonnet-4-6",
    latency_ms: 2210,
    reply: "Found 3 high-priority issues in the last 7 days: (1) ENG-2274 — JQL injection fix, now Complete. (2) ENG-2281 — auth token migration, In Progress. (3) OPS-195 — Render autoscaling, Complete.",
    actions: [
      {
        tool: "list_issues",
        args: { title: "P0", max_results: 10 },
        result: [],
      },
      {
        tool: "list_issues",
        args: { status: "in_progress", max_results: 20 },
        result: [
          { id: "ENG-2281", title: "Migrate auth tokens from localStorage to httpOnly cookies", status: "in_progress", members: ["aria.chen@northwind.io"], due_date: "2026-05-12" },
          { id: "ENG-2284", title: "Fix login redirect loop on Safari 17", status: "in_progress", members: ["aria.chen@northwind.io", "dani.okafor@northwind.io"], due_date: "2026-05-14" },
        ],
      },
    ],
  },
  {
    id: "cmd-005",
    ts: "11m ago",
    message: "close all stale tickets in BACKEND untouched for 60+ days",
    status: "fail",
    model: "anthropic/claude-sonnet-4-6",
    latency_ms: 3140,
    reply: "I wasn't able to bulk-close those tickets — the operation was denied. Your OAuth scope (issue:write) allows individual updates but bulk transitions require admin permissions. Ask your Jira admin to run this.",
    actions: [
      {
        tool: "list_issues",
        args: { status: "todo", max_results: 50 },
        result: [{ id: "BACKEND-87", title: "Close stale issues untouched for 60+ days", status: "todo", members: ["marcus.liu@northwind.io"], due_date: null }],
      },
      {
        tool: "update_issue",
        args: { issue_id: "BACKEND-87", status: "cancelled" },
        result: { error: "403 Forbidden: insufficient permissions to transition this issue" },
      },
    ],
  },
  {
    id: "cmd-006",
    ts: "14m ago",
    message: "reassign ENG-2274 to priya.shah@northwind.io and set priority to high",
    status: "ok",
    model: "anthropic/claude-sonnet-4-6",
    latency_ms: 980,
    reply: "ENG-2274 has been reassigned to Priya Shah. Note: priority is not a supported field in the current API — only title, desc, status, members, and due_date can be updated.",
    actions: [
      {
        tool: "update_issue",
        args: { issue_id: "ENG-2274", members: ["priya.shah@northwind.io"] },
        result: { id: "ENG-2274", title: "Fix JQL injection in get_issues() when filtering by title", status: "complete", members: ["priya.shah@northwind.io"], due_date: "2026-05-08" },
      },
    ],
  },
  {
    id: "cmd-007",
    ts: "21m ago",
    message: "create epic Q3 mobile rewrite in ENG and assign to dani and theo",
    status: "ok",
    model: "anthropic/claude-sonnet-4-6",
    latency_ms: 1560,
    reply: "Created ENG-2240 'Epic: Q3 mobile rewrite' and assigned to Dani Okafor and Theo Vasquez.",
    actions: [
      {
        tool: "create_issue",
        args: { title: "Epic: Q3 mobile rewrite", desc: "Full rewrite of the iOS and Android apps using React Native.", status: "in_progress", members: ["dani.okafor@northwind.io", "theo.vasquez@northwind.io"] },
        result: { id: "ENG-2240", title: "Epic: Q3 mobile rewrite", status: "in_progress", members: ["dani.okafor@northwind.io", "theo.vasquez@northwind.io"], due_date: null },
      },
    ],
  },
  {
    id: "cmd-008",
    ts: "33m ago",
    message: "what is the status of ENG-2281?",
    status: "ok",
    model: "anthropic/claude-haiku-4-5",
    latency_ms: 480,
    reply: "ENG-2281 ('Migrate auth tokens from localStorage to httpOnly cookies') is currently In Progress, assigned to aria.chen@northwind.io, due 2026-05-12.",
    actions: [
      {
        tool: "get_issue",
        args: { issue_id: "ENG-2281" },
        result: { id: "ENG-2281", title: "Migrate auth tokens from localStorage to httpOnly cookies", desc: "...", status: "in_progress", members: ["aria.chen@northwind.io"], due_date: "2026-05-12" },
      },
    ],
  },
  {
    id: "cmd-009",
    ts: "47m ago",
    message: "add description to DESIGN-441 about the Figma handoff deadline",
    status: "ok",
    model: "anthropic/claude-sonnet-4-6",
    latency_ms: 870,
    reply: "Updated DESIGN-441 with the Figma handoff deadline information in the description.",
    actions: [
      {
        tool: "update_issue",
        args: { issue_id: "DESIGN-441", desc: "Design tokens, button variants, form controls, and navigation patterns. Export to Figma and Storybook. Hand off to ENG by end of sprint. Figma link due May 15." },
        result: { id: "DESIGN-441", title: "Create component library for Q3 mobile rewrite", status: "in_progress", members: ["theo.vasquez@northwind.io"], due_date: "2026-05-22" },
      },
    ],
  },
  {
    id: "cmd-010",
    ts: "1h ago",
    message: "delete QA-87, it was created by mistake",
    status: "ok",
    model: "anthropic/claude-haiku-4-5",
    latency_ms: 390,
    reply: "QA-87 has been permanently deleted.",
    actions: [
      {
        tool: "delete_issue",
        args: { issue_id: "QA-87" },
        result: { status: "deleted", issue_id: "QA-87" },
      },
    ],
  },
];

// ─── KPI stats ─────────────────────────────────────────────────────────────

export const KPIS = {
  commands_processed: { value: "1,247", delta: "+18.4%", dir: "up",   suffix: "vs last 7d" },
  avg_latency_ms:     { value: "1,184", unit: "ms", delta: "-7.1%",  dir: "up",   suffix: "faster than last week" },
  issues_created:     { value: "342",   delta: "+12%",  dir: "flat", suffix: "vs last 7d" },
  success_rate:       { value: "97.8",  unit: "%", delta: "+0.3pp", dir: "up",   suffix: "vs last 7d" },
};

export const SPARK_COMMANDS  = [22, 30, 26, 38, 34, 44, 52, 48, 56, 62, 58, 70];
export const SPARK_LATENCY   = [60, 52, 58, 50, 44, 48, 40, 38, 42, 36, 30, 28];
export const SPARK_CREATED   = [42, 38, 44, 40, 48, 46, 50, 52, 48, 54, 56, 58];
export const SPARK_SUCCESS   = [62, 70, 66, 72, 68, 74, 78, 72, 80, 76, 82, 84];

// ─── Usage chart (28 days of command counts) ───────────────────────────────

export const USAGE_CHART = Array.from({ length: 28 }, (_, i) => {
  const seed = (n) => Math.sin((i + n) * 1.7) * 0.5 + 0.5;
  const created = Math.round(18 + seed(1) * 55);
  const updated = Math.round(22 + seed(3) * 70);
  const queries  = Math.round(8  + seed(5) * 30);
  return { day: i, created, updated, queries, total: created + updated + queries };
});
export const USAGE_MAX = Math.max(...USAGE_CHART.map(u => u.total));

// ─── Model breakdown ────────────────────────────────────────────────────────

export const MODEL_BREAKDOWN = [
  { name: "claude-sonnet-4-6", vendor: "Anthropic", via: "OpenRouter", pct: 62, calls: "774", cost: "$8.42" },
  { name: "claude-haiku-4-5",  vendor: "Anthropic", via: "OpenRouter", pct: 38, calls: "473", cost: "$0.94" },
];

// ─── OpenRouter billing summary ─────────────────────────────────────────────

export const OR_BILLING = {
  total_tokens: "2.4M",
  spend_mtd: "$9.36",
  cap: "$50.00",
  cap_pct: 19,
  avg_tokens_per_cmd: 1926,
};

// ─── Example prompts for Commands page ─────────────────────────────────────

export const COMMAND_EXAMPLES = [
  'create issue "fix login redirect loop on safari" in ENG',
  "list my open tickets due this week",
  "move ENG-2283 to in-progress and assign to dani.okafor@northwind.io",
  "summarize all in-progress issues in ENG",
  "close stale tickets in BACKEND untouched for 60+ days",
  'add comment "reviewed, looks good" to ENG-2274',
  "what is blocking ENG-2240?",
  "create a QA ticket for the Safari redirect bug",
];
