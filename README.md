# B2B Company Tech-Stack & Lead Contact Scraper (Apify Standby PPE)

A lightweight, zero-proxy Standby Apify Actor extracting company technology stacks, hosting providers, analytics, payments, and public contact information for sales intelligence and AI agents.

## ⚡ Key Highlights
- **Standby Mode:** Pre-warmed HTTP endpoint responding in milliseconds with 0 MB idle RAM cost.
- **Pay-Per-Event (PPE):** Micro-metered pricing at $0.0001 per request + $0.005 per analyzed company profile.
- **Zero-Proxy Cost:** Direct HTTPS requests with no expensive residential proxy overhead.
- **Enriched Profile:** Identifies CMS (Shopify, Webflow, Next.js), analytics (GA4, Segment, Mixpanel), CRM/Chat (HubSpot, Intercom), CDN/Hosting (Cloudflare, Vercel, AWS), and public emails.

## 📡 API Usage & Standby Endpoint

### 1. Readiness Check (Health Check)
```bash
curl -I -H "x-apify-container-server-readiness-probe: 1" "https://<actor-standby-url>"
# Returns: 200 OK
```

### 2. Analyze Company Domain
```bash
curl "https://<actor-standby-url>?domain=stripe.com"
```

Sample Response:
```json
{
  "status": "success",
  "actor": "b2b-company-tech-stack-scraper",
  "version": "0.1.0",
  "pricing_model": "PAY_PER_EVENT",
  "events_billed": {
    "actor-start": 1,
    "company-analyzed": 1
  },
  "count": 1,
  "data": [
    {
      "domain": "stripe.com",
      "status": "ONLINE",
      "http_code": 200,
      "title": "Stripe | Financial Infrastructure for the Internet",
      "tech_stack": [
        {"name": "Fastly", "category": "CDN & Edge"},
        {"name": "Stripe", "category": "Payments"},
        {"name": "Google Tag Manager", "category": "Analytics & Tracking"}
      ],
      "tech_count": 3,
      "public_emails": ["info@stripe.com"],
      "social_profiles": {
        "twitter": "https://twitter.com/stripe",
        "github": "https://github.com/stripe"
      }
    }
  ]
}
```

## 🛠️ Deploy to Apify Store
1. Open [Apify Console](https://console.apify.com/actors/new).
2. Choose **Git repository** -> Link `https://github.com/frag70/b2b-company-tech-stack-scraper`.
3. Click **Build & Publish** to list on the Apify Store.
