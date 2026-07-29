"""Stripe integration service for V5 commercial features.

This service provides:
- Customer management in Stripe
- Subscription creation and management
- Payment method handling
- Invoice generation and management
- Webhook event processing
- Payment failure handling
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

import stripe

from . import db, config, commercial_service as cs

logger = logging.getLogger("momento.stripe_service")

# Initialize Stripe with API key from config or environment
STRIPE_API_KEY = os.getenv("STRIPE_API_KEY") or getattr(config, "STRIPE_API_KEY", None)
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET") or getattr(config, "STRIPE_WEBHOOK_SECRET", None)

if STRIPE_API_KEY:
    stripe.api_key = STRIPE_API_KEY
else:
    logger.warning("STRIPE_API_KEY not configured - Stripe integration will be in test mode")


# ---------------------------------------------------------------------------
# Enums and Constants
# ---------------------------------------------------------------------------

class StripeEventType(str, Enum):
    """Stripe webhook event types."""
    CUSTOMER_CREATED = "customer.created"
    CUSTOMER_UPDATED = "customer.updated"
    CUSTOMER_DELETED = "customer.deleted"
    CUSTOMER_SUBSCRIPTION_CREATED = "customer.subscription.created"
    CUSTOMER_SUBSCRIPTION_UPDATED = "customer.subscription.updated"
    CUSTOMER_SUBSCRIPTION_DELETED = "customer.subscription.deleted"
    INVOICE_PAYMENT_SUCCEEDED = "invoice.payment_succeeded"
    INVOICE_PAYMENT_FAILED = "invoice.payment_failed"
    INVOICE_CREATED = "invoice.created"
    PAYMENT_INTENT_SUCCEEDED = "payment_intent.succeeded"
    PAYMENT_INTENT_FAILED = "payment_intent.failed"


# ---------------------------------------------------------------------------
# Customer Management
# ---------------------------------------------------------------------------

def create_stripe_customer(
    user_id: int,
    email: str,
    name: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create a customer in Stripe."""
    if not STRIPE_API_KEY:
        logger.warning("Stripe API key not configured - returning mock customer")
        return {
            "id": f"cus_mock_{user_id}",
            "email": email,
            "name": name,
            "metadata": metadata or {}
        }
    
    try:
        customer_params = {
            "email": email,
            "metadata": {
                "user_id": str(user_id),
                **(metadata or {})
            }
        }
        
        if name:
            customer_params["name"] = name
        
        customer = stripe.Customer.create(**customer_params)
        
        logger.info(f"Created Stripe customer: {customer.id} for user {user_id}")
        return {
            "id": customer.id,
            "email": customer.email,
            "name": customer.name,
            "metadata": customer.metadata
        }
    except stripe.error.StripeError as e:
        logger.error(f"Error creating Stripe customer: {e}")
        raise


def get_stripe_customer(stripe_customer_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a customer from Stripe."""
    if not STRIPE_API_KEY:
        return None
    
    try:
        customer = stripe.Customer.retrieve(stripe_customer_id)
        return {
            "id": customer.id,
            "email": customer.email,
            "name": customer.name,
            "metadata": customer.metadata
        }
    except stripe.error.StripeError as e:
        logger.error(f"Error retrieving Stripe customer: {e}")
        return None


def update_stripe_customer(
    stripe_customer_id: str,
    **updates
) -> Optional[Dict[str, Any]]:
    """Update a customer in Stripe."""
    if not STRIPE_API_KEY:
        return None
    
    try:
        customer = stripe.Customer.modify(stripe_customer_id, **updates)
        return {
            "id": customer.id,
            "email": customer.email,
            "name": customer.name,
            "metadata": customer.metadata
        }
    except stripe.error.StripeError as e:
        logger.error(f"Error updating Stripe customer: {e}")
        return None


# ---------------------------------------------------------------------------
# Payment Methods
# ---------------------------------------------------------------------------

def create_payment_method(
    user_id: int,
    stripe_customer_id: str,
    payment_method_id: str,
    is_default: bool = False,
) -> Dict[str, Any]:
    """Attach a payment method to a customer."""
    if not STRIPE_API_KEY:
        logger.warning("Stripe API key not configured - creating mock payment method")
        return {
            "id": f"pm_mock_{payment_method_id}",
            "type": "card",
            "card": {"brand": "visa", "last4": "4242"}
        }
    
    try:
        # Attach payment method to customer
        payment_method = stripe.PaymentMethod.attach(
            payment_method_id,
            customer=stripe_customer_id
        )
        
        # Set as default if requested
        if is_default:
            stripe.Customer.modify(
                stripe_customer_id,
                invoice_settings={"default_payment_method": payment_method_id}
            )
        
        # Store in database
        card = payment_method.card if hasattr(payment_method, 'card') else None
        
        cs.create_payment_method(
            user_id=user_id,
            stripe_payment_method_id=payment_method_id,
            payment_type=payment_method.type,
            brand=card.brand if card else None,
            last4=card.last4 if card else None,
            expiry_month=card.exp_month if card else None,
            expiry_year=card.exp_year if card else None,
            is_default=is_default
        )
        
        logger.info(f"Created payment method: {payment_method_id} for user {user_id}")
        return {
            "id": payment_method.id,
            "type": payment_method.type,
            "card": {
                "brand": card.brand if card else None,
                "last4": card.last4 if card else None,
                "exp_month": card.exp_month if card else None,
                "exp_year": card.exp_year if card else None
            }
        }
    except stripe.error.StripeError as e:
        logger.error(f"Error creating payment method: {e}")
        raise


def list_payment_methods(stripe_customer_id: str) -> List[Dict[str, Any]]:
    """List payment methods for a customer."""
    if not STRIPE_API_KEY:
        return []
    
    try:
        payment_methods = stripe.PaymentMethod.list(
            customer=stripe_customer_id,
            type="card"
        )
        
        return [
            {
                "id": pm.id,
                "type": pm.type,
                "card": {
                    "brand": pm.card.brand if hasattr(pm, 'card') else None,
                    "last4": pm.card.last4 if hasattr(pm, 'card') else None,
                    "exp_month": pm.card.exp_month if hasattr(pm, 'card') else None,
                    "exp_year": pm.card.exp_year if hasattr(pm, 'card') else None
                }
            }
            for pm in payment_methods.data
        ]
    except stripe.error.StripeError as e:
        logger.error(f"Error listing payment methods: {e}")
        return []


# ---------------------------------------------------------------------------
# Subscription Management
# ---------------------------------------------------------------------------

def create_stripe_subscription(
    user_id: int,
    stripe_customer_id: str,
    plan_id: str,
    billing_period: str = "monthly",
    trial_period_days: Optional[int] = None,
    payment_method_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create a subscription in Stripe."""
    if not STRIPE_API_KEY:
        logger.warning("Stripe API key not configured - creating mock subscription")
        # Create local subscription without Stripe
        return cs.create_user_subscription(
            user_id=user_id,
            plan_id=plan_id,
            billing_period=billing_period,
            trial_days=trial_period_days,
            stripe_customer_id=stripe_customer_id,
            metadata=metadata
        )
    
    try:
        # Get plan details
        plan = cs.get_subscription_plan(plan_id)
        if not plan:
            raise ValueError(f"Plan {plan_id} not found")
        
        # Determine price ID based on billing period
        # In production, you would map plan_id to Stripe price IDs
        price_id = plan.get(f"stripe_price_{billing_period}")
        if not price_id:
            # For now, use a placeholder - in production, create Stripe prices
            price_id = f"price_{plan_id}_{billing_period}"
        
        subscription_params = {
            "customer": stripe_customer_id,
            "items": [{"price": price_id}],
            "metadata": {
                "user_id": str(user_id),
                "plan_id": plan_id,
                **(metadata or {})
            }
        }
        
        if trial_period_days:
            subscription_params["trial_period_days"] = trial_period_days
        
        if payment_method_id:
            subscription_params["default_payment_method"] = payment_method_id
        
        # Create subscription
        stripe_subscription = stripe.Subscription.create(**subscription_params)
        
        # Create local subscription
        local_subscription = cs.create_user_subscription(
            user_id=user_id,
            plan_id=plan_id,
            billing_period=billing_period,
            trial_days=trial_period_days,
            stripe_customer_id=stripe_customer_id,
            stripe_subscription_id=stripe_subscription.id,
            metadata={
                **(metadata or {}),
                "stripe_subscription_id": stripe_subscription.id
            }
        )
        
        logger.info(f"Created Stripe subscription: {stripe_subscription.id} for user {user_id}")
        return local_subscription
    except stripe.error.StripeError as e:
        logger.error(f"Error creating Stripe subscription: {e}")
        raise


def cancel_stripe_subscription(
    subscription_id: str,
    cancel_at_period_end: bool = True,
) -> Dict[str, Any]:
    """Cancel a subscription in Stripe."""
    if not STRIPE_API_KEY:
        # Cancel local subscription
        return cs.cancel_subscription(subscription_id, cancel_at_period_end=cancel_at_period_end)
    
    try:
        # Get local subscription
        local_sub = cs.get_subscription_by_id(subscription_id)
        if not local_sub:
            raise ValueError(f"Subscription {subscription_id} not found")
        
        stripe_subscription_id = local_sub.get("stripe_subscription_id")
        
        if stripe_subscription_id:
            if cancel_at_period_end:
                stripe.Subscription.modify(
                    stripe_subscription_id,
                    cancel_at_period_end=True
                )
            else:
                stripe.Subscription.delete(stripe_subscription_id)
        
        # Cancel local subscription
        result = cs.cancel_subscription(subscription_id, cancel_at_period_end=cancel_at_period_end)
        
        logger.info(f"Cancelled Stripe subscription: {stripe_subscription_id}")
        return result
    except stripe.error.StripeError as e:
        logger.error(f"Error cancelling Stripe subscription: {e}")
        raise


def update_stripe_subscription(
    subscription_id: str,
    new_plan_id: str,
    proration_behavior: str = "create_prorations",
) -> Dict[str, Any]:
    """Update a subscription in Stripe (plan change)."""
    if not STRIPE_API_KEY:
        # Update local subscription
        return cs.update_user_subscription(
            subscription_id=subscription_id,
            plan_id=new_plan_id,
            reason="Plan change"
        )
    
    try:
        # Get local subscription
        local_sub = cs.get_subscription_by_id(subscription_id)
        if not local_sub:
            raise ValueError(f"Subscription {subscription_id} not found")
        
        stripe_subscription_id = local_sub.get("stripe_subscription_id")
        
        if stripe_subscription_id:
            # Get new plan details
            new_plan = cs.get_subscription_plan(new_plan_id)
            if not new_plan:
                raise ValueError(f"Plan {new_plan_id} not found")
            
            # Determine new price ID
            billing_period = local_sub.get("billing_period", "monthly")
            price_id = new_plan.get(f"stripe_price_{billing_period}")
            if not price_id:
                price_id = f"price_{new_plan_id}_{billing_period}"
            
            # Update Stripe subscription
            stripe.Subscription.modify(
                stripe_subscription_id,
                items=[{
                    "id": local_sub.get("stripe_subscription_item_id"),
                    "price": price_id
                }],
                proration_behavior=proration_behavior
            )
        
        # Update local subscription
        result = cs.update_user_subscription(
            subscription_id=subscription_id,
            plan_id=new_plan_id,
            reason="Plan upgrade/downgrade"
        )
        
        logger.info(f"Updated Stripe subscription: {stripe_subscription_id} to plan {new_plan_id}")
        return result
    except stripe.error.StripeError as e:
        logger.error(f"Error updating Stripe subscription: {e}")
        raise


# ---------------------------------------------------------------------------
# Invoice Management
# ---------------------------------------------------------------------------

def create_invoice(
    subscription_id: str,
    amount: float,
    currency: str = "USD",
    description: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create an invoice in Stripe."""
    if not STRIPE_API_KEY:
        # Create local invoice
        return cs.create_invoice(
            subscription_id=subscription_id,
            amount=amount,
            currency=currency,
            description=description,
            metadata=metadata
        )
    
    try:
        # Get local subscription
        local_sub = cs.get_subscription_by_id(subscription_id)
        if not local_sub:
            raise ValueError(f"Subscription {subscription_id} not found")
        
        stripe_customer_id = local_sub.get("stripe_customer_id")
        
        if stripe_customer_id:
            # Create invoice in Stripe
            invoice = stripe.Invoice.create(
                customer=stripe_customer_id,
                description=description,
                metadata=metadata or {}
            )
            
            # Add invoice item
            stripe.InvoiceItem.create(
                customer=stripe_customer_id,
                amount=int(amount * 100),  # Convert to cents
                currency=currency,
                description=description or "Subscription billing"
            )
            
            # Finalize invoice
            invoice = stripe.Invoice.pay(invoice.id)
            
            # Create local invoice
            local_invoice = cs.create_invoice(
                subscription_id=subscription_id,
                amount=amount,
                currency=currency,
                status="paid" if invoice.paid else "open",
                stripe_invoice_id=invoice.id,
                hosted_invoice_url=invoice.hosted_invoice_url,
                invoice_pdf_url=invoice.invoice_pdf,
                description=description,
                metadata=metadata
            )
            
            logger.info(f"Created Stripe invoice: {invoice.id}")
            return local_invoice
        else:
            # Create local invoice without Stripe
            return cs.create_invoice(
                subscription_id=subscription_id,
                amount=amount,
                currency=currency,
                description=description,
                metadata=metadata
            )
    except stripe.error.StripeError as e:
        logger.error(f"Error creating Stripe invoice: {e}")
        raise


def get_invoice(invoice_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve an invoice from Stripe."""
    if not STRIPE_API_KEY:
        return cs.get_invoice(invoice_id)
    
    try:
        invoice = stripe.Invoice.retrieve(invoice_id)
        return {
            "id": invoice.id,
            "amount": invoice.amount_due / 100,
            "currency": invoice.currency,
            "status": invoice.status,
            "paid": invoice.paid,
            "hosted_invoice_url": invoice.hosted_invoice_url,
            "invoice_pdf_url": invoice.invoice_pdf
        }
    except stripe.error.StripeError as e:
        logger.error(f"Error retrieving Stripe invoice: {e}")
        return None


# ---------------------------------------------------------------------------
# Webhook Handling
# ---------------------------------------------------------------------------

def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    """Verify Stripe webhook signature."""
    if not STRIPE_WEBHOOK_SECRET:
        logger.warning("Stripe webhook secret not configured - skipping verification")
        return True
    
    try:
        stripe.Webhook.construct_event(
            payload, signature, STRIPE_WEBHOOK_SECRET
        )
        return True
    except ValueError:
        logger.error("Invalid webhook payload")
        return False
    except stripe.error.SignatureVerificationError:
        logger.error("Invalid webhook signature")
        return False


def handle_webhook_event(event_data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle a Stripe webhook event."""
    event_type = event_data.get("type")
    event_id = event_data.get("id")
    
    logger.info(f"Processing Stripe webhook event: {event_type} ({event_id})")
    
    try:
        if event_type == StripeEventType.CUSTOMER_CREATED:
            return _handle_customer_created(event_data)
        elif event_type == StripeEventType.CUSTOMER_UPDATED:
            return _handle_customer_updated(event_data)
        elif event_type == StripeEventType.CUSTOMER_SUBSCRIPTION_CREATED:
            return _handle_subscription_created(event_data)
        elif event_type == StripeEventType.CUSTOMER_SUBSCRIPTION_UPDATED:
            return _handle_subscription_updated(event_data)
        elif event_type == StripeEventType.CUSTOMER_SUBSCRIPTION_DELETED:
            return _handle_subscription_deleted(event_data)
        elif event_type == StripeEventType.INVOICE_PAYMENT_SUCCEEDED:
            return _handle_invoice_payment_succeeded(event_data)
        elif event_type == StripeEventType.INVOICE_PAYMENT_FAILED:
            return _handle_invoice_payment_failed(event_data)
        elif event_type == StripeEventType.INVOICE_CREATED:
            return _handle_invoice_created(event_data)
        else:
            logger.info(f"Unhandled event type: {event_type}")
            return {"status": "ignored", "event_type": event_type}
    except Exception as e:
        logger.error(f"Error handling webhook event {event_type}: {e}")
        raise


def _handle_customer_created(event_data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle customer.created event."""
    customer = event_data["data"]["object"]
    user_id = customer.get("metadata", {}).get("user_id")
    
    if user_id:
        # Update user with Stripe customer ID
        cs.update_user_stripe_customer(int(user_id), customer["id"])
    
    return {"status": "processed", "event_type": "customer.created"}


def _handle_customer_updated(event_data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle customer.updated event."""
    customer = event_data["data"]["object"]
    # Update customer information if needed
    return {"status": "processed", "event_type": "customer.updated"}


def _handle_subscription_created(event_data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle customer.subscription.created event."""
    subscription = event_data["data"]["object"]
    stripe_customer_id = subscription["customer"]
    stripe_subscription_id = subscription["id"]
    
    # Find local subscription by Stripe ID
    local_sub = cs.get_subscription_by_stripe_id(stripe_subscription_id)
    
    if local_sub:
        # Update local subscription status
        cs.update_user_subscription(
            local_sub["id"],
            status=subscription["status"],
            current_period_start=subscription["current_period_start"],
            current_period_end=subscription["current_period_end"]
        )
    
    return {"status": "processed", "event_type": "customer.subscription.created"}


def _handle_subscription_updated(event_data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle customer.subscription.updated event."""
    subscription = event_data["data"]["object"]
    stripe_subscription_id = subscription["id"]
    
    # Find local subscription by Stripe ID
    local_sub = cs.get_subscription_by_stripe_id(stripe_subscription_id)
    
    if local_sub:
        # Update local subscription
        cs.update_user_subscription(
            local_sub["id"],
            status=subscription["status"],
            cancel_at_period_end=subscription.get("cancel_at_period_end", False),
            current_period_start=subscription["current_period_start"],
            current_period_end=subscription["current_period_end"]
        )
    
    return {"status": "processed", "event_type": "customer.subscription.updated"}


def _handle_subscription_deleted(event_data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle customer.subscription.deleted event."""
    subscription = event_data["data"]["object"]
    stripe_subscription_id = subscription["id"]
    
    # Find local subscription by Stripe ID
    local_sub = cs.get_subscription_by_stripe_id(stripe_subscription_id)
    
    if local_sub:
        # Cancel local subscription
        cs.cancel_subscription(local_sub["id"], cancel_at_period_end=False)
    
    return {"status": "processed", "event_type": "customer.subscription.deleted"}


def _handle_invoice_payment_succeeded(event_data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle invoice.payment_succeeded event."""
    invoice = event_data["data"]["object"]
    stripe_invoice_id = invoice["id"]
    stripe_subscription_id = invoice.get("subscription")
    
    # Update local invoice
    local_invoice = cs.get_invoice_by_stripe_id(stripe_invoice_id)
    if local_invoice:
        cs.update_invoice(
            local_invoice["id"],
            status="paid",
            paid_at=invoice["status_transitions"]["paid_at"]
        )
    
    # Clear billing alerts if any
    if stripe_subscription_id:
        local_sub = cs.get_subscription_by_stripe_id(stripe_subscription_id)
        if local_sub:
            cs.resolve_billing_alerts(local_sub["id"], "payment_failed")
    
    return {"status": "processed", "event_type": "invoice.payment_succeeded"}


def _handle_invoice_payment_failed(event_data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle invoice.payment_failed event."""
    invoice = event_data["data"]["object"]
    stripe_invoice_id = invoice["id"]
    stripe_subscription_id = invoice.get("subscription")
    
    # Update local invoice
    local_invoice = cs.get_invoice_by_stripe_id(stripe_invoice_id)
    if local_invoice:
        cs.update_invoice(local_invoice["id"], status="open")
    
    # Create billing alert
    if stripe_subscription_id:
        local_sub = cs.get_subscription_by_stripe_id(stripe_subscription_id)
        if local_sub:
            cs.create_billing_alert(
                user_id=local_sub["user_id"],
                subscription_id=local_sub["id"],
                alert_type="payment_failed",
                alert_level="critical",
                message=f"Payment failed for invoice {stripe_invoice_id}"
            )
    
    return {"status": "processed", "event_type": "invoice.payment_failed"}


def _handle_invoice_created(event_data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle invoice.created event."""
    invoice = event_data["data"]["object"]
    stripe_invoice_id = invoice["id"]
    stripe_subscription_id = invoice.get("subscription")
    
    # Create billing alert for new invoice
    if stripe_subscription_id:
        local_sub = cs.get_subscription_by_stripe_id(stripe_subscription_id)
        if local_sub:
            cs.create_billing_alert(
                user_id=local_sub["user_id"],
                subscription_id=local_sub["id"],
                alert_type="invoice_created",
                alert_level="info",
                message=f"New invoice created: {stripe_invoice_id}"
            )
    
    return {"status": "processed", "event_type": "invoice.created"}
