"""Client mappings, project IDs, regex patterns, and constants."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

KETRYX_DOMAIN = "ketryx.com"

# Domains to ignore when classifying attendees (not real people)
IGNORED_DOMAINS = {
    "resource.calendar.google.com",
    "calendar.google.com",
    "group.calendar.google.com",
}
MIN_DURATION_MINUTES = 30
ROUNDING_INCREMENT_MINUTES = 30

# ---------------------------------------------------------------------------
# Time entry category IDs (from GET /time-entries/categories)
# ---------------------------------------------------------------------------

CATEGORY_REPORTABLE = 125238        # billable reportable client work
CATEGORY_INVESTMENT = 125235        # investment / non-reportable (incl. overhead)


# ---------------------------------------------------------------------------
# Project / phase registry
# ---------------------------------------------------------------------------

@dataclass
class ClientProject:
    """A billable client project in Rocketlane."""
    name: str
    project_id: int
    domains: list[str] = field(default_factory=list)
    title_patterns: list[re.Pattern] = field(default_factory=list)
    billable_type_default: str = "reportable"  # reportable or investment
    # For clients with multiple projects, use disambiguators
    # pattern -> (project_id, project_name) override
    disambiguate: dict[str, tuple[int, str]] | None = None
    # Phase mapping: ordered list of (pattern, phase_name). First match wins.
    # Falls back to default_phase_name if no pattern matches.
    phase_patterns: list[tuple[re.Pattern, str]] = field(default_factory=list)
    default_phase_name: str | None = None


@dataclass
class OverheadPhase:
    """A phase within the Overhead project."""
    name: str
    phase_id: int
    title_patterns: list[re.Pattern] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Client projects
# ---------------------------------------------------------------------------

CLIENT_PROJECTS: list[ClientProject] = [
    ClientProject(
        name="Philips - HPM (PICiX)",
        project_id=994649,
        domains=["philips.com"],
        title_patterns=[
            re.compile(r"\bphilips\b", re.IGNORECASE),
            re.compile(r"\bproduct\s+trio\b", re.IGNORECASE),
        ],
        default_phase_name="Configuration",
        phase_patterns=[
            (re.compile(r"\b(prep|admin|onboard|kickoff|kick.off)\b", re.IGNORECASE), "Admin/Onboarding"),
            (re.compile(r"\b(baseline|release)\b", re.IGNORECASE), "Baseline Release"),
            (re.compile(r"\btemplate", re.IGNORECASE), "Templating"),
            (re.compile(r"\bpre.?kick", re.IGNORECASE), "Pre-kickoff"),
            (re.compile(r"\bpost.?impl", re.IGNORECASE), "Post-implementation"),
        ],
    ),
    ClientProject(
        name="Vista Robotics",
        project_id=1000461,
        domains=["vistarobotics.com"],
        title_patterns=[
            re.compile(r"\bvista\b", re.IGNORECASE),
        ],
        default_phase_name="Implementation",
        phase_patterns=[
            (re.compile(r"\b(plan|prep|email|schedule)\b", re.IGNORECASE), "Planning"),
            (re.compile(r"\b(support|ticket)\b", re.IGNORECASE), "Support"),
            (re.compile(r"\b(improv)", re.IGNORECASE), "Continuous Improvement"),
        ],
    ),
    ClientProject(
        name="Flo Health",
        project_id=1000411,
        domains=["flo.health"],
        title_patterns=[
            re.compile(r"\bflo\b", re.IGNORECASE),
        ],
        default_phase_name="Continuous Improvement",
    ),
    ClientProject(
        name="Roche nCH",
        project_id=1000449,
        domains=["roche.com", "gene.com"],
        title_patterns=[
            re.compile(r"\broche\b", re.IGNORECASE),
        ],
        disambiguate={
            "nDP": (1001080, "Roche nDP"),
        },
    ),
    ClientProject(
        name="Dexcom Stelo",
        project_id=1000398,
        domains=["dexcom.com"],
        disambiguate={
            "strategic": (1018219, "Dexcom Strategic"),
        },
    ),
    ClientProject(
        name="J&J Q1 2026",
        project_id=1018147,
        domains=["its.jnj.com", "jnj.com"],
    ),
    ClientProject(
        name="Meta RL: General work",
        project_id=1000414,
        domains=["meta.com", "fb.com", "facebook.com"],
    ),
    ClientProject(
        name="Inogen Post-Implementation",
        project_id=1014475,
        domains=["inogen.com"],
    ),
    ClientProject(
        name="Medtronic ACM",
        project_id=1121886,
        domains=["medtronic.com"],
        title_patterns=[
            re.compile(r"\bmedtronic\b", re.IGNORECASE),
        ],
        disambiguate={
            "stitch": (1017352, "Medtronic - Project Stitch"),
        },
    ),
]

# Support Tickets — matched by title, not domain
SUPPORT_TICKETS_PROJECT_ID = 1047192
SUPPORT_TICKETS_NAME = "Support Tickets (strategic)"

# Value Engineering — matched by title, logged to Value Engineering project
VALUE_ENGINEERING_PATTERN = re.compile(r"value\s+engineering", re.IGNORECASE)
VALUE_ENGINEERING_PROJECT_ID = 1119785
VALUE_ENGINEERING_PROJECT_NAME = "Value Engineering"
VALUE_ENGINEERING_PHASE_ID = 4529082
VALUE_ENGINEERING_PHASE_NAME = "ROI Calculator"

# Enterprise Methodology Pod — "enterprise methodology/pod" events → project 1000405
ENTERPRISE_POD_PATTERN = re.compile(
    r"enterprise\s+(methodology|pod)",
    re.IGNORECASE,
)
ENTERPRISE_POD_PROJECT_ID = 1000405
ENTERPRISE_POD_PROJECT_NAME = "Enterprise Methodology Pod"
ENTERPRISE_POD_DEFAULT_PHASE_NAME = "Enterprise Pod Work Q1 2026"

# Enterprise GTM / Account PODs — POD 1, Hockey Stick, Commercial Pod → project 1100677
ENTERPRISE_GTM_POD_PATTERN = re.compile(
    r"hockey\s*stick"
    r"|\bpod\s*1\b"
    r"|\bpod\s+one\b"
    r"|commercial\s+pod"
    r"|\bcompod\b"
    r"|los\s+chingones",
    re.IGNORECASE,
)
ENTERPRISE_GTM_POD_PROJECT_ID = 1100677
ENTERPRISE_GTM_POD_PROJECT_NAME = "Enterprise Account PODs"
ENTERPRISE_GTM_POD_DEFAULT_PHASE_NAME = "Enterprise Pod Work Q1 2026"

# Projects whose Rocketlane budget is non-billable — must be posted with billable=False
INTERNAL_TOOLING_POD_PROJECT_ID = 1116583
PRE_SALES_SUPPORT_PROJECT_ID = 1046918

NON_BILLABLE_ROCKETLANE_PROJECTS: set[int] = {
    ENTERPRISE_POD_PROJECT_ID,
    ENTERPRISE_GTM_POD_PROJECT_ID,
    INTERNAL_TOOLING_POD_PROJECT_ID,
    1121886,  # Medtronic ACM
}

# ---------------------------------------------------------------------------
# Overhead project and phases
# ---------------------------------------------------------------------------

OVERHEAD_PROJECT_ID = 1000862
OVERHEAD_PROJECT_NAME = "Overhead"

OVERHEAD_PHASES: list[OverheadPhase] = [
    OverheadPhase(
        name="QM Work",
        phase_id=0,  # Will be resolved from Rocketlane API
        title_patterns=[
            re.compile(r"QM\b", re.IGNORECASE),
            re.compile(r"quality\s+management", re.IGNORECASE),
            re.compile(r"CAPA\b", re.IGNORECASE),
        ],
    ),
    OverheadPhase(
        name="Non-Project Meetings",
        phase_id=0,  # Will be resolved from Rocketlane API
        title_patterns=[
            re.compile(r"all[\s-]?hands", re.IGNORECASE),
            re.compile(r"\bBoW\b"),
            re.compile(r"\bEoW\b"),
            re.compile(r"beginning\s+of\s+week", re.IGNORECASE),
            re.compile(r"end\s+of\s+week", re.IGNORECASE),
            re.compile(r"\b1[:\s]*1\b"),
            re.compile(r"one[\s-]?on[\s-]?one", re.IGNORECASE),
            re.compile(r"team\s+(sync|standup|meeting|call)", re.IGNORECASE),
            re.compile(r"sprint\s+(review|retro|planning)", re.IGNORECASE),
        ],
    ),
    OverheadPhase(
        name="Enabling Work",
        phase_id=0,  # Will be resolved from Rocketlane API
        title_patterns=[
            re.compile(r"enabling\s+work", re.IGNORECASE),
            re.compile(r"training", re.IGNORECASE),
            re.compile(r"onboarding", re.IGNORECASE),
            re.compile(r"\bwebinar\b", re.IGNORECASE),
        ],
    ),
    OverheadPhase(
        name="Other Overhead",
        phase_id=0,  # Will be resolved from Rocketlane API — fallback phase
        title_patterns=[],  # catch-all for internal events not matching other phases
    ),
]


# ---------------------------------------------------------------------------
# Skip patterns (events that should not be tracked)
# ---------------------------------------------------------------------------

SKIP_TITLE_PATTERNS: list[re.Pattern] = [
    re.compile(r"time\s+tracking", re.IGNORECASE),
    re.compile(r"\bflight\b", re.IGNORECASE),
    re.compile(r"\blunch\b", re.IGNORECASE),
    re.compile(r"\bdinner\b", re.IGNORECASE),
    re.compile(r"\bhappy\s+hour\b", re.IGNORECASE),
    re.compile(r"\bsocial\b", re.IGNORECASE),
    re.compile(r"\bOOO\b"),
    re.compile(r"out\s+of\s+office", re.IGNORECASE),
    re.compile(r"\bPTO\b"),
    re.compile(r"working\s+location", re.IGNORECASE),
    re.compile(r"\bfocus\s+time\b", re.IGNORECASE),
    re.compile(r"\bblock(ed)?\s+time\b", re.IGNORECASE),
    # "Hold:" prefix = calendar blocker, skip it so the real events behind it are used
    re.compile(r"^\s*hold\s*:", re.IGNORECASE),
    # Recurring internal sessions not tracked
    re.compile(r"wiring\s+to\s+win", re.IGNORECASE),
    re.compile(r"\bwater\s+polo\b", re.IGNORECASE),
]

# Events with these titles are investment (not reportable) for client projects
INVESTMENT_TITLE_PATTERNS: list[re.Pattern] = [
    re.compile(r"internal", re.IGNORECASE),
    re.compile(r"prep\b", re.IGNORECASE),
    re.compile(r"planning", re.IGNORECASE),
    re.compile(r"strategy", re.IGNORECASE),
    re.compile(r"review", re.IGNORECASE),
    re.compile(r"\bproduct\s+trio\b", re.IGNORECASE),
]

# Support ticket title patterns
SUPPORT_TICKET_PATTERNS: list[re.Pattern] = [
    re.compile(r"support\s+ticket", re.IGNORECASE),
    re.compile(r"ticket\s+review", re.IGNORECASE),
    re.compile(r"support\s+call", re.IGNORECASE),
    re.compile(r"\bST[-\s]?\d+", re.IGNORECASE),  # ST-123 style
]


# ---------------------------------------------------------------------------
# HubSpot domain → Rocketlane project mapping
# ---------------------------------------------------------------------------
# Source: HubSpot Closed-Won deals export, March 2026 (117 unique domains).
# Maps every known customer email domain to its active Rocketlane project ID.
# Used by find_client_by_domain() as a fallback after CLIENT_PROJECTS.domains.
# Domains with no active Rocketlane project are omitted (Completed deals, etc.).

HUBSPOT_DOMAIN_MAP: dict[str, int] = {
    # ── Roche ──────────────────────────────────────────────────────────
    "roche.com":                1000449,
    "gene.com":                 1000449,
    # ── Dexcom ─────────────────────────────────────────────────────────
    "dexcom.com":               1000398,
    # ── Medtronic ──────────────────────────────────────────────────────
    "medtronic.com":            1121886,
    # ── Philips ────────────────────────────────────────────────────────
    "philips.com":              994649,
    # ── J&J ────────────────────────────────────────────────────────────
    "its.jnj.com":              1018147,
    "jnj.com":                  1018147,
    # ── Meta ───────────────────────────────────────────────────────────
    "meta.com":                 1000414,
    "fb.com":                   1000414,
    "facebook.com":             1000414,
    # ── Inogen ─────────────────────────────────────────────────────────
    "inogen.net":               1014475,
    # ── Flo Health ─────────────────────────────────────────────────────
    "flo.health":               1000411,
    # ── Click Therapeutics ─────────────────────────────────────────────
    "clicktherapeutics.com":    1000390,
    # ── Deep Health ────────────────────────────────────────────────────
    "deephealth.com":           1000395,
    "deep.health":              1014526,
    # ── DigestAID ──────────────────────────────────────────────────────
    "digestaid.health":         1000401,
    # ── Heartflow ──────────────────────────────────────────────────────
    "heartflow.com":            1000418,
    # ── HTD Health ─────────────────────────────────────────────────────
    "htdhealth.com":            1000420,
    # ── Labviva ────────────────────────────────────────────────────────
    "labviva.com":              1000430,
    # ── Linus Health ───────────────────────────────────────────────────
    "linushealth.com":          1000431,
    # ── PictorLabs ─────────────────────────────────────────────────────
    "pictorlabs.ai":            1000444,
    # ── Sequel ─────────────────────────────────────────────────────────
    "sequelmedtech.com":        1000450,
    # ── ki:elements ────────────────────────────────────────────────────
    "ki-elements.de":           1000784,
    # ── Enovis ─────────────────────────────────────────────────────────
    "enovis.com":               1001246,
    # ── Huxley ─────────────────────────────────────────────────────────
    "huxleymed.com":            1002899,
    # ── Tachmed ────────────────────────────────────────────────────────
    "tachmed.com":              1002911,
    # ── Tactile ────────────────────────────────────────────────────────
    "tactilemedical.com":       1002958,
    # ── Revvity ────────────────────────────────────────────────────────
    "revvity.com":              1003301,
    # ── Alto ───────────────────────────────────────────────────────────
    "altoneuroscience.com":     1003388,
    # ── Optain ─────────────────────────────────────────────────────────
    "optainhealth.com":         1004063,
    # ── HOPPR ──────────────────────────────────────────────────────────
    "hoppr.ai":                 1004065,
    # ── Surgical Theater ───────────────────────────────────────────────
    "surgicaltheater.com":      1004066,
    "surgicaltheater.net":      1004066,
    # ── Stryker ────────────────────────────────────────────────────────
    "stryker.com":              1005660,
    # ── Moberg Analytics ───────────────────────────────────────────────
    "moberganalytics.com":      1017226,
    # ── Quadrivia ──────────────────────────────────────────────────────
    "quadrivia.ai":             1047506,
    # ── GeneDx ─────────────────────────────────────────────────────────
    "genedx.com":               1034070,
    # ── SideKick ───────────────────────────────────────────────────────
    "sidekickhealth.com":       1035238,
    # ── Cytovale ───────────────────────────────────────────────────────
    "cytovale.com":             1035261,
    # ── Nutrino ────────────────────────────────────────────────────────
    "nutrinohealth.com":        1037098,
    # ── Curai ──────────────────────────────────────────────────────────
    "curai.com":                1058509,
    # ── Hippocratic AI ─────────────────────────────────────────────────
    "hippocraticai.com":        1058511,
    # ── Neurotrack ─────────────────────────────────────────────────────
    "neurotrack.com":           1083276,
    # ── REDCap Cloud ───────────────────────────────────────────────────
    "redcapcloud.com":          1088856,
    # ── MedCognetics ───────────────────────────────────────────────────
    "medcognetics.com":         1088857,
    # ── Atlas Medical ──────────────────────────────────────────────────
    "atlasmed.ai":              1091467,
    # ── Agiliti ────────────────────────────────────────────────────────
    "agilitihealth.com":        1094411,
    # ── Lumonus ────────────────────────────────────────────────────────
    "lumonus.com":              1099020,
    # ── Not mapped (no active Rocketlane project as of March 2026) ─────
    # 10xbeta.com, beacon.bio, aignostics.com, foresight-dx.com,
    # empyreanmed.com, florencehc.com, canaray.com, imagen.ai,
    # iterativescopes.com, orikami.nl, talkiatry.com, vero-biotech.com,
    # andromedasurgical.com, faeththerapeutics.com, marsbioimaging.com,
    # owletcare.com, pathpresenter.com, rookqs.com, 360med.care,
    # aetion.com, gexcorp.com, glucotrack.com, henkesasswolf.de,
    # identifeye.health, iterative.health, jasprhealth.com, medlogix.eu,
    # medice.de, neckcare.com, ouitherapeutics.com, oxos.com, ozlosleep.com,
    # truesilencetherapeutics.com, abbott.com, bayer.com, bd.com,
    # docboxinc.com, eforto.com, evidation.com, figur8tech.com, gaglani.com,
    # galenrobotics.com, goengen.com, illumor.co, indd.org, iota.bio,
    # kheironmed.com, kinomica.com, klinic.com, lambdasurgical.com,
    # medicept.com, mocacognition.com, momentum.health, nephrodite.com,
    # openai.com, patchmypc.com, physicalweb.com, prolaio.com, quantco.com,
    # radnet.com, remedyrobotics.com, rlgmc.com, singulargenomics.com,
    # swansurg.com, tandemhealth.ai, teloshealth.com, uniweb.eu, updoc.ai,
    # vektormedical.com, vitrafy.com, wellframe.com, xion-medical.com
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_domain(email: str) -> str:
    """Extract domain from an email address."""
    return email.rsplit("@", 1)[-1].lower()


def find_client_by_title(title: str) -> ClientProject | None:
    """Look up a client project by matching title patterns.

    Used when no attendee domain match is found — catches solo work events
    and internal meetings whose titles reference a client (e.g. 'philips config').
    """
    for client in CLIENT_PROJECTS:
        for pattern in client.title_patterns:
            if pattern.search(title):
                return client
    return None


def find_client_by_domain(domain: str) -> ClientProject | None:
    """Look up a client project by attendee email domain.

    First checks CLIENT_PROJECTS.domains (explicit config), then falls back
    to HUBSPOT_DOMAIN_MAP which covers all known customer domains.
    """
    for client in CLIENT_PROJECTS:
        if domain in client.domains:
            return client
    # Fallback: HubSpot domain map — covers all closed-won customer domains
    project_id = HUBSPOT_DOMAIN_MAP.get(domain)
    if project_id:
        for client in CLIENT_PROJECTS:
            if client.project_id == project_id:
                return client
    return None


def resolve_project(client: ClientProject, title: str) -> tuple[int, str]:
    """Resolve the correct project ID and name for clients with multiple projects."""
    if client.disambiguate:
        for pattern, (project_id, project_name) in client.disambiguate.items():
            if re.search(pattern, title, re.IGNORECASE):
                return project_id, project_name
    return client.project_id, client.name


def is_investment_title(title: str) -> bool:
    """Check if event title indicates investment (non-reportable) work."""
    return any(p.search(title) for p in INVESTMENT_TITLE_PATTERNS)


def match_client_phase(client: ClientProject, title: str) -> str | None:
    """Match a title to a client phase name. Falls back to default_phase_name."""
    for pattern, phase_name in client.phase_patterns:
        if pattern.search(title):
            return phase_name
    return client.default_phase_name


def is_support_ticket(title: str) -> bool:
    """Check if event title matches support ticket patterns."""
    return any(p.search(title) for p in SUPPORT_TICKET_PATTERNS)


def match_overhead_phase(title: str) -> OverheadPhase:
    """Match a title to an overhead phase. Falls back to Other Overhead."""
    for phase in OVERHEAD_PHASES:
        if any(p.search(title) for p in phase.title_patterns):
            return phase
    # Fallback to Other Overhead (last phase)
    return OVERHEAD_PHASES[-1]


# ---------------------------------------------------------------------------
# Cache-based client lookup (matches any Rocketlane project name)
# ---------------------------------------------------------------------------

_CACHE_PATH = Path(__file__).resolve().parent.parent.parent / "cache" / "rocketlane_projects_phases.json"

# Internal project IDs — excluded from cache-based client matching
INTERNAL_PROJECT_IDS: frozenset[int] = frozenset({
    OVERHEAD_PROJECT_ID,
    ENTERPRISE_POD_PROJECT_ID,
    ENTERPRISE_GTM_POD_PROJECT_ID,
    SUPPORT_TICKETS_PROJECT_ID,
    VALUE_ENGINEERING_PROJECT_ID,
    PRE_SALES_SUPPORT_PROJECT_ID,  # too generic to match by title
})

# Generic words to ignore when extracting keywords from project names
_PROJECT_NAME_STOP_WORDS: frozenset[str] = frozenset({
    "and", "the", "for", "inc", "llc", "ltd", "rl", "general", "work",
    "post", "pre", "implementation", "project", "strategic", "support",
    "tickets", "overhead", "enterprise", "methodology", "pod", "account",
    "pods", "value", "engineering", "sales", "internal", "venture", "studios",
    "new", "deal", "pilot", "phase", "priority", "steady", "state",
    "q1", "q2", "q3", "q4", "2024", "2025", "2026",
})

_rocketlane_cache: dict | None = None


def _get_rocketlane_cache() -> dict:
    global _rocketlane_cache
    if _rocketlane_cache is not None:
        return _rocketlane_cache
    if not _CACHE_PATH.exists():
        _rocketlane_cache = {}
        return {}
    try:
        _rocketlane_cache = json.loads(_CACHE_PATH.read_text())
    except Exception:
        _rocketlane_cache = {}
    return _rocketlane_cache


# ---------------------------------------------------------------------------
# Auto-population of CLIENT_PROJECTS from Rocketlane cache
# ---------------------------------------------------------------------------

# Ketryx-internal project IDs — not client work, skip auto-loading
_KETRYX_INTERNAL_PROJECT_IDS: frozenset[int] = frozenset({
    1034013,  # Adrian - Internal
    1022417,  # Business Case Presentation for LT
    1000391,  # Client Intelligence POD
    1000393,  # Client Operations Leadership
    1096200,  # Client Operations Onboarding - Gideon F
    1020628,  # Jolani Internal
    1004499,  # Kevin B - Internal
    1045980,  # Lee Internal
    1069828,  # QA/RA - Internal
    992170,   # QMS Templates
    1002637,  # Quality
    1047256,  # Rocketlane test
    1035211,  # SMB Investment
    1000451,  # SMB POD
    1021612,  # Solutions Architecture POD
    1000453,  # Support Overhaul
    1103253,  # Product x Client Request Tracker
})

# Qualifier phrases stripped before extracting brand name from project name
_NAME_QUALIFIER_PATTERN = re.compile(
    r"\b(new\s+deal|implementation|strategic|steady\s+state|"
    r"post.implementation|account\s+management|priority\s+projects|"
    r"general\s+work|internal\s+only|phase\s+\d+|q[1-4]\s+\d{4}|pilot|"
    r"post.deployment|project\s+stitch|sports?\s+medicine)\b",
    re.IGNORECASE,
)

# Generic company-type suffixes stripped when more words remain
_COMPANY_SUFFIX_PATTERN = re.compile(
    r"\b(health|medical|therapeutics|analytics|robotics|cloud|"
    r"labs?|sciences?|diagnostics|biomedical|biotechnology|imaging|"
    r"surgical|biosciences?)\b",
    re.IGNORECASE,
)

_ACTIVE_STATUSES = {"In progress", "To be Staffed", "In Planning", "In Planning (Internal)"}
_PHASE_HOUSEKEEPING = re.compile(
    r"housekeeping|pre.kick|presales|backlog|untitled|milestone", re.IGNORECASE
)


_BRAND_NAME_NOISE = frozenset({
    # Generic pronouns / articles that slip through stop-word filter
    "my", "our", "the", "its",
    # Ketryx-internal terms that appear in project names but mean nothing in event titles
    "ketryx", "professional", "services", "rl",
})


def _brand_name_keywords(project_name: str) -> list[str]:
    """Extract brand-name keywords from a Rocketlane project name.

    Strips qualifier phrases (phase, year, deal status) and generic company
    suffixes, returning the core identifying words people actually use in
    event titles (e.g. "Click Therapeutics Q1 2026" → ["click"]).
    """
    name = _NAME_QUALIFIER_PATTERN.sub("", project_name)
    # Only strip company suffixes if meaningful words remain after stripping
    stripped = _COMPANY_SUFFIX_PATTERN.sub("", name).strip()
    remaining = [w for w in re.split(r"[^a-zA-Z0-9&+]+", stripped) if len(w) >= 3]
    words = re.split(r"[^a-zA-Z0-9&+]+", stripped if remaining else name)
    keywords = [
        w for w in words
        if len(w) >= 3
        and w.lower() not in _PROJECT_NAME_STOP_WORDS
        and w.lower() not in _BRAND_NAME_NOISE
    ]
    return keywords


def _auto_load_client_projects() -> None:
    """Append a ClientProject entry for every active Rocketlane project not
    already explicitly configured.  Called once at module import time so the
    full project list is always current with the cache."""
    # Collect every project ID already handled (explicit + disambiguate targets)
    configured_ids: set[int] = {c.project_id for c in CLIENT_PROJECTS}
    for c in CLIENT_PROJECTS:
        if c.disambiguate:
            for _, (pid, _) in c.disambiguate.items():
                configured_ids.add(pid)

    skip_ids = INTERNAL_PROJECT_IDS | _KETRYX_INTERNAL_PROJECT_IDS | configured_ids

    cache = _get_rocketlane_cache()
    for pid_str, project in sorted(cache.items(), key=lambda x: x[0]):
        pid = int(pid_str)
        if pid in skip_ids:
            continue
        if not isinstance(project, dict):
            continue
        if project.get("status") not in _ACTIVE_STATUSES:
            continue

        project_name = project.get("name", "")
        if not project_name:
            continue

        keywords = _brand_name_keywords(project_name)
        if not keywords:
            continue

        # Build pattern from the minimum keywords needed to identify the client.
        # If the first keyword is long/distinctive (≥5 chars), use it alone.
        # If it's short (≤4 chars, e.g. "ART", "IND"), add a second keyword for
        # disambiguation. People write "Agilent kickoff" not "Agilent Atlassian kickoff".
        if len(keywords[0]) >= 5:
            match_keywords = keywords[:1]
        else:
            match_keywords = keywords[:2]
        parts = "".join(r"(?=.*\b" + re.escape(kw) + r"\b)" for kw in match_keywords)
        pattern = re.compile(parts, re.IGNORECASE)

        # Pick first non-housekeeping phase as default
        phases = project.get("phases", [])
        default_phase = next(
            (p["name"] for p in phases if not _PHASE_HOUSEKEEPING.search(p.get("name", ""))),
            phases[0]["name"] if phases else None,
        )

        CLIENT_PROJECTS.append(ClientProject(
            name=project_name,
            project_id=pid,
            title_patterns=[pattern],
            default_phase_name=default_phase,
        ))


_auto_load_client_projects()


def find_client_in_cache(title: str) -> tuple[int, str] | None:
    """Match event title against all Rocketlane project names.

    Extracts meaningful keywords from each project name and checks if they
    appear in the event title. Returns (project_id, project_name) of the
    best match, or None if no match found.
    """
    cache = _get_rocketlane_cache()
    if not cache:
        return None

    title_lower = title.lower()
    best: tuple[int, str] | None = None
    best_score = 0

    for pid_str, project in cache.items():
        pid = int(pid_str)
        if pid in INTERNAL_PROJECT_IDS:
            continue

        project_name = project.get("name", "") if isinstance(project, dict) else str(project)
        if not project_name:
            continue

        # Extract meaningful keywords from project name
        words = re.split(r"[^a-zA-Z0-9]+", project_name)
        keywords = [
            w.lower() for w in words
            if len(w) >= 3 and w.lower() not in _PROJECT_NAME_STOP_WORDS
        ]
        if not keywords:
            continue

        matched = sum(1 for kw in keywords if re.search(r'\b' + re.escape(kw) + r'\b', title_lower))
        # Require coverage proportional to number of keywords:
        # 1-keyword projects → keyword must be ≥6 chars (avoids short names like "flo", "gex")
        # 2+ keyword projects → at least half must match
        if len(keywords) == 1:
            required = 1 if len(keywords[0]) >= 6 else 999  # short single-kw → never auto-match
        else:
            required = max(1, len(keywords) // 2)
        if matched >= required and matched > best_score:
            best_score = matched
            best = (pid, project_name)

    return best
