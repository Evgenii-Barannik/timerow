#!/usr/bin/env python3

import os
import subprocess
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import threading
import time
import datetime
import json

PROJECT_DIR = "/Users/meguka/GIT/timerow"
INPUT_DIR = os.path.join(PROJECT_DIR, "input")
SECRETS = os.path.join(PROJECT_DIR, "secrets.json")

os.makedirs(INPUT_DIR, exist_ok=True)

def load_config():
    if not os.path.exists(SECRETS):
        default_config = {
            "telegram_token": "YOUR_TELEGRAM_TOKEN",
            "github_token": "YOUR_GITHUB_TOKEN"
        }
        with open(SECRETS, "w") as f:
            json.dump(default_config, f, indent=2)
        print(f"Создан файл {SECRETS}. Заполните его своими токенами.")
        exit(1)
        
    with open(SECRETS) as f:
        config = json.load(f)
    return config

def status_printer():
    while True:
        print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Бот работает")
        time.sleep(300)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Это бот для отправки CSV-файла с данными.")

async def process_csv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.document or not update.message.document.file_name.endswith('.csv'):
        await update.message.reply_text("Отправь файл .csv сюда.")
        return
    
    try:
        file = await context.bot.get_file(update.message.document.file_id)
        csv_path = os.path.join(INPUT_DIR, update.message.document.file_name)
        await update.message.reply_text("Получил файл.")
        await file.download_to_drive(csv_path)
        
        await run_processing(update, context)
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {e}")

async def run_processing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        os.chdir(PROJECT_DIR)
        
        await update.message.reply_text("Запускаю обработку.")
        subprocess.run(["python", "main.py"], check=True)
        
        dataset_file = "output/prepared_dataset.csv"
        file_status = subprocess.run(
            ["git", "status", "--porcelain", dataset_file], 
            capture_output=True, text=True
        )
        
        if file_status.stdout.strip():
            await update.message.reply_text("Отправляю изменения в Git.")
            
            config = load_config()
            remote_url = subprocess.run(["git", "remote", "get-url", "origin"], 
                                       capture_output=True, text=True).stdout.strip()
            if "https://" in remote_url and "@github.com" not in remote_url:
                token_url = remote_url.replace("https://", f"https://x-access-token:{config['github_token']}@")
                subprocess.run(["git", "remote", "set-url", "origin", token_url], check=True)
            
            subprocess.run(["git", "add", dataset_file], check=True)
            subprocess.run(["git", "commit", "-m", "Update dataset via bot"], check=True)
            subprocess.run(["git", "push", "origin", "master"], check=True)
            
            await update.message.reply_text("✅ Готово! Данные отправлены. Сайт обновится через несколько минут: https://evgenii-barannik.github.io/timerow/")
        else:
            await update.message.reply_text("✅ Данные обработаны, но там нет изменений.")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

def main():
    config = load_config()
    threading.Thread(target=status_printer, daemon=True).start()
    
    app = Application.builder().token(config['telegram_token']).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL, process_csv))
    app.run_polling()

if __name__ == "__main__":
    main() 
