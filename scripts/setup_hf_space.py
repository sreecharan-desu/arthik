import os
from huggingface_hub import HfApi
from dotenv import dotenv_values

def setup_space():
    token = os.getenv("HUG")
    if not token:
        env_vars = dotenv_values(".env")
        token = env_vars.get("HUG")

    if not token:
        print("Could not find HUG token in environment or .env file.")
        return

    repo_id = "sreecharan-desu/ArthikBackend"
    api = HfApi(token=token)

    print(f"Creating Space: {repo_id}")
    try:
        api.create_repo(
            repo_id=repo_id,
            repo_type="space",
            space_sdk="docker",
            exist_ok=True,
            private=False
        )
        print("Space created successfully (or already exists).")
    except Exception as e:
        print(f"Error creating space: {e}")
        return

    print("Adding secrets to Space...")
    env_vars = dotenv_values(".env")
    for key, value in env_vars.items():
        if value and key != "HUG": # Don't need to save the HF token itself
            try:
                # Add secret to Space
                api.add_space_secret(repo_id=repo_id, key=key, value=value)
                print(f"Added secret: {key}")
            except Exception as e:
                print(f"Failed to add secret {key}: {e}")

    print("\nNext steps:")
    print(f"1. git remote add hfbackend https://sreecharan-desu:{token}@huggingface.co/spaces/{repo_id}")
    print("2. git push hfbackend main -f")

if __name__ == "__main__":
    setup_space()
