"""AI Persona Selector - selects the most relevant personas for a given product."""

import math
import random

from src.personas.schema import (
    InterestCategory,
    Persona,
    PriceSensitivity,
    PurchaseTendency,
    ReactionPattern,
)

# Product category keyword mapping to InterestCategory
CATEGORY_KEYWORD_MAP: dict[str, InterestCategory] = {
    # health
    "건강식품": InterestCategory.HEALTH,
    "비타민": InterestCategory.HEALTH,
    "영양제": InterestCategory.HEALTH,
    "건강": InterestCategory.HEALTH,
    "헬스": InterestCategory.HEALTH,
    "운동": InterestCategory.HEALTH,
    "의약품": InterestCategory.HEALTH,
    # electronics
    "전자기기": InterestCategory.ELECTRONICS,
    "가전": InterestCategory.ELECTRONICS,
    "IT": InterestCategory.ELECTRONICS,
    "컴퓨터": InterestCategory.ELECTRONICS,
    "스마트폰": InterestCategory.ELECTRONICS,
    "디지털": InterestCategory.ELECTRONICS,
    "테크": InterestCategory.ELECTRONICS,
    # fashion
    "패션": InterestCategory.FASHION,
    "의류": InterestCategory.FASHION,
    "신발": InterestCategory.FASHION,
    "액세서리": InterestCategory.FASHION,
    "옷": InterestCategory.FASHION,
    "가방": InterestCategory.FASHION,
    # food
    "식품": InterestCategory.FOOD,
    "간식": InterestCategory.FOOD,
    "음료": InterestCategory.FOOD,
    "먹거리": InterestCategory.FOOD,
    "요리": InterestCategory.FOOD,
    "식재료": InterestCategory.FOOD,
    # hobby
    "취미": InterestCategory.HOBBY,
    "게임": InterestCategory.HOBBY,
    "여행": InterestCategory.HOBBY,
    "레저": InterestCategory.HOBBY,
    "캠핑": InterestCategory.HOBBY,
    "스포츠": InterestCategory.HOBBY,
    # home
    "인테리어": InterestCategory.HOME,
    "가구": InterestCategory.HOME,
    "생활용품": InterestCategory.HOME,
    "주방": InterestCategory.HOME,
    "홈": InterestCategory.HOME,
    "리빙": InterestCategory.HOME,
}

# Related interest categories (secondary matches)
RELATED_CATEGORIES: dict[InterestCategory, list[InterestCategory]] = {
    InterestCategory.HEALTH: [InterestCategory.FOOD, InterestCategory.HOBBY],
    InterestCategory.ELECTRONICS: [InterestCategory.HOBBY],
    InterestCategory.FASHION: [InterestCategory.HOBBY],
    InterestCategory.FOOD: [InterestCategory.HEALTH, InterestCategory.HOME],
    InterestCategory.HOBBY: [InterestCategory.ELECTRONICS, InterestCategory.FASHION],
    InterestCategory.HOME: [InterestCategory.FOOD],
}

# Challenger reaction patterns (used for stress-testing a strategy)
CHALLENGER_PATTERNS = {ReactionPattern.SKEPTICAL, ReactionPattern.DEFENSIVE, ReactionPattern.IMPATIENT}


def _match_category(product_category: str) -> InterestCategory | None:
    """Match a Korean product category string to an InterestCategory."""
    normalized = product_category.strip().lower()
    # Direct enum value match
    for cat in InterestCategory:
        if cat.value == normalized:
            return cat
    # Keyword match
    for keyword, category in CATEGORY_KEYWORD_MAP.items():
        if keyword in normalized or normalized in keyword:
            return category
    return None


def select_personas(
    personas: list[Persona],
    product_category: str,
    product_price: float = 0.0,
    count: int = 10,
    include_challengers: bool = True,
) -> list[Persona]:
    """Select the most relevant personas for a given product.

    Selection strategy:
    - 60% primary match: personas whose interest_category matches or is related
    - 20% challengers: skeptical, defensive, or high price_sensitivity
    - 20% diverse fill: random from remaining, ensuring generation diversity
    """
    if count >= len(personas):
        return list(personas)

    matched_category = _match_category(product_category)
    related_categories = RELATED_CATEGORIES.get(matched_category, []) if matched_category else []

    # Calculate slot counts
    primary_count = math.ceil(count * 0.6)
    challenger_count = math.floor(count * 0.2) if include_challengers else 0
    diverse_count = count - primary_count - challenger_count

    selected: list[Persona] = []
    used_ids: set[str] = set()

    # --- 1. Primary match (60%) ---
    primary_exact = []
    primary_related = []
    for p in personas:
        if matched_category and p.interest_category == matched_category:
            primary_exact.append(p)
        elif p.interest_category in related_categories:
            primary_related.append(p)

    random.shuffle(primary_exact)
    random.shuffle(primary_related)

    # Fill primary slots: exact matches first, then related
    for p in primary_exact:
        if len(selected) >= primary_count:
            break
        selected.append(p)
        used_ids.add(p.id)

    for p in primary_related:
        if len(selected) >= primary_count:
            break
        if p.id not in used_ids:
            selected.append(p)
            used_ids.add(p.id)

    # --- 2. Challenger personas (20%) ---
    if include_challengers and challenger_count > 0:
        challengers = [
            p
            for p in personas
            if p.id not in used_ids
            and (
                p.reaction_pattern in CHALLENGER_PATTERNS
                or p.price_sensitivity == PriceSensitivity.HIGH
            )
        ]
        random.shuffle(challengers)
        for p in challengers:
            if len(selected) >= primary_count + challenger_count:
                break
            selected.append(p)
            used_ids.add(p.id)

    # --- 3. Diverse fill (20%) - ensure generation diversity ---
    remaining = [p for p in personas if p.id not in used_ids]
    # Group remaining by generation for diversity
    by_generation: dict[str, list[Persona]] = {}
    for p in remaining:
        gen = p.generation.value
        by_generation.setdefault(gen, []).append(p)

    # Shuffle within each generation group
    for gen_list in by_generation.values():
        random.shuffle(gen_list)

    # Round-robin pick from each generation to ensure diversity
    target_total = count
    generations = list(by_generation.keys())
    random.shuffle(generations)
    gen_idx = 0
    while len(selected) < target_total and any(by_generation.values()):
        gen_key = generations[gen_idx % len(generations)]
        if by_generation.get(gen_key):
            p = by_generation[gen_key].pop()
            selected.append(p)
            used_ids.add(p.id)
        gen_idx += 1
        # Remove empty generations
        generations = [g for g in generations if by_generation.get(g)]
        if not generations:
            break

    return selected[:count]


def _infer_categories_from_text(text: str) -> list[InterestCategory]:
    """Infer interest categories from product name/description using keyword matching."""
    categories: list[InterestCategory] = []
    seen: set[InterestCategory] = set()
    normalized = text.lower()
    for keyword, category in CATEGORY_KEYWORD_MAP.items():
        if keyword in normalized and category not in seen:
            categories.append(category)
            seen.add(category)
    return categories


def _infer_purchase_tendencies(
    product_price: float,
    product_description: str,
) -> list[PurchaseTendency]:
    """Infer relevant purchase tendencies based on price and description."""
    tendencies: list[PurchaseTendency] = []
    desc = product_description.lower()

    # Price-based inference
    if product_price > 100000:
        tendencies.append(PurchaseTendency.DELIBERATE)
        tendencies.append(PurchaseTendency.BRAND_LOYAL)
    elif product_price < 20000:
        tendencies.append(PurchaseTendency.IMPULSE)
        tendencies.append(PurchaseTendency.BARGAIN_HUNTER)
    else:
        tendencies.append(PurchaseTendency.NEEDS_BASED)

    # Description-based inference
    if any(kw in desc for kw in ["할인", "세일", "특가", "저렴"]):
        if PurchaseTendency.BARGAIN_HUNTER not in tendencies:
            tendencies.append(PurchaseTendency.BARGAIN_HUNTER)
    if any(kw in desc for kw in ["프리미엄", "명품", "브랜드", "고급"]):
        if PurchaseTendency.BRAND_LOYAL not in tendencies:
            tendencies.append(PurchaseTendency.BRAND_LOYAL)
    if any(kw in desc for kw in ["필수", "필요", "기본"]):
        if PurchaseTendency.NEEDS_BASED not in tendencies:
            tendencies.append(PurchaseTendency.NEEDS_BASED)

    return tendencies


def recommend_personas_for_product(
    personas: list[Persona],
    product_name: str,
    product_category: str,
    product_price: float = 0.0,
    product_description: str = "",
    count: int = 10,
) -> list[Persona]:
    """Recommend personas for a product using keyword matching on name/description.

    Uses simple keyword matching to determine relevant interest categories
    and purchase tendencies, then delegates to select_personas.
    """
    # Combine text sources for category inference
    combined_text = f"{product_name} {product_category} {product_description}"
    inferred_categories = _infer_categories_from_text(combined_text)
    inferred_tendencies = _infer_purchase_tendencies(product_price, product_description)

    # If we can infer a primary category, use select_personas directly
    if product_category:
        selected = select_personas(
            personas=personas,
            product_category=product_category,
            product_price=product_price,
            count=count,
            include_challengers=True,
        )
    elif inferred_categories:
        # Use the first inferred category as primary
        selected = select_personas(
            personas=personas,
            product_category=inferred_categories[0].value,
            product_price=product_price,
            count=count,
            include_challengers=True,
        )
    else:
        # No category match - select diverse set
        selected = select_personas(
            personas=personas,
            product_category="",
            product_price=product_price,
            count=count,
            include_challengers=True,
        )

    # Boost personas matching inferred purchase tendencies
    # Move matching personas toward the front of the list
    if inferred_tendencies:
        matching = [p for p in selected if p.purchase_tendency in inferred_tendencies]
        non_matching = [p for p in selected if p.purchase_tendency not in inferred_tendencies]
        selected = matching + non_matching

    return selected[:count]
