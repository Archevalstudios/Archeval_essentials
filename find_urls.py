import urllib.parse
from googlesearch import search
import os
import time

# Get search query
query = input("Enter keyword to search: ").strip()

# Get URLs from Google search
urls = []
for url in search(query, num_results=20, lang="en"):
    urls.append(url)
    time.sleep(10)  # Delay to avoid getting blocked by Google

# Load URL history
history_file = "urls_history.txt"
if os.path.exists(history_file):
    with open(history_file, "r") as f:
        url_history = set(line.strip() for line in f if line.strip())
else:
    url_history = set()

# Filter out URLs already in history
new_urls = [url for url in urls if url not in url_history]

# Write only new URLs to urls.txt (one per line)
with open("urls.txt", "w") as f:
    for url in new_urls:
        f.write(str(url) + "\n")

# Append new URLs to history
if new_urls:
    with open(history_file, "a") as f:
        for url in new_urls:
            f.write(str(url) + "\n")

print(f"✅ {len(new_urls)} new URLs written to urls.txt (out of {len(urls)} found)")