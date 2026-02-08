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

# 2. Custom Evaluation Metric
class TravelJsonMetric:
    def __init__(self):
        self.name = "JSON_Correctness_and_Intent"

    # Changed the argument name to 'expected_destination'
    # Opik automatically passes keys with the same name from the dataset.
    def score(self, output, expected_destination, **kwargs):
        try:
            # JSON parsing process
            # [Robust Parsing]: Extract everything between the first '{' and the last '}'
            match = re.search(r'\{.*\}', output, re.DOTALL)
            if not match:
                return ScoreResult(name=self.name, value=0.0, reason="No JSON found in text")
            
            json_str = match.group()
            plan = json.loads(json_str) # Significantly increases the success rate of JSON parsing here
                
            score = 1.0
            reasons = []

            # Check 1: Does the destination match?
            # Use the 'expected_destination' argument directly
            dest_in_plan = plan.get("destination", "")

            # [NEW]: Logic for when the agent correctly identifies the request as "Impossible"
            if dest_in_plan == "N/A":
                # Full marks if the dataset expectation is also "None" or "N/A"
                if expected_destination == "None" or expected_destination == "N/A":
                    return ScoreResult(name=self.name, value=1.0, reason="Correctly identified impossible request.")
                else:
                    # Penalty if the agent refuses a valid request
                    return ScoreResult(name=self.name, value=0.0, reason="Refused a valid request.")
                
            if expected_destination.lower() in dest_in_plan.lower():
                reasons.append("Destination matches.")
            else:
                score -= 0.5
                reasons.append(f"Wrong destination: {dest_in_plan} (Expected: {expected_destination})")

            # Check 2: Is the mandatory field 'total_cost' present?
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
        
# New Judge: Price Appropriateness Evaluator
class TravelJudgeMetric:
    def __init__(self):
        self.name = "Price_Appropriateness_Judge"

    def score(self, output, expected_price_sensitivity, **kwargs):
        """
        Uses another LLM-as-judge logic to determine if the pricing is reasonable for the user request.
        """
        # (Here, we would normally call Opik's `LLM-as-judge` function or the OpenAI API.)
        # Simulating logic by matching specific price thresholds with sensitivity levels.
        
        try:
        # Extract using regex in the same manner
            match = re.search(r'\{.*\}', output, re.DOTALL)
            if not match:
                return ScoreResult(name=self.name, value=0.0, reason="No JSON found")
            
            plan = json.loads(match.group())

            # If the request was refused (N/A), skip the price check and grant full marks.
            #（Because TravelJsonMetric has already checked whether the refusal was legitimate）
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

# 3. Evaluation Task
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
    
    # Data insertion (with try-except to handle potential errors)
    try:
        dataset.insert(DATASET_ITEMS)
        print(f"✅ Data inserted into {dataset_name}")
    except Exception as e:
        print(f"ℹ️ Data insertion skipped (might already exist).")

    # Execute Evaluation
    evaluate(
        dataset=dataset,
        task=eval_task,
        scoring_metrics=[
            TravelJsonMetric(),       # Format Check
            TravelJudgeMetric(),      # Custom Judge
            AnswerRelevance(require_context=False)         # Opik's `LLM-as-judge`
        ],
        experiment_name="TravelAgent_MVP_Experiment"
    )