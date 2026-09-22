import json
import requests
import time

API_URL = "http://127.0.0.1:8000/check"
EVALS_FILE = "evals/cases.json"


def run_evaluations():

    with open(EVALS_FILE, "r", encoding="utf-8") as f:
        cases = json.load(f)

    total_cases = len(cases)
    matched = 0
    failed_cases = []

    print(f"Starting evaluation of {total_cases} test cases...\n")


    for index, case in enumerate(cases, 1):
        query = case["query"]
        expected = case["expected_verdict"]

        try:
            response = requests.post(
                API_URL,
                json={"query": query},
                timeout=120
            )

            if response.status_code == 200:
                result = response.json()
                actual = result.get("verdict")


                if actual == expected:
                    matched += 1
                    print(f"[{index}/{total_cases}] PASS")
                else:
                    failed_cases.append({
                        "query": query,
                        "expected": expected,
                        "actual": actual,
                        "reason": result.get("reason")
                    })
                    print(f"[{index}/{total_cases}] FAIL (Expected: {expected}, Got: {actual})")
            else:
                print(f"[{index}/{total_cases}] ERROR: API returned status {response.status_code}")
                failed_cases.append({
                    "query": query,
                    "expected": expected,
                    "actual": f"HTTP {response.status_code}",
                    "reason": "API Request Failed"
                })

        except Exception as e:
            print(f"[{index}/{total_cases}] CRASH: {str(e)}")

        if index < total_cases:
            print("Wait 20s because of API limit")
            time.sleep(20)


    percentage = (matched / total_cases) * 100

    print("\n" + "=" * 40)
    print("EVALUATION RESULTS")
    print("=" * 40)
    print(f"Total matches: {matched} od {total_cases}")
    print(f"Accuracy percentage: {percentage:.1f}%")

    if failed_cases:
        print("\n FAILED CASES:")
        for idx, fail in enumerate(failed_cases, 1):
            print(f"\n{idx}. Query: \"{fail['query']}\"")
            print(f"   Expected: {fail['expected']}")
            print(f"   Obtained:  {fail['actual']}")
            print(f"   The reason of the model: {fail['reason']}")
    else:
        print("\nAll tests passed successfully!")


if __name__ == "__main__":
    run_evaluations()