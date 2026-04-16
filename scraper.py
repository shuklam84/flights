import asyncio
from playwright.async_api import async_playwright
import datetime
import smtplib
from email.mime.text import MIMEText
import os

EMAIL = os.environ["EMAIL"]
EMAIL_PASSWORD = os.environ["EMAIL_PASSWORD"]
TO_EMAIL = os.environ["TO_EMAIL"]

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
# EXTRACT FLIGHT CARDS
# -------------------------
async def extract_flights(page):
    flights = []

    cards = await page.query_selector_all("div[jscontroller]")

    for card in cards[:12]:
        try:
            text = await card.inner_text()

            if "$" not in text:
                continue

            # Filter only usable itineraries
            if "Nonstop" in text or "1 stop" in text:
                flights.append(text)

        except:
            continue

    return flights[:3]

# -------------------------
# SEARCH FUNCTION
# -------------------------
async def search(cabin):
    outbound_dates = generate_dates(OUTBOUND_START, OUTBOUND_END, 3)
    return_dates = generate_dates(RETURN_START, RETURN_END, 4)

    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        for dep in outbound_dates[:6]:
            for ret in return_dates[:6]:

                page = await browser.new_page()

                cabin_code = "BUSINESS" if cabin == "business" else "PREMIUM_ECONOMY"

                url = f"https://www.google.com/travel/flights#flt={ORIGIN}.{DEST}.{dep}*{DEST}.{ORIGIN}.{ret};c:{cabin_code};e:1"

                try:
                    await page.goto(url)
                    await page.wait_for_timeout(5000)

                    flights = await extract_flights(page)

                    for f in flights:
                        results.append({
                            "dep": dep,
                            "ret": ret,
                            "details": f
                        })

                except:
                    pass

                await page.close()

        await browser.close()

    return results[:5]

# -------------------------
# EMAIL
# -------------------------
def send_email(premium, business):
    today = datetime.date.today().strftime("%B %d, %Y")

    body = f"✈️ DEL → SFO Flight Deals\nDate: {today}\n\n"

    body += "=== Premium Economy ===\n\n"
    for i, r in enumerate(premium):
        body += f"{i+1}. {r['dep']} → {r['ret']}\n"
        body += f"{r['details']}\n\n"

    body += "=== Business Class ===\n\n"
    for i, r in enumerate(business):
        body += f"{i+1}. {r['dep']} → {r['ret']}\n"
        body += f"{r['details']}\n\n"

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
# MAIN
# -------------------------
async def main():
    premium = await search("premium")
    business = await search("business")

    send_email(premium, business)

if __name__ == "__main__":
    asyncio.run(main())
