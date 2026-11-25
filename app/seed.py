"""Seed data for the CostTrack API.

One project, ``proj_01J8X``, with a priced bill of quantities of 37 items
across three trades. The numbers are chosen so the project totals match the
figures in the API reference exactly:

- concrete  SGD 642,300.00  (19 items)
- steel    SGD 518,400.00  (8 items)
- finishes SGD 681,800.00  (10 items)
- live total SGD 1,842,500.00

``amount`` is always ``quantity x rate`` rounded to 2 decimal places.
"""

from decimal import Decimal

PROJECT_ID = "proj_01J8X"
CURRENCY = "SGD"
_UPDATED_AT = "2026-11-10T09:30:00+08:00"


def _item(item_no, description, unit, quantity, rate, trade):
    amount = float((Decimal(str(quantity)) * Decimal(str(rate))).quantize(Decimal("0.01")))
    return {
        "item_no": item_no,
        "description": description,
        "unit": unit,
        "quantity": quantity,
        "rate": rate,
        "amount": amount,
        "trade": trade,
        "updated_at": _UPDATED_AT,
    }


ITEMS = [
    # Concrete (19 items, SGD 642,300.00)
    _item("3.1", "Grade 40 reinforced concrete, columns", "m3", 120.5, 185.00, "concrete"),
    _item("3.2", "Grade 40 reinforced concrete, beams", "m3", 86.0, 185.00, "concrete"),
    _item("3.3", "Grade 40 reinforced concrete, slabs", "m3", 240.0, 185.00, "concrete"),
    _item("3.4", "Grade 30 reinforced concrete, footings", "m3", 150.0, 165.00, "concrete"),
    _item("3.5", "Reinforced concrete, retaining walls", "m3", 95.5, 195.00, "concrete"),
    _item("3.6", "Concrete blinding layer", "m2", 320.0, 45.00, "concrete"),
    _item("3.7", "Formwork, columns and beams", "m2", 1850.0, 38.00, "concrete"),
    _item("3.8", "Formwork, slabs", "m2", 2400.0, 32.00, "concrete"),
    _item("3.9", "Steel reinforcement, high-yield bars", "kg", 85000.0, 1.85, "concrete"),
    _item("3.10", "Steel reinforcement, mild steel bars", "kg", 22000.0, 1.60, "concrete"),
    _item("3.11", "Precast concrete, staircases", "nr", 12, 2850.00, "concrete"),
    _item("3.12", "Concrete, column encasement", "m3", 45.0, 210.00, "concrete"),
    _item("3.13", "Waterproofing admixture to concrete", "m3", 380.0, 28.00, "concrete"),
    _item("3.14", "Concrete pumping and placing", "m3", 580.0, 85.00, "concrete"),
    _item("3.15", "Grade 25 concrete, ground floor slab", "m3", 180.0, 150.00, "concrete"),
    _item("3.16", "Precast concrete, lintels", "m", 240.0, 85.00, "concrete"),
    _item("3.17", "Grout, non-shrink, under base plates", "m3", 12.5, 320.00, "concrete"),
    _item("3.18", "Concrete, thrust blocks", "m3", 8.0, 220.00, "concrete"),
    _item("3.19", "Damp-proof membrane", "m2", 312.5, 18.00, "concrete"),
    # Steel (8 items, SGD 518,400.00)
    _item("4.1", "Structural steel, columns", "t", 118.0, 2450.00, "steel"),
    _item("4.2", "Structural steel, beams", "t", 62.0, 2450.00, "steel"),
    _item("4.3", "Steel decking, composite floor", "m2", 380.0, 95.00, "steel"),
    _item("4.4", "Steel, handrails and balustrades", "m", 120.0, 145.00, "steel"),
    _item("4.5", "Steel, gratings", "m2", 45.0, 120.00, "steel"),
    _item("4.6", "Steel, ladders and cages", "m", 28.0, 95.00, "steel"),
    _item("4.7", "Steel, base plates", "nr", 64, 180.00, "steel"),
    _item("4.8", "Steel, holding-down bolts", "nr", 96, 45.00, "steel"),
    # Finishes (10 items, SGD 681,800.00)
    _item("5.1", "Plaster to walls", "m2", 4200.0, 28.00, "finishes"),
    _item("5.2", "Plaster to ceilings", "m2", 2600.0, 32.00, "finishes"),
    _item("5.3", "Ceramic floor tiles", "m2", 1850.0, 85.00, "finishes"),
    _item("5.4", "Vinyl flooring", "m2", 1200.0, 65.00, "finishes"),
    _item("5.5", "Emulsion paint to walls", "m2", 6800.0, 12.00, "finishes"),
    _item("5.6", "Emulsion paint to ceilings", "m2", 2600.0, 14.00, "finishes"),
    _item("5.7", "Skirting, timber", "m", 950.0, 22.00, "finishes"),
    _item("5.8", "Suspended ceiling, mineral fibre", "m2", 1400.0, 68.00, "finishes"),
    _item("5.9", "Ironmongery to doors", "nr", 120, 85.00, "finishes"),
    _item("5.10", "Allow for sundry finishes and making good", "lot", 1, 1450.00, "finishes"),
]
