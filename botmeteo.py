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

    # ------------------ CONSEILS REALISTES ------------------
    # Priorité : température
    if temp < 0:
        emoji = "🥶"
        conseil = "Gros manteau, gants, bonnet et écharpe obligatoires !"
    elif temp < 5:
        emoji = "🥶"
        conseil = "Mets un manteau chaud, bonnet conseillé."
    elif temp < 10:
        emoji = "🧥"
        conseil = "Un pull bien chaud ou une veste épaisse."
    elif temp < 18:
        emoji = "🧥"
        conseil = "Une veste légère ou un pull suffira."
    elif temp < 25:
        emoji = "👕"
        conseil = "T-shirt ou tenue légère."
    else:
        emoji = "🥵"
        conseil = "Très chaud ! Casquette, eau et vêtements légers."

    # Ajustement selon météo
    if "pluie" in meteo:
        emoji = "🌧️"
        conseil += " Et prends un parapluie ☔."
    elif "averse" in meteo or "bruine" in meteo:
        emoji = "🌦️"
        conseil += " Un K-way peut suffire."
    elif "neige" in meteo:
        emoji = "❄️"
        conseil += " Et attention aux routes !"
    elif "vent" in meteo:
        emoji = "💨"
        conseil += " Le vent augmente le froid ressenti."
    elif "brouillard" in meteo or "brume" in meteo:
        emoji = "🌫️"
        conseil += " L’air humide peut être froid."

    # ---------------------------------------------------------

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
    text = await get_meteo()
    asyncio.create_task(send_meteo())  # envoi discord sans bloquer HTTP
    return web.Response(text=text)

async def start_web():
    app = web.Application()
    app.router.add_get("/", http_health)
    app.router.add_get("/meteo", http_meteo)

    port = int(os.getenv("PORT", "10000"))  # Render fournit PORT dynamiquement

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

    # Lancer serveur web pour Render
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
