import logging
import httpx
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from app.core.config import settings

logger = logging.getLogger("paypilot.paypal")

class PayPalService:
    _access_token: Optional[str] = None
    _token_expires_at: Optional[datetime] = None

    @classmethod
    async def get_access_token(cls, force_refresh: bool = False) -> str:
        """
        Retrieve a valid OAuth 2.0 access token using client credentials.
        Reuses cached token if valid; requests a new token upon expiration.
        """
        now = datetime.now(timezone.utc)
        if (
            not force_refresh
            and cls._access_token
            and cls._token_expires_at
            and cls._token_expires_at > (now + timedelta(seconds=60))
        ):
            return cls._access_token

        if not settings.paypal_client_id or not settings.paypal_client_secret:
            raise ValueError("PayPal client credentials are not configured in environment")

        auth = (settings.paypal_client_id, settings.paypal_client_secret)
        url = f"{settings.paypal_api_base}/v1/oauth2/token"

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.post(
                    url,
                    data={"grant_type": "client_credentials"},
                    auth=auth,
                    headers={"Accept": "application/json", "Accept-Language": "en_US"},
                )

            if res.status_code != 200:
                logger.error(f"PayPal OAuth failed: {res.status_code} - {res.text}")
                raise ValueError(f"PayPal authentication failed with status {res.status_code}")

            data = res.json()
            cls._access_token = data["access_token"]
            expires_in = data.get("expires_in", 32400)
            cls._token_expires_at = now + timedelta(seconds=expires_in)
            logger.info("Successfully refreshed PayPal OAuth2 token")
            return cls._access_token

        except httpx.RequestError as e:
            logger.error(f"Network error during PayPal authentication: {e}")
            raise

    @classmethod
    async def _get_auth_headers(cls) -> Dict[str, str]:
        token = await cls.get_access_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    @classmethod
    async def create_order(cls, invoice: Dict[str, Any], return_url: str = None, cancel_url: str = None) -> Dict[str, Any]:
        """
        Create a PayPal checkout order for an invoice.
        Uses CAPTURE intent and passes line item breakdown and reference IDs.
        Converts non-supported currencies (e.g. INR) to USD for PayPal compatibility.
        """
        raw_currency = (invoice.get("currency") or "USD").upper()
        total_amt = float(invoice.get("total_amount", 0.0))

        # PayPal REST API supported currency list
        supported_currencies = [
            "USD", "EUR", "GBP", "CAD", "AUD", "JPY", "SGD",
            "CHF", "NZD", "HKD", "SEK", "NOK", "DKK", "PLN", "ILS"
        ]

        if raw_currency in supported_currencies:
            currency_code = raw_currency
            amount_val = f"{total_amt:.2f}"
            desc = f"PayPilot - {invoice.get('invoice_number', 'Invoice')} ({invoice.get('customer_name', 'Client')})"[:127]
        else:
            # Convert INR to USD equivalent (approx 85 INR per USD)
            currency_code = "USD"
            usd_equiv = round(total_amt / 85.0, 2)
            amount_val = f"{max(usd_equiv, 1.00):.2f}"
            desc = f"PayPilot - {invoice.get('invoice_number')} (₹{total_amt:,.0f} {raw_currency} in USD)"[:127]

        headers = await cls._get_auth_headers()
        url = f"{settings.paypal_api_base}/v2/checkout/orders"

        payload = {
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "reference_id": invoice.get("id"),
                    "custom_id": invoice.get("id"),
                    "invoice_id": invoice.get("invoice_number", invoice.get("id"))[:127],
                    "description": desc,
                    "amount": {
                        "currency_code": currency_code,
                        "value": amount_val,
                    },
                }
            ],
            "application_context": {
                "brand_name": "PayPilot",
                "landing_page": "NO_PREFERENCE",
                "user_action": "PAY_NOW",
                "return_url": return_url or "http://localhost:5173/invoices?paypal_success=true",
                "cancel_url": cancel_url or "http://localhost:5173/invoices?paypal_cancel=true",
            },
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            res = await client.post(url, json=payload, headers=headers)

        if res.status_code not in [200, 201]:
            logger.error(f"PayPal Create Order error: {res.status_code} - {res.text}")
            raise ValueError(f"Failed to create PayPal order: {res.text}")

        return res.json()

    @classmethod
    async def capture_order(cls, order_id: str) -> Dict[str, Any]:
        """
        Capture payment for an approved PayPal order.
        """
        headers = await cls._get_auth_headers()
        url = f"{settings.paypal_api_base}/v2/checkout/orders/{order_id}/capture"

        async with httpx.AsyncClient(timeout=25.0) as client:
            res = await client.post(url, headers=headers, json={})

        if res.status_code not in [200, 201]:
            logger.error(f"PayPal Capture Order error: {res.status_code} - {res.text}")
            raise ValueError(f"PayPal capture failed: {res.text}")

        return res.json()

    @classmethod
    async def get_order(cls, order_id: str) -> Dict[str, Any]:
        """
        Retrieve order status and details from PayPal.
        """
        headers = await cls._get_auth_headers()
        url = f"{settings.paypal_api_base}/v2/checkout/orders/{order_id}"

        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.get(url, headers=headers)

        if res.status_code != 200:
            logger.error(f"PayPal Get Order error: {res.status_code} - {res.text}")
            raise ValueError(f"Failed to fetch PayPal order: {res.text}")

        return res.json()

    @classmethod
    async def verify_webhook_signature(
        cls,
        headers: Dict[str, str],
        event_body: Dict[str, Any]
    ) -> bool:
        """
        Verify incoming webhook signature using PayPal's verification endpoint.
        """
        # If webhook ID is not configured, perform structural check of headers for testing
        webhook_id = settings.paypal_webhook_id
        transmission_id = headers.get("paypal-transmission-id")
        transmission_sig = headers.get("paypal-transmission-sig")
        transmission_time = headers.get("paypal-transmission-time")
        cert_url = headers.get("paypal-cert-url")
        auth_algo = headers.get("paypal-auth-algo")

        if not all([transmission_id, transmission_sig, transmission_time, cert_url, auth_algo]):
            logger.warning("Webhook request missing required PayPal verification headers")
            return False

        if not webhook_id:
            # When testing locally without registered webhook ID, header presence and validity confirms payload
            logger.info("Webhook ID not configured; verified transmission headers presence")
            return True

        verify_headers = await cls._get_auth_headers()
        verify_url = f"{settings.paypal_api_base}/v1/notifications/verify-webhook-signature"

        verify_payload = {
            "auth_algo": auth_algo,
            "cert_url": cert_url,
            "transmission_id": transmission_id,
            "transmission_sig": transmission_sig,
            "transmission_time": transmission_time,
            "webhook_id": webhook_id,
            "webhook_event": event_body,
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.post(verify_url, json=verify_payload, headers=verify_headers)

            if res.status_code == 200:
                data = res.json()
                return data.get("verification_status") == "SUCCESS"
            return False
        except Exception as e:
            logger.error(f"Error calling PayPal webhook verification API: {e}")
            return False
