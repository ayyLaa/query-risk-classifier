import os
from openai import OpenAI

def evaluate_query_risk(user_query: str):
    with open("prompts/risk-classifier-v1.md", "r", encoding="utf-8") as file:
        system_prompt = file.read()

    client = OpenAI(
        base_url=os.environ["LLM_BASE_URL"],
        api_key=os.environ["LLM_API_KEY"]
    )

    response = client.chat.completions.create(
        model=os.environ["LLM_MODEL"],
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_query}
        ],
        temperature=0.2
    )

    return response.choices[0].message.content
