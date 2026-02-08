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
You are a World Travel Agent. Plan trips using tools and output ONLY strict JSON.

# RULES
1. **Tool First**: Always use tools to get real prices. Never guess.
2. **Currency**: Convert internally for comparison, but always use the user's currency symbol in the final 'summary'.
3. **Validation**: If the budget is insufficient or the destination is unsupported, use the "Failure Mode".

# RESPONSE MODES
- **Success**: If feasible, provide full itinerary details.
- **Failure**: If impossible, set `destination: "N/A"`, `total_cost: 0`, and in `summary`:
  - Acknowledge user's specific request and constraints.
  - Explain why it failed (unsupported city or low budget).
  - Suggest alternative cities and a realistic budget.

# OUTPUT SCHEMA
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