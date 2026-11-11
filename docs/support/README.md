# Jinn Project — optional tips for published work

Static, bilingual support page for the official GitHub Pages site.

- English: `/support/` (`docs/support/index.html`)
- Japanese: `/support/index-ja.html`
- Both official home pages link here from Contact and footer.
- Checkout is **disabled by default**; this PR does not process money.
- No server, key, account system, database, email collection, payment promises, or payout tracking.

## Intended use

Voluntary **tips for content already supplied** by Jinn Project LLC:
research articles, papers, OSS/apps, music, fiction, and free seminars.
They are not required to read or use free content. No rewards, equity,
priority access, subscriptions, or rights are granted for tipping.

Do not use this page for unrestricted charitable donations, financing
a future product, rewards-based crowdfunding or paying other creators.

Stripe's published conditions:
- Tips must relate to already provided goods or services (including content).
  https://support.stripe.com/questions/requirements-for-accepting-tips-or-donations?locale=ja-JP
- Directly selling one's own content on one's own site is not the same as
  operating a third-party creator marketplace:
  https://support.stripe.com/questions/restricted-business-list-faqs?locale=ja-JP

## Enabling checkout (manual)

1. In the **Jinn Project LLC Stripe account**, confirm the tip-for-published-content use case and any required account settings.
2. Create a **one-time Payment Link** for the relevant published-content tip use case. If supported for the account, allow the customer to choose the amount; keep the label as a *tip/payment*, not a charitable-donation claim.
3. The required **Commercial Disclosure / 特定商取引法に基づく表記** page lives at `docs/legal/index.html` (published as `/legal/`), linked from both homepages and both support pages. It carries the registered company name, representative, head-office address, contact email, payment methods and the tip refund policy; the telephone number uses the Act's request-disclosure wording (provided without delay on request). If Stripe's review asks for a published number, add a company number there instead. After deployment, register the live URL in the Stripe Dashboard under Settings → Business → Business details → Commerce disclosures.
   Stripe's requirements: https://support.stripe.com/questions/how-to-create-and-display-a-commerce-disclosure-page?locale=ja-JP
4. Replace the empty `STRIPE_TIP_PAYMENT_LINK` in `docs/support/support.js` with the approved **live** `https://buy.stripe.com/...` link.
5. Only after appropriate checks, merge this branch to deploy. Do not expose a Stripe test link on the production domain.

Payment Links handles amount selection and payment details; this static page
never collects or stores card data. The page accepts only an HTTPS
`buy.stripe.com` checkout URL. No amount buttons exist locally because
an arbitrary user-entered amount cannot be passed safely to a fixed
Payment Link by editing the URL. Stripe manages amount entry.

## Smoke check

Open `docs/support/index.html` and `docs/support/index-ja.html` in a
static local server. Verify both render, language/home links work, and
the checkout link is **not clickable** while the config is blank.
When testing the link separately, verify the destination is genuinely
Stripe-hosted, amount is optional, and it is a **single** payment.

For the homepage generator:

```sh
node docs/tools/generate-index-ja.mjs
node --test tests/*.mjs
```

The homepage English and Japanese files and the generator translation
map were updated together to preserve the site's generated-page workflow.
