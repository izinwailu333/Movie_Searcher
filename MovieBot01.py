import os
import time
import sqlite3
from datetime import datetime
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask
from threading import Thread

# ==========================================
# Flask Web Server (24/7 Uptime)
# ==========================================
app = Flask('')

@app.route('/')
def home():
    return "Movie Bot is actively running!"

def run_web():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# ==========================================
# Config / Bot Data
# ==========================================
# သင်ပေးထားသော Bot Token အသစ်
TOKEN = '8851102821:AAFyaFEyy22U0BaLNlpfPPfEvPu8PDypgOA'  

# ⚠️ အရေးကြီး: ဤနေရာတွင် သင့်ရဲ့ Telegram User ID (ဂဏန်း) ကို ပြောင်းထည့်ပါ
ADMIN_ID = 5293498783  

# သင်ပေးထားသော Adsterra Direct Link အသစ်
DIRECT_AD_LINK = 'https://www.profitableratecpmnetwork.com/z6jgwxkza?key=bc0115c60096e6024fb9b5c27ec2bdcb' 

CHANNEL_USERNAME = '@zinnnmovie1219'
CHANNEL_LINK = 'https://t.me/zinnnmovie1219'

bot = telebot.TeleBot(TOKEN)
pending_movie_requests = {}

# ==========================================
# Database Setup
# ==========================================
def init_dbs():
    # 1. Users Ad Views Database
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS ad_views (user_id INTEGER PRIMARY KEY, last_view_date TEXT)''')
    conn.commit()
    conn.close()

    # 2. Movies Database
    conn2 = sqlite3.connect('movies.db')
    c2 = conn2.cursor()
    c2.execute('''CREATE TABLE IF NOT EXISTS movies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    title TEXT, 
                    file_id TEXT, 
                    file_type TEXT)''')
    conn2.commit()
    conn2.close()

init_dbs()

# --- Ad System Functions ---
def has_viewed_ad_today(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT last_view_date FROM ad_views WHERE user_id = ?', (user_id,))
    result = c.fetchone()
    conn.close()
    if result:
        return result[0] == datetime.now().strftime('%Y-%m-%d')
    return False

def mark_ad_viewed(user_id):
    today = datetime.now().strftime('%Y-%m-%d')
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''INSERT INTO ad_views (user_id, last_view_date) VALUES (?, ?)
                 ON CONFLICT(user_id) DO UPDATE SET last_view_date = ?''', (user_id, today, today))
    conn.commit()
    conn.close()

# --- Force Subscribe Check ---
def check_join(user_id):
    if user_id == ADMIN_ID: return True # Admin ကို မစစ်ပါ
    try:
        status = bot.get_chat_member(CHANNEL_USERNAME, user_id).status
        return status in ['member', 'administrator', 'creator']
    except Exception as e:
        print(f"Check Join Error: {e}")
        return False

# ==========================================
# Handlers
# ==========================================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    if not check_join(user_id):
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("✅ Channel ကို Join ပါ", url=CHANNEL_LINK))
        bot.send_message(message.chat.id, "❌ သင်သည် Channel ကို Join ရသေးပါ။\nကျေးဇူးပြု၍ အောက်ပါ Button ကိုနှိပ်ပြီး Join ပါ။", reply_markup=markup)
        return
        
    bot.send_message(message.chat.id, "🎬 **Movie Search Bot မှ ကြိုဆိုပါသည်!**\n\n🔎 သင်ကြည့်ရှုလိုသော ဇာတ်ကားအမည်ကို ရိုက်ထည့်၍ ရှာဖွေနိုင်ပါသည်။ (ဥပမာ - Iron Man)", parse_mode="Markdown")

# [ADMIN ONLY] ဇာတ်ကားအသစ် တင်ရန် (Video သို့မဟုတ် Document ပို့လျှင်)
@bot.message_handler(content_types=['video', 'document'])
def handle_new_movie(message):
    if message.from_user.id != ADMIN_ID:
        return # Admin မဟုတ်လျှင် ဘာမှမလုပ်ပါ

    file_id = message.video.file_id if message.content_type == 'video' else message.document.file_id
    file_type = message.content_type
    
    if not message.caption:
        bot.reply_to(message, "❌ ဇာတ်ကားနာမည် (Caption) တပ်ပြီး ပြန်ပို့ပေးပါ။ Caption မပါလျှင် မှတ်၍မရပါ။")
        return

    title = message.caption.strip()

    conn = sqlite3.connect('movies.db')
    c = conn.cursor()
    c.execute('INSERT INTO movies (title, file_id, file_type) VALUES (?, ?, ?)', (title, file_id, file_type))
    conn.commit()
    conn.close()

    bot.reply_to(message, f"✅ ဇာတ်ကားအသစ် Database ထဲသို့ သိမ်းဆည်းပြီးပါပြီ!\n\n🎬 နာမည်: {title}")

# [USER] ဇာတ်ကား ရှာဖွေရန်
@bot.message_handler(func=lambda message: True)
def search_movie(message):
    user_id = message.from_user.id
    search_text = message.text.strip()

    if not check_join(user_id):
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("✅ Channel ကို Join ပါ", url=CHANNEL_LINK))
        bot.send_message(message.chat.id, "❌ သင်သည် Channel ကို Join ရသေးပါ။\nကျေးဇူးပြု၍ အောက်ပါ Button ကိုနှိပ်ပြီး Join ပါ။", reply_markup=markup)
        return

    conn = sqlite3.connect('movies.db')
    c = conn.cursor()
    # နာမည်ဆင်တူတဲ့ ကားတွေအကုန်ရှာမယ် (အများဆုံး ၁၀ ကား)
    c.execute('SELECT id, title FROM movies WHERE title LIKE ? LIMIT 10', ('%'+search_text+'%',))
    results = c.fetchall()
    conn.close()

    if not results:
        bot.reply_to(message, "❌ သင်ရှာဖွေသော ဇာတ်ကားကို မတွေ့ရှိပါ။ နာမည်စာလုံးပေါင်း မှန်ကန်အောင် ပြန်လည်ရိုက်ထည့်ကြည့်ပါ။")
        return

    markup = InlineKeyboardMarkup()
    for row in results:
        movie_id = row[0]
        movie_title = row[1]
        markup.add(InlineKeyboardButton(f"🎬 {movie_title}", callback_data=f"dl_{movie_id}"))

    bot.send_message(message.chat.id, "🔎 အောက်ပါ ဇာတ်ကားများကို ရှာဖွေတွေ့ရှိပါသည်။ ကြည့်လိုသောကားကို နှိပ်ပါ။", reply_markup=markup)

# [USER] ဇာတ်ကားခလုတ် နှိပ်သောအခါ
@bot.callback_query_handler(func=lambda call: call.data.startswith('dl_'))
def handle_movie_click(call):
    user_id = call.from_user.id
    movie_id = call.data.split('_')[1]

    # ကြော်ငြာကြည့်ပြီးသားလား စစ်ဆေးမယ်
    if not has_viewed_ad_today(user_id):
        pending_movie_requests[user_id] = movie_id
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("▶️ ကြော်ငြာကြည့်မည်", url=DIRECT_AD_LINK))
        markup.add(InlineKeyboardButton("✅ ကြော်ငြာကြည့်ရှုမှုကို အတည်ပြုပါ", callback_data="verify_ad"))
        bot.send_message(call.message.chat.id, 
                         "⚠️ ယနေ့အတွက် ကြော်ငြာမကြည့်ရသေးပါ။\n\nအောက်ပါ 'ကြော်ငြာကြည့်မည်' ကိုနှိပ်ပြီး ကြည့်ပါ။ ထို့နောက် 'အတည်ပြုပါ' ခလုတ်ကို နှိပ်မှသာ ဇာတ်ကားဖိုင်ကို ရရှိပါမည်။", 
                         reply_markup=markup)
        return

    # ကြည့်ပြီးသားဆိုရင် ချက်ချင်းပို့ပေးမယ်
    send_movie_file(call.message.chat.id, movie_id)
    bot.answer_callback_query(call.id)

# [USER] ကြော်ငြာ အတည်ပြုသောအခါ
@bot.callback_query_handler(func=lambda call: call.data == 'verify_ad')
def verify_ad(call):
    user_id = call.from_user.id
    movie_id = pending_movie_requests.get(user_id)
    
    if not movie_id:
        bot.answer_callback_query(call.id, "❌ လင့်ခ်မှတ်သားထားခြင်း မရှိတော့ပါ။ ဇာတ်ကားကို ပြန်လည်ရှာဖွေပါ။", show_alert=True)
        return
        
    mark_ad_viewed(user_id)
    bot.answer_callback_query(call.id, "✅ ကြော်ငြာကြည့်ရှုမှု အတည်ပြုပြီးပါပြီ။", show_alert=True)
    
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="ကြော်ငြာကြည့်ရှုမှုကို အတည်ပြုပြီးပါပြီ ✅\nဇာတ်ကားဖိုင် ပို့ဆောင်နေပါသည်... ⏳")
    time.sleep(2) # အနည်းငယ် စောင့်ဆိုင်းဟန်ဆောင်ခြင်း
    
    send_movie_file(call.message.chat.id, movie_id)
    
    if user_id in pending_movie_requests:
        del pending_movie_requests[user_id]

def send_movie_file(chat_id, movie_id):
    conn = sqlite3.connect('movies.db')
    c = conn.cursor()
    c.execute('SELECT file_id, file_type, title FROM movies WHERE id = ?', (movie_id,))
    result = c.fetchone()
    conn.close()

    if not result:
        bot.send_message(chat_id, "❌ ဤဇာတ်ကားကို Database တွင် မတွေ့တော့ပါ။")
        return

    file_id, file_type, title = result
    try:
        if file_type == 'video':
            bot.send_video(chat_id, file_id, caption=f"🎬 {title}\n\nDownloaded via @movie_Searcherrr_Bot")
        elif file_type == 'document':
            bot.send_document(chat_id, file_id, caption=f"🎬 {title}\n\nDownloaded via @movie_Searcherrr_Bot")
    except Exception as e:
        bot.send_message(chat_id, "❌ ဖိုင်ပို့ဆောင်ရာတွင် Error ဖြစ်ပေါ်နေပါသည်။")
        print(f"Send File Error: {e}")

# ==========================================
# Main Execution
# ==========================================
if __name__ == "__main__":
    print("Movie Bot is running...")
    keep_alive()
    bot.infinity_polling()
