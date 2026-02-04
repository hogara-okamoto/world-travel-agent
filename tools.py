from langchain_core.tools import tool
from pydantic import BaseModel, Field
from typing import List

# 1. 最終的にエージェントに出力させたい型（構造化データ）
class Flight(BaseModel):
    airline: str
    price: int

class Hotel(BaseModel):
    name: str
    price_per_night: int

class Itinerary(BaseModel):
    destination: str
    flights: List[Flight]
    hotels: List[Hotel]
    total_cost: int
    summary: str = Field(description="旅程の魅力的な要約")

# 2. モックツール群（世界対応）
VALID_CITIES = ["London", "Paris", "New York", "Tokyo"] # Tokyoも例として追加

@tool
def search_flights(destination: str, origin: str = "Tokyo"):
    """Search for flights. Returns flight options with prices."""
    # 入力の正規化（大文字小文字の揺れ吸収）
    dest_normalized = destination.title()

    if dest_normalized not in VALID_CITIES:
        # 【ここが重要】: エラーメッセージ自体を「証拠」として使えるように詳細化する
        return (f"Error: No flights found for '{destination}'. "
                f"Currently, we only support flights to: {', '.join(VALID_CITIES)}.")
    
    return [
        {"airline": "Global Air", "flight_number": "GA101", "price": 250000},
        {"airline": "Budget Fly", "flight_number": "BF505", "price": 120000}
    ]

@tool
def search_hotels(destination: str, budget_level: str = "medium"):
    """Search for hotels. budget_level can be 'low', 'medium', 'high'."""
    # 入力の正規化（大文字小文字の揺れ吸収）
    dest_normalized = destination.title()

    # フライトと同じロジックでガード
    if dest_normalized not in VALID_CITIES:
        return (f"Error: No hotels found in '{destination}'. "
                f"Currently, we only support hotels in: {', '.join(VALID_CITIES)}.")
    
    if budget_level == "high":
        base_price = 150000  # 豪華なら1泊15万円〜
    elif budget_level == "low":
        base_price = 8000    # 安いなら1泊8千円〜
    else:
        base_price = 30000   # 普通なら1泊3万円〜

    return [
        {"name": f"{destination} Comfort Inn", "price_per_night": base_price},
        {"name": f"{destination} Royal Palace", "price_per_night": base_price * 2}
    ]