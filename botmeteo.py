# botmeteo.py
import os
import discord
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import aiohttp

# --- Config ---
TOKEN = os.getenv("DISCORD_TOKEN")                 # définit via setx DISCORD_TOKEN "..."
API_KEY = os.getenv("OPENWEATHER_API_KEY")         # fais aussi setx OPENWEATHER_API_KEY "ta_clef"
VILLE = "Sainte-Croix"
CHANNEL_ID = 1412736489892352093                 # <- remplace par l'ID réel du salon

intents = discord.Intents.default()
client = discord.Client(intents=intents)
scheduler = AsyncIOScheduler(timezone="Europe/Paris")


async def get_meteo():
    if not API_KEY:
        return "❌ Erreur : OPENWEATHER_API_KEY manquante (setx OPENWEATHER_API_KEY \"...\")."

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

    # --- CONSEILS D'HABILLAGE (à l'intérieur de la fonction !) ---
    if "pluie" in meteo:
        emoji, conseil = "🌧️", "Prends un imperméable et un parapluie ☔."
    elif "averse" in meteo or "bruine" in meteo:
        emoji, conseil = "🌦️", "Un K-way ou une capuche suffira pour rester au sec."
    elif "neige" in meteo:
        emoji, conseil = "❄️", "Mets un manteau chaud, bonnet, gants et écharpe 🧤🧣."
    elif "verglas" in meteo:
        emoji, conseil = "🧊", "Chaussures à bonne adhérence et tenue bien chaude."
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
        emoji, conseil = "🌤️", "Habille-toi confortablement, ni trop chaud ni trop froid."

    return (
        f"☁️ **Météo à {VILLE}** ☁️\n"
        f"🌡 Température : {temp}°C\n"
        f"{emoji} {meteo.capitalize()}\n"
        f"👕 {conseil}"
    )

@client.event
async def on_ready():
    print(f"Connecté en tant que {client.user} (ID: {client.user.id})")

    async def envoyer_meteo():
        try:
            channel = await client.fetch_channel(CHANNEL_ID)  # plus fiable que get_channel
            await channel.send(await get_meteo())
        except Exception as e:
            print(f"Erreur envoi météo: {e}")

    # Envoi quotidien
    scheduler.add_job(envoyer_meteo, "cron", hour=6, minute=40)
    scheduler.start()

    # 👉 Décommente pour tester tout de suite un premier envoi
    # await envoyer_meteo()

if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit("❌ DISCORD_TOKEN manquant (setx DISCORD_TOKEN \"...\" puis rouvre PowerShell).")
    client.run(TOKEN)
