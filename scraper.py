import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import datetime
import smtplib
from email.mime.text import MIMEText
import os

EMAIL = os.environ["EMAIL"]
EMAIL_PASSWORD = os.environ["EMAIL_PASSWORD"]
TO_EMAIL = os.environ["TO_EMAIL"]

# -------------------------
# CONFIG
# -------------------------
SEARCH_URL = "https://www.google.com/travel/flights"

# -------------------------
# SCRAPER
# -------------------------
async def scrape_flights(page, cabin="business"):
    # Pre-built Google Flights URL
    base_url = "https://www.google.com/travel/flights"

    if cabin == "business":
        cabin_code = "BUSINESS"
    else:
        cabin_code = "PREMIUM_ECONOMY"

    url = f"{base_url}?hl=en#flt=DEL.SFO.2026-05-20*SFO.DEL.2026-09-20;c:{cabin_code};e:1;sd:1;t:f"

    await page.goto(url)
    await page.wait_for_timeout(8000)

    html = await page.content()
    soup = BeautifulSoup(html, "lxml")

    results = []

    for item in soup.select("div[role='listitem']")[:10]:
        text = item.get_text(" ", strip=True)

        if "$" in text:
            results.append(text)

    return results[:5]

    for item in soup.select("div[role='listitem']")[:10]:
        text = item.get_text(" ", strip=True)

        if "$" in text:
            results.append(text)

    return results[:5]

# -------------------------
# EMAIL
# -------------------------
def send_email(premium, business):
    today = datetime.date.today().strftime("%B %d, %Y")

    body = f"✈️ DEL → SFO Flight Deals\nDate: {today}\n\n"

    body += "=== Premium Economy ===\n"
    for r in premium:
        body += f"- {r}\n"

    body += "\n=== Business Class ===\n"
    for r in business:
        body += f"- {r}\n"

    msg = MIMEText(body)
    msg["Subject"] = f"✈️ DEL→SFO Flight Deals – {today}"
    msg["From"] = EMAIL
    msg["To"] = TO_EMAIL

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL, EMAIL_PASSWORD)
        server.send_message(msg)

# -------------------------
# MAIN
# -------------------------
async def main():
    if datetime.date.today() > datetime.date(2026, 5, 10):
        return

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        premium = await scrape_flights(page, "premium")
        business = await scrape_flights(page, "business")

        await browser.close()

    send_email(premium, business)

if __name__ == "__main__":
    asyncio.run(main())
