"""Seed two tenants with distinct catalogs and approved documents.

Run with:  python -m agriconnect.seed   (drops and recreates all tables)

All content here is synthetic / original, with simulated prices and stock,
matching the proposal's data plan (no real customer data is used).
"""
from __future__ import annotations
import time

from . import db

TENANTS = [
    ("greenharvest", "GreenHarvest Agri Supplies"),
    ("farmdirect", "FarmDirect Co-op"),
]

# (sku, name, category, price, stock, unit, description)
PRODUCTS = {
    "greenharvest": [
        ("GH-SEED-001", "Hybrid Maize Seed H614", "Seeds", 230.0, 180, "2kg bag", "High-yield drought-tolerant hybrid maize seed for medium-altitude zones."),
        ("GH-SEED-002", "Hybrid Maize Seed H628", "Seeds", 255.0, 95, "2kg bag", "Late-maturing hybrid maize for high-rainfall highland areas."),
        ("GH-SEED-003", "Bean Seed Rosecoco", "Seeds", 180.0, 240, "2kg bag", "Certified rosecoco bush bean seed, good for intercropping with maize."),
        ("GH-SEED-004", "Sorghum Seed Gadam", "Seeds", 140.0, 70, "1kg bag", "Early-maturing sorghum variety suited to dry, semi-arid conditions."),
        ("GH-SEED-005", "Kale Sukuma Wiki Seed", "Seeds", 90.0, 300, "250g pack", "Fast-growing collard greens seed for continuous leaf harvest."),
        ("GH-SEED-006", "Tomato Seed Rio Grande", "Seeds", 350.0, 60, "50g pack", "Determinate processing tomato with firm fruit and good shelf life."),
        ("GH-FERT-001", "NPK 23:23:0 Fertilizer", "Fertilizer", 3200.0, 120, "50kg bag", "Balanced planting fertilizer for cereals; apply at sowing."),
        ("GH-FERT-002", "CAN Topdress Fertilizer", "Fertilizer", 2850.0, 140, "50kg bag", "Calcium ammonium nitrate for topdressing maize at knee height."),
        ("GH-FERT-003", "DAP Fertilizer", "Fertilizer", 3600.0, 0, "50kg bag", "Di-ammonium phosphate planting fertilizer, high phosphorus."),
        ("GH-FERT-004", "Foliar Feed Micromix", "Fertilizer", 650.0, 85, "1L bottle", "Chelated micronutrient foliar spray for vegetables."),
        ("GH-PEST-001", "Pyrethrin Insecticide", "Pesticides", 780.0, 65, "500ml bottle", "Contact insecticide for aphids and caterpillars on vegetables."),
        ("GH-PEST-002", "Fall Armyworm Control FAW-Stop", "Pesticides", 1150.0, 40, "250ml bottle", "Systemic control for fall armyworm in maize; observe label rates."),
        ("GH-PEST-003", "Copper Fungicide", "Pesticides", 540.0, 110, "500g pack", "Protective fungicide for blight on tomatoes and potatoes."),
        ("GH-PEST-004", "Glyphosate Herbicide", "Pesticides", 920.0, 75, "1L bottle", "Non-selective herbicide for land preparation before planting."),
        ("GH-TOOL-001", "Knapsack Sprayer 16L", "Tools", 2400.0, 30, "unit", "Manual 16-litre knapsack sprayer with adjustable nozzle."),
        ("GH-TOOL-002", "Hand Hoe Jembe", "Tools", 650.0, 200, "unit", "Forged steel jembe with hardwood handle."),
        ("GH-TOOL-003", "Pruning Secateurs", "Tools", 480.0, 90, "unit", "Bypass pruning shears for orchard and vegetable work."),
        ("GH-TOOL-004", "Garden Rake 14-tooth", "Tools", 560.0, 55, "unit", "Steel bow rake for seedbed preparation."),
        ("GH-IRR-001", "Drip Line 16mm", "Irrigation", 32.0, 5000, "metre", "Inline dripper tape, 30cm spacing, for row crops."),
        ("GH-IRR-002", "Drip Kit 1/8 acre", "Irrigation", 18500.0, 12, "kit", "Complete gravity drip kit covering an eighth of an acre."),
        ("GH-IRR-003", "Water Storage Tank 1000L", "Irrigation", 12500.0, 18, "unit", "UV-stabilised polyethylene tank for irrigation storage."),
        ("GH-IRR-004", "Rain Gauge", "Irrigation", 850.0, 45, "unit", "Manual rainfall gauge for on-farm records."),
        ("GH-SEED-007", "Onion Seed Red Creole", "Seeds", 420.0, 50, "100g pack", "Pungent red storage onion with good keeping quality."),
        ("GH-SEED-008", "Watermelon Seed Sukari F1", "Seeds", 1600.0, 25, "50g pack", "Sweet hybrid watermelon with high field tolerance."),
        ("GH-FERT-005", "Organic Compost", "Fertilizer", 450.0, 160, "25kg bag", "Composted farmyard manure for soil conditioning."),
        ("GH-PEST-005", "Sticky Traps Yellow", "Pesticides", 320.0, 130, "pack of 10", "Yellow sticky traps for monitoring whitefly and aphids."),
    ],
    "farmdirect": [
        ("FD-SEED-101", "Certified Potato Seed Shangi", "Seeds", 3800.0, 60, "50kg bag", "Popular fast-cooking potato variety, certified clean seed."),
        ("FD-SEED-102", "Wheat Seed Robin", "Seeds", 2600.0, 80, "50kg bag", "Rust-resistant bread wheat for highland cropping."),
        ("FD-SEED-103", "Barley Seed Grace", "Seeds", 2450.0, 40, "50kg bag", "Malting barley variety grown on contract."),
        ("FD-SEED-104", "Green Gram Seed N26", "Seeds", 260.0, 150, "2kg bag", "Early-maturing green gram for dryland rotation."),
        ("FD-FERT-101", "NPK 17:17:17 Fertilizer", "Fertilizer", 3400.0, 100, "50kg bag", "General-purpose compound fertilizer for mixed farming."),
        ("FD-FERT-102", "Urea 46% N", "Fertilizer", 3100.0, 0, "50kg bag", "High-nitrogen topdressing fertilizer."),
        ("FD-FERT-103", "Gypsum Soil Conditioner", "Fertilizer", 1200.0, 70, "50kg bag", "Calcium sulphate for sodic soil correction."),
        ("FD-PEST-101", "Metalaxyl Fungicide", "Pesticides", 980.0, 55, "500g pack", "Systemic fungicide for late blight in potatoes."),
        ("FD-PEST-102", "Imidacloprid Insecticide", "Pesticides", 1250.0, 35, "250ml bottle", "Systemic insecticide for sucking pests."),
        ("FD-TOOL-101", "Ox Plough", "Tools", 8900.0, 8, "unit", "Mouldboard ox-drawn plough for primary tillage."),
        ("FD-TOOL-102", "Wheelbarrow Heavy Duty", "Tools", 4800.0, 22, "unit", "Reinforced wheelbarrow with pneumatic tyre."),
        ("FD-TOOL-103", "Grain Moisture Meter", "Tools", 6500.0, 10, "unit", "Handheld meter for safe grain storage moisture."),
        ("FD-IRR-101", "Sprinkler Head Brass", "Irrigation", 420.0, 300, "unit", "Impact sprinkler head for overhead irrigation."),
        ("FD-IRR-102", "Lay-flat Hose 2 inch", "Irrigation", 95.0, 2000, "metre", "Lay-flat delivery hose for pumped irrigation."),
        ("FD-IRR-103", "Water Pump 3HP Petrol", "Irrigation", 28500.0, 6, "unit", "Petrol centrifugal pump for furrow irrigation."),
        ("FD-SEED-105", "Sunflower Seed Hysun", "Seeds", 1400.0, 30, "5kg bag", "Hybrid oil sunflower grown on contract for crushing."),
        ("FD-SEED-106", "Lucerne Pasture Seed", "Seeds", 2200.0, 25, "5kg bag", "Perennial fodder legume for dairy farms."),
        ("FD-FERT-104", "Foliar Calcium Nitrate", "Fertilizer", 720.0, 60, "1L bottle", "Foliar calcium to reduce blossom-end rot."),
        ("FD-PEST-103", "Rodent Bait Blocks", "Pesticides", 380.0, 140, "pack", "Wax bait blocks for grain-store rodent control."),
        ("FD-TOOL-104", "Tarpaulin 6x8m", "Tools", 2600.0, 45, "unit", "Heavy tarpaulin for grain drying and covering."),
        ("FD-IRR-104", "Pressure Tank 24L", "Irrigation", 7800.0, 14, "unit", "Pressure vessel for booster pump systems."),
        ("FD-SEED-107", "Napier Grass Splits", "Seeds", 15.0, 4000, "split", "Fodder napier grass planting material."),
        ("FD-FERT-105", "Sulphate of Ammonia", "Fertilizer", 2900.0, 50, "50kg bag", "Acidifying nitrogen fertilizer for tea and pasture."),
        ("FD-TOOL-105", "Grain Storage Bag Hermetic", "Tools", 350.0, 500, "unit", "Triple-layer hermetic bag for pest-free grain storage."),
    ],
}

# (title, source, body)  -- body split into paragraphs = chunks
DOCUMENTS = {
    "greenharvest": [
        ("Maize Seed Planting Guide", "greenharvest-maize-guide-v2.pdf",
         "Hybrid maize should be planted at the onset of reliable rains, when the "
         "soil is moist to at least a hand's depth. Plant two seeds per hole and "
         "thin to one healthy seedling after emergence.\n\n"
         "Recommended spacing is 75 cm between rows and 25 cm within the row, "
         "giving about 53,000 plants per hectare. Apply NPK 23:23:0 planting "
         "fertilizer at sowing, placed below the seed and covered with soil.\n\n"
         "Topdress with CAN when the maize reaches knee height, usually four to "
         "six weeks after planting, and again at tasseling if rainfall allows. "
         "Keep the field weed-free for the first six weeks, which is the period "
         "most critical for yield."),
        ("Fertilizer Application Rates", "greenharvest-fertilizer-rates.pdf",
         "For cereals, apply one 50 kg bag of NPK 23:23:0 per acre at planting. "
         "Place the fertilizer in the furrow and cover lightly before dropping "
         "the seed to avoid direct contact that can scorch the germ.\n\n"
         "Topdressing uses CAN at one 50 kg bag per acre, applied as a band "
         "beside the rows when the crop is actively growing and the soil is "
         "moist. Do not topdress onto dry soil, as the nitrogen can be lost.\n\n"
         "For vegetables, foliar micronutrient feeds are applied every two weeks "
         "during active growth. Always follow the dilution rate printed on the "
         "product label."),
        ("Pesticide Safety and Handling", "greenharvest-pesticide-safety.pdf",
         "Always wear gloves, a mask, and protective clothing when mixing or "
         "spraying pesticides. Mix only the quantity you will use in one session "
         "and never store diluted spray overnight.\n\n"
         "Observe the pre-harvest interval printed on every product label; this "
         "is the minimum number of days that must pass between the last spray "
         "and harvest. For most vegetable insecticides this is seven days.\n\n"
         "Triple-rinse empty containers and puncture them before disposal. Keep "
         "all pesticides locked away from children, food, and animal feed."),
        ("Storage and Shelf Life", "greenharvest-storage-shelf-life.pdf",
         "Store seed in a cool, dry place off the ground and away from direct "
         "sunlight. Certified seed retains good germination for one planting "
         "season; do not carry opened seed over to the next year.\n\n"
         "Fertilizer must be kept dry and sealed, as it absorbs moisture and "
         "hardens when exposed to humid air. Stack bags on pallets, not directly "
         "on a concrete floor.\n\n"
         "Treated seed is poisonous and must never be eaten or fed to animals. "
         "Keep it clearly separated from grain meant for food."),
        ("Delivery and Returns Policy", "greenharvest-delivery-policy.pdf",
         "Orders placed before noon are dispatched the same day for delivery "
         "within two business days inside the main service area. Delivery outside "
         "the main area takes three to five business days.\n\n"
         "Unopened products in their original packaging may be returned within "
         "fourteen days for a full refund or exchange. Seed, fertilizer, and "
         "pesticides cannot be returned once opened, for safety and quality "
         "reasons.\n\n"
         "If a product arrives damaged, report it within forty-eight hours with "
         "a photograph and we will replace it at no cost."),
    ],
    "farmdirect": [
        ("Drip Irrigation Setup", "farmdirect-drip-setup.pdf",
         "A gravity drip kit works from a tank raised at least one metre above "
         "the field. Connect the mainline to the tank outlet, lay the drip lines "
         "along each crop row, and flush the system before fitting the end caps.\n\n"
         "Run the system for a short test and walk the lines to check that every "
         "dripper is wetting the soil evenly. Clean the filter weekly, as "
         "sediment is the most common cause of blocked drippers.\n\n"
         "For most vegetables, irrigate for one to two hours in the early "
         "morning. Adjust the duration by checking soil moisture at root depth "
         "rather than at the surface."),
        ("Co-op Membership and Pricing", "farmdirect-membership-pricing.pdf",
         "FarmDirect Co-op members receive contract pricing on seed and "
         "fertilizer and are paid for produce delivered to the aggregation "
         "centre. Membership is open to registered farmers within the catchment.\n\n"
         "Members order inputs on credit against their expected harvest, up to a "
         "limit set each season by the committee. Repayment is deducted at the "
         "point of produce delivery.\n\n"
         "Grain delivered for storage must meet the moisture standard of "
         "thirteen percent or below. Deliveries above this are dried at a fee "
         "before they are accepted into the store."),
        ("Grain Storage Guide", "farmdirect-grain-storage.pdf",
         "Dry grain to thirteen percent moisture or less before storage; this is "
         "the single most important step in preventing mould and insect damage. "
         "Use a moisture meter rather than guessing.\n\n"
         "Hermetic storage bags cut off oxygen and control storage pests without "
         "chemicals when they are sealed correctly. Inspect bags for punctures "
         "before filling and tie them tightly.\n\n"
         "Keep the store clean, ventilated, and free of last season's grain, "
         "which is a common source of carry-over infestation."),
    ],
}


def seed() -> None:
    db.init_db(reset=True)
    conn = db.get_conn()
    now = time.time()
    try:
        for tid, name in TENANTS:
            conn.execute("INSERT INTO tenants (id, name) VALUES (?, ?)", (tid, name))
        for tid, rows in PRODUCTS.items():
            for sku, pname, cat, price, stock, unit, desc in rows:
                conn.execute(
                    "INSERT INTO products (tenant_id, sku, name, category, price, stock, unit, description)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (tid, sku, pname, cat, price, stock, unit, desc),
                )
        for tid, docs in DOCUMENTS.items():
            for title, source, body in docs:
                cur = conn.execute(
                    "INSERT INTO documents (tenant_id, title, source, created_at) VALUES (?, ?, ?, ?)",
                    (tid, title, source, now),
                )
                doc_id = cur.lastrowid
                for ord_, para in enumerate(p.strip() for p in body.split("\n\n")):
                    if para:
                        conn.execute(
                            "INSERT INTO chunks (tenant_id, document_id, ord, text) VALUES (?, ?, ?, ?)",
                            (tid, doc_id, ord_, para),
                        )
        conn.commit()
    finally:
        conn.close()

    # report
    for tid, name in TENANTS:
        print(f"  {name:28s}  products={db.count_products(tid):3d}")
    total = sum(len(v) for v in PRODUCTS.values())
    print(f"Seeded {len(TENANTS)} tenants, {total} products, "
          f"{sum(len(v) for v in DOCUMENTS.values())} documents.")


if __name__ == "__main__":
    seed()
