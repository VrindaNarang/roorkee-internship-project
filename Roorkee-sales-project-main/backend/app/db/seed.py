"""Full synthetic dataset seeder (Milestone 12: production-demo dataset).

Generates a large, internally-consistent dataset — ~500 customer institutions
across 5 segments (government/private/university/research_lab/industry), ~200
lab/engineering products across 10 categories, ~24 sales reps, and 20,000+
orders spread across 24 months of seasonal, segment-aware, growth-trending
purchasing behavior — so every live-computed page (dashboard, analytics,
customer health, recommendations, ML predictions, copilot) has a coherent
story to tell from one source of raw data. Nothing here is denormalized or
duplicated per-page; every downstream number (health scores, SHAP predictions,
recommendations) is computed by the app's own real logic against these rows.

Deliberately reproducible: `Faker`/`random` are seeded, so re-running this
script (with `--reset`) always regenerates the same dataset byte-for-byte.

Run with:  python -m app.db.seed [--reset]

`bootstrap_if_empty(db)` is the entry point `app.main`'s startup lifespan calls
so a brand-new (empty) database self-populates — data + health scores — with
no manual commands. ML predictions/SHAP explanations are a deliberately
separate, heavier step (`POST /ml/retrain`, or the equivalent `ml/` CLI) since
the backend intentionally carries no ML dependencies (see `ml_admin.py`).
"""

from __future__ import annotations

import argparse
import datetime as dt
import math
import random

from faker import Faker
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import seed_users
from app.db.session import SessionLocal
from app.health_score.health_service import HealthScoreService
from app.models import College, Order, OrderItem, Product, ProductCategory, SalesRep

fake = Faker("en_IN")
Faker.seed(42)
random.seed(42)

# ---------------------------------------------------------------------------
# Geography — 6 zones, ~27 states, ~100 cities
# ---------------------------------------------------------------------------

REGION_WEIGHTS: list[tuple[float, str]] = [
    (22, "North"),
    (24, "South"),
    (20, "West"),
    (14, "East"),
    (10, "Central"),
    (10, "North-East"),
]

STATES_BY_REGION: dict[str, list[str]] = {
    "North": ["Delhi", "Punjab", "Haryana", "Uttar Pradesh", "Rajasthan", "Uttarakhand", "Himachal Pradesh", "Jammu and Kashmir"],
    "South": ["Karnataka", "Tamil Nadu", "Andhra Pradesh", "Telangana", "Kerala", "Puducherry"],
    "West": ["Maharashtra", "Gujarat", "Goa"],
    "East": ["West Bengal", "Odisha", "Bihar", "Jharkhand"],
    "Central": ["Madhya Pradesh", "Chhattisgarh"],
    "North-East": ["Assam", "Meghalaya", "Manipur", "Tripura"],
}

CITIES_BY_STATE: dict[str, list[str]] = {
    "Delhi": ["New Delhi", "Dwarka", "Rohini"],
    "Punjab": ["Ludhiana", "Amritsar", "Patiala"],
    "Haryana": ["Gurugram", "Faridabad", "Panipat"],
    "Uttar Pradesh": ["Lucknow", "Kanpur", "Varanasi", "Noida"],
    "Rajasthan": ["Jaipur", "Udaipur", "Jodhpur"],
    "Uttarakhand": ["Dehradun", "Haridwar", "Roorkee"],
    "Himachal Pradesh": ["Shimla", "Solan"],
    "Jammu and Kashmir": ["Srinagar", "Jammu"],
    "Karnataka": ["Bengaluru", "Mysuru", "Mangaluru"],
    "Tamil Nadu": ["Chennai", "Coimbatore", "Madurai"],
    "Andhra Pradesh": ["Visakhapatnam", "Vijayawada", "Tirupati"],
    "Telangana": ["Hyderabad", "Warangal"],
    "Kerala": ["Kochi", "Thiruvananthapuram", "Kozhikode"],
    "Puducherry": ["Puducherry"],
    "Maharashtra": ["Mumbai", "Pune", "Nagpur", "Nashik"],
    "Gujarat": ["Ahmedabad", "Surat", "Vadodara"],
    "Goa": ["Panaji", "Margao"],
    "West Bengal": ["Kolkata", "Siliguri", "Durgapur"],
    "Odisha": ["Bhubaneswar", "Cuttack", "Rourkela"],
    "Bihar": ["Patna", "Gaya"],
    "Jharkhand": ["Ranchi", "Jamshedpur"],
    "Madhya Pradesh": ["Bhopal", "Indore", "Gwalior"],
    "Chhattisgarh": ["Raipur", "Bhilai"],
    "Assam": ["Guwahati", "Dibrugarh"],
    "Meghalaya": ["Shillong"],
    "Manipur": ["Imphal"],
    "Tripura": ["Agartala"],
}

# ---------------------------------------------------------------------------
# Customer segments (institution_type) — see alembic revision b3f7a1d9c264
# ---------------------------------------------------------------------------

SEGMENT_SPECS: dict[str, dict] = {
    "government": {
        "weight": 26,
        "name_templates": [
            "{city} Government Polytechnic",
            "Government College of Engineering, {city}",
            "District Government Hospital, {city}",
            "{city} Government Medical College",
            "State Institute of Technology, {city}",
            "Government Industrial Training Institute, {city}",
            "{city} Government Degree College",
            "Rashtriya Vidyalaya, {city}",
            "Government Polytechnic for Women, {city}",
        ],
        "cadence_per_month": 2.6,
        "payment_profile": [(0.42, "paid"), (0.30, "pending"), (0.28, "overdue")],
        "payment_delay_range": (-5, 50),
        "discount_bump_chance": 0.40,
        "discount_bump_range": (2, 6),
        "category_weights": {
            "Glassware & Labware": 26, "Reagents & Chemicals": 22, "Lab Consumables": 26,
            "Safety Equipment & PPE": 10, "Lab Furniture & Storage": 4, "Analytical Instruments": 5,
            "Measurement & Testing Instruments": 3, "Electrical & Electronic Lab Equipment": 2,
            "Microscopy & Imaging": 1, "Engineering Tools & Fabrication Equipment": 1,
        },
    },
    "private": {
        "weight": 20,
        "name_templates": [
            "{city} Institute of Technology",
            "St. Xavier's College, {city}",
            "{city} Multispecialty Hospital",
            "{city} Institute of Applied Sciences",
            "Sacred Heart College, {city}",
            "{city} Polytechnic for Women",
            "{city} Women's College",
            "{city} Junior College of Science",
        ],
        "cadence_per_month": 2.8,
        "payment_profile": [(0.72, "paid"), (0.20, "pending"), (0.08, "overdue")],
        "payment_delay_range": (-5, 18),
        "discount_bump_chance": 0.15,
        "discount_bump_range": (1, 3),
        "category_weights": {
            "Glassware & Labware": 24, "Reagents & Chemicals": 20, "Lab Consumables": 24,
            "Safety Equipment & PPE": 12, "Lab Furniture & Storage": 5, "Analytical Instruments": 6,
            "Measurement & Testing Instruments": 4, "Electrical & Electronic Lab Equipment": 2,
            "Microscopy & Imaging": 2, "Engineering Tools & Fabrication Equipment": 1,
        },
    },
    "university": {
        "weight": 20,
        "name_templates": [
            "{city} University",
            "{city} University of Science & Technology",
            "National Institute of Technology, {city}",
            "Indian Institute of Science Education, {city}",
            "{city} Central University",
            "{city} State University",
        ],
        "cadence_per_month": 3.0,
        "payment_profile": [(0.65, "paid"), (0.23, "pending"), (0.12, "overdue")],
        "payment_delay_range": (-5, 25),
        "discount_bump_chance": 0.20,
        "discount_bump_range": (1, 4),
        "category_weights": {
            "Glassware & Labware": 30, "Reagents & Chemicals": 22, "Lab Consumables": 28,
            "Safety Equipment & PPE": 12, "Lab Furniture & Storage": 2, "Analytical Instruments": 3,
            "Measurement & Testing Instruments": 1.5, "Electrical & Electronic Lab Equipment": 1,
            "Microscopy & Imaging": 0.3, "Engineering Tools & Fabrication Equipment": 0.2,
        },
    },
    "research_lab": {
        "weight": 16,
        "name_templates": [
            "CSIR - {city} Research Institute",
            "{city} Advanced Research Laboratory",
            "National Research Centre, {city}",
            "{city} Institute of Scientific Research",
            "Defence Research Laboratory, {city}",
            "{city} Centre for Applied Research",
        ],
        "cadence_per_month": 1.3,
        "payment_profile": [(0.80, "paid"), (0.15, "pending"), (0.05, "overdue")],
        "payment_delay_range": (-5, 12),
        "discount_bump_chance": 0.05,
        "discount_bump_range": (1, 2),
        "category_weights": {
            "Glassware & Labware": 26, "Reagents & Chemicals": 20, "Lab Consumables": 20,
            "Safety Equipment & PPE": 10, "Lab Furniture & Storage": 4, "Analytical Instruments": 8,
            "Measurement & Testing Instruments": 5, "Electrical & Electronic Lab Equipment": 4,
            "Microscopy & Imaging": 2, "Engineering Tools & Fabrication Equipment": 1,
        },
    },
    "industry": {
        "weight": 18,
        "name_templates": [
            "{city} Industries Ltd",
            "{city} Manufacturing Works",
            "{city} Precision Engineering Ltd",
            "{city} Heavy Industries",
            "{city} Engineering Corporation",
            "{city} Industrial Fabrication Pvt Ltd",
        ],
        "cadence_per_month": 2.5,
        "payment_profile": [(0.78, "paid"), (0.17, "pending"), (0.05, "overdue")],
        "payment_delay_range": (-5, 10),
        "discount_bump_chance": 0.08,
        "discount_bump_range": (1, 3),
        "category_weights": {
            "Glassware & Labware": 20, "Reagents & Chemicals": 18, "Lab Consumables": 20,
            "Safety Equipment & PPE": 18, "Lab Furniture & Storage": 4, "Analytical Instruments": 5,
            "Measurement & Testing Instruments": 7, "Electrical & Electronic Lab Equipment": 5,
            "Microscopy & Imaging": 1, "Engineering Tools & Fabrication Equipment": 2,
        },
    },
}

# ---------------------------------------------------------------------------
# Product catalog — 10 categories, ~200 products
# ---------------------------------------------------------------------------

VOLUME_VARIANTS = ["", " (Small)", " (250ml)", " (500ml)", " (1L)", " (Large)", " (5L)", " (Pack of 10)"]
SPEC_VARIANTS = ["", " - Standard", " - Advanced", " - Digital", " - Compact", " - Industrial Grade", " - Portable", " - Research Grade"]

CATEGORY_SPECS: list[dict] = [
    {
        "name": "Glassware & Labware",
        "description": "Beakers, flasks, test tubes, and general laboratory glassware",
        "price_band": (100, 4000),
        "units": ["piece", "box", "set"],
        "variants": VOLUME_VARIANTS,
        "names": [
            "Borosilicate Beaker Set", "Erlenmeyer Flask", "Graduated Cylinder", "Test Tube Rack",
            "Volumetric Flask", "Petri Dish Pack", "Watch Glass Set", "Burette (Class A)",
            "Glass Funnel Set", "Reagent Bottle (Amber)", "Round Bottom Flask", "Desiccator",
        ],
    },
    {
        "name": "Reagents & Chemicals",
        "description": "Analytical and reagent-grade chemicals",
        "price_band": (150, 9000),
        "units": ["litre", "kg", "pack"],
        "variants": VOLUME_VARIANTS,
        "names": [
            "Sulfuric Acid (AR Grade)", "Sodium Hydroxide Pellets", "Ethanol (Absolute)",
            "Hydrochloric Acid", "Potassium Permanganate", "Acetone (AR Grade)",
            "Copper Sulfate Crystals", "Silver Nitrate", "Phenolphthalein Indicator",
            "Distilled Water", "Sodium Chloride (AR Grade)", "Methanol (HPLC Grade)",
        ],
    },
    {
        "name": "Lab Consumables",
        "description": "Filter paper, pipette tips, labels, and other lab consumables",
        "price_band": (50, 2500),
        "units": ["pack", "box", "roll"],
        "variants": VOLUME_VARIANTS,
        "names": [
            "Filter Paper (Whatman Grade 1)", "Micropipette Tips (Box)", "Parafilm Roll",
            "Disposable Petri Dishes (Pack)", "Cotton Wool Roll", "Litmus Paper Strips",
            "Weighing Boats (Pack)", "Sample Vials (Pack of 50)", "Lab Labels Roll",
            "Disposable Syringes (Pack)", "Nitrile Gloves (Box of 100)",
        ],
    },
    {
        "name": "Safety Equipment & PPE",
        "description": "Personal protective equipment and lab safety fixtures",
        "price_band": (100, 30000),
        "units": ["piece", "box", "set"],
        "variants": VOLUME_VARIANTS,
        "names": [
            "Safety Goggles", "Lab Coat (Cotton)", "Fume Hood (Ductless)", "CO2 Fire Extinguisher",
            "Eye Wash Station", "First Aid Kit", "Face Shield", "Chemical Splash Apron",
            "Spill Containment Kit", "Respirator Mask (Box)",
        ],
    },
    {
        "name": "Lab Furniture & Storage",
        "description": "Workbenches, storage cabinets, and lab fit-out furniture",
        "price_band": (3000, 70000),
        "units": ["piece", "set"],
        "variants": SPEC_VARIANTS,
        "names": [
            "Laboratory Workbench", "Chemical Storage Cabinet", "Adjustable Lab Stool",
            "Fume Cupboard", "Glassware Storage Rack", "Mobile Lab Trolley",
            "Wall-mounted Shelf Unit", "Acid-resistant Cabinet",
        ],
    },
    {
        "name": "Analytical Instruments",
        "description": "pH meters, spectrophotometers, balances, and benchtop instruments",
        "price_band": (3000, 200000),
        "units": ["piece", "set"],
        "variants": SPEC_VARIANTS,
        "names": [
            "Digital pH Meter", "UV-Vis Spectrophotometer", "Analytical Balance (0.1mg)",
            "Benchtop Centrifuge", "Hot Air Oven", "Muffle Furnace",
            "Magnetic Stirrer with Hotplate", "Colony Counter", "Digital Water Bath",
            "Autoclave (Vertical)", "Refractometer", "Conductivity Meter",
        ],
    },
    {
        "name": "Measurement & Testing Instruments",
        "description": "Precision measurement, calibration, and materials-testing instruments",
        "price_band": (1500, 120000),
        "units": ["piece", "set"],
        "variants": SPEC_VARIANTS,
        "names": [
            "Digital Vernier Caliper", "Digital Multimeter", "Torque Wrench Set",
            "Dial Gauge Indicator", "Surface Roughness Tester", "Hardness Tester (Rockwell)",
            "Ultrasonic Thickness Gauge", "Digital Micrometer", "Strain Gauge Kit",
            "Pressure Gauge Calibrator", "Sound Level Meter",
        ],
    },
    {
        "name": "Electrical & Electronic Lab Equipment",
        "description": "Bench power supplies, signal instruments, and electronics trainer kits",
        "price_band": (2000, 250000),
        "units": ["piece", "set"],
        "variants": SPEC_VARIANTS,
        "names": [
            "Regulated DC Power Supply", "Function Generator", "Digital Storage Oscilloscope",
            "LCR Meter", "Bench Power Supply Unit", "PLC Trainer Kit",
            "Breadboard Prototyping Kit", "Variable Autotransformer", "Circuit Trainer Board",
            "Insulation Resistance Tester", "Frequency Counter",
        ],
    },
    {
        "name": "Microscopy & Imaging",
        "description": "Optical, digital, and research-grade microscopy systems",
        "price_band": (5000, 800000),
        "units": ["piece", "set"],
        "variants": SPEC_VARIANTS,
        "names": [
            "Compound Optical Microscope", "Stereo Zoom Microscope", "Digital Microscope Camera",
            "Inverted Research Microscope", "Fluorescence Microscope", "Metallurgical Microscope",
            "Polarizing Microscope", "Trinocular Microscope", "Portable Digital Microscope",
        ],
    },
    {
        "name": "Engineering Tools & Fabrication Equipment",
        "description": "Workshop, fabrication, and engineering training equipment",
        "price_band": (500, 1500000),
        "units": ["piece", "set"],
        "variants": SPEC_VARIANTS,
        "names": [
            "Bench Vice", "Hydraulic Press Trainer", "CNC Milling Trainer Machine",
            "Industrial 3D Printer", "Arc Welding Trainer Unit", "Lathe Machine (Trainer)",
            "Drill Press (Bench)", "Sheet Metal Bending Machine", "Pneumatics Trainer Kit",
            "Hydraulics Trainer Kit", "Robotics Arm Trainer", "Precision Hand Tool Kit",
        ],
    },
]

SALES_REP_COUNT = 24
COLLEGE_COUNT = 520
PRODUCT_TARGET = 200
ORDER_MONTHS = 24
MIN_ORDER_VALUE = 10_000
MAX_ORDER_VALUE = 1_500_000
GROWTH_START = 0.85
GROWTH_END = 1.20

# Order-value distribution — each order first rolls a size tier, THEN line
# items are built to hit that target (log-uniform within the tier's band),
# rather than hoping category/quantity randomness happens to land in range.
# Weights/bands calibrated (via a few empirical seed-and-measure passes) so
# ~500 colleges x 24 months lands annual revenue in the ₹15-40 Cr band with
# every individual order inside [MIN_ORDER_VALUE, MAX_ORDER_VALUE].
ORDER_SIZE_TIERS: list[tuple[float, tuple[float, float]]] = [
    (0.88, (MIN_ORDER_VALUE, 40_000)),
    (0.10, (40_000, 120_000)),
    (0.02, (120_000, MAX_ORDER_VALUE)),
]
# Small-tier orders are restricted to these categories so a single line item
# realistically lands near a small target instead of one expensive instrument
# blowing a ₹15k order out to ₹80k+.
CHEAP_CATEGORIES = {"Glassware & Labware", "Reagents & Chemicals", "Lab Consumables", "Safety Equipment & PPE"}


def _weighted_choice(options: list[tuple[float, object]]) -> object:
    total = sum(weight for weight, _ in options)
    pick = random.uniform(0, total)
    upto = 0.0
    for weight, value in options:
        upto += weight
        if pick <= upto:
            return value
    return options[-1][1]


def _apportion(total: int, weights: list[tuple[float, str]]) -> dict[str, int]:
    """Largest-remainder apportionment — used so a small fixed count (sales
    reps) is distributed across zones proportionally without any zone
    rounding down to zero."""
    weight_sum = sum(w for w, _ in weights)
    shares = {name: total * w / weight_sum for w, name in weights}
    floors = {name: int(v) for name, v in shares.items()}
    remainder = total - sum(floors.values())
    remainders_sorted = sorted(shares.items(), key=lambda kv: kv[1] - floors[kv[0]], reverse=True)
    for name, _ in remainders_sorted[:remainder]:
        floors[name] += 1
    return floors


def _log_uniform(low: float, high: float) -> float:
    """Prices span 2-3 orders of magnitude within a category (e.g. a bench
    vice vs. a CNC trainer machine, both "Engineering Tools"). A linear
    `random.uniform` over a band that wide has its *mean* sitting near the
    midpoint (i.e. near the expensive end) — unrealistic for a real catalog,
    where most items are mid-range and only a few are top-of-line. Sampling
    log-uniformly keeps that same [low, high] range but concentrates most
    products toward the cheaper end, matching real product-catalog shape."""
    return math.exp(random.uniform(math.log(low), math.log(high)))


def _pick_region() -> str:
    return _weighted_choice([(w, r) for w, r in REGION_WEIGHTS])


def seed_categories(db: Session) -> list[ProductCategory]:
    categories = []
    for spec in CATEGORY_SPECS:
        category = ProductCategory(name=spec["name"], description=spec["description"])
        db.add(category)
        categories.append(category)
    db.flush()
    return categories


def seed_products(db: Session, categories: list[ProductCategory]) -> list[Product]:
    products: list[Product] = []
    sku_counter = 1000
    variants_needed = max(1, PRODUCT_TARGET // len(CATEGORY_SPECS))
    for category, spec in zip(categories, CATEGORY_SPECS):
        prefix = "".join(w[0] for w in category.name.split() if w[0].isalpha())[:3].upper()
        combos = [(name, variant) for name in spec["names"] for variant in spec["variants"]]
        random.shuffle(combos)
        for name, variant in combos[:variants_needed]:
            sku_counter += 1
            unit_price = round(_log_uniform(*spec["price_band"]), 2)
            cost_price = round(unit_price * random.uniform(0.55, 0.78), 2)
            product = Product(
                sku=f"{prefix}-{sku_counter}",
                name=f"{name}{variant}",
                category_id=category.id,
                unit_price=unit_price,
                cost_price=cost_price,
                unit_of_measure=random.choice(spec["units"]),
                is_active=random.random() > 0.05,
            )
            db.add(product)
            products.append(product)
    db.flush()
    return products


def seed_sales_reps(db: Session) -> list[SalesRep]:
    reps: list[SalesRep] = []
    counts = _apportion(SALES_REP_COUNT, [(w, r) for w, r in REGION_WEIGHTS])
    for region, count in counts.items():
        for _ in range(count):
            name = fake.name()
            rep = SalesRep(
                name=name,
                email=f"{name.lower().replace(' ', '.').replace('.mr.', '').replace('mr.', '')}@salespilot-reps.example.com",
                region=region,
                hire_date=fake.date_between(start_date="-6y", end_date="-1y"),
            )
            db.add(rep)
            reps.append(rep)
    db.flush()
    return reps


def _segment_for_college() -> str:
    return _weighted_choice([(spec["weight"], key) for key, spec in SEGMENT_SPECS.items()])


def seed_colleges(db: Session) -> list[College]:
    colleges: list[College] = []
    used_names: set[str] = set()
    for i in range(COLLEGE_COUNT):
        region = _pick_region()
        state = random.choice(STATES_BY_REGION[region])
        city = random.choice(CITIES_BY_STATE[state])
        segment = _segment_for_college()
        templates = SEGMENT_SPECS[segment]["name_templates"]

        name = None
        for _attempt in range(12):
            candidate = random.choice(templates).format(city=city)
            if candidate not in used_names:
                name = candidate
                used_names.add(candidate)
                break
        if name is None:
            name = f"{city} {segment.replace('_', ' ').title()} Institute #{i + 1}"
            used_names.add(name)

        # ~12% onboarded in the last 90 days (feeds "new customers" KPI),
        # ~15% dormant (churn signal for health scores/recommendations).
        if random.random() < 0.12:
            onboarded_date = fake.date_between(start_date="-85d", end_date="-1d")
        else:
            onboarded_date = fake.date_between(start_date="-6y", end_date="-91d")
        status = "dormant" if random.random() < 0.15 else "active"

        college = College(
            name=name,
            institution_type=segment,
            region=region,
            state=state,
            city=city,
            address=fake.street_address(),
            contact_name=fake.name(),
            contact_email=fake.company_email(),
            contact_phone=fake.phone_number()[:30],
            onboarded_date=onboarded_date,
            status=status,
        )
        db.add(college)
        colleges.append(college)
    db.flush()
    return colleges


def _order_cadence_profile() -> str:
    return _weighted_choice([(0.25, "frequent"), (0.40, "regular"), (0.35, "sporadic")])


def _seasonal_weight(month: int) -> float:
    # Academic-year start (Jun-Jul) and grant/fiscal cycle (Feb-Mar) peaks;
    # a pre-fiscal-year-end push in Nov; a quiet Dec/Jan.
    if month in (6, 7):
        return 1.8
    if month in (2, 3):
        return 1.5
    if month == 11:
        return 1.3
    if month in (12, 1):
        return 0.7
    return 1.0


def seed_orders(db: Session, colleges: list[College], products: list[Product], reps: list[SalesRep]) -> int:
    today = dt.date.today()
    window_start = (today - dt.timedelta(days=ORDER_MONTHS * 30)).replace(day=1)
    total_months = max(
        1,
        (today.year - window_start.year) * 12 + (today.month - window_start.month) + 1,
    )
    order_counter = 0

    reps_by_region: dict[str, list[SalesRep]] = {}
    for rep in reps:
        reps_by_region.setdefault(rep.region, []).append(rep)

    active_products = [p for p in products if p.is_active]
    products_by_category: dict[str, list[Product]] = {}
    for p in active_products:
        products_by_category.setdefault(p.category.name, []).append(p)

    category_weight_options_by_segment = {
        segment: [(w, cat) for cat, w in spec["category_weights"].items()]
        for segment, spec in SEGMENT_SPECS.items()
    }

    def _month_growth_multiplier(month_index: int) -> float:
        if total_months <= 1:
            return (GROWTH_START + GROWTH_END) / 2
        frac = month_index / (total_months - 1)
        return GROWTH_START + (GROWTH_END - GROWTH_START) * frac

    def _pick_line_item(
        segment: str, used_products: set[int], *, cheap_only: bool = False
    ) -> Product | None:
        weighted_cats = category_weight_options_by_segment[segment]
        if cheap_only:
            weighted_cats = [(w, c) for w, c in weighted_cats if c in CHEAP_CATEGORIES] or weighted_cats
        for _attempt in range(6):
            category_name = _weighted_choice(weighted_cats)
            pool = [p for p in products_by_category.get(category_name, []) if p.id not in used_products]
            if pool:
                return random.choice(pool)
        return None

    def _build_order_items(segment: str) -> list[tuple[Product, int, float, float]]:
        """Rolls a size tier first, then picks/quantities line items to land
        near that target subtotal — order value is steered directly instead
        of emerging from unconstrained category/quantity randomness, which
        is what makes the resulting distribution's mean predictable/tunable."""
        lo, hi = _weighted_choice(ORDER_SIZE_TIERS)
        target_total = _log_uniform(lo, hi)
        target_subtotal = target_total / 1.18
        cheap_only = hi <= 40_000

        # Most orders are a single restock/purchase line; multi-line orders
        # (a small basket, or an occasional bundled capital purchase) are
        # the minority — matches how institutional procurement actually works.
        n_items = int(_weighted_choice([(0.80, 1), (0.18, 2), (0.02, 3)]))

        used_products: set[int] = set()
        items_payload: list[tuple[Product, int, float, float]] = []
        remaining_slots = n_items
        remaining_target = target_subtotal
        for _ in range(n_items):
            share = remaining_target / remaining_slots
            product = _pick_line_item(segment, used_products, cheap_only=cheap_only)
            remaining_slots -= 1
            if product is None:
                continue
            used_products.add(product.id)
            price = float(product.unit_price)
            quantity = max(1, min(500, round(share / price)))
            line_discount = round(random.uniform(0, 3), 2)
            line_total = round(price * quantity * (1 - line_discount / 100), 2)
            items_payload.append((product, quantity, line_discount, line_total))
            remaining_target -= line_total

        # Rounding a real product's quantity to hit a continuous target
        # rarely drifts far, but clamp back inside bounds defensively so
        # this holds even for an unlucky combination of prices/rounding.
        def _subtotal() -> float:
            return round(sum(t[3] for t in items_payload), 2)

        guard = 0
        while _subtotal() * 1.18 > MAX_ORDER_VALUE and guard < 12 and items_payload:
            items_payload.sort(key=lambda t: t[3], reverse=True)
            product, quantity, line_discount, _line_total = items_payload[0]
            if quantity > 1:
                new_quantity = max(1, quantity // 2)
                new_line_total = round(float(product.unit_price) * new_quantity * (1 - line_discount / 100), 2)
                items_payload[0] = (product, new_quantity, line_discount, new_line_total)
            elif len(items_payload) > 1:
                items_payload.pop(0)
            else:
                break
            guard += 1

        guard = 0
        while _subtotal() * 1.18 < MIN_ORDER_VALUE and guard < 6:
            product = _pick_line_item(segment, used_products, cheap_only=cheap_only)
            if product is None:
                break
            used_products.add(product.id)
            price = float(product.unit_price)
            quantity = max(1, round((MIN_ORDER_VALUE / 1.18 - _subtotal()) / price))
            line_discount = round(random.uniform(0, 3), 2)
            line_total = round(price * quantity * (1 - line_discount / 100), 2)
            items_payload.append((product, quantity, line_discount, line_total))
            guard += 1

        return items_payload

    for college in colleges:
        segment = college.institution_type
        spec = SEGMENT_SPECS[segment]
        profile = _order_cadence_profile()
        profile_multiplier = {"frequent": 1.6, "regular": 1.0, "sporadic": 0.45}[profile]
        # Divisor calibrated so ~520 colleges over 24 months land at 20,000+
        # orders once seasonal/growth/dormant-cutoff factors are applied —
        # see the seeding calibration note in the module docstring's caller.
        base_orders_per_month = spec["cadence_per_month"] * profile_multiplier / 1.55

        if college.status == "dormant":
            cutoff_days_ago = random.randint(190, 480)
            college_last_order = today - dt.timedelta(days=cutoff_days_ago)
        else:
            college_last_order = today

        region_reps = reps_by_region.get(college.region) or reps
        rep = random.choice(region_reps)

        month_cursor = window_start
        month_index = 0
        while month_cursor <= today:
            if month_cursor > college_last_order:
                break
            seasonal = _seasonal_weight(month_cursor.month)
            growth = _month_growth_multiplier(month_index)
            expected_orders = base_orders_per_month * seasonal * growth
            n_orders = max(0, round(random.gauss(expected_orders, expected_orders * 0.4)))

            for _ in range(n_orders):
                day_offset = random.randint(0, 27)
                order_date = month_cursor.replace(day=1) + dt.timedelta(days=day_offset)
                if order_date > today or order_date > college_last_order:
                    continue

                items_payload = _build_order_items(segment)
                if not items_payload:
                    continue

                subtotal = round(sum(t[3] for t in items_payload), 2)
                order_discount = round(random.uniform(0, 5), 2)
                if random.random() < spec["discount_bump_chance"]:
                    order_discount = round(order_discount + random.uniform(*spec["discount_bump_range"]), 2)
                tax_amount = round(subtotal * 0.18, 2)
                total_amount = round(subtotal + tax_amount, 2)

                payment_status = _weighted_choice(spec["payment_profile"])
                payment_due_date = order_date + dt.timedelta(days=30)
                payment_received_date = None
                if payment_status == "paid":
                    delay = random.randint(*spec["payment_delay_range"])
                    payment_received_date = min(payment_due_date + dt.timedelta(days=delay), today)
                    if payment_received_date < order_date:
                        payment_received_date = order_date

                order_counter += 1
                order = Order(
                    order_number=f"ORD-{order_date.year}-{order_counter:06d}",
                    college_id=college.id,
                    sales_rep_id=rep.id,
                    order_date=order_date,
                    status="fulfilled" if payment_status != "overdue" else random.choice(["fulfilled", "pending"]),
                    payment_status=payment_status,
                    payment_due_date=payment_due_date,
                    payment_received_date=payment_received_date,
                    discount_pct=order_discount,
                    subtotal=subtotal,
                    tax_amount=tax_amount,
                    total_amount=total_amount,
                )
                db.add(order)
                db.flush()

                for product, quantity, line_discount, line_total in items_payload:
                    db.add(
                        OrderItem(
                            order_id=order.id,
                            product_id=product.id,
                            quantity=quantity,
                            unit_price=product.unit_price,
                            discount_pct=line_discount,
                            line_total=line_total,
                        )
                    )

            if month_cursor.month == 12:
                month_cursor = month_cursor.replace(year=month_cursor.year + 1, month=1)
            else:
                month_cursor = month_cursor.replace(month=month_cursor.month + 1)
            month_index += 1

    db.flush()
    print(f"Seeded {order_counter} orders")
    return order_counter


def reset_data(db: Session) -> None:
    db.execute(
        text(
            "TRUNCATE TABLE order_items, orders, predictions, customer_health_scores, "
            "model_registry, products, product_categories, sales_reps, colleges "
            "RESTART IDENTITY CASCADE"
        )
    )
    db.commit()


def seed_all(db: Session) -> None:
    print("Seeding product categories & products...")
    categories = seed_categories(db)
    products = seed_products(db, categories)
    print(f"  {len(categories)} categories, {len(products)} products")

    print("Seeding sales reps...")
    reps = seed_sales_reps(db)
    print(f"  {len(reps)} sales reps")

    print("Seeding colleges...")
    colleges = seed_colleges(db)
    print(f"  {len(colleges)} colleges")

    print("Seeding orders (this can take a little while)...")
    seed_orders(db, colleges, products, reps)

    db.commit()


def bootstrap_if_empty(db: Session) -> bool:
    """Called from `app.main`'s startup lifespan. Returns True if it seeded
    anything. Safe to call on every startup — it's a no-op once data exists."""
    if db.query(College).count() > 0:
        return False

    print("Empty database detected — running full auto-seed...")
    seed_all(db)

    print("Seeding demo user accounts...")
    seed_users.seed_default_users(db)

    print("Computing initial customer health scores...")
    HealthScoreService(db).recalculate()

    print(
        "Auto-seed complete. Purchase-probability predictions and SHAP "
        "explanations still need `POST /ml/retrain` (admin/sales_manager) "
        "against this data before the Explainability/Sales Opportunities "
        "pages have model output."
    )
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reset", action="store_true", help="Truncate existing data before seeding")
    parser.add_argument(
        "--skip-health",
        action="store_true",
        help="Skip the health-score recalculation pass after seeding (useful while calibrating order volume).",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        existing = db.query(College).count()
        if existing and not args.reset:
            print(f"Database already has {existing} colleges. Pass --reset to re-seed.")
            return
        if args.reset:
            reset_data(db)

        seed_all(db)

        if not args.skip_health:
            print("Computing customer health scores...")
            HealthScoreService(db).recalculate()

        print("Done.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
