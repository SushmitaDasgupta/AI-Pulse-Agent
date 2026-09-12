"""Fixed ChatGPT Play theme catalog (P2 v1) + keyword classifiers."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class CatalogTheme:
    theme_id: str
    label: str
    description: str
    patterns: tuple[re.Pattern[str], ...]
    is_pain: bool = True


def _p(*patterns: str) -> tuple[re.Pattern[str], ...]:
    return tuple(re.compile(p, re.IGNORECASE) for p in patterns)


# Order matters for first-match assignment among pain themes.
CATALOG: tuple[CatalogTheme, ...] = (
    CatalogTheme(
        theme_id="t_login",
        label="Login / account access",
        description="Sign-in failures, Google account loops, device validation, reload forever.",
        patterns=_p(
            r"\b(log\s*in|login|sign\s*in|sign-in|can't enter|cannot enter|device validation|"
            r"google account|authentication|reload forever|keeps?\s+reload)\b",
        ),
    ),
    CatalogTheme(
        theme_id="t_reliability",
        label="Reliability / crashes / errors",
        description="Crashes, freezes, bugs, broken updates, hard errors that block use.",
        patterns=_p(
            r"\b(crash|crashing|freeze|freezes|frozen|bug|buggy|glitch|force.?close|"
            r"not working|stopped working|broken|error|unstable)\b",
        ),
    ),
    CatalogTheme(
        theme_id="t_image",
        label="Image & photo generation limits",
        description="Photo/image upload or generation caps, slow image creates, vision limits.",
        patterns=_p(
            r"\b(image|images|photo|photos|picture|pictures|pic|pics|dall.?e|"
            r"generate image|image generat|upload photos?|photo system)\b",
        ),
    ),
    CatalogTheme(
        theme_id="t_paywall",
        label="Paywall / limits / upgrade friction",
        description="Free-tier chat caps, Plus/Go/Pro upgrade nags, billing and subscription pain.",
        patterns=_p(
            r"\b(upgrade|subscribe|subscription|plus|premium|\bpro\b|paywall|billing|"
            r"payment|paid|pay money|free (plan|limit|tier)|limit(ed|s)?|"
            r"out of (messages|chats|usage)|quota|recharge)\b",
        ),
    ),
    CatalogTheme(
        theme_id="t_quality",
        label="Answer quality / misunderstandings",
        description="Wrong answers, flip-flopping when corrected, not understanding the user.",
        patterns=_p(
            r"\b(wrong|incorrect|mistake|mistakes|hallucin|inaccurate|lying|not correct|"
            r"doesn't understand|does not understand|not understanding|misunderstand|"
            r"useless answer|bad answer|dumb)\b",
        ),
    ),
    CatalogTheme(
        theme_id="t_praise",
        label="Praise / high satisfaction",
        description="Generic love for the app, study help, and usefulness without a concrete complaint.",
        patterns=_p(
            r"\b(love|amazing|awesome|excellent|best app|very (good|helpful|nice)|"
            r"great app|helpful for (study|studies)|wonderful)\b",
        ),
        is_pain=False,
    ),
)

CATALOG_BY_ID = {t.theme_id: t for t in CATALOG}
PAIN_THEME_IDS = {t.theme_id for t in CATALOG if t.is_pain}


def classify_review(text: str) -> str:
    """
    Assign a primary catalog theme_id.

    Pain themes win over praise when both match. Unmatched → praise if complimentary
    keywords absent else paywall-adjacent 'other' folded into quality as weakest pain.
    """
    pain_hits = [t for t in CATALOG if t.is_pain and any(p.search(text) for p in t.patterns)]
    if pain_hits:
        # Prefer more specific operational themes when multiple match.
        priority = ["t_login", "t_reliability", "t_image", "t_paywall", "t_quality"]
        pain_hits.sort(key=lambda t: priority.index(t.theme_id) if t.theme_id in priority else 99)
        return pain_hits[0].theme_id

    praise = CATALOG_BY_ID["t_praise"]
    if any(p.search(text) for p in praise.patterns):
        return praise.theme_id

    # Neutral / unclear → fold into praise share for counting, but low complaint weight
    return "t_praise"
