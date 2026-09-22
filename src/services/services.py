import datetime
import time
import json
import os
from openai import OpenAI, APITimeoutError
from pydantic import ValidationError
from src.llm.schema import QueryResponse
from fastapi import HTTPException

query_cache = {}


def clean_json_string(raw_text:str)->str:
    cleaned = raw_text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
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

def log_cost(prompt_version: str, model: str, input_tokens: int, output_tokens: int, duration_ms: float, is_repair: bool):
    os.makedirs("logs", exist_ok=True)

    cost_entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "prompt_version": prompt_version,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "duration_ms": round(duration_ms, 2),
        "is_repair": is_repair
    }

    with open("logs/cost.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(cost_entry) + "\n")

def evaluate_query_risk(user_query: str):
    prompt_version = "risk-classifier-v2"

    cache_key = f"{prompt_version}_{user_query}"

    if cache_key in query_cache:
        print(f"CACHE HIT: Returning cached response for query '{user_query}'")
        return query_cache[cache_key]

    with open(f"prompts/{prompt_version}.md", "r", encoding="utf-8") as file:
        system_prompt = file.read()

    client = OpenAI(
        base_url=os.environ["LLM_BASE_URL"],
        api_key=os.environ["LLM_API_KEY"],
        timeout=30.0,
        max_retries=2
    )

    raw_output = ""

    try:
        start_time = time.time()
        response = client.chat.completions.create(
            model=os.environ["LLM_MODEL"],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_query}
            ],
            temperature=0.2
        )
        duration_ms = (time.time() - start_time) * 1000
        raw_output = response.choices[0].message.content
        log_cost(
            prompt_version=prompt_version,
            model=response.model,
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
            duration_ms=duration_ms,
            is_repair=False
        )

    except APITimeoutError:
        raise HTTPException(
            status_code=504,
            detail="Upstream AI provider timed out after 30 seconds."
        )

    try:
        cleaned_output = clean_json_string(raw_output)
        valid_data = QueryResponse.model_validate_json(cleaned_output)

        query_cache[cache_key] = valid_data

        return valid_data

    except (ValueError, ValidationError) as e:
        error_msg = str(e)

        repair_start = time.time()
        repair_response = client.chat.completions.create(
            model=os.environ["LLM_MODEL"],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_query},
                {"role": "assistant", "content": raw_output},
                {"role": "user",
                 "content": f"Your previous answer was rejected for this reason: {error_msg}. Return only corrected JSON matching the schema."}
            ],
            temperature=0.2
        )
        repair_duration = (time.time() - repair_start) * 1000
        repair_raw_output = repair_response.choices[0].message.content
        log_cost(
            prompt_version=prompt_version,
            model=repair_response.model,
            input_tokens=repair_response.usage.prompt_tokens,
            output_tokens=repair_response.usage.completion_tokens,
            duration_ms=repair_duration,
            is_repair=True
        )

        try:
            repair_cleaned = clean_json_string(repair_raw_output)
            valid_repaired_data = QueryResponse.model_validate_json(repair_cleaned)
            query_cache[cache_key] = valid_repaired_data

            return valid_repaired_data

        except (ValueError, ValidationError) as final_error:
            log_to_quarantine(
                input_data=user_query,
                raw_output=repair_raw_output,
                error_msg=str(final_error),
                prompt_version=prompt_version
            )
            raise HTTPException(
                status_code=422,
                detail="Model failed to produce valid JSON matching the schema after repair attempt."
            )
