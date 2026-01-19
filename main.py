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

# システムプロンプト（JSON出力を指示）
SYSTEM_PROMPT_TEXT = """
You are a World Travel Agent. 
Plan a trip based on the user's request using the available tools.
After making tool calls, YOU MUST output the final result in JSON format matching this schema:
{
  "destination": "string (MUST be in English, e.g. 'Paris', 'New York')",  # <--- ここを追加！
  "flights": [{"airline": "string", "price": int}],
  "hotels": [{"name": "string", "price_per_night": int}],
  "total_cost": int,
  "summary": "string"
}
Don't guess prices; use the tools.
"""

# 修正点: ここでは modifier を一切渡さない（引数エラーを回避）
graph = create_react_agent(llm, tools)

@track(name="TravelAgent_Run")
def run_agent(user_input: str):
    # 修正点: ここで手動でシステムプロンプトを先頭に追加する
    # これならどんなバージョンのライブラリでも動きます
    messages = [
        SystemMessage(content=SYSTEM_PROMPT_TEXT),
        HumanMessage(content=user_input)
    ]
    
    inputs = {"messages": messages}
    opik_tracer = OpikTracer()
    result = graph.invoke(inputs, config={"callbacks": [opik_tracer]})
    
    # AIの最後の回答を取得
    return result["messages"][-1].content

if __name__ == "__main__":
    try:
        print("Agent is running...")
        result = run_agent("ニューヨークへ行きたい。予算は普通で。")
        print("--- Agent Result ---")
        print(result)
    except Exception as e:
        print(f"Error: {e}")