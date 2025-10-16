# CaptionProx

A Python script that uses Mullvad VPN to make HTTP requests through different relay locations when direct requests fail.

## Prerequisites

- Mullvad app + CLI installed and logged in
- (Recommended) Mullvad SOCKS5 proxy enabled (127.0.0.1:1080)
- Python 3.8+

## Setup

1. **Clone and navigate to the project:**
   ```bash
   cd /home/moth/personal_scripts/captionprox
   ```

2. **Run the setup script:**
   ```bash
   ./setup.sh
   ```

3. **Activate the virtual environment:**
   ```bash
   source venv/bin/activate
   ```

## Usage

1. **Configure the target URL:**
   Edit `captionprox.py` and change the `TARGET_URL` variable to the page you want to access.

2. **Run the script:**
   ```bash
   python captionprox.py
   ```

## How it works

1. First attempts a direct request using the configured SOCKS proxy
2. If that fails, it randomly selects Mullvad relay locations
3. Connects to each relay and retries the request
4. Continues until successful or max attempts reached

## Configuration

Edit the configuration section in `captionprox.py`:

- `TARGET_URL`: The URL you want to access
- `MAX_ATTEMPTS`: Maximum number of attempts (default: 6)
- `REQUEST_TIMEOUT`: HTTP request timeout in seconds (default: 10)
- `SOCKS_PROXY`: SOCKS5 proxy address (default: socks5h://127.0.0.1:1080)

## Dependencies

- `requests[socks]`: For HTTP requests with SOCKS proxy support

## Deactivating the virtual environment

When you're done:
```bash
deactivate
```
