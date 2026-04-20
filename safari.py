#!/usr/bin/env python3
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, List
import subprocess
import threading
import time
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    filters,
    ContextTypes
)
import pymongo
from pymongo import MongoClient, ASCENDING, DESCENDING
from bson import ObjectId
import re
from functools import wraps
import html
import uuid
import os
import socket
import requests  # For IP validation/port checking
import uvloop; uvloop.install()

# --- DIRECT CONFIGURATION (FIXED) ---
BOT_TOKEN = "8735434023:AAFyHYvRVuK_XajrwAQdMjR5XyZ3C8-BWDU"
ADMIN_IDS = [6241594867]
MONGODB_URI = "mongodb+srv://aizensosukei671_db_user:ZNcc8ats5e3dCkjH@fire.ldyx5mo.mongodb.net/?appName=FIRE"
DATABASE_NAME = "attack_bot"

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Attack configuration
ATTACK_METHODS = {
    "udp": ["udp-flood", "udp-flood"],
    "tcp": ["tcp-flood", "tcp-flood"],
    "syn": ["syn-flood", "syn-flood"],
    "http": ["http-flood", "http-flood"]
}

BLOCKED_PORTS = {8700, 20000, 443, 17500, 9031, 20002, 20001}
MIN_PORT = 1
MAX_PORT = 65535
MAX_DURATION = 300  
MAX_CONCURRENT = 3

# --- HELPER FUNCTIONS ---
def make_aware(dt):
    if dt is None: return None
    if hasattr(dt, 'tzinfo') and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt

def get_current_time():
    return datetime.now(timezone.utc)

# Attack Manager Class
class AttackManager:
    def __init__(self):
        self.active_attacks = {}
        self.lock = threading.Lock()
    
    def launch_attack(self, attack_id: str, ip: str, port: int, duration: int, method: str = "udp") -> Dict:
        try:
            with self.lock:
                if len(self.active_attacks) >= MAX_CONCURRENT:
                    return {"success": False, "error": "Max concurrent attacks reached"}
                
                self.active_attacks[attack_id] = {
                    "ip": ip, "port": port, "duration": duration,
                    "method": method, "start_time": time.time(),
                    "end_time": time.time() + duration
                }
            
            attack_thread = threading.Thread(target=self._simulate_attack, args=(attack_id, ip, port, duration))
            attack_thread.daemon = True
            attack_thread.start()
            
            return {
                "success": True,
                "attack": {
                    "id": attack_id, "target": ip, "port": port,
                    "startsAt": get_current_time().isoformat(),
                    "endsAt": (get_current_time() + timedelta(seconds=duration)).isoformat()
                },
                "limits": {"currentActive": len(self.active_attacks), "maxConcurrent": MAX_CONCURRENT}
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _simulate_attack(self, attack_id: str, ip: str, port: int, duration: int):
        time.sleep(duration)
        with self.lock:
            if attack_id in self.active_attacks:
                del self.active_attacks[attack_id]
    
    def get_active_attacks(self) -> Dict:
        active = []
        current_time = time.time()
        with self.lock:
            for aid, data in list(self.active_attacks.items()):
                if current_time > data["end_time"]:
                    del self.active_attacks[aid]
                else:
                    active.append({
                        "attackId": aid, "target": data["ip"],
                        "port": data["port"], "expiresIn": int(data["end_time"] - current_time)
                    })
        return {"success": True, "activeAttacks": active, "count": len(active), "maxConcurrent": MAX_CONCURRENT}

attack_manager = AttackManager()

# MongoDB Database Class
class Database:
    def __init__(self):
        self.client = MongoClient(MONGODB_URI)
        self.db = self.client[DATABASE_NAME]
        self.users = self.db.users
        self.attacks = self.db.attacks
        self.users.create_index([("user_id", ASCENDING)], unique=True)

    def get_user(self, user_id: int):
        return self.users.find_one({"user_id": user_id})

    def create_user(self, user_id: int, username: str = None):
        if not self.get_user(user_id):
            self.users.insert_one({
                "user_id": user_id, "username": username, "approved": False,
                "total_attacks": 0, "created_at": get_current_time()
            })

    def approve_user(self, user_id: int, days: int):
        expiry = get_current_time() + timedelta(days=days)
        self.users.update_one({"user_id": user_id}, {"$set": {"approved": True, "expires_at": expiry}})
        return True

    def log_attack(self, user_id: int, ip: str, port: int, duration: int, status: str):
        self.attacks.insert_one({
            "user_id": user_id, "ip": ip, "port": port, "duration": duration,
            "status": status, "timestamp": get_current_time()
        })
        self.users.update_one({"user_id": user_id}, {"$inc": {"total_attacks": 1}})

db = Database()

# --- DECORATORS & CHECKS ---
def admin_required(func):
    @wraps(func)
    async def wrapper(update, context):
        if update.effective_user.id not in ADMIN_IDS:
            await update.message.reply_text("❌ Admin only!")
            return
        return await func(update, context)
    return wrapper

async def is_approved(user_id):
    user = db.get_user(user_id)
    if not user or not user.get("approved"): return False
    expiry = user.get("expires_at")
    if expiry and make_aware(expiry) < get_current_time(): return False
    return True

# --- BOT COMMANDS ---
async def start_command(update, context):
    db.create_user(update.effective_user.id, update.effective_user.username)
    await update.message.reply_text("🚀 **Welcome to SAFARI Attack Bot!**\nUse /help for commands.")

@admin_required
async def approve_command(update, context):
    try:
        uid, days = int(context.args[0]), int(context.args[1])
        db.approve_user(uid, days)
        await update.message.reply_text(f"✅ User {uid} approved for {days} days.")
    except: await update.message.reply_text("Usage: /approve <id> <days>")

async def attack_command(update, context):
    user_id = update.effective_user.id
    if not await is_approved(user_id):
        return await update.message.reply_text("❌ You are not approved!")

    if len(context.args) != 3:
        return await update.message.reply_text("Usage: /attack <ip> <port> <time>")

    ip, port, duration = context.args[0], int(context.args[1]), int(context.args[2])
    
    if port in BLOCKED_PORTS: return await update.message.reply_text("❌ Port Blocked!")
    if duration > MAX_DURATION: return await update.message.reply_text(f"❌ Max {MAX_DURATION}s!")

    res = attack_manager.launch_attack(str(uuid.uuid4())[:8], ip, port, duration)
    if res["success"]:
        db.log_attack(user_id, ip, port, duration, "success")
        await update.message.reply_text(f"🚀 **Attack Started!**\nTarget: {ip}:{port}\nTime: {duration}s")
    else:
        await update.message.reply_text(f"❌ Error: {res['error']}")

async def help_command(update, context):
    msg = "/attack - Launch attack\n/myinfo - Check account\n/status - System status"
    if update.effective_user.id in ADMIN_IDS:
        msg += "\n\nAdmin:\n/approve <id> <days>\n/users - List users"
    await update.message.reply_text(msg)

# --- MAIN ---
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("approve", approve_command))
    app.add_handler(CommandHandler("attack", attack_command))
    app.add_handler(CommandHandler("help", help_command))
    
    print("✅ Bot is running with Direct MongoDB and Admin Access!")
    app.run_polling()

if __name__ == "__main__":
    main()
