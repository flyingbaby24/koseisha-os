// Paste the approved *live* Stripe Payment Link (customer chooses what to pay)
// after Stripe confirms this account's use case: tips for already-published work.
// Never paste a secret key here. A blank value keeps checkout disabled.
const STRIPE_TIP_PAYMENT_LINK = "";

for (const link of document.querySelectorAll("[data-tip-checkout]")) {
  let valid = false;
  try {
    const url = new URL(STRIPE_TIP_PAYMENT_LINK);
    valid = url.protocol === "https:" && url.hostname === "buy.stripe.com" && url.pathname.length > 1;
  } catch { /* Checkout stays disabled. */ }
  if (!valid) continue;
  link.href = STRIPE_TIP_PAYMENT_LINK;
  link.textContent = link.dataset.activeLabel;
  link.classList.remove("is-disabled");
  link.removeAttribute("aria-disabled");
  link.removeAttribute("tabindex");
}
