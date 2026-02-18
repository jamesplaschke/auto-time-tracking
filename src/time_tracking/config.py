"""Client mappings, project IDs, regex patterns, and constants."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TIMEZONE = "America/New_York"
USER_EMAIL = "jamesp@ketryx.com"
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
        title_patterns=[re.compile(r"\bphilips\b", re.IGNORECASE)],
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
        default_phase_name="Implementation",
        phase_patterns=[
            (re.compile(r"\b(plan|prep|email|schedule)\b", re.IGNORECASE), "Planning"),
            (re.compile(r"\b(support|ticket)\b", re.IGNORECASE), "Support"),
            (re.compile(r"\b(improv)", re.IGNORECASE), "Continuous Improvement"),
        ],
    ),
    ClientProject(
        name="Roche nCH",
        project_id=1000449,
        domains=["roche.com", "gene.com"],
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
]

# Support Tickets — matched by title, not domain
SUPPORT_TICKETS_PROJECT_ID = 1047192
SUPPORT_TICKETS_NAME = "Support Tickets (strategic)"

# Value Engineering — matched by title, logged to Overhead > Enabling Work
VALUE_ENGINEERING_PATTERN = re.compile(r"value\s+engineering", re.IGNORECASE)

# Enterprise Methodology Pod — matched by title, logged to project 1000405
ENTERPRISE_POD_PATTERN = re.compile(r"enterprise\s+(methodology|pod)", re.IGNORECASE)
ENTERPRISE_POD_PROJECT_ID = 1000405
ENTERPRISE_POD_PROJECT_NAME = "Enterprise Methodology Pod"
ENTERPRISE_POD_DEFAULT_PHASE_NAME = "Enterprise Pod Work Q1 2026"

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
            re.compile(r"\bpod\b", re.IGNORECASE),
            re.compile(r"team\s+(sync|standup|meeting|call)", re.IGNORECASE),
            re.compile(r"sprint\s+(review|retro|planning)", re.IGNORECASE),
            # Hockey stick pod / commercial pod 1 — logged to overhead until project exists
            re.compile(r"hockey\s*stick", re.IGNORECASE),
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
    # Personal / non-work activities
    re.compile(r"\bwater\s+polo\b", re.IGNORECASE),
]

# Events with these titles are investment (not reportable) for client projects
INVESTMENT_TITLE_PATTERNS: list[re.Pattern] = [
    re.compile(r"internal", re.IGNORECASE),
    re.compile(r"prep\b", re.IGNORECASE),
    re.compile(r"planning", re.IGNORECASE),
    re.compile(r"strategy", re.IGNORECASE),
    re.compile(r"review", re.IGNORECASE),
]

# Support ticket title patterns
SUPPORT_TICKET_PATTERNS: list[re.Pattern] = [
    re.compile(r"support\s+ticket", re.IGNORECASE),
    re.compile(r"ticket\s+review", re.IGNORECASE),
    re.compile(r"support\s+call", re.IGNORECASE),
    re.compile(r"\bST[-\s]?\d+", re.IGNORECASE),  # ST-123 style
]


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
    """Look up a client project by attendee email domain."""
    for client in CLIENT_PROJECTS:
        if domain in client.domains:
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
