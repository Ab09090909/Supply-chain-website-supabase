"""Customer shopping cart."""
from __future__ import annotations

import streamlit as st

from auth.session import get_current_user
from database.connection import get_supabase_client
from utils.ui import page_header
from utils.helpers import format_currency, generate_order_number


def render_customer_cart():
    page_header("Shopping Cart", "Review items and place your order")

    user = get_current_user()
    if not user:
        return

    client = get_supabase_client()

    try:
        cart_items = (
            client.table("cart_items")
            .select("*, products(*)")
            .eq("user_id", user["id"])
            .execute()
        ).data or []
    except Exception as e:
        st.error(f"Failed to load cart: {e}")
        return

    if not cart_items:
        st.info("🛒 Your cart is empty. Browse the marketplace to add products!")
        return

    subtotal = 0.0
    for item in cart_items:
        product = item.get("products") or {}
        price = float(product.get("price", 0))
        line_total = price * item["quantity"]
        subtotal += line_total

        with st.container(border=True):
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
            with col1:
                st.markdown(f"**{product.get('name', '—')}**")
                st.caption(f"SKU: {product.get('sku', '—')}")
            with col2:
                st.metric("Price", format_currency(price))
            with col3:
                st.metric("Qty", item["quantity"])
            with col4:
                st.metric("Subtotal", format_currency(line_total))
                if st.button("Remove", key=f"rm_{item['id']}"):
                    client.table("cart_items").delete().eq("id", item["id"]).execute()
                    st.rerun()

    st.markdown("---")
    tax = subtotal * 0.15  # 15% VAT (Ethiopia)
    shipping = 200.0 if subtotal < 5000 else 0.0  # ETB
    total = subtotal + tax + shipping

    col1, col2 = st.columns([3, 1])
    with col2:
        st.markdown(f"**Subtotal:** {format_currency(subtotal)}")
        st.markdown(f"**Tax (15%):** {format_currency(tax)}")
        st.markdown(f"**Shipping:** {format_currency(shipping)}")
        st.markdown(f"### Total: {format_currency(total)}")

        if st.button("Place Order", type="primary", use_container_width=True):
            # ---- Pre-flight check: is the session valid? ----
            # The most common cause of RLS rejection on orders is a
            # missing or expired JWT. Catch that early with a clear
            # message instead of letting the user see a generic
            # "RLS violation" error.
            import streamlit as st
            access_token = st.session_state.get("access_token")
            if not access_token:
                st.error(
                    "❌ You are not signed in. Please log in again and retry. "
                    "If the page looks like you're signed in, your session "
                    "token may have expired — log out and log back in."
                )
                return
            if not user.get("id"):
                st.error(
                    "❌ Your user profile is missing. Please log out and log "
                    "back in. If that doesn't help, contact admin."
                )
                return

            # ---- ACTIVE DEBUG: verify JWT user matches session user ----
            # The most common cause of the persistent 42501 RLS error is
            # that ``st.session_state["user"]["id"]`` (which we use as
            # buyer_id) does NOT match the user id encoded in the JWT
            # (which PostgREST sees as ``auth.uid()``). When those two
            # differ, the RLS WITH CHECK fails because
            # auth.uid() != buyer_id. This happens when the user has
            # signed in with one account but their session_state was
            # populated with a different user's profile (e.g. from a
            # previous login, or from a key rotation that changed the
            # user id format). We diagnose this by decoding the JWT
            # in Python and comparing.
            with st.expander("🔍 Debug: verify your session", expanded=False):
                import base64
                import json as _json
                try:
                    parts = access_token.split(".")
                    if len(parts) >= 2:
                        # Pad base64 if needed
                        pad = "=" * ((4 - len(parts[1]) % 4) % 4)
                        payload = base64.urlsafe_b64decode(parts[1] + pad).decode("utf-8")
                        jwt_claims = _json.loads(payload)
                        jwt_sub = jwt_claims.get("sub", "(none)")
                        jwt_email = jwt_claims.get("email", "(none)")
                        jwt_role = jwt_claims.get("role", "(none)")
                        jwt_exp = jwt_claims.get("exp", "(none)")
                        session_uid = user.get("id", "(none)")
                        session_email = user.get("email", "(none)")
                        session_role = user.get("role", "(none)")

                        st.markdown("**JWT (token) claims:**")
                        st.code(
                            f"sub (user id):  {jwt_sub}\n"
                            f"email:          {jwt_email}\n"
                            f"role:           {jwt_role}\n"
                            f"exp (expiry):   {jwt_exp}\n"
                        )
                        st.markdown("**Session state (what the app uses):**")
                        st.code(
                            f"user.id:        {session_uid}\n"
                            f"user.email:     {session_email}\n"
                            f"user.role:      {session_role}\n"
                        )
                        if str(jwt_sub) == str(session_uid):
                            st.success("✅ JWT sub matches session user.id — no session mismatch.")
                        else:
                            st.error(
                                f"❌ **MISMATCH DETECTED!**\n\n"
                                f"The JWT says you are user `{jwt_sub}` but the session "
                                f"says you are user `{session_uid}`. The RLS policy "
                                f"`auth.uid() = buyer_id` will ALWAYS fail when these "
                                f"don't match.\n\n"
                                f"**Fix:** Click the Logout button (in the sidebar), "
                                f"then log in again. This will refresh both the JWT "
                                f"and the session state to the same user."
                            )
                    else:
                        st.warning("Could not parse JWT (malformed).")
                except Exception as e:
                    st.warning(f"Could not decode JWT: {e}")

            try:
                # Use first product's producer as the seller (simplified)
                first_product = cart_items[0]["products"]
                seller_id = first_product["producer_id"]

                order_number = generate_order_number("CUST")

                order_payload = {
                    "order_number": order_number,
                    "buyer_id": user["id"],
                    "buyer_role": "customer",
                    "seller_id": seller_id,
                    "seller_role": "producer",
                    "subtotal": subtotal,
                    "tax": tax,
                    "shipping_cost": shipping,
                    "total": total,
                    "status": "pending",
                    "payment_status": "pending",
                    "shipping_address": {"name": user["full_name"], "city": user.get("location", "")},
                }
                insert_response = client.table("orders").insert(order_payload).execute()
                inserted_data = insert_response.data or []

                # Get the order id reliably
                if inserted_data and isinstance(inserted_data, list) and len(inserted_data) > 0:
                    new_order = inserted_data[0]
                else:
                    fetched = (
                        client.table("orders")
                        .select("id")
                        .eq("order_number", order_number)
                        .maybe_single()
                        .execute()
                    )
                    new_order = fetched.data if (fetched and fetched.data) else None

                # Insert order items (only if we have the order id)
                if new_order and new_order.get("id"):
                    items_to_insert = [
                        {
                            "order_id": new_order["id"],
                            "product_id": item["product_id"],
                            "sku": item["products"]["sku"],
                            "name": item["products"]["name"],
                            "unit_price": float(item["products"]["price"]),
                            "quantity": item["quantity"],
                        }
                        for item in cart_items
                    ]
                    try:
                        client.table("order_items").insert(items_to_insert).execute()
                    except Exception as items_err:
                        # Don't silently swallow this — the user is about to
                        # be told their order succeeded while the order has
                        # zero line items, which is a data-integrity bug.
                        # Roll back: delete the half-created order and tell
                        # the user to retry. We do NOT clear the cart.
                        try:
                            client.table("orders").delete().eq("id", new_order["id"]).execute()
                        except Exception:
                            pass
                        st.error(
                            "Order could not be saved completely. The order was "
                            "rolled back and your cart was preserved. Please "
                            f"try again. Detail: {items_err}"
                        )
                        return

                # Clear cart
                client.table("cart_items").delete().eq("user_id", user["id"]).execute()

                st.success(f"Order {order_number} placed successfully!")
                st.balloons()
                st.rerun()
            except Exception as e:
                err = str(e)
                # Most common cause: RLS rejection. Explain the fix.
                if "row-level security" in err.lower() or "42501" in err:
                    st.error(
                        f"❌ **Order blocked by RLS policy**\n\n"
                        f"**What this means:** Supabase rejected the INSERT because "
                        f"the row-level security policy on the `orders` table didn't "
                        f"match your user. The most common cause is that your JWT is "
                        f"for a different user than the session in the app "
                        f"(see the **🔍 Debug** expander above to check).\n\n"
                        f"**Try these in order:**\n\n"
                        f"1. **Logout and log back in.** This refreshes the JWT and "
                        f"the session to the same user. The 90% fix.\n\n"
                        f"2. **Hard-refresh the page** (Ctrl+Shift+R / Cmd+Shift+R) to "
                        f"clear any stale Streamlit state.\n\n"
                        f"3. **Re-run `migration_v6.sql`** if you haven't recently. "
                        f"It has the NULL-safe `auth.uid() is not null` guard on the "
                        f"orders INSERT policy.\n\n"
                        f"4. **Verify the policy is actually applied.** In Supabase SQL "
                        f"Editor, run:\n"
                        f"```sql\n"
                        f"select polname, polcmd from pg_policies\n"
                        f"where tablename = 'orders' order by polname;\n"
                        f"```\n"
                        f"You should see 3 policies: 'Users see orders they "
                        f"participate in' (SELECT), 'Authenticated users can create "
                        f"orders' (INSERT), and 'Buyer/seller can update own orders' "
                        f"(UPDATE). If you see only the old ones without "
                        f"`auth.uid() is not null`, the migration didn't apply.\n\n"
                        f"Supabase response: `{err[:300]}`"
                    )
                else:
                    st.error(f"Failed to place order: {err}")
