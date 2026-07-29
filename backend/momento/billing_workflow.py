"""Billing workflow automation for V5 commercial features.

This service provides:
- Automated invoice generation
- Payment retry logic
- Subscription renewal handling
- Dunning management
- Billing reminders
- Usage-based billing calculations
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from enum import Enum

from . import db, commercial_service as cs, stripe_service as ss, pricing_service as ps

logger = logging.getLogger("momento.billing_workflow")


# ---------------------------------------------------------------------------
# Enums and Constants
# ---------------------------------------------------------------------------

class BillingStatus(str, Enum):
    """Billing workflow status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"


class DunningStage(str, Enum):
    """Dunning process stages."""
    INITIAL = "initial"
    REMINDER_1 = "reminder_1"
    REMINDER_2 = "reminder_2"
    REMINDER_3 = "reminder_3"
    FINAL = "final"
    CANCELLED = "cancelled"


# ---------------------------------------------------------------------------
# Invoice Generation
# ---------------------------------------------------------------------------

def generate_monthly_invoices() -> List[Dict[str, Any]]:
    """Generate invoices for all active subscriptions due for billing."""
    now = datetime.now(timezone.utc)
    
    # Get subscriptions due for billing (period ending within next 7 days)
    rows = db.query(
        """SELECT * FROM user_subscriptions 
           WHERE status = 'active' 
           AND datetime(current_period_end) <= datetime('now', '+7 days')
           AND cancel_at_period_end = 0""",
    )
    
    subscriptions = [db.rows_to_dicts([row])[0] for row in rows]
    
    invoices_created = []
    
    for subscription in subscriptions:
        try:
            invoice = generate_subscription_invoice(subscription["id"])
            invoices_created.append(invoice)
        except Exception as e:
            logger.error(f"Error generating invoice for subscription {subscription['id']}: {e}")
    
    logger.info(f"Generated {len(invoices_created)} monthly invoices")
    return invoices_created


def generate_subscription_invoice(subscription_id: str) -> Dict[str, Any]:
    """Generate an invoice for a specific subscription."""
    subscription = cs.get_subscription_by_id(subscription_id)
    if not subscription:
        raise ValueError(f"Subscription {subscription_id} not found")
    
    plan = cs.get_subscription_plan(subscription["plan_id"])
    if not plan:
        raise ValueError(f"Plan {subscription['plan_id']} not found")
    
    # Calculate base subscription cost
    billing_period = subscription["billing_period"]
    base_amount = plan["price_monthly"] if billing_period == "monthly" else plan["price_yearly"]
    
    # Calculate usage-based costs
    user_id = subscription["user_id"]
    period_start = subscription["current_period_start"]
    period_end = subscription["current_period_end"]
    
    usage_cost_data = ps.calculate_monthly_usage_cost(
        user_id=user_id,
        subscription_id=subscription_id,
        period_start=period_start,
        period_end=period_end
    )
    
    usage_amount = usage_cost_data["total_cost"]
    
    # Total amount
    total_amount = base_amount + usage_amount
    
    # Create invoice
    invoice = cs.create_invoice(
        subscription_id=subscription_id,
        amount=total_amount,
        currency=plan["currency"],
        status="draft",
        description=f"{billing_period.capitalize()} subscription billing",
        metadata={
            "billing_period": billing_period,
            "base_amount": base_amount,
            "usage_amount": usage_amount,
            "period_start": period_start,
            "period_end": period_end
        }
    )
    
    # Add line items
    # Base subscription
    cs.add_invoice_line_item(
        invoice_id=invoice["id"],
        description=f"{plan['name']} - {billing_period} subscription",
        quantity=1,
        unit_price=base_amount,
        period_start=period_start,
        period_end=period_end
    )
    
    # Usage-based items
    for feature_cost in usage_cost_data["feature_costs"]:
        cs.add_invoice_line_item(
            invoice_id=invoice["id"],
            description=f"{feature_cost['feature_key']} usage",
            quantity=int(feature_cost["billable_units"]),
            unit_price=feature_cost["unit_price"],
            period_start=period_start,
            period_end=period_end
        )
    
    # Finalize invoice
    cs.update_invoice(invoice["id"], status="open")
    
    # Create billing alert
    cs.create_billing_alert(
        user_id=user_id,
        subscription_id=subscription_id,
        alert_type="invoice_created",
        alert_level="info",
        message=f"Invoice {invoice['id']} created for ${total_amount:.2f}"
    )
    
    logger.info(f"Generated invoice {invoice['id']} for subscription {subscription_id}")
    return invoice


# ---------------------------------------------------------------------------
# Payment Processing
# ---------------------------------------------------------------------------

def process_pending_invoices() -> List[Dict[str, Any]]:
    """Process all pending invoices."""
    # Get open invoices
    rows = db.query(
        """SELECT * FROM invoices 
           WHERE status = 'open' 
           AND datetime(due_date) <= datetime('now')""",
    )
    
    invoices = [db.rows_to_dicts([row])[0] for row in rows]
    
    processed = []
    
    for invoice in invoices:
        try:
            result = process_invoice_payment(invoice["id"])
            processed.append(result)
        except Exception as e:
            logger.error(f"Error processing invoice {invoice['id']}: {e}")
    
    logger.info(f"Processed {len(processed)} pending invoices")
    return processed


def process_invoice_payment(invoice_id: str) -> Dict[str, Any]:
    """Process payment for an invoice."""
    invoice = cs.get_invoice(invoice_id)
    if not invoice:
        raise ValueError(f"Invoice {invoice_id} not found")
    
    subscription = cs.get_subscription_by_id(invoice["subscription_id"])
    if not subscription:
        raise ValueError(f"Subscription {invoice['subscription_id']} not found")
    
    # If Stripe is configured, process through Stripe
    if subscription.get("stripe_customer_id"):
        try:
            stripe_invoice = ss.create_invoice(
                subscription_id=invoice["subscription_id"],
                amount=invoice["amount"],
                currency=invoice["currency"],
                description=invoice["description"]
            )
            
            # Update local invoice
            cs.update_invoice(
                invoice_id=invoice_id,
                status="paid",
                paid_at=db.utc_now(),
                stripe_invoice_id=stripe_invoice.get("id")
            )
            
            # Clear billing alerts
            cs.resolve_billing_alerts(invoice["subscription_id"], "payment_failed")
            
            return {
                "invoice_id": invoice_id,
                "status": "paid",
                "method": "stripe"
            }
        except Exception as e:
            logger.error(f"Stripe payment failed for invoice {invoice_id}: {e}")
            
            # Update invoice status
            cs.update_invoice(invoice_id, status="open")
            
            # Create billing alert
            cs.create_billing_alert(
                user_id=subscription["user_id"],
                subscription_id=subscription["id"],
                alert_type="payment_failed",
                alert_level="critical",
                message=f"Payment failed for invoice {invoice_id}: {str(e)}"
            )
            
            # Start dunning process
            start_dunning_process(invoice_id)
            
            return {
                "invoice_id": invoice_id,
                "status": "failed",
                "method": "stripe",
                "error": str(e)
            }
    else:
        # Mock payment for testing
        cs.update_invoice(
            invoice_id=invoice_id,
            status="paid",
            paid_at=db.utc_now()
        )
        
        return {
            "invoice_id": invoice_id,
            "status": "paid",
            "method": "mock"
        }


# ---------------------------------------------------------------------------
# Dunning Management
# ---------------------------------------------------------------------------

def start_dunning_process(invoice_id: str) -> Dict[str, Any]:
    """Start the dunning process for a failed payment."""
    invoice = cs.get_invoice(invoice_id)
    if not invoice:
        raise ValueError(f"Invoice {invoice_id} not found")
    
    subscription = cs.get_subscription_by_id(invoice["subscription_id"])
    if not subscription:
        raise ValueError(f"Subscription {invoice['subscription_id']} not found")
    
    # Record dunning event
    dunning_data = {
        "invoice_id": invoice_id,
        "subscription_id": subscription["id"],
        "stage": DunningStage.INITIAL,
        "failed_at": db.utc_now(),
        "retry_count": 0
    }
    
    # Schedule retry (1 day later)
    schedule_payment_retry(invoice_id, days=1)
    
    logger.info(f"Started dunning process for invoice {invoice_id}")
    return dunning_data


def schedule_payment_retry(invoice_id: str, days: int = 1) -> None:
    """Schedule a payment retry for an invoice."""
    # In production, this would use a task queue (Celery, etc.)
    # For now, we'll just log it
    retry_date = datetime.now(timezone.utc) + timedelta(days=days)
    logger.info(f"Scheduled payment retry for invoice {invoice_id} at {retry_date}")
    
    # Update invoice metadata with retry schedule
    invoice = cs.get_invoice(invoice_id)
    metadata = invoice.get("metadata", {})
    if isinstance(metadata, str):
        import json
        metadata = json.loads(metadata)
    
    metadata["next_retry"] = retry_date.isoformat()
    metadata["retry_count"] = metadata.get("retry_count", 0) + 1
    
    cs.update_invoice(invoice_id, metadata=metadata)


def retry_payment(invoice_id: str) -> Dict[str, Any]:
    """Retry payment for an invoice."""
    invoice = cs.get_invoice(invoice_id)
    if not invoice:
        raise ValueError(f"Invoice {invoice_id} not found")
    
    if invoice["status"] == "paid":
        return {"invoice_id": invoice_id, "status": "already_paid"}
    
    # Process payment again
    return process_invoice_payment(invoice_id)


def check_dunning_status() -> List[Dict[str, Any]]:
    """Check and update dunning status for all failed invoices."""
    # Get invoices with failed payments
    rows = db.query(
        """SELECT * FROM invoices 
           WHERE status = 'open' 
           AND datetime(due_date) < datetime('now', '-1 day')""",
    )
    
    invoices = [db.rows_to_dicts([row])[0] for row in rows]
    
    dunning_updates = []
    
    for invoice in invoices:
        metadata = invoice.get("metadata", {})
        if isinstance(metadata, str):
            import json
            metadata = json.loads(metadata)
        
        retry_count = metadata.get("retry_count", 0)
        
        # Determine dunning stage based on retry count
        if retry_count == 0:
            stage = DunningStage.INITIAL
        elif retry_count == 1:
            stage = DunningStage.REMINDER_1
        elif retry_count == 2:
            stage = DunningStage.REMINDER_2
        elif retry_count == 3:
            stage = DunningStage.REMINDER_3
        elif retry_count >= 4:
            stage = DunningStage.FINAL
        else:
            stage = DunningStage.INITIAL
        
        # Check if we should cancel subscription
        if stage == DunningStage.FINAL and retry_count >= 5:
            # Cancel subscription
            subscription = cs.get_subscription_by_id(invoice["subscription_id"])
            if subscription:
                cs.cancel_subscription(subscription["id"], cancel_at_period_end=False)
                stage = DunningStage.CANCELLED
        
        dunning_updates.append({
            "invoice_id": invoice["id"],
            "stage": stage,
            "retry_count": retry_count
        })
    
    return dunning_updates


# ---------------------------------------------------------------------------
# Subscription Renewal
# ---------------------------------------------------------------------------

def process_subscription_renewals() -> List[Dict[str, Any]]:
    """Process subscription renewals for expiring subscriptions."""
    now = datetime.now(timezone.utc)
    
    # Get subscriptions expiring within next 3 days
    rows = db.query(
        """SELECT * FROM user_subscriptions 
           WHERE status = 'active' 
           AND datetime(current_period_end) <= datetime('now', '+3 days')
           AND cancel_at_period_end = 0""",
    )
    
    subscriptions = [db.rows_to_dicts([row])[0] for row in rows]
    
    renewals = []
    
    for subscription in subscriptions:
        try:
            renewal = renew_subscription(subscription["id"])
            renewals.append(renewal)
        except Exception as e:
            logger.error(f"Error renewing subscription {subscription['id']}: {e}")
    
    logger.info(f"Processed {len(renewals)} subscription renewals")
    return renewals


def renew_subscription(subscription_id: str) -> Dict[str, Any]:
    """Renew a subscription."""
    subscription = cs.get_subscription_by_id(subscription_id)
    if not subscription:
        raise ValueError(f"Subscription {subscription_id} not found")
    
    # Generate invoice for the renewal period
    invoice = generate_subscription_invoice(subscription_id)
    
    # Process payment
    payment_result = process_invoice_payment(invoice["id"])
    
    if payment_result["status"] == "paid":
        # Extend subscription period
        billing_period = subscription["billing_period"]
        current_end = datetime.fromisoformat(subscription["current_period_end"])
        
        if billing_period == "monthly":
            new_end = current_end + timedelta(days=30)
        else:
            new_end = current_end + timedelta(days=365)
        
        # Update subscription
        cs.update_user_subscription(
            subscription_id=subscription_id,
            current_period_end=new_end.isoformat()
        )
        
        # Record renewal in history using the public interface
        # We'll update the subscription with a reason to trigger history recording
        cs.update_user_subscription(
            subscription_id=subscription_id,
            reason="Automatic renewal"
        )
        
        logger.info(f"Renewed subscription {subscription_id}")
        return {
            "subscription_id": subscription_id,
            "status": "renewed",
            "new_period_end": new_end.isoformat()
        }
    else:
        logger.warning(f"Payment failed for subscription renewal {subscription_id}")
        return {
            "subscription_id": subscription_id,
            "status": "payment_failed",
            "invoice_id": invoice["id"]
        }


# ---------------------------------------------------------------------------
# Billing Reminders
# ---------------------------------------------------------------------------

def send_billing_reminders() -> List[Dict[str, Any]]:
    """Send billing reminders for upcoming payments."""
    now = datetime.now(timezone.utc)
    
    # Get subscriptions with payments due in 3 days
    rows = db.query(
        """SELECT * FROM user_subscriptions 
           WHERE status = 'active' 
           AND datetime(current_period_end) <= datetime('now', '+3 days')
           AND datetime(current_period_end) > datetime('now', '+2 days')
           AND cancel_at_period_end = 0""",
    )
    
    subscriptions = [db.rows_to_dicts([row])[0] for row in rows]
    
    reminders_sent = []
    
    for subscription in subscriptions:
        try:
            plan = cs.get_subscription_plan(subscription["plan_id"])
            amount = plan["price_monthly"] if subscription["billing_period"] == "monthly" else plan["price_yearly"]
            
            # Create billing alert as reminder
            cs.create_billing_alert(
                user_id=subscription["user_id"],
                subscription_id=subscription["id"],
                alert_type="payment_due",
                alert_level="warning",
                message=f"Payment of ${amount:.2f} due in 3 days"
            )
            
            reminders_sent.append({
                "subscription_id": subscription["id"],
                "user_id": subscription["user_id"],
                "amount": amount,
                "due_date": subscription["current_period_end"]
            })
        except Exception as e:
            logger.error(f"Error sending billing reminder for subscription {subscription['id']}: {e}")
    
    logger.info(f"Sent {len(reminders_sent)} billing reminders")
    return reminders_sent


# ---------------------------------------------------------------------------
# Scheduled Tasks
# ---------------------------------------------------------------------------

def run_daily_billing_tasks() -> Dict[str, Any]:
    """Run all daily billing tasks."""
    logger.info("Running daily billing tasks")
    
    results = {
        "timestamp": db.utc_now(),
        "invoices_generated": 0,
        "payments_processed": 0,
        "renewals_processed": 0,
        "reminders_sent": 0,
        "dunning_checks": 0
    }
    
    try:
        # Generate invoices
        invoices = generate_monthly_invoices()
        results["invoices_generated"] = len(invoices)
    except Exception as e:
        logger.error(f"Error in invoice generation: {e}")
    
    try:
        # Process payments
        payments = process_pending_invoices()
        results["payments_processed"] = len(payments)
    except Exception as e:
        logger.error(f"Error in payment processing: {e}")
    
    try:
        # Process renewals
        renewals = process_subscription_renewals()
        results["renewals_processed"] = len(renewals)
    except Exception as e:
        logger.error(f"Error in renewal processing: {e}")
    
    try:
        # Send reminders
        reminders = send_billing_reminders()
        results["reminders_sent"] = len(reminders)
    except Exception as e:
        logger.error(f"Error in reminder sending: {e}")
    
    try:
        # Check dunning status
        dunning = check_dunning_status()
        results["dunning_checks"] = len(dunning)
    except Exception as e:
        logger.error(f"Error in dunning check: {e}")
    
    logger.info(f"Daily billing tasks completed: {results}")
    return results


def run_hourly_billing_tasks() -> Dict[str, Any]:
    """Run hourly billing tasks (payment retries, etc.)."""
    logger.info("Running hourly billing tasks")
    
    results = {
        "timestamp": db.utc_now(),
        "payment_retries": 0
    }
    
    try:
        # Check for invoices that need retry
        rows = db.query(
            """SELECT * FROM invoices 
               WHERE status = 'open' 
               AND metadata LIKE '%next_retry%'
               AND datetime(json_extract(metadata, '$.next_retry')) <= datetime('now')"""
        )
        
        invoices = [db.rows_to_dicts([row])[0] for row in rows]
        
        for invoice in invoices:
            try:
                retry_payment(invoice["id"])
                results["payment_retries"] += 1
            except Exception as e:
                logger.error(f"Error retrying payment for invoice {invoice['id']}: {e}")
    except Exception as e:
        logger.error(f"Error in payment retry check: {e}")
    
    logger.info(f"Hourly billing tasks completed: {results}")
    return results
