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
@tool
def search_flights(destination: str, origin: str = "Tokyo"):
    """Search for flights. Returns flight options with prices."""
    # モックなので、どこへ行っても適当なデータを返す
    return [
        {"airline": "Global Air", "flight_number": "GA101", "price": 80000},
        {"airline": "Budget Fly", "flight_number": "BF505", "price": 45000}
    ]

@tool
def search_hotels(destination: str, budget_level: str = "medium"):
    """Search for hotels. budget_level can be 'low', 'medium', 'high'."""
    base_price = 15000 if budget_level == "medium" else 8000
    return [
        {"name": f"{destination} Central Hotel", "price_per_night": base_price},
        {"name": f"{destination} Grand Resort", "price_per_night": base_price * 2}
    ]