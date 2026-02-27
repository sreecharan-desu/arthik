import requests
import json
import sys
from dotenv import dotenv_values

env = dotenv_values(".env")
token = env.get("HUG")
repo_id = "sreecharan-desu/ArthikBackend"

headers = {"Authorization": f"Bearer {token}"}
url = f"https://huggingface.co/api/spaces/{repo_id}/logs/build"

print(f"Connecting to {url} ...")
with requests.get(url, headers=headers, stream=True, timeout=5) as r:
    if r.status_code != 200:
        print(f"Error {r.status_code}: {r.text}")
        sys.exit(1)
    
    count = 0
    for line in r.iter_lines():
        if line:
            print(line.decode('utf-8'))
            count += 1
            if count > 50:
                break
