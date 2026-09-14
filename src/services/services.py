import datetime
import json
import os
from openai import OpenAI
from pydantic import ValidationError
from src.llm.schema import QueryResponse
from fastapi import HTTPException

def clean_json_string(raw_text:str)->str:
    cleaned = raw_text.strip()
    if cleaned.startswith("json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith(""):
        cleaned = cleaned[3:]

    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]

    return cleaned.strip()



def log_to_quarantine(input_data: str, raw_output: str, error_msg: str, prompt_version: str):

    os.makedirs("logs", exist_ok=True)

    log_entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "prompt_version": prompt_version,
        "input": input_data,
        "error": error_msg,
        "raw_output": raw_output
    }

    with open("logs/quarantine.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry) + "\n")


def evaluate_query_risk(user_query: str):
    prompt_version = "risk-classifier-v1"
    with open(f"prompts/{prompt_version}.md", "r", encoding="utf-8") as file:
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

    raw_output = response.choices[0].message.content

    try:
        cleaned_output = clean_json_string(raw_output)
        valid_data = QueryResponse.model_validate_json(cleaned_output)

        return valid_data
    except (ValueError, ValidationError) as e:
        error_msg = str(e)
        repair_response = client.chat.completions.create(
            model=os.environ["LLM_MODEL"],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_query},
                {"role": "assistant", "content": raw_output},
                {"role": "user", "content": f"Your previous answer was rejected for this reason: {error_msg}. Return only corrected JSON matching the schema."}
            ],
            temperature=0.2
        )

        repair_raw_output = repair_response.choices[0].message.content

        try:
            repair_cleaned = clean_json_string(repair_raw_output)
            valid_repaired_data = QueryResponse.model_validate_json(repair_cleaned)
            return valid_repaired_data
        except (ValueError, ValidationError) as e:
            log_to_quarantine(
                input_data=user_query,
                raw_output=repair_raw_output,
                error_msg=str(e),
                prompt_version=prompt_version
            )
