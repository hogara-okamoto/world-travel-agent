import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import SystemMessage, HumanMessage # 追加
from opik import track
from tools import search_flights, search_hotels, Itinerary
from opik.integrations.langchain import OpikTracer

load_dotenv()

llm = ChatOpenAI(model="gpt-4o")
tools = [search_flights, search_hotels]

# System prompt (Instructing JSON output)
SYSTEM_PROMPT_TEXT = """
You are a World Travel Agent. 
Plan a trip based on the user's request using the available tools.

# 1. TOOL USAGE & DATA GATHERING
- Always query the tools to get real-world data (prices, locations).
- Do NOT guess prices. Even if a request seems impossible, use tools first to get "evidence" prices.

# 2. CALCULATION & VALIDATION PROCESS (Step-by-Step)
1. **Identify User Constraints:** Note the user's budget, currency, and specific destinations.
2. **Retrieve Data:** Get flight and hotel options.
3. **Currency Normalization:** - For *internal calculation* and comparison, roughly convert tool prices to the user's budget currency (e.g., $1 ≈ 150 JPY, €1 ≈ $1.1).
   - For *final output*, always respect the user's requested currency symbol (or the input symbol if unspecified).
4. **Feasibility Check:** Compare the sum of the cheapest valid options against the user's budget.

# 3. RESPONSE MODES

## MODE A: Success (Trip is Feasible)
Output a JSON with the itinerary.
- 'total_cost' MUST be the exact sum of the selected flight and hotel.
- Ensure airline/hotel names in 'summary' match the JSON objects.

## MODE B: Failure (Trip is Impossible)
If the budget is too low OR **the destination is not supported**, output a JSON with this SPECIAL format:
{
  "destination": "N/A",
  "total_cost": 0,
  "summary": "Follow this strict structure:
    1. Acknowledge: Explicitly name the specific destination(s) and constraints the user requested.
    2. Primary Reason: State clearly if the destination is not supported by the tools.
    3. Secondary Reason (CRITICAL): Even if the destination is invalid, YOU MUST ALSO comment on the user's budget. Explain that their budget (using their EXACT currency symbol) is too low for ANY destination we offer.
    4. Suggest Alternatives: List valid cities and a realistic budget."
}

# OUTPUT SCHEMA (Strict JSON)
{
  "destination": "string",
  "flights": [{"airline": "string", "price": int}],
  "hotels": [{"name": "string", "price_per_night": int}],
  "total_cost": int,
  "summary": "string"
}
"""

# No modifiers passed here (to avoid argument errors)
graph = create_react_agent(llm, tools)

@track(name="TravelAgent_Run")
def run_agent(user_input: str):
    # Manually prepend the system prompt to the messages here
    messages = [
        SystemMessage(content=SYSTEM_PROMPT_TEXT),
        HumanMessage(content=user_input)
    ]
    
    inputs = {"messages": messages}
    opik_tracer = OpikTracer()
    result = graph.invoke(inputs, config={"callbacks": [opik_tracer]})
    
    # Retrieve the final response from the AI
    return result["messages"][-1].content

if __name__ == "__main__":
    try:
        print("Agent is running...")
        result = run_agent("I want to go to New York. My budget is average.")
        print("--- Agent Result ---")
        print(result)
    except Exception as e:
        print(f"Error: {e}")