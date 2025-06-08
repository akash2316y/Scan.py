import re
import os
import asyncio
from collections import Counter
from flask import Flask, request, jsonify
from telethon import TelegramClient, events
from telethon.errors import ChannelPrivateError, ChannelInvalidError, RPCError

API_ID = 27705761
API_HASH = "822cb334ca4527a134aae97f9fe44fd6"
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
SESSION_NAME = "ScanBot"

app = Flask(__name__)
bot = TelegramClient(SESSION_NAME, API_ID, API_HASH).start(bot_token=BOT_TOKEN)

report_categories = {
    "Child Abuse": ([
        "child porn", "cp", "minor abuse", "underage", "illegal adoption", "child trafficking",
        "nude", "nudes", "toddlercon", "jailbait", "preteen", "pedo", "kiddie porn",
        "child grooming", "pedophile", "child sex tourism", "infant abuse",
        "minor nudes", "forced adoption", "illegal surrogacy", "baby for sale",
        "child slavery", "child exploitation", "underage sexting"
    ], 95),

    "Violence": ([
        "kill", "murder", "attack", "bomb", "terrorism", "gun", "weapon", "massacre",
        "riot", "fight", "assault", "genocide", "execution", "lynching", "homicide",
        "torture", "bomb threat", "extremism", "assassinate", "terrorism funding",
        "jihad", "extremist propaganda", "radicalization", "biohazard attack",
        "WMD", "hate crime", "war crime", "school shooting", "death threat",
        "violence incitement", "mass murder", "shooting spree", "arson"
    ], 60),

    "Illegal Goods": ([
        "drugs", "drug", "cocaine", "heroin", "marijuana", "weed", "meth", "LSD", "ecstasy",
        "opioid", "crack", "ketamine", "dark web", "onion link", "illegal trade", "C2", "ganja",
        "fentanyl", "xanax", "steroids", "darknet", "vendor shop", "fake ID", "counterfeit",
        "darknet market", "hitman service", "gun trade", "organ trafficking", "forged passport",
        "human smuggling", "identity theft", "fake diploma", "anabolic steroids",
        "cryptocurrency scam", "fake currency", "money counterfeiting", "unlicensed firearms",
        "gun running", "organ selling", "human harvesting", "smuggled goods",
        "illegal weapons", "bioweapon", "black market trade"
    ], 50),
    # Add more categories if needed
}

keywords = {
    kw: (category, impact)
    for category, (words, impact) in report_categories.items()
    for kw in words
}

async def search_keywords(client, chat, event):
    messages = []
    category_counter = Counter()
    keyword_report_map = {}

    total_messages = await client.get_messages(chat, limit=1)
    if not total_messages:
        await event.respond("No messages found.")
        return [], {}, {}

    total_messages = total_messages[0].id
    scanned = 0

    progress_message = await event.respond("🔍 Starting scan... 0%")

    async for message in client.iter_messages(chat, limit=total_messages):
        scanned += 1
        progress = (scanned / total_messages) * 100
        bar = "▰" * int(progress // 10) + "▱" * (10 - int(progress // 10))
        await progress_message.edit(f"🔍 Scanning... {bar} {int(progress)}%")

        if message.text:
            for keyword, (category, impact) in keywords.items():
                if re.search(rf"\b{re.escape(keyword)}\b", message.text, re.IGNORECASE):
                    post_link = (
                        f"https://t.me/{chat.username}/{message.id}"
                        if getattr(chat, 'username', None)
                        else f"Private: {chat.id}/{message.id}"
                    )
                    messages.append(f"{keyword} ➤ {post_link}")

                    category_counter[category] += 1
                    if keyword not in keyword_report_map:
                        keyword_report_map[keyword] = (category, impact)
                    break

        await asyncio.sleep(0)

    await progress_message.edit("✅ Scan complete!")
    return messages, keyword_report_map, category_counter

async def generate_report(messages, keyword_report_map, category_counter):
    if not messages:
        return "✅ Scan complete! No matches found."

    report = "🚨 **Scan Results:**\n\n"
    for msg in messages:
        report += f"- {msg}\n"

    total_matches = sum(category_counter.values())
    if total_matches > 0:
        report += f"\n📢 **Reports:**\n"
        total_ban_score = 0
        for keyword, (category, impact) in keyword_report_map.items():
            effectiveness = round((category_counter[category] / total_matches) * 100, 2)
            total_ban_score += (category_counter[category] / total_matches) * impact
            report += f"`{keyword}` ➔ {category} [{effectiveness}%]\n"
        final_ban_percentage = round(total_ban_score, 2)
        report += f"\n📊 Estimated Ban Probability: **{final_ban_percentage}%**"

    return report

@bot.on(events.NewMessage(pattern="/start"))
async def start(event):
    await event.respond("👋 Welcome! Send /scan <chat_username> to start scanning a channel.")

@bot.on(events.NewMessage(pattern=r"/scan (.+)"))
async def scan(event):
    chat_link = event.pattern_match.group(1).strip()

    is_invite_link = "t.me/joinchat/" in chat_link or "t.me/+" in chat_link
    is_username = chat_link.startswith("https://t.me/") and not is_invite_link

    if is_username:
        chat_link = chat_link.replace("https://t.me/", "").strip()

    try:
        chat_entity = await bot.get_entity(chat_link)
    except (ChannelPrivateError, ValueError):
        await event.respond("❌ Error: Private channel detected. Ensure you have joined it.")
        return
    except ChannelInvalidError:
        await event.respond("❌ Error: Invalid channel link or ID.")
        return
    except RPCError as e:
        await event.respond(f"❌ Error: {e}")
        return

    await event.respond(f"🔍 Scanning {chat_link}... Please wait.")
    results, keyword_report_map, category_counter = await search_keywords(bot, chat_entity, event)
    report = await generate_report(results, keyword_report_map, category_counter)
    await event.respond(report)

@app.route("/", methods=["POST"])
def webhook():
    update = request.get_json(force=True)
    loop = asyncio.get_event_loop()
    loop.create_task(bot.process_update(update))
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    bot.loop.run_until_complete(bot.start())
    app.run(host="0.0.0.0", port=port)
