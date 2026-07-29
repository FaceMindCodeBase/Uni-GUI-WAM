import json
import requests
import base64
from pathlib import Path

SERVER_URL = "http://127.0.0.1:8000/infer"

def encode_image(path):
    with open(path,"rb") as f:
        return base64.b64encode(f.read()).decode()

def infer(
    image_path,
    task,
    task_id,
    step,
    action_history,
    plan,
    config,
    server_url=SERVER_URL
):
    payload = {
        "task_id": task_id,
        "task": task,
        "step": step,
        "image_base64": encode_image(image_path),
        "action_history": action_history,
        "plan": plan,
        "config": config
    }

    response = requests.post(
        server_url,
        json=payload,
        timeout=300
    )

    try:
        data = response.json()
    except Exception:
        data = {
            "error": response.text
        }


    if response.status_code != 200:
        raise requests.exceptions.HTTPError(
            json.dumps(
                data,
                ensure_ascii=False
            ),
            response=response
        )


    return data