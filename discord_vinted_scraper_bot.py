import discord
from discord.ext import commands, tasks
import requests
import asyncio
import json
import os
import cloudscraper

TOKEN = "YOUR_DISCORD_BOT_TOKEN"
CHANNEL_ID = 123456789012345678

# Recherche Lacoste optimisée (tri par récent)
SEARCH_URL = "https://www.vinted.fr/api/v2/catalog/items?search_text=lacoste&order=newest_first&per_page=20"

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

SEEN_FILE = "seen_items.json"

headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json"
}

# =========================
# Gestion persistance
# =========================

def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r") as f:
            return set(json.load(f))
    return set()


def save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f)


seen_items = load_seen()

# =========================
# Scraping via API
# =========================

def scrape_vinted():
    try:
    scraper = cloudscraper.create_scraper()
    response = scraper.get(SEARCH_URL, headers=headers)
    data = response.json()

        items = []

        for item in data.get("items", []):
            items.append({
                "id": item["id"],
                "title": item["title"],
                "price": item["price"],
                "brand": item.get("brand_title", "?"),
                "size": item.get("size_title", "?"),
                "url": item["url"],
                "photo": item["photo"]["url"]
            })

        return items

    except Exception as e:
        print("Erreur scraping:", e)
        return []


# =========================
# Boucle principale
# =========================

@tasks.loop(seconds=45)
async def check_new_items():
    channel = bot.get_channel(CHANNEL_ID)
    items = scrape_vinted()

    new_count = 0

    for item in items:
        if str(item["id"]) not in seen_items:
            seen_items.add(str(item["id"]))
            new_count += 1

            embed = discord.Embed(
                title=item["title"],
                url=item["url"],
                description=f"💰 {item['price']} €",
                color=0x00ff99
            )

            embed.add_field(name="Marque", value=item["brand"], inline=True)
            embed.add_field(name="Taille", value=item["size"], inline=True)
            embed.set_image(url=item["photo"])

            await channel.send(embed=embed)

    if new_count > 0:
        save_seen(seen_items)
        print(f"{new_count} nouveaux items envoyés")


# =========================
# Commandes Discord
# =========================

@bot.command()
async def ping(ctx):
    await ctx.send("pong")


@bot.command()
async def stats(ctx):
    await ctx.send(f"Items déjà vus : {len(seen_items)}")


@bot.command()
async def reset(ctx):
    global seen_items
    seen_items = set()
    save_seen(seen_items)
    await ctx.send("Base reset.")


# =========================
# Ready event
# =========================

@bot.event
async def on_ready():
    print(f"Connecté en tant que {bot.user}")
    check_new_items.start()


bot.run(TOKEN)
