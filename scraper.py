import asyncio
from playwright.async_api import async_playwright
import datetime
import smtplib
from email.mime.text import MIMEText
import os
import re
import json

EMAIL = os.environ["EMAIL"]
EMAIL_PASSWORD = os.environ["EMAIL_PASSWORD"]
TO_EMAIL = os.environ["TO_EMAIL"]

# -------------------------
# CONFIG
# -------------------------
ORIGIN = "DEL"
DEST = "SFO"

OUTBOUND_START = datetime.date(2026, 5, 15)
OUTBOUND_END = datetime.date(2026, 6, 30)

RETURN_START = datetime.date(2026, 9, 15)
RETURN_END = datetime.date(2026, 10, 31)

# -------------------------
# DATE GENERATOR
# -------------------------
def generate_dates(start, end, step):
    dates = []
    d = start
    while d <= end:
        dates.append(d.strftime("%Y-%m-%d"))
        d += datetime.timedelta(days=step)
    return dates

# -------------------------
# SCRAPE ONE SEARCH
# -------------------------
async def get_price(page, dep, ret, cabin):
    cabin_code = "BUSINESS" if cabin == "business" else "PREMIUM_ECONOMY"

    url = f"https://www.google.com/travel/flights?q=Flights%20to%20San%20Francisco%20from%20Delhi&hl=en#flt={ORIGIN}.{DEST}.{dep}*{DEST}.{ORIGIN}.{ret};c:{cabin_code};e:1"

    await page.goto(url)
    await page.wait_for_timeout(6000)

    html = await page.content()

    # Extract price via regex (fast + reliable enough)
    prices = re.findall(r'\$\d{3,5}', html)

    if not prices:
        return None

    # Take cheapest visible
    price = min([int(p.replace("$", "")) for p in prices])

    return price

# -------------------------
# MAIN SEARCH
# -------------------------
async def search(cabin):
    outbound_dates = generate_dates(OUTBOUND_START, OUTBOUND_END, 2)
    return_dates = generate_dates(RETURN_START, RETURN_END, 3)

    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        for dep in outbound_dates:
            for ret in return_dates:
                try:
                    price = await get_price(page, dep, ret, cabin)

                    if price:
                        results.append({
                            "dep": dep,
                            "ret": ret,
                            "price": price
                        })
                except:
                    continue

        await browser.close()

    results.sort(key=lambda x: x["price"])
    return results[:5]

# -------------------------
# EMAIL
# -------------------------
def send_email(premium, business):
    today = datetime.date.today().strftime("%B %d, %Y")

    body = f"✈️ DEL → SFO Flight Deals\nDate: {today}\n\n"

    body += "=== Premium Economy ===\n"
    for i, r in enumerate(premium):
        body += f"{i+1}. Outbound: {r['dep']} | Return: {r['ret']} | Price: ${r['price']*2}\n"

    body += "\n=== Business Class ===\n"
    for i, r in enumerate(business):
        body += f"{i+1}. Outbound: {r['dep']} | Return: {r['ret']} | Price: ${r['price']*2}\n"

    msg = MIMEText(body)
    msg["Subject"] = f"✈️ DEL→SFO Flight Deals – {today}"
    msg["From"] = EMAIL
    msg["To"] = TO_EMAIL

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL, EMAIL_PASSWORD)
        server.send_message(msg)

# -------------------------
# STOP CONDITION
# -------------------------
if datetime.date.today() > datetime.date(2026, 5, 10):
    exit()

# -------------------------
# RUN
# -------------------------
async def main():
    premium = await search("premium")
    business = await search("business")

    send_email(premium, business)

if __name__ == "__main__":
    asyncio.run(main())
