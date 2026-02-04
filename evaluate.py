import json
import os
import re
from dotenv import load_dotenv
from opik import Opik
from opik.evaluation import evaluate
from opik.evaluation.metrics.score_result import ScoreResult
from opik.evaluation.metrics import AnswerRelevance
from main import run_agent

load_dotenv()

# 1. Test Dataset (English version)
DATASET_ITEMS = [
    {
    "input": "I need a trip to Panama City with a five-star hotel stay. Specify both as two separate cities, one referring to the capital of a Central American country and the other to the city in Florida. Book a business class flight with an ultra-luxury hotel room for under $200 in total. Make sure to use Euros for the total cost while listing flight and hotel prices in USD.",
    "expected_destination": "None",
    "expected_price_sensitivity": "high"
    },
]

# 2. カスタム評価指標 (Metric)
class TravelJsonMetric:
    def __init__(self):
        self.name = "JSON_Correctness_and_Intent"

    # 【修正ポイント】
    # 引数名を 'input_data' から 'expected_destination' に変更しました。
    # Opikはデータセット内の同名のキーを自動的にここに渡してくれます。
    def score(self, output, expected_destination, **kwargs):
        try:
            # JSONパース処理
            #【最強のパース】最初に出現する { から 最後に出現する } までを抜き出す
            match = re.search(r'\{.*\}', output, re.DOTALL)
            if not match:
                return ScoreResult(name=self.name, value=0.0, reason="No JSON found in text")
            
            json_str = match.group()
            plan = json.loads(json_str) # ここでパースに成功する確率が激増します
                
            score = 1.0
            reasons = []

            # チェック1: 目的地が合っているか？
            # 引数で受け取った expected_destination を直接使います
            dest_in_plan = plan.get("destination", "")

            # 【追加】エージェントが「無理です」と正しく判断した場合の処理
            if dest_in_plan == "N/A":
                # データセット側の期待値も "None" や "N/A" なら満点
                if expected_destination == "None" or expected_destination == "N/A":
                    return ScoreResult(name=self.name, value=1.0, reason="Correctly identified impossible request.")
                else:
                    # 本当は行けるはずなのに断った場合は減点
                    return ScoreResult(name=self.name, value=0.0, reason="Refused a valid request.")
                
            if expected_destination.lower() in dest_in_plan.lower():
                reasons.append("Destination matches.")
            else:
                score -= 0.5
                reasons.append(f"Wrong destination: {dest_in_plan} (Expected: {expected_destination})")

            # チェック2: 必須項目(total_cost)があるか？
            if "total_cost" in plan and isinstance(plan["total_cost"], int):
                reasons.append("Total cost is valid.")
            else:
                score -= 0.5
                reasons.append("Missing total_cost.")
            
            return ScoreResult(
                name=self.name,
                value=max(0.0, score),
                reason="; ".join(reasons)
            )

        except json.JSONDecodeError:
            return ScoreResult(
                name=self.name,
                value=0.0,
                reason="FAILED to parse JSON."
            )
        except Exception as e:
            return ScoreResult(
                name=self.name,
                value=0.0,
                reason=f"Error: {str(e)}"
            )
        
# --- 新しいJudge: 価格妥当性評価器 ---
class TravelJudgeMetric:
    def __init__(self):
        self.name = "Price_Appropriateness_Judge"

    def score(self, output, expected_price_sensitivity, **kwargs):
        """
        別のLLMを使って、入力（安く済ませたい等）に対して
        回答の価格設定が妥当かを人間のように判定させます。
        """
        # ここでは本来、Opikの `LLM-as-judge` 機能や OpenAI API を呼び出しますが
        # 簡易的に「安い」という言葉と金額を照合するロジックをシミュレートします。
        
        try:
        # 3. こちらも同様に正規表現で抽出
            match = re.search(r'\{.*\}', output, re.DOTALL)
            if not match:
                return ScoreResult(name=self.name, value=0.0, reason="No JSON found")
            
            plan = json.loads(match.group())

            # 【追加】もしエージェントがリクエストを拒否(N/A)していたら、価格判定はスキップして満点とする
            # （TravelJsonMetric側で正当な拒否かどうかはチェック済みのため）
            if plan.get("destination") == "N/A":
                return ScoreResult(name=self.name, value=1.0, reason="Request refused, price check skipped.")
            
            cost = plan.get("total_cost", 0)
            
            score = 1.0
            reason = "Price seems reasonable for the request."

            if expected_price_sensitivity == "low":
                return ScoreResult(value=1.0 if cost < 200000 else 0.2, name=self.name)
                
            elif expected_price_sensitivity == "medium":
                return ScoreResult(value=1.0 if 100000 <= cost <= 400000 else 0.5, name=self.name)
                
            elif expected_price_sensitivity == "high":
                return ScoreResult(value=1.0 if cost > 300000 else 0.2, name=self.name)

            return ScoreResult(name=self.name, value=score, reason=reason)
        except:
            return ScoreResult(name=self.name, value=0.0, reason="Invalid output format")

# 3. 評価タスク
def eval_task(item):
    res = run_agent(item["input"])
    return {
        "output": res
    }

if __name__ == "__main__":
    print("🚀 Starting Opik Evaluation...")
    
    client = Opik()
    
    dataset_name = "Hackathon_Travel_Dataset_V2"
    dataset = client.get_or_create_dataset(name=dataset_name)
    
    # データ挿入（エラー回避のtry-except付き）
    try:
        dataset.insert(DATASET_ITEMS)
        print(f"✅ Data inserted into {dataset_name}")
    except Exception as e:
        print(f"ℹ️ Data insertion skipped (might already exist).")

    # 評価実行
    evaluate(
        dataset=dataset,
        task=eval_task,
        scoring_metrics=[
            TravelJsonMetric(),       # 以前の形式チェック
            TravelJudgeMetric(),      # 今回追加したカスタムJudge
            AnswerRelevance(require_context=False)         # Opik標準のLLM-as-judge
        ],
        experiment_name="TravelAgent_MVP_Experiment"
    )