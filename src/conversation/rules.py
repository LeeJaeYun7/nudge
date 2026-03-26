TERMINATION_KEYWORDS_PURCHASE = [
    "결제할게요",
    "구매할게요",
    "살게요",
    "이걸로 할게요",
    "장바구니 담을게요",
    "장바구니 담고",
    "바로 결제",
    "포장해 주세요",
]

TERMINATION_KEYWORDS_EXIT = [
    "안 살게요",
    "됐어요",
    "필요 없어요",
    "나갈게요",
    "다른 데 좀 더",
    "그만하세요",
    "괜찮아요",
]

TERMINATION_KEYWORDS_WISHLIST = [
    "찜해둘게요",
    "위시리스트",
    "다시 올게요",
    "나중에",
    "생각해볼게요",
    "좀 더 생각",
]


def check_termination(content: str) -> str | None:
    """고객 발화에서 종료 키워드를 확인합니다.

    Returns:
        "purchase" | "customer_exit" | "wishlist" | None
    """
    content_lower = content.strip()

    for keyword in TERMINATION_KEYWORDS_PURCHASE:
        if keyword in content_lower:
            return "purchase"

    for keyword in TERMINATION_KEYWORDS_EXIT:
        if keyword in content_lower:
            return "customer_exit"

    for keyword in TERMINATION_KEYWORDS_WISHLIST:
        if keyword in content_lower:
            return "wishlist"

    return None
