from typing import Any


def calculate_bargain_feedback(
    target_price: float,
    market_min_price: float,
    current_price: float,
    current_round: int,
    max_rounds: int,
) -> tuple[float, float, str]:
    target_price = float(target_price)
    market_min_price = float(market_min_price)
    current_price = float(current_price)

    if current_price <= target_price:
        return 0.0, current_price, ""

    ideal_price = min(target_price, market_min_price)
    if current_price <= ideal_price:
        return 0.0, current_price, ""

    required_drop_ratio = (current_price - ideal_price) / current_price
    if max_rounds <= 1:
        adjust_factor = 1.0
    else:
        adjust_factor = float(current_round) / float(max_rounds - 1)
    actual_drop_ratio = required_drop_ratio * adjust_factor

    if actual_drop_ratio > 0.15:
        actual_drop_ratio = 0.15
    if actual_drop_ratio < 0.01:
        return 0.0, current_price, ""

    new_price = current_price * (1 - actual_drop_ratio)
    message = (
        f"您当前报价{current_price:.4f}元，高于目标价和市场最低价，"
        f"请降价{actual_drop_ratio * 100:.2f}%至{new_price:.4f}元。"
    )
    return actual_drop_ratio, new_price, message


def calculate_supplier_scores(suppliers_data: list[dict]) -> list[dict]:
    if not suppliers_data:
        return []

    enriched: list[dict[str, Any]] = []
    for supplier in suppliers_data:
        items = supplier.get("items") or []
        total_price = sum(float(item.get("price", 0)) * float(item.get("qty", 0)) for item in items)
        item_count = len(items)
        avg_delivery_days = (
            sum(float(item.get("delivery_days", 0)) for item in items) / item_count if item_count > 0 else 0.0
        )
        record = dict(supplier)
        record["total_price"] = total_price
        record["avg_delivery_days"] = avg_delivery_days
        enriched.append(record)

    valid_total_prices = [item["total_price"] for item in enriched if item["total_price"] > 0]
    min_total_price = min(valid_total_prices) if valid_total_prices else 0.0

    valid_avg_days = [item["avg_delivery_days"] for item in enriched if item["avg_delivery_days"] > 0]
    min_avg_delivery_days = min(valid_avg_days) if valid_avg_days else 0.0

    for supplier in enriched:
        total_price = supplier["total_price"]
        avg_delivery_days = supplier["avg_delivery_days"]
        if min_total_price > 0 and total_price > 0:
            price_score = (min_total_price / total_price) * 100
        else:
            price_score = 0.0

        if min_avg_delivery_days > 0 and avg_delivery_days > 0:
            delivery_score = (min_avg_delivery_days / avg_delivery_days) * 100
        else:
            delivery_score = 0.0

        total_score = price_score * 0.7 + delivery_score * 0.3
        supplier["price_score"] = price_score
        supplier["delivery_score"] = delivery_score
        supplier["total_score"] = total_score

    return enriched
