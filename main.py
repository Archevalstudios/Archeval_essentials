import requests
from bs4 import BeautifulSoup, Tag
import re
import pandas as pd
import urllib.parse
from googlesearch import search
import os
import time

# === Step 1: Get search query ===
query = input("Enter keyword to search: ").strip()

# === Step 2: Google search with delay ===
raw_urls = []
for url in search(query, num_results=30, lang="en"):
    raw_urls.append(url)
    time.sleep(7)

# === Step 3: Filter URLs using history + known bad domains ===
history_file = "urls_history.txt"
if os.path.exists(history_file):
    with open(history_file, "r") as f:
        url_history = set(line.strip() for line in f if line.strip())
else:
    url_history = set()

banned_domains = [
    "crunchbase.com", "techcrunch.com", "forbes.com", "medium.com", "businessinsider.com",
    "ycombinator.com", "tracxn.com", "dealroom.co", "trends.co", "investopedia.com",
    "retaildive.com", "storemapper.com"
]
# If you want to skip only the main domain, not subpages of real brands
def is_blacklisted(url):
    parsed = urllib.parse.urlparse(url)
    domain = parsed.netloc.lower()
    return any(bad in domain for bad in banned_domains)

def is_store_url(url):
    # Whitelist if URL path contains these
    store_keywords = ["shop", "store", "brand", "collections", "products", "cart", "checkout"]
    parsed = urllib.parse.urlparse(url)
    path = parsed.path.lower()
    return any(word in path for word in store_keywords)

def is_ecommerce_html(html):
    # Look for e-commerce signals in HTML
    signals = ["add to cart", "buy now", "checkout", "basket", "your cart", "order now"]
    html_lower = html.lower()
    return any(sig in html_lower for sig in signals)

def is_shopify(html):
    return "cdn.shopify.com" in html or "shopify" in html.lower()

def is_other_ecommerce(html):
    # Add more e-commerce platform checks if needed
    return any(x in html.lower() for x in [
        "woocommerce", "bigcommerce", "magento", "prestashop", "opencart"
    ])

urls = []
skipped_urls = []
for url in raw_urls:
    if url in url_history or is_blacklisted(url):
        # If it's blacklisted but looks like a store, check further
        if is_store_url(url):
            try:
                res = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
                html = res.text
                if is_shopify(html) or is_other_ecommerce(html) or is_ecommerce_html(html):
                    urls.append(url)
                    print(f"✔️ Store detected (overriding blacklist): {url}")
                else:
                    skipped_urls.append(url)
                    print(f"❌ Skipped (blacklisted, not a store): {url}")
            except:
                skipped_urls.append(url)
                print(f"⚠️ Failed to check (blacklisted): {url}")
            time.sleep(5)
        else:
            skipped_urls.append(url)
            print(f"❌ Skipped (blacklisted): {url}")
        continue
    try:
        res = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
        html = res.text
        if is_shopify(html) or is_other_ecommerce(html) or is_ecommerce_html(html) or is_store_url(url):
            urls.append(url)
            print(f"✔️ Store/brand: {url}")
        else:
            skipped_urls.append(url)
            print(f"❌ Skipped (not a store): {url}")
    except:
        skipped_urls.append(url)
        print(f"⚠️ Failed to check: {url}")
    time.sleep(5)

# Save skipped URLs for review
with open("skipped_urls.txt", "w") as f:
    for url in skipped_urls:
        f.write(url + "\n")

# Save new URLs
with open("urls.txt", "w") as f:
    for url in urls:
        f.write(url + "\n")
if urls:
    with open(history_file, "a") as f:
        for url in urls:
            f.write(url + "\n")

# === Scraping function ===
EMAIL_REGEX = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
PHONE_REGEX = r"\+?\d[\d\s().-]{8,}"
NAME_REGEX = r"([A-Z][a-z]+(?: [A-Z][a-z]+)+)"

def scrape_site(url):
    try:
        print(f"\n🔎 Scraping: {url}")
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")

        text = soup.get_text("\n")
        emails = list(set(re.findall(EMAIL_REGEX, text)))
        phones = list(set(re.findall(PHONE_REGEX, text)))

        # Collect links
        links = [a.get("href") for a in soup.find_all("a", href=True) if isinstance(a, Tag)]
        ig_links = [l for l in links if "instagram.com" in l]
        about_links = [l for l in links if "about" in l.lower()]

        # Try founder/co-founder extraction
        founder_name = cofounder_name = founder_email = cofounder_email = ""
        for line in text.split("\n"):
            l = line.lower()
            if "founder" in l and "co-founder" not in l and not founder_name:
                if (m := re.search(NAME_REGEX, line)): founder_name = m.group(1)
                if (m := re.search(EMAIL_REGEX, line)): founder_email = m.group(0)
            elif "co-founder" in l and not cofounder_name:
                if (m := re.search(NAME_REGEX, line)): cofounder_name = m.group(1)
                if (m := re.search(EMAIL_REGEX, line)): cofounder_email = m.group(0)

        return {
            "Website": url,
            "Email": emails[0] if emails else "",
            "Phone": phones[0] if phones else "",
            "Instagram": ig_links[0] if ig_links else "",
            "About Link": about_links[0] if about_links else "",
            "Founder Name": founder_name,
            "Co-founder Name": cofounder_name,
            "Founder Email": founder_email,
            "Co-founder Email": cofounder_email,
        }

    except Exception as e:
        print(f"❌ Error scraping {url}: {e}")
        return {
            "Website": url,
            "Email": "",
            "Phone": "",
            "Instagram": "",
            "About Link": "",
            "Founder Name": "",
            "Co-founder Name": "",
            "Founder Email": "",
            "Co-founder Email": "",
        }

# === Run scraper ===
results = [scrape_site(url) for url in urls]

# === Save output ===
df = pd.DataFrame(results)
df = df.reindex(columns=[
    "Website", "Email", "Phone", "Instagram", "About Link",
    "Founder Name", "Co-founder Name", "Founder Email", "Co-founder Email"
])
df.to_csv("output.csv", index=False)
print("\n✅ Scraping complete! Results saved to output.csv")