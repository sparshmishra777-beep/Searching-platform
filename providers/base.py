import time, requests
import config

class ProviderError(Exception): pass

class Provider:
    name = ""; category = ""; needs_auth = False; coverage = ""; docs = ""
    def configured(self): return True
    def search(self, query, limit=25): raise NotImplementedError

def get_json(url, headers=None, params=None, auth=None):
    last = None
    for i in range(config.RETRIES):
        try:
            r = requests.get(url, headers=headers, params=params, auth=auth, timeout=config.TIMEOUT)
            if r.status_code in (401, 403): raise ProviderError(f"Authentication/permission failure (HTTP {r.status_code}). Check credentials/User-Agent.")
            if r.status_code == 429 or r.status_code >= 500:
                last = ProviderError(f"HTTP {r.status_code} (rate limit or server error)"); time.sleep(2 ** i); continue
            if r.status_code >= 400: raise ProviderError(f"HTTP {r.status_code}")
            try: return r.json()
            except ValueError: raise ProviderError("Invalid (non-JSON) response")
        except requests.RequestException as e:
            last = ProviderError(f"Network error: {e}"); time.sleep(2 ** i)
    raise last or ProviderError("Unknown error")
