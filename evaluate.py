import json
import os
from dotenv import load_dotenv
from opik import Opik
from opik.evaluation import evaluate
from opik.evaluation.metrics.score_result import ScoreResult
from main import run_agent

load_dotenv()

# 1. テストデータセット
DATASET_ITEMS = [
    {
        "input": "パリへ行きたい。安く済ませたい。",
        "expected_destination": "Paris",
        "expected_price_sensitivity": "low"
    },
    {
        "input": "ニューヨークへ豪華に行きたい。",
        "expected_destination": "New York",
        "expected_price_sensitivity": "high"
    },
    {
        "input": "東京からロンドンへの出張。予算は普通。",
        "expected_destination": "London",
        "expected_price_sensitivity": "medium"
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
            clean_output = output.replace("```json", "").replace("```", "").strip()
            plan = json.loads(clean_output)
            
            score = 1.0
            reasons = []

            # チェック1: 目的地が合っているか？
            # 引数で受け取った expected_destination を直接使います
            dest_in_plan = plan.get("destination", "")
            if expected_destination in dest_in_plan:
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

# 3. 評価タスク
def eval_task(item):
    res = run_agent(item["input"])
    return {
        "output": res
    }

if __name__ == "__main__":
    print("🚀 Starting Opik Evaluation...")
    
    client = Opik()
    
    dataset_name = "Hackathon_Travel_Dataset_Final"
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
        scoring_metrics=[TravelJsonMetric()],
        experiment_name="TravelAgent_MVP_Experiment"
    )