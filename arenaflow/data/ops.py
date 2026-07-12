"""Synthetic live operations state.

In a real deployment these would stream from sensors, gate counters, transit APIs.
For evaluation we generate a small deterministic scenario per kickoff minute.
"""

from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import random


@dataclass
class GateStatus:
    gate: str
    wait_min: int
    status: str  # open | busy | paused


@dataclass
class Snapshot:
    venue: str
    city: str
    kickoff_utc: str
    gates: list[GateStatus]
    inside: int
    capacity: int
    transit_load: dict[str, str]  # line -> status
    weather: str
    air_quality: str
    sustainability: dict[str, str]
    alerts: list[str]
    generated_at: str

    def to_dict(self) -> dict:
        d = asdict(self)
        return d


VENUES = [
    ("Estadio Azteca", "Mexico City", 87000),
    ("AT&T Stadium", "Arlington", 80000),
    ("GEHA Field at Arrowhead", "Kansas City", 76000),
    ("NRG Stadium", "Houston", 72000),
    ("Hard Rock Stadium", "Miami Gardens", 65000),
    ("Mercedes-Benz Stadium", "Atlanta", 71000),
    ("Lincoln Financial Field", "Philadelphia", 69000),
    ("Lumen Field", "Seattle", 69000),
    ("Levi's Stadium", "Santa Clara", 68500),
    ("SoFi Stadium", "Inglewood", 70000),
    ("Gillette Stadium", "Foxborough", 65000),
    ("BMO Field", "Toronto", 45000),
    ("BC Place", "Vancouver", 54000),
]

WEATHER = ["Clear 24C", "Cloudy 19C", "Light rain 16C", "Hot 31C", "Cool 12C"]
AQ = ["Good (AQI 32)", "Moderate (AQI 65)", "Good (AQI 28)"]
TRANSIT = {
    "Estadio Azteca": {"Metro L2": "On time", "Metrobus": "5 min delay"},
    "AT&T Stadium": {"DART Orange": "Crowded", "TRE": "On time"},
    "GEHA Field at Arrowhead": {"Ride KC 101": "Crowded", "Streetcar": "On time"},
    "NRG Stadium": {"METRORail Red": "On time"},
    "Hard Rock Stadium": {"Tri-Rail": "Crowded"},
    "Mercedes-Benz Stadium": {"MARTA": "On time"},
    "Lincoln Financial Field": {"SEPTA BSL": "On time"},
    "Lumen Field": {"Link Light Rail": "Crowded"},
    "Levi's Stadium": {"VTA": "On time"},
    "SoFi Stadium": {"SoFi Shuttle": "Crowded", "LAX FlyAway": "On time"},
    "Gillette Stadium": {"MBTA Commuter": "On time"},
    "BMO Field": {"GO Transit": "On time"},
    "BC Place": {"SkyTrain": "Crowded"},
}

SUSTAIN = {
    "Estadio Azteca": {"recycling": "available", "transit_included": "yes"},
    "AT&T Stadium": {"recycling": "available", "transit_included": "no"},
    "GEHA Field at Arrowhead": {"recycling": "available", "transit_included": "yes"},
    "NRG Stadium": {"recycling": "available", "transit_included": "yes"},
    "Hard Rock Stadium": {"recycling": "available", "transit_included": "no"},
    "Mercedes-Benz Stadium": {"recycling": "compost co-located", "transit_included": "yes"},
    "Lincoln Financial Field": {"recycling": "available", "transit_included": "yes"},
    "Lumen Field": {"recycling": "compost co-located", "transit_included": "yes"},
    "Levi's Stadium": {"recycling": "available", "transit_included": "yes"},
    "SoFi Stadium": {"recycling": "compost co-located", "transit_included": "yes"},
    "Gillette Stadium": {"recycling": "available", "transit_included": "no"},
    "BMO Field": {"recycling": "available", "transit_included": "yes"},
    "BC Place": {"recycling": "compost co-located", "transit_included": "yes"},
}


def _rng_for(venue: str, minute: int) -> random.Random:
    return random.Random(f"{venue}-{minute}")


def snapshot(venue: str, minute: int = 60) -> Snapshot:
    """Return a synthetic snapshot for a venue at N minutes before kickoff.

    minute is minutes until kickoff (0 = kickoff).
    """
    info = next((v for v in VENUES if v[0] == venue), None)
    if info is None:
        raise ValueError(f"unknown venue: {venue!r}")
    name, city, capacity = info
    rng = _rng_for(venue, minute)
    # inside % grows as kickoff approaches
    ramp = max(0.05, 1.0 - (minute / 180.0))
    inside = int(capacity * ramp * rng.uniform(0.85, 1.05))
    inside = min(inside, capacity)

    n_gates = rng.choice([4, 5, 6])
    gate_states = ["open", "open", "busy", "busy", "paused"]
    gates = [
        GateStatus(
            gate=f"G{i+1}",
            wait_min=rng.randint(2, 25) if (s := rng.choice(gate_states)) != "paused" else 0,
            status=s,
        )
        for i in range(n_gates)
    ]

    alerts: list[str] = []
    if any(g.wait_min > 20 for g in gates):
        alerts.append("Gate wait >20 min: redirect to next open gate.")
    if "Hot" in WEATHER[minute % len(WEATHER)]:
        alerts.append("Heat advisory: activate cooling zones & free water stations.")
    if inside / capacity > 0.9:
        alerts.append("Venue >90% full: pause non-essential re-entries.")

    return Snapshot(
        venue=name,
        city=city,
        kickoff_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        gates=gates,  # kept as GateStatus; to_dict serialises them
        inside=inside,
        capacity=capacity,
        transit_load=TRANSIT.get(name, {}),
        weather=WEATHER[minute % len(WEATHER)],
        air_quality=AQ[minute % len(AQ)],
        sustainability=SUSTAIN.get(name, {}),
        alerts=alerts,
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )


def venue_names() -> list[str]:
    return [v[0] for v in VENUES]
