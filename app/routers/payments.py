from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import stripe

from app.config import settings
from app.db import get_session
from app.deps import auth_required
from app.models import Payment, PaymentMethod, User
from app.schemas import PaymentCheckoutIn, PaymentMethodOut

router = APIRouter()


@router.get("/me", response_model=PaymentMethodOut)
async def get_my_payment_method(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(auth_required),
):
    res = await session.execute(
        select(PaymentMethod).where(PaymentMethod.user_id == user.id)
    )
    method = res.scalars().first()
    if not method:
        raise HTTPException(status_code=404, detail="Payment method not found")
    return method


@router.post("/checkout")
async def create_checkout_session(
    payload: PaymentCheckoutIn,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(auth_required),
):
    if payload.provider == "mobile":
        # Mobile money flow handled outside Stripe. Preserve existing behavior.
        return {
            "provider": "mobile",
            "detail": "Mobile payment flow unchanged",
        }

    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stripe is not configured",
        )

    success_url = (
        f"{settings.FRONTEND_DOMAIN.rstrip('/')}/payments/success?session_id="
        "{CHECKOUT_SESSION_ID}"
    )
    cancel_url = f"{settings.FRONTEND_DOMAIN.rstrip('/')}/payments/cancel"

    stripe.api_key = settings.STRIPE_SECRET_KEY
    try:
        checkout_session = stripe.checkout.Session.create(
            mode="payment",
            payment_method_types=["card"],
            customer_email=user.email,
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={"user_id": str(user.id)},
        )
    except stripe.error.StripeError as exc:  # pragma: no cover - handled in tests via mocking
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    payment = Payment(
        user_id=user.id,
        provider="stripe",
        status="pending",
        external_id=checkout_session.get("id"),
        metadata_json={"mode": checkout_session.get("mode")},
    )
    session.add(payment)
    await session.commit()

    return {
        "checkout_url": checkout_session.get("url"),
        "session_id": checkout_session.get("id"),
    }


@router.post("/webhook/stripe")
async def stripe_webhook(
    request: Request,
    session: AsyncSession = Depends(get_session),
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
):
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=400, detail="Stripe webhook secret missing")
    if stripe_signature is None:
        raise HTTPException(status_code=400, detail="Missing Stripe signature")

    payload = await request.body()
    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, settings.STRIPE_WEBHOOK_SECRET
        )
    except (ValueError, stripe.error.SignatureVerificationError) as exc:
        raise HTTPException(status_code=400, detail="Invalid Stripe payload") from exc

    if event.get("type") == "checkout.session.completed":
        data_object: dict[str, Any] = event.get("data", {}).get("object", {})
        session_id = data_object.get("id")
        metadata = data_object.get("metadata") or {}

        payment = (
            await session.execute(
                select(Payment).where(Payment.external_id == session_id)
            )
        ).scalar_one_or_none()

        user: User | None = None
        if payment:
            payment.status = "paid"
            user = (
                await session.execute(select(User).where(User.id == payment.user_id))
            ).scalar_one_or_none()
            if payment.metadata_json is None:
                payment.metadata_json = metadata
        else:
            user_id = metadata.get("user_id")
            if user_id is not None:
                user = (
                    await session.execute(select(User).where(User.id == int(user_id)))
                ).scalar_one_or_none()
            if user:
                payment = Payment(
                    user_id=user.id,
                    provider="stripe",
                    status="paid",
                    external_id=session_id,
                    metadata_json=metadata,
                )
                session.add(payment)

        if user and not user.is_active:
            user.is_active = True

        await session.commit()

    return {"received": True}

