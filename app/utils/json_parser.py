import json

def parse_llm_json(raw_text:str)->dict:
    text=raw_text.strip()
    if text.startswith("```"):
        text=text.split("\n",1)[1] if "\n" in text else text[3:]
    if text.endswith("```"):
        text=text.rsplit("```", 1)[0]
    text=text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        raise ValueError(
            f"AI output cannot be understood by python even after we tried fixing it.\n"
             f"First 200 chars: {text[:200]}"
        )