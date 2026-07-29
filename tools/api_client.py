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

    try:
        response = requests.post(
            server_url,
            json=payload,
            timeout=300
        )
    except requests.exceptions.ConnectionError:
        raise RuntimeError(f"服务器连接失败: {server_url}")
    except requests.exceptions.Timeout:
        raise RuntimeError("服务器请求超时")

    try:
        data = response.json()
    except Exception:
        data = {
            "error": response.text or f"HTTP {response.status_code} 无响应内容"
        }

    if response.status_code != 200:
        raise RuntimeError(
            json.dumps(
                data,
                ensure_ascii=False
            )
        )


    return data