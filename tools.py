from langchain_core.tools import tool
from pydantic import BaseModel, Field
from typing import List

# 1. The schema for the agent's final output (Structured Data)
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
    summary: str = Field(description="An engaging summary of the itinerary")

# 2. Mock tools (Global coverage)
VALID_CITIES = ["London", "Paris", "New York", "Tokyo"] 

@tool
def search_flights(destination: str, origin: str = "Tokyo"):
    """Search for flights. Returns flight options with prices."""
    # Normalize input (to handle casing variations)
    dest_normalized = destination.title()

    if dest_normalized not in VALID_CITIES:
        # [CRITICAL]: Detail the error message so the agent can use it as "evidence"
        return (f"Error: No flights found for '{destination}'. "
                f"Currently, we only support flights to: {', '.join(VALID_CITIES)}.")
    
    return [
        {"airline": "Global Air", "flight_number": "GA101", "price": 250000},
        {"airline": "Budget Fly", "flight_number": "BF505", "price": 120000}
    ]

@tool
def search_hotels(destination: str, budget_level: str = "medium"):
    """Search for hotels. budget_level can be 'low', 'medium', 'high'."""
    # Normalize input (to handle casing variations)
    dest_normalized = destination.title()

    # Guard logic identical to the flight search
    if dest_normalized not in VALID_CITIES:
        return (f"Error: No hotels found in '{destination}'. "
                f"Currently, we only support hotels in: {', '.join(VALID_CITIES)}.")
    
    if budget_level == "high":
        base_price = 150000  # luxury
    elif budget_level == "low":
        base_price = 8000    # budget
    else:
        base_price = 30000   # standard

    return [
        {"name": f"{destination} Comfort Inn", "price_per_night": base_price},
        {"name": f"{destination} Royal Palace", "price_per_night": base_price * 2}
    ]