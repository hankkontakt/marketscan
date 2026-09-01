"""
Security Master v2 Resolver & Tradability Gating (Phase 1)
"""
from typing import Optional, Dict, List
from datetime import datetime
from backend_worker.security_master.models import SecurityState, Listing, Issuer, Security, CorporateAction

class SecurityMasterResolver:
    """
    In-memory / repository resolver for Security Master entities.
    Enforces hard tradability gates before scoring or serving decisions.
    """
    def __init__(self):
        self._issuers: Dict[str, Issuer] = {}
        self._securities: Dict[str, Security] = {}
        self._listings: Dict[str, Listing] = {}  # listing_id -> Listing
        self._ticker_map: Dict[str, str] = {}    # ticker -> listing_id
        self._corporate_actions: List[CorporateAction] = []

    def register_issuer(self, legal_name: str, country: str, sector: Optional[str] = None, lei: Optional[str] = None) -> Issuer:
        issuer = Issuer(legal_name=legal_name, country=country, sector=sector, lei=lei)
        self._issuers[issuer.issuer_id] = issuer
        return issuer

    def register_security(self, issuer_id: str, isin: Optional[str] = None, share_class: str = "Common") -> Security:
        security = Security(issuer_id=issuer_id, isin=isin, share_class=share_class)
        self._securities[security.security_id] = security
        return security

    def register_listing(
        self,
        security_id: str,
        mic: str,
        ticker: str,
        currency: str,
        state: SecurityState = SecurityState.ACTIVE,
        is_primary: bool = True
    ) -> Listing:
        listing = Listing(
            security_id=security_id,
            mic=mic,
            ticker=ticker,
            currency=currency,
            state=state,
            is_primary_listing=is_primary
        )
        self._listings[listing.listing_id] = listing
        self._ticker_map[ticker.upper()] = listing.listing_id
        return listing

    def record_corporate_action(self, action: CorporateAction):
        self._corporate_actions.append(action)
        # Apply immediate state impact
        if action.listing_id and action.listing_id in self._listings:
            listing = self._listings[action.listing_id]
            if action.action_type == "DELISTING":
                listing.state = SecurityState.DELISTED
            elif action.action_type == "MERGER_ACQUISITION":
                listing.state = SecurityState.MERGED
            elif action.action_type == "BANKRUPTCY":
                listing.state = SecurityState.BANKRUPT

    def resolve_listing_by_ticker(self, ticker: str) -> Optional[Listing]:
        """Lookup listing by trading symbol."""
        listing_id = self._ticker_map.get(ticker.upper())
        if listing_id:
            return self._listings.get(listing_id)
        return None

    def enforce_tradability_gate(self, ticker_or_listing_id: str) -> tuple[bool, SecurityState, str]:
        """
        Hard gate: determines if an instrument is eligible for active ranking/recommendations.
        Returns: (is_tradable, state, explanation)
        """
        listing = None
        if ticker_or_listing_id in self._listings:
            listing = self._listings[ticker_or_listing_id]
        else:
            listing = self.resolve_listing_by_ticker(ticker_or_listing_id)

        if not listing:
            return False, SecurityState.UNKNOWN, "Listing not found in Security Master (UNKNOWN state -> NO_SIGNAL)"

        if listing.state == SecurityState.ACTIVE:
            return True, SecurityState.ACTIVE, "Tradable and active listing"
        elif listing.state in (SecurityState.DELISTED, SecurityState.MERGED, SecurityState.BANKRUPT):
            return False, listing.state, f"Security is inactive ({listing.state.value}) — quarantined from active decisions"
        elif listing.state == SecurityState.ACQUISITION_PENDING:
            return False, listing.state, "Acquisition pending — thesis viewable but trading action suppressed"
        elif listing.state == SecurityState.HALTED:
            return False, listing.state, "Trading currently halted — frozen ranking"
        else:
            return False, listing.state, f"Listing state {listing.state.value} does not permit active recommendation"
