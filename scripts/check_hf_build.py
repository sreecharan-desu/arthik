import requests
import json
from dotenv import dotenv_values

env = dotenv_values(".env")
token = env.get("HUG")
repo_id = "sreecharan-desu/ArthikBackend"

headers = {"Authorization": f"Bearer {token}"}

# Get space info
url = f"https://huggingface.co/api/spaces/{repo_id}"
response = requests.get(url, headers=headers)
data = response.json()

runtime = data.get("runtime", {})
print(f"Stage: {runtime.get('stage')}")
if "error" in runtime:
    print(f"Error: {runtime.get('error')}")
if "errorMessage" in runtime:
    print(f"Error Message: {runtime.get('errorMessage')}")

print("\nFull runtime info:")
print(json.dumps(runtime, indent=2))
