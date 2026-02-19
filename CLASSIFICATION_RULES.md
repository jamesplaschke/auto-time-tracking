# Time Tracking Classification Rules

This file documents how calendar events get classified into Rocketlane projects.
**Add new rules here and update `src/time_tracking/config.py` to match.**

---

## How Classification Works

Events are matched in this order (first match wins):

1. **Skip** — event is ignored entirely (see [Skip Rules](#skip-rules))
2. **Enterprise Pod** — title matches pod pattern → Enterprise Methodology Pod (billable, investment)
3. **Client by domain** — attendee email domain matches a known client
4. **Client by title** — title matches a client keyword (for solo/internal events with no client attendees)
5. **Support ticket** — title matches a support ticket pattern
6. **Value Engineering** — title contains "value engineering" → Overhead > Enabling Work
7. **Overhead** — all-Ketryx internal meetings → Overhead project, phase matched by title
8. **Unknown** — needs manual review

---

## Client Projects

| Client | Rocketlane Project ID | Domains | Title Keywords | Default Phase |
|--------|-----------------------|---------|----------------|---------------|
| Philips - HPM (PICiX) | 994649 | philips.com | `philips`, `product trio` | Configuration |
| Vista Robotics | 1000461 | vistarobotics.com | `vista` | Implementation |
| Roche nCH | 1000449 | roche.com, gene.com | — | — |
| Roche nDP | 1001080 | roche.com, gene.com | title contains `nDP` | — |
| Dexcom Stelo | 1000398 | dexcom.com | — | — |
| Dexcom Strategic | 1018219 | dexcom.com | title contains `strategic` | — |
| J&J Q1 2026 | 1018147 | its.jnj.com, jnj.com | — | — |
| Meta RL | 1000414 | meta.com, fb.com, facebook.com | — | — |
| Inogen Post-Implementation | 1014475 | inogen.com | — | — |

### Adding a new client
1. Add a `ClientProject` entry to `CLIENT_PROJECTS` in `config.py`
2. Add a row to the table above
3. Note: `domains` catches meetings where the client has attendees; `title_patterns` catches solo/internal events where you're working for the client without them on the call

---

## Enterprise Methodology Pod

**Project ID:** 1000405 | **Billable type:** investment

Matched by title — any of:

| Pattern | Example |
|---------|---------|
| `enterprise methodology` / `enterprise pod` | "Enterprise Methodology Pod Sync" |
| `hockey stick` | "Hockey Stick Planning" |
| `pod 1` / `pod one` | "POD 1 Weekly" |
| `commercial pod` | "Commercial Pod 1 Update" |
| `compod` | "ComPOD 1 🏒: J&J Work" |

### Adding a new pod alias
Add to `ENTERPRISE_POD_PATTERN` in `config.py`.

---

## Overhead Phases

All internal (Ketryx-only) meetings go to the **Overhead** project (ID: 1000862).
Phase is matched by title:

| Phase | Title keywords |
|-------|---------------|
| QM Work | `QM`, `quality management`, `CAPA` |
| Non-Project Meetings | `all-hands`, `BoW`, `EoW`, `1:1`, `one-on-one`, `team sync`, `sprint review/retro/planning` |
| Enabling Work | `enabling work`, `training`, `onboarding`, `webinar` |
| Other Overhead | _(catch-all for anything else)_ |

### Adding a new overhead keyword
Add a `re.compile(...)` to the relevant `OverheadPhase.title_patterns` list in `config.py`.

---

## Investment vs. Reportable

Client events are **reportable** (billable) by default.
Certain title keywords mark an event as **investment** instead:

| Keyword |
|---------|
| `internal` |
| `prep` |
| `planning` |
| `strategy` |
| `review` |
| `product trio` |

### Adding a new investment keyword
Add a `re.compile(...)` to `INVESTMENT_TITLE_PATTERNS` in `config.py`.

---

## Skip Rules

These events are **never tracked** (skipped entirely):

| Reason | Pattern / Rule |
|--------|---------------|
| Meta | `time tracking` |
| Travel | `flight` |
| Meals | `lunch`, `dinner`, `happy hour` |
| Social | `social` |
| OOO / PTO | `OOO`, `out of office`, `PTO` |
| Calendar noise | `working location`, `focus time`, `blocked time` |
| Calendar blockers | `Hold:` prefix |
| Personal | `water polo` |
| Internal session | `wiring to win` |
| All-day events | any all-day event |

### Adding a new skip rule
Add a `re.compile(...)` to `SKIP_TITLE_PATTERNS` in `config.py` with a comment explaining why.

---

## Minimum Duration

Events shorter than **30 minutes** are skipped. Durations are rounded to the nearest **30 minutes**.

---

## Contributing

1. Found an event that classified wrong? Check which rule it hit in the output JSON (`category` field).
2. Add or update the relevant section above.
3. Update `config.py` to match — the table and the code should always stay in sync.
4. Test with `uv run pull-my-time-for <date>` and verify the output.
