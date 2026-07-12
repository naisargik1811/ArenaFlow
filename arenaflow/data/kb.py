"""Curated knowledge base for FIFA World Cup 2026 host cities & operations.

All entries are short, factual snippets intended for RAG retrieval.
Each snippet includes tags for cheap filtering.
"""

from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class Snippet:
    id: str
    title: str
    text: str
    tags: tuple[str, ...]
    city: str | None = None


KB: tuple[Snippet, ...] = (
    Snippet(
        "venue-mexcity",
        "Estadio Azteca (Mexico City)",
        "Capacity ~87,000. Step-free access at all gates. Nearest Metro: Tasqueña (Line 2). Accessible drop-off at Gate 5. "
        "Sensory room: Gate 3. Steep upper tier - mobility users advised to use Sections 12-14.",
        ("venue", "accessibility", "transport"),
        "Mexico City",
    ),
    Snippet(
        "venue-dallas",
        "AT&T Stadium (Arlington/Dallas)",
        "Capacity ~80,000. Step-free access throughout; accessible drop-off at the ADA entrance - Guest Services directs you to the nearest point. DART Orange Line to CentrePort. ADA shuttles every 10 min from "
        "remote lots B/C. Quiet room next to Guest Services on Lower Level concourse.",
        ("venue", "accessibility", "transport"),
        "Arlington",
    ),
    Snippet(
        "venue-kansascity",
        "GEHA Field at Arrowhead (Kansas City)",
        "Capacity ~76,000. Step-free access throughout; accessible drop-off at the ADA entrance - Guest Services directs you to the nearest point. Ride KC Bus 101 from Union Station. Sensory bags available at all "
        "gates. Family/sensory section in Sections 130-134.",
        ("venue", "accessibility", "transport"),
        "Kansas City",
    ),
    Snippet(
        "venue-houston",
        "NRG Stadium (Houston)",
        "Capacity ~72,000. Step-free access throughout; accessible drop-off at the ADA entrance - Guest Services directs you to the nearest point. METRORail Red Line to NRG Park. 1,000+ accessible seats; book via "
        "ticket portal for ADA. Hearing loop at all service desks.",
        ("venue", "accessibility", "transport"),
        "Houston",
    ),
    Snippet(
        "venue-miami",
        "Hard Rock Stadium (Miami)",
        "Capacity ~65,000. Step-free access throughout; accessible drop-off at the ADA entrance - Guest Services directs you to the nearest point. Tri-Rail to Miami Gardens. Free ADA paratransit from parking; "
        "request on arrival. Climate-controlled rest zones at Section 100, 200, 300.",
        ("venue", "accessibility", "transport"),
        "Miami Gardens",
    ),
    Snippet(
        "venue-atlanta",
        "Mercedes-Benz Stadium (Atlanta)",
        "Capacity ~71,000. Step-free access throughout; accessible drop-off at the ADA entrance - Guest Services directs you to the nearest point. MARTA to Vine City / GWCC. Concierge companions available (free) at "
        "Guest Services - book same day. Service-animal relief on Plaza level.",
        ("venue", "accessibility", "transport"),
        "Atlanta",
    ),
    Snippet(
        "venue-philly",
        "Lincoln Financial Field (Philadelphia)",
        "Capacity ~69,000. Step-free access throughout; accessible drop-off at the ADA entrance - Guest Services directs you to the nearest point. SEPTA Broad Street Line to NRG Station. Step-free route from "
        "platform to Section C128. Sensory bags and weighted lap pads at Guest Services.",
        ("venue", "accessibility", "transport"),
        "Philadelphia",
    ),
    Snippet(
        "venue-seattle",
        "Lumen Field (Seattle)",
        "Capacity ~69,000. Link Light Rail to Stadium Station. All-gender restrooms on every "
        "level. Audio description available for visually impaired fans - request headset at Gate 1. Step-free access throughout; accessible drop-off at the ADA entrance - Guest Services directs you to the nearest point.",
        ("venue", "accessibility", "transport"),
        "Seattle",
    ),
    Snippet(
        "venue-sf",
        "Levi's Stadium (San Francisco Bay Area)",
        "Capacity ~68,500. Step-free access throughout; accessible drop-off at the ADA entrance - Guest Services directs you to the nearest point. VTA Light Rail to Great America. Free accessibility shuttle from "
        "Great America lot. Tactile maps at Guest Services.",
        ("venue", "accessibility", "transport"),
        "Santa Clara",
    ),
    Snippet(
        "venue-la",
        "SoFi Stadium (Los Angeles/Inglewood)",
        "Capacity ~70,000. Step-free access throughout; accessible drop-off at the ADA entrance (West Plaza) - Guest Services directs you to the nearest point. LAX FlyAway to Inglewood + free SoFi shuttle on match days. "
        "Sensory room: Gate P. Free sunscreen stations on West Plaza.",
        ("venue", "accessibility", "transport", "sustainability"),
        "Inglewood",
    ),
    Snippet(
        "venue-boston",
        "Gillette Stadium (Boston/Foxborough)",
        "Capacity ~65,000. MBTA Commuter Rail to Foxborough. ADA golf-cart shuttles run every "
        "5 min on match day. Sensory-friendly room at Patriot Place Gate. Step-free access throughout; accessible drop-off at the ADA entrance - Guest Services directs you to the nearest point.",
        ("venue", "accessibility", "transport"),
        "Foxborough",
    ),
    Snippet(
        "venue-toronto",
        "BMO Field (Toronto)",
        "Capacity ~45,000 Step-free access throughout; accessible drop-off at the ADA entrance - Guest Services directs you to the nearest point. (expandable to 47,000). TTC + GO to Exhibition. Wheelchair-accessible "
        "platforms at every gate. Sensory room: Gate 1.",
        ("venue", "accessibility", "transport"),
        "Toronto",
    ),
    Snippet(
        "venue-vancouver",
        "BC Place (Vancouver)",
        "Capacity ~54,000. Step-free access throughout; accessible drop-off at the ADA entrance - Guest Services directs you to the nearest point. SkyTrain to Stadium-Chinatown. ASL-interpreted screens at Sections "
        "204, 218, 240. Indigenous welcome space at Gate A.",
        ("venue", "accessibility", "transport"),
        "Vancouver",
    ),
    Snippet(
        "lang",
        "Match-day languages",
        "Stadium help desks support English, Spanish, French, Arabic, Portuguese, German, "
        "Japanese, Korean and sign language. The ArenaFlow chat auto-detects and replies in the "
        "user's language.",
        ("language", "policy"),
    ),
    Snippet(
        "sustain",
        "Sustainability on match day",
        "Bring an empty bottle - free refill stations at every concourse. Recycling and compost "
        "bins are co-located. Public transit is included with match ticket in 11 of 16 host cities.",
        ("sustainability", "policy"),
    ),
    Snippet(
        "crowd",
        "Crowd management - pre-match",
        "Gates open 3 hours before kickoff. Aim to arrive 90+ min early to clear security and "
        "reach your seat by team warmups. If a gate shows >15 min wait, follow staff to the next "
        "open gate - don't queue-jump.",
        ("crowd", "policy"),
    ),
    Snippet(
        "crowd-hf",
        "Heat & weather policy",
        "Free water at any concession. Cooling zones in shaded concourses. If you feel unwell, "
        "find the nearest Red Cross station (markings every ~50m on concourse).",
        ("crowd", "safety"),
    ),
    Snippet(
        "fanid",
        "Fan ID & safety",
        "FIFA Fan ID is optional in host cities but speeds security screening. Don't share your "
        "ticket QR. Report suspicious items to nearest steward - not via phone.",
        ("safety", "policy"),
    ),
)


def all_snippets() -> list[Snippet]:
    return list(KB)

def venue_cities() -> list[tuple[str, str]]:
    """(display label, host city) for venue snippets, for city filters."""
    out: list[tuple[str, str]] = []
    for snip in KB:
        if snip.city:
            out.append((snip.title, snip.city))
    return out
