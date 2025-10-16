#!/usr/bin/env python3
"""
try_via_mullvad.py

Requirements:
  - Mullvad app + CLI installed and you're logged in.
  - (Recommended) Mullvad SOCKS5 proxy enabled (127.0.0.1:1080).
  - Python 3.8+, pip install requests[socks]
"""

import subprocess
import random
import re
import time
import sys
from typing import List, Optional
import requests

# ---- CONFIG ----
TARGET_URL = "https://example.com/"   # <- change to the page you want
MAX_ATTEMPTS = 6                      # total tries (including first attempt)
REQUEST_TIMEOUT = 10                  # seconds for HTTP request
SOCKS_PROXY = "socks5h://127.0.0.1:1080"  # leave as-is if you enabled local SOCKS in Mullvad
# ----------------

def run_cmd(cmd: List[str], timeout: int = 20) -> str:
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=timeout, text=True)
        return out
    except subprocess.CalledProcessError as e:
        return e.output or ""
    except Exception as e:
        return str(e)

def http_try_once(url: str, proxy: Optional[str]) -> (bool, Optional[str]):
    """Return (success, response_text_or_error)"""
    try:
        if proxy:
            proxies = {"http": proxy, "https": proxy}
            r = requests.get(url, proxies=proxies, timeout=REQUEST_TIMEOUT)
        else:
            r = requests.get(url, timeout=REQUEST_TIMEOUT)
        if 200 <= r.status_code < 300:
            return True, r.text
        else:
            return False, f"HTTP {r.status_code}"
    except Exception as e:
        return False, str(e)

def get_relay_list() -> List[str]:
    """Uses `mullvad relay list` and tries to parse reasonable location tokens.
       Output format varies; we'll extract "country" and "city/server tokens" heuristically.
    """
    out = run_cmd(["mullvad", "relay", "list"])
    lines = out.splitlines()
    candidates = []
    # example mullvad relay list lines might contain 'se  Malmö' or 'se-mma-wg-001'. We'll capture tokens like 'se', 'se-mma-wg-001', 'se mma', etc.
    for ln in lines:
        ln = ln.strip()
        if not ln: 
            continue
        # if there's a server hostname (contains '-wg-' or '-br-' or ends with wg-###) add it
        m_host = re.search(r'([a-z]{2}(?:-[a-z0-9]+)+-wg-\d+)', ln)
        if m_host:
            candidates.append(m_host.group(1))
            continue
        # tokens like "se mma" or "se got"
        m = re.match(r'^([a-z]{2})(?:\s+([a-z0-9]{2,}))?', ln)
        if m:
            country = m.group(1)
            city = m.group(2)
            if city:
                candidates.append(f"{country} {city}")
            else:
                candidates.append(country)
    # fallback: if nothing parsed, return a small default set
    if not candidates:
        return ["se", "us", "de", "nl", "gb"]
    # deduplicate and return
    seen = []
    for c in candidates:
        if c not in seen:
            seen.append(c)
    return seen

def pick_random_relay(relays: List[str]) -> str:
    return random.choice(relays)

def set_and_connect_relay(relay_token: str, wait_connected: int = 25) -> bool:
    """Set location and connect. Return True if Mullvad reports Connected within timeout."""
    print(f"[mullvad] Setting relay -> {relay_token}")
    # Accept tokens like "se", "se mma", or "se-mma-wg-001"
    args = ["mullvad", "relay", "set", "location"] + relay_token.split()
    run_cmd(args)
    # Now connect
    run_cmd(["mullvad", "connect"])
    # Poll status for 'Connected' text
    deadline = time.time() + wait_connected
    while time.time() < deadline:
        stat = run_cmd(["mullvad", "status"])
        if "Connected" in stat:
            print("[mullvad] Connected.")
            return True
        time.sleep(2)
    print("[mullvad] Did not reach Connected state within timeout.")
    return False

def main():
    print("Trying direct request first (no Mullvad change).")
    ok, resp = http_try_once(TARGET_URL, SOCKS_PROXY)
    if ok:
        print("[ok] Got page on first try.")
        print(resp[:1000])  # print first chunk
        return
    print("[warn] First try failed:", resp)
    # iterate attempts
    attempts = 1
    relays = get_relay_list()
    if not relays:
        print("[error] Couldn't find any relays via 'mullvad relay list'. Make sure the Mullvad CLI is installed and you are logged in.")
        sys.exit(2)
    print(f"[info] Found {len(relays)} parsed relay choices (will pick randomly).")
    while attempts < MAX_ATTEMPTS:
        attempts += 1
        choice = pick_random_relay(relays)
        print(f"[attempt {attempts}/{MAX_ATTEMPTS}] Trying relay: {choice}")
        success = set_and_connect_relay(choice)
        if not success:
            print("[warn] Could not establish Mullvad connection to that relay; trying another.")
            continue
        # small pause to settle routing
        time.sleep(2)
        ok, resp = http_try_once(TARGET_URL, SOCKS_PROXY)
        if ok:
            print("[success] Request succeeded via Mullvad relay:", choice)
            print(resp[:2000])
            return
        else:
            print("[fail] Request failed via that relay:", resp)
            # try next random relay
    print("[final] Exhausted attempts. Last error:", resp)
    sys.exit(1)

if __name__ == "__main__":
    main()
