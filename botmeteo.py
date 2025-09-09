# botmeteo.py
import os
import discord
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import aiohttp
from aiohttp import web  # mini serveur HTTP pour Render

# --- Config ---
TOKEN = os.getenv("DISCORD_TOKEN")
API_KEY = os.getenv("OPENWEATHER_API_KEY")
VILLE = os.getenv("VILLE", "Sainte-Croix")
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))

intents = discord.Intents.default()
client = discord.Client(intents=intents)
scheduler = AsyncIOScheduler(timezone="Europe/Paris")

# ------------- METEO -------------
async def get_meteo():
    if not API_KEY:
        return "❌ Erreur : OPENWEATHER_API_KEY manquante."

    url = f"http://api.openweathermap.org/data/2.5/weather?q={VILLE}&appid={API_KEY}&units=metric&lang=fr"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                if resp.status != 200:
                    return f"❌ Erreur API météo ({resp.status})."
                data = await resp.json()
    except Exception as e:
        return f"❌ Erreur réseau météo : {e}"

    temp = data["main"]["temp"]
    meteo = data["weather"][0]["description"]

    # Conseils d'habillage
    if "pluie" in meteo:
        emoji, conseil = "🌧️", "Prends un imperméable et un parapluie ☔."
    elif "averse" in meteo or "bruine" in meteo:
        emoji, conseil = "🌦️", "Un K-way ou une capuche suffira."
    elif "neige" in meteo:
        emoji, conseil = "❄️", "Manteau chaud, bonnet, gants et écharpe 🧤🧣."
    elif "verglas" in meteo:
        emoji, conseil = "🧊", "Chaussures à bonne adhérence et tenue chaude."
    elif "nuageux" in meteo or "couvert" in meteo:
        emoji, conseil = "☁️", "Un pull ou une veste légère sera parfait."
    elif "brume" in meteo or "brouillard" in meteo:
        emoji, conseil = "🌫️", "Prends une petite veste pour l’humidité."
    elif "vent" in meteo or "venteux" in meteo:
        emoji, conseil = "💨", "Mets une veste coupe-vent."
    elif "soleil" in meteo or "clair" in meteo:
        emoji, conseil = "☀️", "Lunettes de soleil 🕶️ et vêtements légers."
    elif temp > 30:
        emoji, conseil = "🥵", "T-shirt, short et casquette 🧢."
    elif temp < 5:
        emoji, conseil = "🥶", "Manteau, bonnet et gants indispensables."
    else:
        emoji, conseil = "🌤️", "Habille-toi confortablement."

    return (
        f"☁️ **Météo à {VILLE}** ☁️\n"
        f"🌡 Température : {temp}°C\n"
        f"{emoji} {meteo.capitalize()}\n"
        f"👕 {conseil}"
    )

async def send_meteo():
    """Envoie la météo dans le salon Discord configuré."""
    if CHANNEL_ID == 0:
        print("CHANNEL_ID non configuré.")
        return
    try:
        channel = await client.fetch_channel(CHANNEL_ID)
        await channel.send(await get_meteo())
    except Exception as e:
        print(f"Erreur envoi météo: {e}")

# ------------- Mini serveur HTTP (Render) -------------
async def http_health(request):
    return web.Response(text="botmeteo OK")

async def http_meteo(request):
    # Déclenche l’envoi dans Discord ET retourne le texte dans le navigateur
    text = await get_meteo()
    # envoi Discord en tâche séparée pour ne pas bloquer la réponse HTTP
    asyncio.create_task(send_meteo())
    return web.Response(text=text)

async def start_web():
    app = web.Application()
    app.router.add_get("/", http_health)
    app.router.add_get("/meteo", http_meteo)  # endpoint déclencheur
    port = int(os.getenv("PORT", "10000"))  # Render fournit PORT
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"🌍 Serveur web lancé sur le port {port}")

# ------------- Discord bot -------------
_web_started = False

@client.event
async def on_ready():
    global _web_started
    print(f"✅ Connecté en tant que {client.user} (ID: {client.user.id})")

    # Démarre le serveur web pour Render
    if not _web_started:
        asyncio.create_task(start_web())
        _web_started = True

    # Programmation quotidienne à 06:40 Europe/Paris
    scheduler.add_job(send_meteo, "cron", hour=6, minute=40)
    scheduler.start()

if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit("❌ DISCORD_TOKEN manquant.")
    client.run(TOKEN)
