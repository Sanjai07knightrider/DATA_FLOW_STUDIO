"""
Module 3: Synthetic Data Generation
=====================================
Generates realistic but entirely fabricated sample records using the
cleaned dataset as a structural reference.

Key principles:
  - Uses Faker for random, realistic-looking values.
  - Reproducible with a configurable seed.
  - All generated records are clearly labelled as SYNTHETIC.
  - Does NOT copy any personal information from real records.
  - Column names and data types mirror the cleaned dataset.
  - Exports synthetic records to a separate CSV file.
"""

import logging
import random
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SYNTHETIC_OUTPUT_CSV = OUTPUT_DIR / "synthetic_data.csv"

# ─────────────────────────── Static vocabulary pools ─────────────────────────
HOTEL_PREFIXES = [
    "The", "Royal", "Grand", "Golden", "Silver", "Blue", "Green", "Serene",
    "Pacific", "Imperial", "Crystal", "Lotus", "Orchid", "Pearl", "Mystic",
    "Horizon", "Premier", "Tranquil", "Sunrise", "Sunset",
]
HOTEL_SUFFIXES = [
    "Hotel", "Inn", "Resort", "Lodge", "Retreat", "Suites", "Residency",
    "Stays", "Villas", "Haveli", "Palace", "Manor", "Bungalow", "Cottage",
]
CATEGORIES = [
    "Luxury", "Budget", "Business", "Resort", "Heritage", "Eco-Stay",
    "Boutique", "Adventure", "Transit", "Capsule Hotel", "Unique Stay", "Camp",
]
LOCATIONS = [
    "Mumbai, Maharashtra, India",
    "Bengaluru, Karnataka, India",
    "Goa, India",
    "Jaipur, Rajasthan, India",
    "Hyderabad, Telangana, India",
    "Ooty, Tamil Nadu, India",
    "Delhi, India",
    "Alleppey, Kerala, India",
    "Manali, Himachal Pradesh, India",
    "Chennai, Tamil Nadu, India",
    "Jaisalmer, Rajasthan, India",
    "Pondicherry, India",
    "Agra, Uttar Pradesh, India",
    "Varanasi, Uttar Pradesh, India",
    "Shimla, Himachal Pradesh, India",
    "Darjeeling, West Bengal, India",
    "Mysuru, Karnataka, India",
    "Udaipur, Rajasthan, India",
    "Coorg, Karnataka, India",
    "Andaman Islands, India",
]
AMENITY_POOL = [
    "WiFi", "Pool", "Spa", "Gym", "Restaurant", "Bar", "Parking",
    "Breakfast", "24hr Reception", "AC", "Lounge", "Garden",
    "Conference Room", "Bonfire", "Cycling", "Terrace", "Beach Access",
    "Water Sports", "Nature Walks", "Organic Meals",
]
DESCRIPTION_TEMPLATES = [
    "A {adj} {cat} property located in {loc}. Offers {amen} and a memorable stay experience.",
    "Experience the best of {loc} at this {adj} {cat}. Amenities include {amen}.",
    "Nestled in {loc}, this {cat} provides {adj} comfort with {amen}.",
    "Discover {adj} hospitality at our {cat} in {loc}. Guests enjoy {amen}.",
    "A popular {cat} destination in {loc} known for {adj} service and {amen}.",
]
ADJECTIVES = [
    "modern", "cozy", "luxurious", "affordable", "serene",
    "vibrant", "peaceful", "premium", "eco-friendly", "traditional",
]


def _random_amenities(rng: random.Random, min_count: int = 2, max_count: int = 5) -> str:
    count = rng.randint(min_count, max_count)
    return ", ".join(rng.sample(AMENITY_POOL, count))


def _random_description(rng: random.Random, category: str, location: str, amenities: str) -> str:
    template = rng.choice(DESCRIPTION_TEMPLATES)
    amenity_short = amenities.split(",")[0].strip()
    return template.format(
        adj=rng.choice(ADJECTIVES),
        cat=category.lower(),
        loc=location,
        amen=amenity_short,
    )


def _random_email(hotel_name: str, rng: random.Random) -> str:
    """Generate a clearly-fake @synthetic.example.com email — never a real address."""
    slug = hotel_name.lower().replace(" ", "").replace("'", "")[:12]
    num = rng.randint(100, 999)
    prefixes = ["info", "book", "stay", "reservations", "contact"]
    prefix = rng.choice(prefixes)
    return f"{prefix}{num}@{slug}.synthetic.example.com"


# ─────────────────────────── Generator ──────────────────────────────────────
def generate_synthetic_data(
    reference_df: pd.DataFrame,
    n_records: int = 20,
    seed: int = 42,
    output_path: Path = SYNTHETIC_OUTPUT_CSV,
) -> pd.DataFrame:
    """
    Generate n_records synthetic hotel records using the cleaned DataFrame
    as a structural reference.

    Args:
        reference_df: Cleaned DataFrame — used for schema reference only.
        n_records:    How many synthetic records to create (default: 20).
        seed:         Random seed for reproducibility (default: 42).
        output_path:  CSV export destination.

    Returns:
        DataFrame of synthetic records (each labelled record_type=SYNTHETIC).
    """
    if reference_df is None or reference_df.empty:
        logger.warning("Reference DataFrame is empty. Generating using defaults.")
        price_range = (1000, 10000)
        rating_range = (3.0, 5.0)
    else:
        # Derive plausible ranges from real data
        if "price_inr" in reference_df.columns:
            prices = pd.to_numeric(reference_df["price_inr"], errors="coerce").dropna()
            price_range = (int(prices.min()), int(prices.max())) if not prices.empty else (1000, 10000)
        else:
            price_range = (1000, 10000)

        if "rating" in reference_df.columns:
            ratings = pd.to_numeric(reference_df["rating"], errors="coerce").dropna()
            rating_range = (float(ratings.min()), float(ratings.max())) if not ratings.empty else (3.0, 5.0)
        else:
            rating_range = (3.0, 5.0)

    rng = random.Random(seed)
    records = []

    for i in range(n_records):
        prefix = rng.choice(HOTEL_PREFIXES)
        suffix = rng.choice(HOTEL_SUFFIXES)
        hotel_name = f"{prefix} {suffix}"

        category = rng.choice(CATEGORIES)
        location = rng.choice(LOCATIONS)
        amenities = _random_amenities(rng)
        description = _random_description(rng, category, location, amenities)

        price = rng.randint(price_range[0], price_range[1])
        # Round to nearest 100
        price = round(price / 100) * 100

        rating = round(rng.uniform(rating_range[0], rating_range[1]), 1)
        reviews = rng.randint(50, 5000)
        contact_email = _random_email(hotel_name, rng)

        records.append({
            "hotel_name": hotel_name,
            "category": category,
            "location": location,
            "description": description,
            "price_inr": price,
            "rating": rating,
            "reviews": reviews,
            "amenities": amenities,
            "availability": rng.choice(["Available", "Available", "Limited", "Sold Out"]),
            "contact_email": contact_email,
            "record_type": "SYNTHETIC",   # ← clear label
            "synthetic_seed": seed,
            "synthetic_index": i + 1,
        })

    df = pd.DataFrame(records)
    df.to_csv(output_path, index=False)
    logger.info(
        "Synthetic data: %d records (seed=%d) saved to %s",
        len(df), seed, output_path,
    )
    return df


def get_synthetic_summary(df: pd.DataFrame) -> dict:
    """Return a summary dictionary for the synthetic dataset."""
    if df.empty:
        return {"error": "Empty synthetic dataset"}

    return {
        "total_records": len(df),
        "categories": df["category"].value_counts().to_dict(),
        "price_min": int(df["price_inr"].min()),
        "price_max": int(df["price_inr"].max()),
        "price_mean": round(float(df["price_inr"].mean()), 2),
        "rating_min": float(df["rating"].min()),
        "rating_max": float(df["rating"].max()),
        "rating_mean": round(float(df["rating"].mean()), 2),
        "label": "SYNTHETIC — not real data",
    }


if __name__ == "__main__":
    # Quick standalone demo
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from data_collection import load_fallback_csv
    from data_cleaning import clean_data

    raw = load_fallback_csv()
    clean_df, _ = clean_data(raw)
    syn_df = generate_synthetic_data(clean_df, n_records=10, seed=42)
    print(f"Generated {len(syn_df)} synthetic records.")
    print(syn_df[["hotel_name", "category", "price_inr", "rating", "record_type"]].to_string())
