from .base import Provider, ProviderError

class StartupIndia(Provider):
    """PLACEHOLDER: no documented public API found. To connect later, implement search() and return normalized startup dicts."""
    name = "Startup India (DPIIT) - placeholder"; category = "Startups (India)"; needs_auth = False
    coverage = "No documented public API found; not connected. Use CSV import in Startup Explorer."
    def configured(self): return False
    def search(self, query, limit=25): raise ProviderError("Placeholder: no public API connected. Import a CSV instead.")

STARTUP_PROVIDERS = [StartupIndia()]
