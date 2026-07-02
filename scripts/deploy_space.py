"""Deploy Vegas Amnesia as a Hugging Face Docker Space (single service).

Reads credentials from .env, creates/updates the Space, sets secrets, uploads
the repo. Run:  .venv/bin/python scripts/deploy_space.py
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.chdir(Path(__file__).resolve().parents[1])

from dotenv import load_dotenv

load_dotenv(".env", override=True)

from huggingface_hub import HfApi

token = os.environ.get("HF_TOKEN")
if not token:
    sys.exit("HF_TOKEN missing from .env")

api = HfApi(token=token)
user = api.whoami()["name"]
repo_id = f"{user}/vegas-amnesia"
print(f"deploying to https://huggingface.co/spaces/{repo_id}")

api.create_repo(repo_id=repo_id, repo_type="space", space_sdk="docker", exist_ok=True)

for key in ["COGNEE_API_KEY", "COGNEE_BASE_URL", "HF_TOKEN"]:
    api.add_space_secret(repo_id=repo_id, key=key, value=os.environ[key])
api.add_space_variable(repo_id=repo_id, key="LLM_BACKEND", value="hf")

api.upload_folder(
    folder_path=".",
    repo_id=repo_id,
    repo_type="space",
    ignore_patterns=[
        ".venv/**", ".git/**", ".env", "**/__pycache__/**",
        ".pytest_cache/**",
    ],
    commit_message="Vegas Amnesia — hackathon deploy",
)
print("uploaded. Build starts automatically; watch it at:")
print(f"  https://huggingface.co/spaces/{repo_id}")
print(f"game will be live at: https://{user.lower()}-vegas-amnesia.hf.space")
