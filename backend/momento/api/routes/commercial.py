"""Commercial API routes for V5 multi-scope architecture.

This module provides REST API endpoints for:
- Subscription management
- Billing and payment operations
- Usage tracking and analytics
- Revenue reporting
- Customer lifecycle management
- Admin workflows
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from pydantic import BaseModel, Field

from ..deps import get_current_user
from ... import commercial_service as cs, stripe_service as ss
from fastapi import Header

logger = logging.getLogger("momento.api.commercial")

router = APIRouter(prefix="/commercial", tags=["commercial"])


# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------

class SubscriptionPlanCreate(BaseModel):
    """Model for creating a subscription plan."""
    id: str = Field(..., description="Unique plan identifier")
    name: str = Field(..., description="Plan name")
    scope: str = Field(..., description="Scope identifier")
    price_monthly: float = Field(..., ge=0, description="Monthly price")
    price_yearly: float = Field(..., ge=0, description="Yearly price")
    currency: str = Field(default="USD", description="Currency code")
    features: List[str] = Field(default_factory=list, description="List of features")
    rate_limit: int = Field(default=1000, ge=1, description="API rate limit per minute")
    api_access: Dict[str, Any] = Field(default_factory=dict, description="API access configuration")
    support_level: str = Field(default="community", description="Support level")
    sla: Optional[str] = Field(None, description="Service level agreement")
    max_users: Optional[int] = Field(None, description="Maximum users")
    storage_gb: Optional[float] = Field(None, ge=0, description="Storage in GB")


class SubscriptionPlanUpdate(BaseModel):
    """Model for updating a subscription plan."""
    name: Optional[str] = None
    price_monthly: Optional[float] = Field(None, ge=0)
    price_yearly: Optional[float] = Field(None, ge=0)
    currency: Optional[str] = None
    features: Optional[List[str]] = None
    rate_limit: Optional[int] = Field(None, ge=1)
    api_access: Optional[Dict[str, Any]] = None
    support_level: Optional[str] = None
    sla: Optional[str] = None
    max_users: Optional[int] = None
    storage_gb: Optional[float] = Field(None, ge=0)
    active: Optional[bool] = None


class UserSubscriptionCreate(BaseModel):
    """Model for creating a user subscription."""
    plan_id: str = Field(..., description="Plan ID")
    billing_period: str = Field(default="monthly", description="Billing period")
    trial_days: Optional[int] = Field(None, ge=0, description="Trial period in days")
    stripe_customer_id: Optional[str] = Field(None, description="Stripe customer ID")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Custom metadata")


class UserSubscriptionUpdate(BaseModel):
    """Model for updating a user subscription."""
    plan_id: Optional[str] = None
    status: Optional[str] = None
    billing_period: Optional[str] = None
    cancel_at_period_end: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None
    reason: Optional[str] = Field(None, description="Reason for change")


class PaymentMethodCreate(BaseModel):
    """Model for creating a payment method."""
    stripe_payment_method_id: str = Field(..., description="Stripe payment method ID")
    payment_type: str = Field(..., description="Payment method type")
    brand: Optional[str] = Field(None, description="Card brand")
    last4: Optional[str] = Field(None, description="Last 4 digits")
    expiry_month: Optional[int] = Field(None, ge=1, le=12)
    expiry_year: Optional[int] = Field(None, ge=2020)
    is_default: bool = Field(default=False, description="Set as default")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class InvoiceCreate(BaseModel):
    """Model for creating an invoice."""
    subscription_id: str = Field(..., description="Subscription ID")
    amount: float = Field(..., ge=0, description="Invoice amount")
    currency: str = Field(default="USD", description="Currency code")
    status: str = Field(default="draft", description="Invoice status")
    due_date: Optional[str] = Field(None, description="Due date ISO string")
    description: Optional[str] = Field(None, description="Invoice description")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class InvoiceUpdate(BaseModel):
    """Model for updating an invoice."""
    stripe_invoice_id: Optional[str] = None
    status: Optional[str] = None
    due_date: Optional[str] = None
    paid_at: Optional[str] = None
    hosted_invoice_url: Optional[str] = None
    invoice_pdf_url: Optional[str] = None
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class InvoiceLineItemCreate(BaseModel):
    """Model for creating an invoice line item."""
    description: str = Field(..., description="Line item description")
    quantity: int = Field(default=1, ge=1, description="Quantity")
    unit_price: float = Field(default=0.0, ge=0, description="Unit price")
    period_start: Optional[str] = Field(None, description="Period start ISO string")
    period_end: Optional[str] = Field(None, description="Period end ISO string")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class UsageTrack(BaseModel):
    """Model for tracking usage."""
    subscription_id: str = Field(..., description="Subscription ID")
    metric_type: str = Field(..., description="Metric type")
    metric_value: float = Field(..., ge=0, description="Metric value")
    unit: str = Field(default="count", description="Unit of measurement")
    period_start: Optional[str] = Field(None, description="Period start ISO string")
    period_end: Optional[str] = Field(None, description="Period end ISO string")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class ApiUsageLog(BaseModel):
    """Model for logging API usage."""
    subscription_id: Optional[str] = Field(None, description="Subscription ID")
    endpoint: str = Field(..., description="API endpoint")
    method: str = Field(..., description="HTTP method")
    status_code: int = Field(..., description="HTTP status code")
    response_time_ms: float = Field(..., ge=0, description="Response time in milliseconds")
    request_size: Optional[int] = Field(None, ge=0, description="Request size in bytes")
    response_size: Optional[int] = Field(None, ge=0, description="Response size in bytes")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Subscription Plan Endpoints
# ---------------------------------------------------------------------------

@router.get("/plans")
async def list_subscription_plans(
    active_only: bool = Query(default=True, description="Only show active plans")
) -> List[Dict[str, Any]]:
    """List all subscription plans."""
    try:
        plans = cs.get_subscription_plans(active_only=active_only)
        return plans
    except Exception as e:
        logger.error(f"Error listing subscription plans: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/plans/{plan_id}")
async def get_subscription_plan(plan_id: str) -> Dict[str, Any]:
    """Get a specific subscription plan."""
    try:
        plan = cs.get_subscription_plan(plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
        return plan
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting subscription plan: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/plans/scope/{scope}")
async def get_plan_by_scope(scope: str) -> Dict[str, Any]:
    """Get subscription plan by scope."""
    try:
        plan = cs.get_plan_by_scope(scope)
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found for scope")
        return plan
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting plan by scope: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/plans", status_code=status.HTTP_201_CREATED)
async def create_subscription_plan(
    plan_data: SubscriptionPlanCreate,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Create a new subscription plan (admin only)."""
    try:
        # Check admin permissions
        if current_user.get("role") not in ["admin", "platform_owner"]:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        plan = cs.create_subscription_plan(
            plan_id=plan_data.id,
            name=plan_data.name,
            scope=plan_data.scope,
            price_monthly=plan_data.price_monthly,
            price_yearly=plan_data.price_yearly,
            currency=plan_data.currency,
            features=plan_data.features,
            rate_limit=plan_data.rate_limit,
            api_access=plan_data.api_access,
            support_level=plan_data.support_level,
            sla=plan_data.sla,
            max_users=plan_data.max_users,
            storage_gb=plan_data.storage_gb
        )
        return plan
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating subscription plan: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/plans/{plan_id}")
async def update_subscription_plan(
    plan_id: str,
    plan_data: SubscriptionPlanUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Update a subscription plan (admin only)."""
    try:
        # Check admin permissions
        if current_user.get("role") not in ["admin", "platform_owner"]:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # Build update dict
        updates = {}
        if plan_data.name is not None:
            updates["name"] = plan_data.name
        if plan_data.price_monthly is not None:
            updates["price_monthly"] = plan_data.price_monthly
        if plan_data.price_yearly is not None:
            updates["price_yearly"] = plan_data.price_yearly
        if plan_data.currency is not None:
            updates["currency"] = plan_data.currency
        if plan_data.features is not None:
            updates["features"] = plan_data.features
        if plan_data.rate_limit is not None:
            updates["rate_limit"] = plan_data.rate_limit
        if plan_data.api_access is not None:
            updates["api_access"] = plan_data.api_access
        if plan_data.support_level is not None:
            updates["support_level"] = plan_data.support_level
        if plan_data.sla is not None:
            updates["sla"] = plan_data.sla
        if plan_data.max_users is not None:
            updates["max_users"] = plan_data.max_users
        if plan_data.storage_gb is not None:
            updates["storage_gb"] = plan_data.storage_gb
        if plan_data.active is not None:
            updates["active"] = 1 if plan_data.active else 0
        
        plan = cs.update_subscription_plan(plan_id, **updates)
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
        return plan
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating subscription plan: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# User Subscription Endpoints
# ---------------------------------------------------------------------------

@router.get("/subscriptions/me")
async def get_my_subscription(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get current user's subscription."""
    try:
        subscription = cs.get_user_subscription(current_user["id"])
        if not subscription:
            return {"message": "No active subscription"}
        return subscription
    except Exception as e:
        logger.error(f"Error getting user subscription: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/subscriptions/{subscription_id}")
async def get_subscription(
    subscription_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get a specific subscription."""
    try:
        subscription = cs.get_subscription_by_id(subscription_id)
        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")
        
        # Check ownership or admin
        if subscription["user_id"] != current_user["id"] and current_user.get("role") not in ["admin", "platform_owner"]:
            raise HTTPException(status_code=403, detail="Access denied")
        
        return subscription
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting subscription: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/subscriptions", status_code=status.HTTP_201_CREATED)
async def create_subscription(
    subscription_data: UserSubscriptionCreate,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Create a new subscription for current user."""
    try:
        subscription = cs.create_user_subscription(
            user_id=current_user["id"],
            plan_id=subscription_data.plan_id,
            billing_period=subscription_data.billing_period,
            trial_days=subscription_data.trial_days,
            stripe_customer_id=subscription_data.stripe_customer_id,
            metadata=subscription_data.metadata
        )
        return subscription
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating subscription: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/subscriptions/{subscription_id}")
async def update_subscription(
    subscription_id: str,
    subscription_data: UserSubscriptionUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Update a subscription."""
    try:
        # Check ownership or admin
        subscription = cs.get_subscription_by_id(subscription_id)
        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")
        
        if subscription["user_id"] != current_user["id"] and current_user.get("role") not in ["admin", "platform_owner"]:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Build update dict
        updates = {}
        if subscription_data.plan_id is not None:
            updates["plan_id"] = subscription_data.plan_id
        if subscription_data.status is not None:
            updates["status"] = subscription_data.status
        if subscription_data.billing_period is not None:
            updates["billing_period"] = subscription_data.billing_period
        if subscription_data.cancel_at_period_end is not None:
            updates["cancel_at_period_end"] = 1 if subscription_data.cancel_at_period_end else 0
        if subscription_data.metadata is not None:
            updates["metadata"] = subscription_data.metadata
        if subscription_data.reason is not None:
            updates["reason"] = subscription_data.reason
        
        updated = cs.update_user_subscription(subscription_id, **updates)
        return updated
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating subscription: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/subscriptions/{subscription_id}/cancel")
async def cancel_subscription(
    subscription_id: str,
    cancel_at_period_end: bool = Query(default=True, description="Cancel at period end"),
    reason: str = Query(default="User requested cancellation", description="Cancellation reason"),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Cancel a subscription."""
    try:
        # Check ownership or admin
        subscription = cs.get_subscription_by_id(subscription_id)
        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")
        
        if subscription["user_id"] != current_user["id"] and current_user.get("role") not in ["admin", "platform_owner"]:
            raise HTTPException(status_code=403, detail="Access denied")
        
        updated = cs.cancel_subscription(
            subscription_id,
            cancel_at_period_end=cancel_at_period_end,
            reason=reason
        )
        return updated
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error canceling subscription: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/subscriptions/{subscription_id}/history")
async def get_subscription_history(
    subscription_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """Get subscription history."""
    try:
        # Check ownership or admin
        subscription = cs.get_subscription_by_id(subscription_id)
        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")
        
        if subscription["user_id"] != current_user["id"] and current_user.get("role") not in ["admin", "platform_owner"]:
            raise HTTPException(status_code=403, detail="Access denied")
        
        history = cs.get_subscription_history(subscription_id=subscription_id, limit=limit)
        return history
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting subscription history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Payment Method Endpoints
# ---------------------------------------------------------------------------

@router.post("/payment-methods", status_code=status.HTTP_201_CREATED)
async def create_payment_method(
    payment_data: PaymentMethodCreate,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Create a payment method for current user."""
    try:
        payment_method = cs.create_payment_method(
            user_id=current_user["id"],
            stripe_payment_method_id=payment_data.stripe_payment_method_id,
            payment_type=payment_data.payment_type,
            brand=payment_data.brand,
            last4=payment_data.last4,
            expiry_month=payment_data.expiry_month,
            expiry_year=payment_data.expiry_year,
            is_default=payment_data.is_default,
            metadata=payment_data.metadata
        )
        return payment_method
    except Exception as e:
        logger.error(f"Error creating payment method: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/payment-methods")
async def list_payment_methods(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """List payment methods for current user."""
    try:
        payment_methods = cs.get_user_payment_methods(current_user["id"])
        return payment_methods
    except Exception as e:
        logger.error(f"Error listing payment methods: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/payment-methods/{payment_method_id}/default")
async def set_default_payment_method(
    payment_method_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Set default payment method."""
    try:
        success = cs.set_default_payment_method(current_user["id"], payment_method_id)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to set default payment method")
        return {"message": "Default payment method updated"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting default payment method: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Invoice Endpoints
# ---------------------------------------------------------------------------

@router.post("/invoices", status_code=status.HTTP_201_CREATED)
async def create_invoice(
    invoice_data: InvoiceCreate,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Create an invoice."""
    try:
        invoice = cs.create_invoice(
            user_id=current_user["id"],
            subscription_id=invoice_data.subscription_id,
            amount=invoice_data.amount,
            currency=invoice_data.currency,
            status=invoice_data.status,
            due_date=invoice_data.due_date,
            description=invoice_data.description,
            metadata=invoice_data.metadata
        )
        return invoice
    except Exception as e:
        logger.error(f"Error creating invoice: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/invoices/{invoice_id}")
async def get_invoice(
    invoice_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get an invoice."""
    try:
        invoice = cs.get_invoice(invoice_id)
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        # Check ownership or admin
        if invoice["user_id"] != current_user["id"] and current_user.get("role") not in ["admin", "platform_owner"]:
            raise HTTPException(status_code=403, detail="Access denied")
        
        return invoice
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting invoice: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/invoices")
async def list_invoices(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """List invoices for current user."""
    try:
        invoices = cs.get_user_invoices(
            user_id=current_user["id"],
            status=status,
            limit=limit
        )
        return invoices
    except Exception as e:
        logger.error(f"Error listing invoices: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/invoices/{invoice_id}")
async def update_invoice(
    invoice_id: str,
    invoice_data: InvoiceUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Update an invoice (admin only)."""
    try:
        # Check admin permissions
        if current_user.get("role") not in ["admin", "platform_owner"]:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # Build update dict
        updates = {}
        if invoice_data.stripe_invoice_id is not None:
            updates["stripe_invoice_id"] = invoice_data.stripe_invoice_id
        if invoice_data.status is not None:
            updates["status"] = invoice_data.status
        if invoice_data.due_date is not None:
            updates["due_date"] = invoice_data.due_date
        if invoice_data.paid_at is not None:
            updates["paid_at"] = invoice_data.paid_at
        if invoice_data.hosted_invoice_url is not None:
            updates["hosted_invoice_url"] = invoice_data.hosted_invoice_url
        if invoice_data.invoice_pdf_url is not None:
            updates["invoice_pdf_url"] = invoice_data.invoice_pdf_url
        if invoice_data.description is not None:
            updates["description"] = invoice_data.description
        if invoice_data.metadata is not None:
            updates["metadata"] = invoice_data.metadata
        
        updated = cs.update_invoice(invoice_id, **updates)
        if not updated:
            raise HTTPException(status_code=404, detail="Invoice not found")
        return updated
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating invoice: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/invoices/{invoice_id}/items", status_code=status.HTTP_201_CREATED)
async def add_invoice_line_item(
    invoice_id: str,
    item_data: InvoiceLineItemCreate,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Add a line item to an invoice."""
    try:
        # Check invoice ownership or admin
        invoice = cs.get_invoice(invoice_id)
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        if invoice["user_id"] != current_user["id"] and current_user.get("role") not in ["admin", "platform_owner"]:
            raise HTTPException(status_code=403, detail="Access denied")
        
        line_item = cs.add_invoice_line_item(
            invoice_id=invoice_id,
            description=item_data.description,
            quantity=item_data.quantity,
            unit_price=item_data.unit_price,
            period_start=item_data.period_start,
            period_end=item_data.period_end,
            metadata=item_data.metadata
        )
        return line_item
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding invoice line item: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/invoices/{invoice_id}/items")
async def get_invoice_items(
    invoice_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """Get line items for an invoice."""
    try:
        # Check invoice ownership or admin
        invoice = cs.get_invoice(invoice_id)
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        if invoice["user_id"] != current_user["id"] and current_user.get("role") not in ["admin", "platform_owner"]:
            raise HTTPException(status_code=403, detail="Access denied")
        
        items = cs.get_invoice_line_items(invoice_id)
        return items
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting invoice items: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Usage Tracking Endpoints
# ---------------------------------------------------------------------------

@router.post("/usage/track")
async def track_usage(
    usage_data: UsageTrack,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Track usage metric."""
    try:
        result = cs.track_usage(
            user_id=current_user["id"],
            subscription_id=usage_data.subscription_id,
            metric_type=usage_data.metric_type,
            metric_value=usage_data.metric_value,
            unit=usage_data.unit,
            period_start=usage_data.period_start,
            period_end=usage_data.period_end,
            metadata=usage_data.metadata
        )
        return result
    except Exception as e:
        logger.error(f"Error tracking usage: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/usage")
async def get_usage(
    metric_type: Optional[str] = Query(None, description="Filter by metric type"),
    period_start: Optional[str] = Query(None, description="Period start ISO string"),
    period_end: Optional[str] = Query(None, description="Period end ISO string"),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """Get usage data for current user."""
    try:
        usage = cs.get_user_usage(
            user_id=current_user["id"],
            metric_type=metric_type,
            period_start=period_start,
            period_end=period_end
        )
        return usage
    except Exception as e:
        logger.error(f"Error getting usage: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/usage/aggregated")
async def get_aggregated_usage(
    metric_type: str = Query(..., description="Metric type"),
    period_start: str = Query(..., description="Period start ISO string"),
    period_end: str = Query(..., description="Period end ISO string"),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get aggregated usage for a metric and period."""
    try:
        aggregated = cs.get_aggregated_usage(
            user_id=current_user["id"],
            metric_type=metric_type,
            period_start=period_start,
            period_end=period_end
        )
        return aggregated
    except Exception as e:
        logger.error(f"Error getting aggregated usage: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/usage/api-log")
async def log_api_usage(
    usage_data: ApiUsageLog,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Log API usage (internal use)."""
    try:
        cs.log_api_usage(
            user_id=current_user["id"],
            subscription_id=usage_data.subscription_id,
            endpoint=usage_data.endpoint,
            method=usage_data.method,
            status_code=usage_data.status_code,
            response_time_ms=usage_data.response_time_ms,
            request_size=usage_data.request_size,
            response_size=usage_data.response_size,
            metadata=usage_data.metadata
        )
        return {"message": "API usage logged"}
    except Exception as e:
        logger.error(f"Error logging API usage: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Revenue Tracking Endpoints
# ---------------------------------------------------------------------------

@router.get("/revenue/current")
async def get_current_revenue(
    period: str = Query(default="monthly", description="Period: daily, weekly, monthly, yearly"),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get current revenue metrics (admin only)."""
    try:
        # Check admin permissions
        if current_user.get("role") not in ["admin", "platform_owner"]:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        revenue = cs.calculate_revenue(period=period)
        return revenue
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating revenue: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/revenue/history")
async def get_revenue_history(
    period: Optional[str] = Query(None, description="Filter by period"),
    plan_id: Optional[str] = Query(None, description="Filter by plan ID"),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """Get revenue history (admin only)."""
    try:
        # Check admin permissions
        if current_user.get("role") not in ["admin", "platform_owner"]:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        history = cs.get_revenue_history(period=period, plan_id=plan_id, limit=limit)
        return history
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting revenue history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/revenue/plan/{plan_id}")
async def get_plan_revenue(
    plan_id: str,
    months: int = Query(default=12, ge=1, le=36, description="Number of months"),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """Get monthly revenue for a specific plan (admin only)."""
    try:
        # Check admin permissions
        if current_user.get("role") not in ["admin", "platform_owner"]:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        revenue = cs.get_revenue_by_plan(plan_id=plan_id, months=months)
        return revenue
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting plan revenue: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Customer Lifecycle Endpoints
# ---------------------------------------------------------------------------

@router.get("/lifecycle/me")
async def get_my_lifecycle(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get current user's lifecycle data."""
    try:
        lifecycle = cs.get_customer_lifecycle_data(current_user["id"])
        return lifecycle
    except Exception as e:
        logger.error(f"Error getting lifecycle data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/lifecycle/churn-risk/me")
async def get_my_churn_risk(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get current user's churn risk analysis."""
    try:
        risk = cs.get_churn_risk_analysis(current_user["id"])
        return risk
    except Exception as e:
        logger.error(f"Error getting churn risk: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/lifecycle/expansion/me")
async def get_my_expansion_opportunities(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """Get expansion opportunities for current user."""
    try:
        opportunities = cs.get_expansion_opportunities(current_user["id"])
        return opportunities
    except Exception as e:
        logger.error(f"Error getting expansion opportunities: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/lifecycle/user/{user_id}")
async def get_user_lifecycle(
    user_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get lifecycle data for a specific user (admin only)."""
    try:
        # Check admin permissions
        if current_user.get("role") not in ["admin", "platform_owner"]:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        lifecycle = cs.get_customer_lifecycle_data(user_id)
        return lifecycle
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user lifecycle: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Admin Workflow Endpoints
# ---------------------------------------------------------------------------

@router.get("/admin/dashboard")
async def get_admin_dashboard(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get admin dashboard data (admin only)."""
    try:
        # Check admin permissions
        if current_user.get("role") not in ["admin", "platform_owner"]:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        dashboard = cs.get_admin_dashboard_data()
        return dashboard
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting admin dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/users")
async def get_admin_users(
    limit: int = Query(default=50, ge=1, le=200),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """Get user management data (admin only)."""
    try:
        # Check admin permissions
        if current_user.get("role") not in ["admin", "platform_owner"]:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        users = cs.get_admin_user_management_data(limit=limit)
        return users
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting admin users: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/financial-report")
async def get_financial_report(
    period_start: Optional[str] = Query(None, description="Period start ISO string"),
    period_end: Optional[str] = Query(None, description="Period end ISO string"),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get financial report (admin only)."""
    try:
        # Check admin permissions
        if current_user.get("role") not in ["admin", "platform_owner"]:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        report = cs.get_admin_financial_report(
            period_start=period_start,
            period_end=period_end
        )
        return report
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting financial report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/initialize-schema", status_code=status.HTTP_201_CREATED)
async def initialize_commercial_schema(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Initialize commercial schema and default plans (admin only)."""
    try:
        # Check admin permissions
        if current_user.get("role") not in ["admin", "platform_owner"]:
            raise HTTPException(status_code=403, detail="Admin access required")
        
        cs.initialize_commercial_schema()
        return {"message": "Commercial schema initialized successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error initializing commercial schema: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Stripe Webhook Endpoints
# ---------------------------------------------------------------------------

@router.post("/stripe/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(..., alias="Stripe-Signature")
) -> Dict[str, Any]:
    """Handle Stripe webhook events."""
    try:
        # Read request body
        payload = await request.body()
        
        # Verify webhook signature
        if not ss.verify_webhook_signature(payload, stripe_signature):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid webhook signature"
            )
        
        # Parse event
        import stripe
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, ss.STRIPE_WEBHOOK_SECRET
        )
        
        # Handle event
        result = ss.handle_webhook_event(event)
        
        return {
            "status": "success",
            "event_type": event["type"],
            "event_id": event["id"],
            "result": result
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing Stripe webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stripe/customer")
async def create_stripe_customer(
    email: str = Query(..., description="Customer email"),
    name: Optional[str] = Query(None, description="Customer name"),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Create a Stripe customer for the current user."""
    try:
        customer = ss.create_stripe_customer(
            user_id=current_user["id"],
            email=email,
            name=name
        )
        return customer
    except Exception as e:
        logger.error(f"Error creating Stripe customer: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stripe/payment-method")
async def add_payment_method(
    payment_method_id: str = Query(..., description="Stripe payment method ID"),
    is_default: bool = Query(default=False, description="Set as default payment method"),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Add a payment method for the current user."""
    try:
        # Get user's Stripe customer ID
        subscription = cs.get_user_subscription(current_user["id"])
        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")
        
        stripe_customer_id = subscription.get("stripe_customer_id")
        if not stripe_customer_id:
            raise HTTPException(status_code=400, detail="Stripe customer not found")
        
        payment_method = ss.create_payment_method(
            user_id=current_user["id"],
            stripe_customer_id=stripe_customer_id,
            payment_method_id=payment_method_id,
            is_default=is_default
        )
        return payment_method
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding payment method: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stripe/subscription")
async def create_stripe_subscription(
    plan_id: str = Query(..., description="Plan ID"),
    billing_period: str = Query(default="monthly", description="Billing period"),
    payment_method_id: Optional[str] = Query(None, description="Payment method ID"),
    trial_days: Optional[int] = Query(None, description="Trial period in days"),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Create a Stripe subscription for the current user."""
    try:
        # Get user's Stripe customer ID
        subscription = cs.get_user_subscription(current_user["id"])
        stripe_customer_id = subscription.get("stripe_customer_id") if subscription else None
        
        if not stripe_customer_id:
            raise HTTPException(status_code=400, detail="Stripe customer not found")
        
        subscription = ss.create_stripe_subscription(
            user_id=current_user["id"],
            stripe_customer_id=stripe_customer_id,
            plan_id=plan_id,
            billing_period=billing_period,
            trial_period_days=trial_days,
            payment_method_id=payment_method_id
        )
        return subscription
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating Stripe subscription: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/stripe/subscription/{subscription_id}")
async def cancel_stripe_subscription(
    subscription_id: str,
    cancel_at_period_end: bool = Query(default=True, description="Cancel at period end"),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Cancel a Stripe subscription."""
    try:
        result = ss.cancel_stripe_subscription(
            subscription_id=subscription_id,
            cancel_at_period_end=cancel_at_period_end
        )
        return result
    except Exception as e:
        logger.error(f"Error cancelling Stripe subscription: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/stripe/subscription/{subscription_id}")
async def update_stripe_subscription(
    subscription_id: str,
    new_plan_id: str = Query(..., description="New plan ID"),
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """Update a Stripe subscription (plan change)."""
    try:
        result = ss.update_stripe_subscription(
            subscription_id=subscription_id,
            new_plan_id=new_plan_id
        )
        return result
    except Exception as e:
        logger.error(f"Error updating Stripe subscription: {e}")
        raise HTTPException(status_code=500, detail=str(e))