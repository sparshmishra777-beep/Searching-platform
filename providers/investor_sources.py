from .base import Provider, ProviderError

class InvestorDirectory(Provider):
    name = "Investor directory / authorized investor API"; category = "Investors"; needs_auth = True
    coverage = "No keyless, documented investor API was verified. Use the CSV import in Investor Explorer for data you are licensed to use."
    def configured(self): return False
    def search(self, query, limit=25): raise ProviderError("Not connected: no verified keyless investor API. Import a CSV instead.")

INVESTOR_PROVIDERS = [InvestorDirectory()]
