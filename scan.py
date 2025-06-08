import os
import re
import sys
import asyncio
from flask import Flask
from collections import Counter
from telethon import TelegramClient, events
from telethon.errors import ChannelPrivateError, ChannelInvalidError, RPCError

# ====== CONFIGURATION ======
API_ID = 27705761
API_HASH = "822cb334ca4527a134aae97f9fe44fd6"
BOT_TOKEN = "8102123963:AAH9yagDdUSSNDrwmte6QowIFNP21_k5ET8"
SESSION_NAME = "ScanBot"

# ====== FLASK APP ======
app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    return "🚀 Telegram Scanner Bot is running!"

# ====== TELETHON CLIENT ======
client = TelegramClient(SESSION_NAME, API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# ====== SCANNER CONFIG ======
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

    "Illegal Adult Content": ([  
        "porn", "p0rn", "18+", "nude", "xxx", "sex", "hentai", "deepfake", "erotic", "NSFW",   
        "onlyfans leak", "camgirl", "sexting", "amateur porn", "leaked content", "deepfake nudes",  
        "incest", "bestiality", "rape fantasy", "necrophilia", "leaked OF", "deepfake porn",  
        "amateur sex tape", "telegram leaks", "revenge porn", "leaked cam recordings",  
        "pay-per-view leaks", "celeb deepfake", "blackmail porn", "forced porn",   
        "non-consensual content", "underage porn", "peeping tom", "voyeurism", "snuff film"  
    ], 20),  

    "Personal Data": ([  
        "dox", "doxxing", "address leak", "phone number leak", "private data", "credit card leak",   
        "SSN leak", "Aadhar leak", "personal data", "social security number", "SSN dump",   
        "data breach", "passport leak", "IP leak", "email dump", "SSN database", "Aadhaar dump",  
        "leaked passwords", "CCTV leak", "webcam hack", "revenge porn", "deepfake identity",  
        "webcam breach", "passport scan dump", "voter ID leak", "electoral fraud",  
        "credit card dump", "database leak", "identity theft", "phone hack", "SIM swap"  
    ], 25),  

    "Terrorism": ([  
        "terrorism", "terrorist", "extremism", "radicalization", "jihad", "suicide bombing",  
        "ISIS", "Al-Qaeda", "extremist propaganda", "martyrdom", "lone wolf attack",   
        "terrorist recruitment", "bomb-making", "chemical attack", "hostage situation",  
        "funding terrorism", "militant group", "hate group"  
    ], 70),  

    "Scam or Spam": ([  
        "free money", "giveaway scam", "fake offer", "spam link", "referral spam", "scam",   
        "phishing", "carding", "brute force", "SQL injection", "hacking", "black hat hacking",   
        "ddos", "denial of service", "money laundering", "Ponzi scheme", "investment fraud",   
        "refund scam", "card skimming", "cashout", "cash flipping", "fake donation scam",  
        "romance scam", "bitcoin scam", "pump and dump", "wire fraud", "SIM swap scam",  
        "fake investment", "pyramid scheme", "scammer", "malware", "trojan virus", "spyware",  
        "ransomware", "keylogger", "skimmer", "fake escrow", "social engineering", "bank fraud",  
        "fake credit card", "card dump", "click fraud", "SEO spam", "bot traffic", "auto-clicker",  
        "cookie stuffing", "fake job offer", "Ponzi pyramid", "ad fraud", "AI-generated scam",  
        "defacement", "malicious script", "web shell", "ransom demand"  
    ], 30),  

    "Copyright": ([  
        "piracy", "torrent", "cracked software", "leaked content", "illegal streaming",  
        "mod apk", "nulled script", "illegal IPTV", "warez", "keygen", "serial key",  
        "game cracks", "streaming rip", "MP3 leak", "software patch", "bootleg",  
        "fake licensing", "unauthorized content", "movie leak", "leaked series"  
    ], 40),  

    "Other": ([  
        "hate speech", "discrimination", "racism", "cyberbullying", "misinformation",  
        "fake news", "propaganda", "hoax", "slander", "defamation",  
        "deepfake", "misleading ads", "deceptive marketing", "harmful rumors",   
        "impersonation", "privacy violation", "false accusations", "false identity",  
        "AI-generated misinformation", "psyop", "character assassination"  
    ], 10),  

    "Its Not Illegal, But Should Be Taken Down": ([  
        "deepfake", "misleading ads", "deceptive marketing", "harmful rumors",   
        "impersonation", "privacy violation", "false accusations", "malicious AI content",  
        "edited media", "political manipulation", "clickbait conspiracy", "fake statistics"  
    ], 5)
}

keywords = {kw: (category, impact) 
            for category, (words, impact) in report_categories.items() 
            for kw in words}

# ====== BOT COMMAND HANDLER ======
@client.on(events.NewMessage(pattern='/scan'))
async def scan_handler(event):
    try:
        args = event.raw_text.split()
        if len(args) < 2:
            await event.reply("❌ Usage: `/scan <channel_username or invite_link>`")
            return
        
        chat_link = args[1].strip()
        if chat_link.startswith("https://t.me/"):
            chat_link = chat_link.replace("https://t.me/", "")

        await event.reply(f"🔍 Starting scan for `{chat_link}`...")
        try:
            chat_entity = await client.get_entity(chat_link)
        except (ChannelPrivateError, ValueError):
            await event.reply("❌ Private channel detected. Make sure you've joined it.")
            return
        except ChannelInvalidError:
            await event.reply("❌ Invalid channel link or ID.")
            return
        except RPCError as e:
            await event.reply(f"❌ RPCError: {e}")
            return

        messages, category_counter, keyword_report_map = await search_keywords(chat_entity)
        if not messages:
            await event.reply("✅ No suspicious content found.")
            return
        
        result_text = "\n".join(messages)
        total_matches = sum(category_counter.values())
        total_ban_score = 0

        report_summary = "\n📊 Summary:\n"
        for category, count in category_counter.most_common():
            impact = next((impact for cat, (words, impact) in report_categories.items() if cat == category), 0)
            effectiveness = round((count / total_matches) * 100, 2)
            total_ban_score += (count / total_matches) * impact
            report_summary += f"- {category}: {count} messages ({effectiveness}%)\n"

        final_ban_percentage = round(total_ban_score, 2)
        report_summary += f"\n🔥 Estimated ban risk: {final_ban_percentage}%"

        await event.reply(f"✅ Scan complete!\n\n📌 Matches:\n{result_text}\n\n{report_summary}")

    except Exception as e:
        await event.reply(f"⚠️ Error: {str(e)}")

async def search_keywords(chat):
    messages = []
    category_counter = Counter()
    keyword_report_map = {}

    total_messages = await client.get_messages(chat, limit=1)
    if not total_messages:
        return [], {}, {}

    total_messages = total_messages[0].id
    scanned = 0

    async for message in client.iter_messages(chat, limit=total_messages):
        scanned += 1
        if message.text:
            for keyword, (category, impact) in keywords.items():
                if re.search(rf"\b{re.escape(keyword)}\b", message.text, re.IGNORECASE):
                    post_link = f"https://t.me/{chat.username}/{message.id}" if getattr(chat, 'username', None) else f"Private: {chat.id}/{message.id}"
                    messages.append(f"{keyword} ➤ {post_link}")
                    category_counter[category] += 1
                    if keyword not in keyword_report_map:
                        keyword_report_map[keyword] = (category, impact)
                    break
        await asyncio.sleep(0)
    return messages, category_counter, keyword_report_map

# ====== STARTUP ======
async def main():
    print("🤖 Bot is running.")
    await client.run_until_disconnected()

if __name__ == "__main__":
    # Start Telegram bot in background
    loop = asyncio.get_event_loop()
    loop.create_task(main())
    # Run Flask app on 0.0.0.0:8080 for Koyeb
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
