#!/usr/bin/env python3
"""
Fetch Azure AI Document Intelligence (Cognitive Services) endpoint + key via Azure CLI
and merge them into your workspace .env file.

Prerequisites:
  - Azure CLI installed: https://learn.microsoft.com/cli/azure/install-azure-cli
  - Log in:  az login

Usage (from repo root c:\\Users\\...\\Azure):
  python scripts/sync_document_intelligence_env.py --resource-group YOUR_RG --account-name YOUR_DOCINTEL_NAME

This sets:
  DOCUMENT_INTELLIGENCE_ENDPOINT, DOCUMENT_INTELLIGENCE_KEY
  DOC_INTELLIGENCE_ENDPOINT, DOC_INTELLIGENCE_KEY   (aliases for older lab files)
  FORMS_RECOGNIZER_ENDPOINT, FORMS_RECOGNIZER_KEY   (Lab 04 custom skill local.settings)

It does NOT auto-fill (must still copy from portals / Studio):
  MODEL_ID, COMPOSED_MODEL_ID
  PROJECT_CONNECTION, ANALYZER  (Exercise 05 / Foundry)
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def _az_executable() -> str:
    """Resolve `az` when PATH is minimal (e.g. some IDE terminals)."""
    w = shutil.which("az")
    if w:
        return w
    for candidate in (
        r"C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd",
        r"C:\Program Files (x86)\Microsoft SDKs\Azure\CLI2\wbin\az.cmd",
    ):
        if os.path.isfile(candidate):
            return candidate
    raise SystemExit(
        "Azure CLI (az) not found. Install: https://learn.microsoft.com/cli/azure/install-azure-cli"
    )


def _run_az(args: list[str]) -> subprocess.CompletedProcess[str]:
    az = _az_executable()
    return subprocess.run(
        [az, *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
    )


def _require_az_login() -> None:
    r = _run_az(["account", "show"])
    if r.returncode != 0:
        print(
            "Not logged in to Azure CLI.\n"
            "  Run:  az login\n"
            "Then re-run this script.",
            file=sys.stderr,
        )
        sys.exit(1)


def _fetch_endpoint_and_key(resource_group: str, account_name: str) -> tuple[str, str]:
    show = _run_az(
        [
            "cognitiveservices",
            "account",
            "show",
            "--resource-group",
            resource_group,
            "--name",
            account_name,
            "--query",
            "{endpoint:properties.endpoint}",
            "-o",
            "json",
        ]
    )
    if show.returncode != 0:
        print(show.stderr or show.stdout, file=sys.stderr)
        sys.exit(1)
    data = json.loads(show.stdout)
    endpoint = (data.get("endpoint") or "").strip()
    if not endpoint:
        print("Could not read endpoint from Azure CLI output.", file=sys.stderr)
        sys.exit(1)

    keys = _run_az(
        [
            "cognitiveservices",
            "account",
            "keys",
            "list",
            "--resource-group",
            resource_group,
            "--name",
            account_name,
            "--query",
            "key1",
            "-o",
            "tsv",
        ]
    )
    if keys.returncode != 0:
        print(keys.stderr or keys.stdout, file=sys.stderr)
        sys.exit(1)
    key = (keys.stdout or "").strip()
    if not key:
        print("Could not read key1 from Azure CLI.", file=sys.stderr)
        sys.exit(1)

    return endpoint.rstrip("/") + "/", key


def _merge_env(env_path: Path, updates: dict[str, str]) -> None:
    """Update KEY=value lines; append missing keys at end."""
    lines: list[str] = []
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines()

    keys_seen = set()
    new_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            new_lines.append(line)
            continue
        if "=" in line:
            k = line.split("=", 1)[0].strip()
            if k in updates:
                new_lines.append(f"{k}={updates[k]}")
                keys_seen.add(k)
                continue
        new_lines.append(line)

    for k, v in updates.items():
        if k not in keys_seen:
            new_lines.append(f"{k}={v}")

    env_path.parent.mkdir(parents=True, exist_ok=True)
    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def _list_accounts(resource_group: str) -> None:
    r = _run_az(
        [
            "cognitiveservices",
            "account",
            "list",
            "--resource-group",
            resource_group,
            "--query",
            "[].{name:name, kind:kind, endpoint:properties.endpoint}",
            "-o",
            "table",
        ]
    )
    print(r.stdout if r.returncode == 0 else (r.stderr or r.stdout))
    if r.returncode != 0:
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sync Document Intelligence endpoint/key from Azure into .env"
    )
    parser.add_argument(
        "--resource-group",
        "-g",
        required=True,
        help="Resource group that contains the Document Intelligence / Cognitive Services account",
    )
    parser.add_argument(
        "--account-name",
        "-n",
        default=None,
        help="Name of the Azure AI Document Intelligence (or Form Recognizer) resource",
    )
    parser.add_argument(
        "--list-accounts",
        action="store_true",
        help="List Cognitive Services accounts in the resource group and exit",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=None,
        help="Path to .env (default: <repo root>/.env)",
    )
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent
    env_path = args.env_file or (repo_root / ".env")

    _require_az_login()
    if args.list_accounts:
        _list_accounts(args.resource_group)
        return
    if not args.account_name:
        print("Error: --account-name is required (or use --list-accounts).", file=sys.stderr)
        sys.exit(2)

    endpoint, key = _fetch_endpoint_and_key(args.resource_group, args.account_name)

    updates = {
        "DOCUMENT_INTELLIGENCE_ENDPOINT": endpoint,
        "DOCUMENT_INTELLIGENCE_KEY": key,
        "DOC_INTELLIGENCE_ENDPOINT": endpoint,
        "DOC_INTELLIGENCE_KEY": key,
        "FORMS_RECOGNIZER_ENDPOINT": endpoint,
        "FORMS_RECOGNIZER_KEY": key,
    }

    _merge_env(env_path, updates)

    print(f"Updated {env_path}")
    print("Set: DOCUMENT_INTELLIGENCE_*, DOC_INTELLIGENCE_*, FORMS_RECOGNIZER_*")
    print("")
    print("Still set manually when needed:")
    print("  MODEL_ID, COMPOSED_MODEL_ID  (Document Intelligence Studio)")
    print("  PROJECT_CONNECTION, ANALYZER  (Azure AI Foundry project; Exercise 05)")
    print("  FORMS_RECOGNIZER_MODEL_ID  (custom model for Lab 04 AnalyzeForm skill)")


if __name__ == "__main__":
    main()
