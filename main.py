#!/usr/bin/env python3
"""
b2b-company-tech-stack-scraper — Standby Pay-Per-Event (PPE) Apify Actor
Extracts company technology stacks, hosting, CMS, analytics, and public contact information.
"""

import asyncio
import json
import os
import re
import sys
import urllib.request
import urllib.error
from typing import List, Dict, Any

try:
    from apify import Actor
except ImportError:
    Actor = None

TECH_SIGNATURES = {
    # CMS / Frameworks
    "Shopify": [r"cdn\.shopify\.com", r"Shopify\.theme", r"myshopify\.com"],
    "WordPress": [r"wp-content", r"wp-includes", r"WordPress"],
    "Webflow": [r"assets\.webflow\.com", r"webflow\.js"],
    "Next.js": [r"/_next/static", r"__NEXT_DATA__"],
    "Nuxt": [r"/_nuxt/", r"__NUXT__"],
    "Squarespace": [r"static1\.squarespace\.com"],
    "Wix": [r"static\.wixstatic\.com"],
    
    # Analytics / Tracking
    "Google Tag Manager": [r"googletagmanager\.com/gtm\.js"],
    "Google Analytics 4": [r"gtag\(['\"]config['\"],\s*['\"]G-", r"google-analytics\.com/analytics\.js"],
    "Segment": [r"cdn\.segment\.com/analytics\.js"],
    "Mixpanel": [r"cdn\.mxpnl\.com"],
    "Hotjar": [r"static\.hotjar\.com"],
    "Meta Pixel": [r"connect\.facebook\.net/en_US/fbevents\.js"],
    
    # Marketing / CRM / Support
    "HubSpot": [r"js\.hs-scripts\.com", r"js\.hubspot\.com"],
    "Intercom": [r"widget\.intercom\.io", r"ic-chat-widget"],
    "Zendesk": [r"static\.zdassets\.com", r"ekr\.zdassets\.com"],
    "Drift": [r"js\.driftt\.com"],
    
    # Payments
    "Stripe": [r"js\.stripe\.com"],
    "PayPal": [r"paypal\.com/sdk/js"],
}

def analyze_domain(domain: str) -> Dict[str, Any]:
    clean_domain = domain.strip().lower()
    clean_domain = re.sub(r"^https?://", "", clean_domain).split("/")[0]

    url = f"https://{clean_domain}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
    )

    detected_tech = []
    headers_dict = {}
    html_content = ""
    status_code = None

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            status_code = resp.status
            headers_dict = dict(resp.headers)
            raw = resp.read()
            html_content = raw.decode("utf-8", errors="ignore")
    except urllib.error.HTTPError as e:
        status_code = e.code
        headers_dict = dict(e.headers)
    except Exception as e:
        return {
            "domain": clean_domain,
            "status": "UNREACHABLE",
            "error": str(e),
            "tech_stack": [],
            "contacts": {},
        }

    # Inspect Headers for CDN / Infrastructure
    server = headers_dict.get("server", "").lower()
    cf_ray = headers_dict.get("cf-ray")
    if cf_ray or "cloudflare" in server:
        detected_tech.append({"name": "Cloudflare", "category": "CDN & Security"})
    if "fastly" in headers_dict.get("x-served-by", "").lower():
        detected_tech.append({"name": "Fastly", "category": "CDN & Edge"})
    if "cloudfront" in headers_dict.get("via", "").lower():
        detected_tech.append({"name": "AWS CloudFront", "category": "CDN & Cloud"})
    if "vercel" in server or "x-vercel-id" in headers_dict:
        detected_tech.append({"name": "Vercel", "category": "Hosting & Edge"})
    if "netlify" in server or "x-nf-request-id" in headers_dict:
        detected_tech.append({"name": "Netlify", "category": "Hosting & Edge"})

    # Inspect HTML Content for Tech Signatures
    for tech_name, patterns in TECH_SIGNATURES.items():
        for pat in patterns:
            if re.search(pat, html_content, re.IGNORECASE):
                cat = "CMS / Framework" if tech_name in ["Shopify", "WordPress", "Webflow", "Next.js", "Nuxt", "Squarespace", "Wix"] else \
                      "Payments" if tech_name in ["Stripe", "PayPal"] else \
                      "CRM & Support" if tech_name in ["HubSpot", "Intercom", "Zendesk", "Drift"] else "Analytics & Tracking"
                detected_tech.append({"name": tech_name, "category": cat})
                break

    # Extract Public Emails
    email_matches = re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', html_content)
    public_emails = []
    for em in set(email_matches):
        em_lower = em.lower()
        if not em_lower.endswith((".png", ".jpg", ".jpeg", ".svg", ".gif", ".webp", ".js", ".css")):
            if any(k in em_lower for k in ["info@", "contact@", "support@", "sales@", "hello@", "press@"]):
                public_emails.append(em_lower)
            elif em_lower.endswith(f"@{clean_domain}"):
                public_emails.append(em_lower)

    # Extract Social Links
    socials = {}
    li = re.search(r'https?://(?:www\.)?linkedin\.com/company/([a-zA-Z0-9_-]+)', html_content)
    if li:
        socials["linkedin"] = li.group(0)
    tw = re.search(r'https?://(?:www\.)?(?:twitter|x)\.com/([a-zA-Z0-9_]+)', html_content)
    if tw:
        socials["twitter"] = tw.group(0)
    gh = re.search(r'https?://(?:www\.)?github\.com/([a-zA-Z0-9_-]+)', html_content)
    if gh:
        socials["github"] = gh.group(0)

    # Title
    title_m = re.search(r'<title>(.*?)</title>', html_content, re.IGNORECASE | re.DOTALL)
    title = title_m.group(1).strip() if title_m else ""

    return {
        "domain": clean_domain,
        "status": "ONLINE",
        "http_code": status_code,
        "title": title[:100],
        "tech_stack": detected_tech,
        "tech_count": len(detected_tech),
        "public_emails": list(set(public_emails))[:5],
        "social_profiles": socials,
    }

async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    try:
        req_line = await reader.readline()
        if not req_line:
            writer.close()
            await writer.wait_closed()
            return
        parts = req_line.decode("utf-8", errors="ignore").strip().split()
        if len(parts) < 2:
            writer.close()
            await writer.wait_closed()
            return
        method, path = parts[0], parts[1]

        headers = {}
        while True:
            hl = await reader.readline()
            if not hl or hl in (b"\r\n", b"\n"):
                break
            s = hl.decode("utf-8", errors="ignore").strip()
            if ":" in s:
                k, v = s.split(":", 1)
                headers[k.strip().lower()] = v.strip()

        # Apify Readiness Probe
        if "x-apify-container-server-readiness-probe" in headers or path == "/healthz":
            body = b"ok\n"
            resp = b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: " + str(len(body)).encode() + b"\r\nConnection: close\r\n\r\n" + body
            writer.write(resp)
            await writer.drain()
            writer.close()
            await writer.wait_closed()
            return

        is_apify = Actor and hasattr(Actor, "is_at_home") and Actor.is_at_home()
        if is_apify:
            try:
                await Actor.charge(event_name="actor-start", count=1)
            except Exception:
                pass

        # Target domain
        target_domains = ["stripe.com"]
        if "?" in path:
            qs = path.split("?", 1)[1]
            for param in qs.split("&"):
                if param.startswith("domain="):
                    d = param.split("=", 1)[1]
                    if d:
                        target_domains = [d]
                elif param.startswith("domains="):
                    ds = param.split("=", 1)[1].split(",")
                    target_domains = [d.strip() for d in ds if d.strip()][:10]

        loop = asyncio.get_running_loop()
        results = []
        for d in target_domains:
            res = await loop.run_in_executor(None, analyze_domain, d)
            results.append(res)

        if is_apify and results:
            try:
                await Actor.charge(event_name="company-analyzed", count=len(results))
            except Exception:
                pass

        payload = {
            "status": "success",
            "actor": "b2b-company-tech-stack-scraper",
            "version": "0.1.0",
            "pricing_model": "PAY_PER_EVENT",
            "events_billed": {
                "actor-start": 1,
                "company-analyzed": len(results),
            },
            "count": len(results),
            "data": results,
        }
        body = json.dumps(payload, indent=2).encode("utf-8")
        status_line = b"HTTP/1.1 200 OK\r\n"
    except Exception as e:
        body = json.dumps({"status": "error", "message": str(e)}).encode("utf-8")
        status_line = b"HTTP/1.1 500 Internal Server Error\r\n"

    resp = (
        status_line +
        b"Content-Type: application/json; charset=utf-8\r\n"
        b"Access-Control-Allow-Origin: *\r\n"
        b"Content-Length: " + str(len(body)).encode() + b"\r\n"
        b"Connection: close\r\n\r\n" + body
    )
    writer.write(resp)
    await writer.drain()
    writer.close()
    await writer.wait_closed()

async def run_server(port: int):
    server = await asyncio.start_server(handle_client, "0.0.0.0", port)
    print(f"🚀 B2B Scraper Standby Server listening on 0.0.0.0:{port}")
    async with server:
        await server.serve_forever()

async def run_batch(actor_input: Dict[str, Any]):
    """Execute standard batch run, push data to Apify dataset, and charge PPE event."""
    domain = actor_input.get("domain", "stripe.com")
    domains = actor_input.get("domains")

    target_domains = []
    if domains and isinstance(domains, list):
        target_domains = [d.strip() for d in domains if d.strip()][:20]
    elif domain:
        target_domains = [domain.strip()]
    else:
        target_domains = ["stripe.com"]

    print(f"🔎 [BATCH] Analyzing tech stack for {len(target_domains)} domain(s): {target_domains}...")
    loop = asyncio.get_running_loop()
    results = []
    for d in target_domains:
        res = await loop.run_in_executor(None, analyze_domain, d)
        results.append(res)

    is_apify = Actor and hasattr(Actor, "is_at_home") and Actor.is_at_home()
    if is_apify:
        try:
            await Actor.charge(event_name="actor-start", count=1)
        except Exception as e:
            print(f"[WARN] Failed to charge actor-start: {e}", file=sys.stderr)

        if results:
            try:
                await Actor.charge(event_name="company-analyzed", count=len(results))
            except Exception as e:
                print(f"[WARN] Failed to charge company-analyzed: {e}", file=sys.stderr)

    if Actor:
        await Actor.push_data(results)
        print(f"✅ Successfully pushed {len(results)} analyzed company profile(s) to default dataset!")
    else:
        print(json.dumps(results, indent=2))

async def main():
    if "--cli" in sys.argv:
        domain = sys.argv[2] if len(sys.argv) > 2 else "stripe.com"
        print(f"[CLI MODE] Analyzing {domain}...")
        res = analyze_domain(domain)
        print(json.dumps(res, indent=2))
        return

    if "--server" in sys.argv:
        port = int(os.environ.get("ACTOR_WEB_SERVER_PORT", "8080"))
        await run_server(port)
        return

    if Actor:
        async with Actor:
            actor_input = await Actor.get_input() or {}
            mode = actor_input.get("runMode", "BATCH")
            if mode == "STANDBY_SERVER":
                port = int(os.environ.get("ACTOR_WEB_SERVER_PORT", "8080"))
                if hasattr(Actor, "configuration") and hasattr(Actor.configuration, "web_server_port"):
                    if Actor.configuration.web_server_port:
                        port = Actor.configuration.web_server_port
                await run_server(port)
            else:
                await run_batch(actor_input)
    else:
        await run_batch({})

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer stopped.")
