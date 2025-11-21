# botmeteo.py
import os
import discord
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import aiohttp
from aiohttp import web

# --- CONFIG ---
TOKEN = os.getenv("DISCORD_TOKEN")
API_KEY = os.getenv("OPENWEATHER_API_KEY")
VILLE = os.getenv("VILLE", "Sainte-Croix")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))

intents = discord.Intents.default()
client = discord.Client(intents=intents)
scheduler = AsyncIOScheduler(timezone="Europe/Paris")


# =====================================================
#                  MÉTÉO + CONSEILS
# =====================================================

async def get_meteo():
    if not API_KEY:
        return "❌ Erreur : la clé OPENWEATHER_API_KEY est manquante !"

    url = f"http://api.openweathermap.org/data/2.5/weather?q={VILLE}&appid={API_KEY}&units=metric&lang=fr"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                if resp.status != 200:
                    return f"❌ Erreur API météo (code {resp.status})."
                data = await resp.json()
    except Exception as e:
        return f"❌ Erreur réseau météo : {e}"

    temp = data["main"]["temp"]
    meteo = data["weather"][0]["description"]

    # --- Conseils en fonction de la température ---
    if temp < 0:
        emoji, conseil = "🥶", "Gros manteau, gants, bonnet et écharpe obligatoires !"
    elif temp < 5:
        emoji, conseil = "🥶", "Mets un manteau chaud, bonnet conseillé."
    elif temp < 10:
        emoji, conseil = "🧥", "Un pull ou une veste bien chaude."
    elif temp < 18:
        emoji, conseil = "🧥", "Une veste légère suffit."
    elif temp < 25:
        emoji, conseil = "👕", "T-shirt ou tenue légère."
    else:
        emoji, conseil = "🥵", "Très chaud ! Casquette + eau."

    # --- Ajustements selon la météo ---
    meteo_lower = meteo.lower()

    if "pluie" in meteo_lower:
        emoji, conseil = "🌧️", conseil + " Et prends un parapluie ☔."
    elif "averse" in meteo_lower or "bruine" in meteo_lower:
        emoji, conseil = "🌦️", conseil + " Un K-way peut suffire."
    elif "neige" in meteo_lower:
        emoji, conseil = "❄️", conseil + " Et attention aux routes."
    elif "vent" in meteo_lower:
        emoji, conseil = "💨", conseil + " Le vent augmente le froid ressenti."
    elif "brume" in meteo_lower or "brouillard" in meteo_lower:
        emoji, conseil = "🌫️", conseil + " L’air humide peut être froid."

    return (
        f"☁️ **Météo à {VILLE}** ☁️\n"
        f"🌡 Température : {temp}°C\n"
        f"{emoji} {meteo.capitalize()}\n"
        f"👕 {conseil}"
    )


async def send_meteo():
    """Envoie la météo sur Discord."""
    if CHANNEL_ID == 0:
        print("❌ CHANNEL_ID non configuré.")
        return

    try:
        channel = await client.fetch_channel(CHANNEL_ID)
        await channel.send(await get_meteo())
    except Exception as e:
        print(f"❌ Erreur envoi météo : {e}")


# =====================================================
#                 MINI SERVEUR WEB RENDER
# =====================================================

async def http_health(request):
    return web.Response(text="botmeteo OK")

async def http_meteo(request):
    text = await get_meteo()
    asyncio.create_task(send_meteo())
    return web.Response(text=text)

async def start_web():
    app = web.Application()
    app.router.add_get("/", http_health)
    app.router.add_get("/meteo", http_meteo)

    port = int(os.getenv("PORT", "10000"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"🌍 Serveur web lancé sur le port {port}")


# =====================================================
#                 AUTO-PING ANTI-SOMMEIL
# =====================================================

async def auto_ping():
    """Empêche Render de mettre l’instance en veille."""
    url = "https://botmeteo-jouw.onrender.com/"

    while True:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as resp:
                    print(f"[PING] Render → {resp.status}")
        except Exception as e:
            print(f"[PING ERROR] {e}")

        await asyncio.sleep(300)  # toutes les 5 minutes


# =====================================================
#                 DISCORD BOT READY
# =====================================================

_web_started = False

@client.event
async def on_ready():
    global _web_started
    print(f"✅ Connecté en tant que {client.user} (ID: {client.user.id})")

    # Serveur web Render
    if not _web_started:
        asyncio.create_task(start_web())
        _web_started = True

    # Envoi quotidien météo
    scheduler.add_job(send_meteo, "cron", hour=6, minute=40)
    scheduler.start()

    # Auto-ping anti-sommeil 🔥
    asyncio.create_task(auto_ping())


# =====================================================
#                    LANCEMENT BOT
# =====================================================

if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit("❌ DISCORD_TOKEN manquant.")
    client.run(TOKEN)
