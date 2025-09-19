    # Stripe Course Platform (Full Payments Demo)

This repo is a full-feature starter for an online course platform with extensive Stripe integration. It demonstrates:

- One-time payments via Stripe Checkout (handled server-side). Supports connected accounts (Stripe Connect) by passing 'instructor_account' when creating sessions.
- Direct PaymentIntents API for custom card flows (client_secret returned).
- Subscription checkout sessions (for recurring/all-access passes) with trial period support.
- Webhook handling for checkout.session.completed, invoice.paid, charge.refunded, etc. (endpoint at /webhooks/stripe/)
- Coupons & discounts: apply coupons by creating Price or passing discounts in Checkout (docs included).
- 3D Secure / SCA: handled by Stripe when using PaymentIntents/Checkout — client-side challenge via Stripe.js automatically.
- Instructor payouts and Connect onboarding: placeholder for creating Express accounts and setting transfer_data on Checkout sessions.
- Refunds: use Stripe Refund API (admin endpoint can be added easily).

## Quickstart
1. unzip and cd into project
2. Set environment variables in backend/.env.example (STRIPE keys, PUBLIC_BASE_URL)
3. Run with Docker Compose: `docker-compose up --build`
4. In backend container, run migrations and seed courses:
   ```bash
   docker exec -it <backend_container> python manage.py migrate
   docker exec -it <backend_container> python manage.py seed_courses
   ```
5. Configure a Stripe webhook (or use stripe CLI) to forward events to `https://<PUBLIC_BASE_URL>/webhooks/stripe/` and set `STRIPE_WEBHOOK_SECRET` in .env.

## Notes
- This starter focuses on payment flows. Add authentication, instructor dashboards, video hosting, and content security for production.
- For subscriptions and prices: it's often better to create Prices in Stripe dashboard and reference their IDs when creating Checkout sessions.
- Always verify webhooks in production using the `STRIPE_WEBHOOK_SECRET`.

If you want, I can:
- Implement Connect onboarding endpoint and automated payouts with sample UI.
- Add saved payment methods (SetupIntent) and customer portal integration.
- Wire a full subscription management UI (cancel, update, invoices).
- Add Stripe Billing & tax handling (VAT/MOSS).


## Expanded Features Implemented

- Stripe Connect account creation & onboarding link endpoints.
- SetupIntent endpoint to save customer payment methods and retrieve client_secret.
- Customer Portal session creation endpoint (Stripe Billing Portal).
- Subscription cancel endpoint.
- Checkout creation with optional coupon application.
- Webhook handler extended for payout and subscription events.

## Frontend additions

- Buttons in the dashboard to create SetupIntent, open Customer Portal, and start Connect onboarding.

Note: This is a starter integration. In production you must persist customer IDs, account IDs, and securely handle webhooks with STRIPE_WEBHOOK_SECRET.


## PayPal Integration Added

This project now supports PayPal alongside Stripe: one-time course purchases and subscriptions via PayPal Orders/Subscriptions APIs, webhooks, and payouts. Configure PAYPAL_CLIENT_ID and PAYPAL_SECRET in backend/.env.example.
