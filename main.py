import threading
import telebot
import subprocess
import os
import json
import zipfile
import tempfile
import shutil
import requests
import re
import gc
import logging
import json
import hashlib
import sys
import socket
import psutil
import time
from telebot import types
from datetime import datetime, timedelta
import signal
import sqlite3
import platform
import uuid
import base64

import os
import sys

# ✅ استخدام المسار الحالي للبوت
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# أو:
# BASE_DIR = os.getcwd()

PENDING_BOTS_DIR = os.path.join(BASE_DIR, 'pending_bots')
ACTIVE_BOTS_DIR = os.path.join(BASE_DIR, 'active_bots')
HOSTING_MANAGER_DIR = os.path.join(BASE_DIR, 'hosting_manager')

print(f"📁 المسار الأساسي: {BASE_DIR}")

# تأكد من إنشاء المجلدات
for directory in [PENDING_BOTS_DIR, ACTIVE_BOTS_DIR, HOSTING_MANAGER_DIR]:
    if not os.path.exists(directory):
        try:
            os.makedirs(directory, exist_ok=True)
            print(f"✅ تم إنشاء المجلد: {directory}")
        except Exception as e:
            print(f"❌ فشل في إنشاء المجلد {directory}: {e}")
            # محاولة استخدام مسار بديل
            BASE_DIR = '/tmp/bot_hosting' if os.access('/tmp', os.W_OK) else os.getcwd()
            break

# ثانياً: تعريف المتغيرات التي تستخدم المسارات
uploaded_files_dir = ACTIVE_BOTS_DIR  # الآن سيتم التعرف عليها

# ثالثاً: الإعدادات الأساسية
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot_security.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("SecureBot")

# المتغيرات العامة
TOKEN = '8790114718:AAGt9_wXVYBcyVfxgaqPr-mn49Rx_8AnJFY'
ADMIN_ID = 8214454565
YOUR_USERNAME = '@n_7_3_a'
CHANNEL_USERNAME = '@n_7_3_a_2'

# تعريف البوت هنا
bot = telebot.TeleBot(TOKEN)

# بقية المتغيرات...
bot_scripts = {}
stored_tokens = {}
user_subscriptions = {}  
user_files = {}  
active_users = set()  
banned_users = set()  
pending_approvals = {}  

bot_locked = False  
free_mode = False  
def extract_bot_info_from_folder(folder_name):
    """استخراج معلومات البوت من اسم المجلد"""
    try:
        # تنسيق المجلد: bot_<user_id>_<file_name_without_extension>
        if folder_name.startswith('bot_'):
            parts = folder_name.split('_')
            if len(parts) >= 3:
                user_id = int(parts[1])
                file_name = '_'.join(parts[2:]) + '.py'
                return user_id, file_name
        return None, None
    except:
        return None, None

def get_main_script_in_folder(folder_path):
    """الحصول على ملف البايثون الرئيسي في المجلد"""
    try:
        py_files = [f for f in os.listdir(folder_path) 
                   if f.endswith('.py') and not f.startswith('__')]
        
        # الأولوية لملف اسمه main.py أو bot.py
        for preferred in ['main.py', 'bot.py', 'start.py']:
            if preferred in py_files:
                return os.path.join(folder_path, preferred)
        
        # إذا لم يوجد، خذ أول ملف بايثون
        if py_files:
            return os.path.join(folder_path, py_files[0])
        
        return None
    except:
        return None
def start_existing_bots():
    """فحص مجلد البوتات النشطة وتشغيل جميع البوتات الموجودة"""
    try:
        logger.info("🔍 جاري فحص مجلد البوتات النشطة وتشغيل البوتات الموجودة...")
        
        # التأكد من وجود المجلد
        if not os.path.exists(ACTIVE_BOTS_DIR):
            logger.warning("مجلد البوتات النشطة غير موجود")
            return
        
        # الحصول على جميع المجلدات داخل ACTIVE_BOTS_DIR
        bot_folders = [f for f in os.listdir(ACTIVE_BOTS_DIR) 
                      if os.path.isdir(os.path.join(ACTIVE_BOTS_DIR, f))]
        
        if not bot_folders:
            logger.info("لا توجد بوتات مخزنة للبدء")
            return
        
        started_count = 0
        
        for bot_folder in bot_folders:
            try:
                bot_folder_path = os.path.join(ACTIVE_BOTS_DIR, bot_folder)
                
                # استخراج معلومات من اسم المجلد (تنسيق: bot_<user_id>_<file_name>)
                parts = bot_folder.split('_')
                if len(parts) >= 3:
                    user_id = int(parts[1])
                    file_name = '_'.join(parts[2:]) + '.py'
                    
                    # البحث عن ملف البايثون الرئيسي
                    py_files = [f for f in os.listdir(bot_folder_path) if f.endswith('.py')]
                    if not py_files:
                        logger.warning(f"لا توجد ملفات بايثون في {bot_folder}")
                        continue
                    
                    script_path = os.path.join(bot_folder_path, py_files[0])
                    
                    # تثبيت المتطلبات إذا وجدت
                    requirements_path = os.path.join(bot_folder_path, 'requirements.txt')
                    if os.path.exists(requirements_path):
                        logger.info(f"جاري تثبيت المتطلبات لـ {bot_folder}")
                        subprocess.check_call(['pip', 'install', '-r', requirements_path])
                    
                    # تشغيل البوت
                    logger.info(f"جاري تشغيل البوت: {bot_folder}")
                    env = os.environ.copy()
                    env["PYTHONPATH"] = bot_folder_path
                    
                    process = subprocess.Popen(['python3', script_path], 
                                             stdout=subprocess.PIPE, 
                                             stderr=subprocess.PIPE, 
                                             env=env)
                    
                    # حفظ معلومات البوت
                    bot_scripts[user_id] = {
                        'process': process, 
                        'folder_path': bot_folder_path,
                        'file_name': file_name,
                        'script_path': script_path,
                        'status': 'running',
                        'start_time': datetime.now(),
                        'bot_folder_name': bot_folder
                    }
                    
                    # بدء مراقبة البوت
                    threading.Thread(target=monitor_bot_process, 
                                   args=(process, user_id, file_name), 
                                   daemon=True).start()
                    
                    started_count += 1
                    logger.info(f"✅ تم تشغيل البوت: {bot_folder}")
                    
                    # إعلام الأدمن
                    try:
                        token = extract_token_from_script(script_path)
                        if token:
                            bot_info = requests.get(f'https://api.telegram.org/bot{token}/getMe').json()
                            if bot_info.get('ok'):
                                bot_username = bot_info['result']['username']
                                bot.send_message(
                                    ADMIN_ID, 
                                    f"🤖 تم تشغيل البوت تلقائياً عند بدء التشغيل:\n"
                                    f"📁 المجلد: {bot_folder}\n"
                                    f"👤 المستخدم: {user_id}\n"
                                    f"🤖 البوت: @{bot_username}\n"
                                    f"⏰ الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                                )
                    except Exception as e:
                        logger.error(f"خطأ في إعلام الأدمن: {e}")
                        
            except Exception as e:
                logger.error(f"❌ فشل في تشغيل البوت {bot_folder}: {e}")
        
        logger.info(f"✅ تم تشغيل {started_count} بوت من أصل {len(bot_folders)}")
        
        # إرسال تقرير للأدمن
        if started_count > 0:
            bot.send_message(
                ADMIN_ID,
                f"📊 **تقرير بدء التشغيل التلقائي:**\n\n"
                f"✅ تم تشغيل {started_count} بوت تلقائياً\n"
                f"📁 مجلدات موجودة: {len(bot_folders)}\n"
                f"⏰ الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
        
    except Exception as e:
        logger.error(f"❌ خطأ في بدء البوتات التلقائي: {e}")
# إنشاء المجلدات إذا لم تكن موجودة
for directory in [PENDING_BOTS_DIR, ACTIVE_BOTS_DIR, HOSTING_MANAGER_DIR]:
    if not os.path.exists(directory):
        os.makedirs(directory)
        logger.info(f"تم إنشاء المجلد: {directory}")

def init_db():
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS subscriptions
                 (user_id INTEGER PRIMARY KEY, expiry TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS user_files
                 (user_id INTEGER, file_name TEXT)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS active_users
                 (user_id INTEGER PRIMARY KEY)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS banned_users
                 (user_id INTEGER PRIMARY KEY, reason TEXT, ban_date TEXT)''')
    
    # أضف هذا الجدول الجديد:
    c.execute('''CREATE TABLE IF NOT EXISTS pending_uploads
                 (user_id INTEGER,
                  file_name TEXT,
                  temp_path TEXT,
                  libraries TEXT,
                  request_time TEXT,
                  PRIMARY KEY (user_id, file_name))''')
    
    conn.commit()
    conn.close()

def save_pending_upload(user_id, file_name, temp_path, libraries):
    """حفظ طلب الرفع في قاعدة البيانات"""
    try:
        conn = sqlite3.connect('bot_data.db')
        c = conn.cursor()
        
        libraries_str = json.dumps(libraries)  # تحويل القائمة لـ JSON
        
        c.execute('''INSERT OR REPLACE INTO pending_uploads 
                     (user_id, file_name, temp_path, libraries, request_time) 
                     VALUES (?, ?, ?, ?, ?)''',
                  (user_id, file_name, temp_path, libraries_str, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        logger.info(f"تم حفظ طلب الرفع للمستخدم {user_id} - الملف: {file_name}")
    except Exception as e:
        logger.error(f"فشل في حفظ طلب الرفع: {e}")

def load_pending_uploads():
    """تحميل طلبات الرفع من قاعدة البيانات"""
    try:
        conn = sqlite3.connect('bot_data.db')
        c = conn.cursor()
        
        c.execute('SELECT * FROM pending_uploads')
        uploads = c.fetchall()
        
        pending_uploads = {}
        for user_id, file_name, temp_path, libraries_str, request_time in uploads:
            libraries = json.loads(libraries_str) if libraries_str else []
            pending_uploads[(user_id, file_name)] = {
                'temp_path': temp_path,
                'libraries': libraries,
                'request_time': datetime.fromisoformat(request_time)
            }
        
        conn.close()
        logger.info(f"تم تحميل {len(pending_uploads)} طلب رفع من قاعدة البيانات")
        return pending_uploads
    except Exception as e:
        logger.error(f"فشل في تحميل طلبات الرفع: {e}")
        return {}

def remove_pending_upload(user_id, file_name):
    """حذف طلب الرفع من قاعدة البيانات"""
    try:
        conn = sqlite3.connect('bot_data.db')
        c = conn.cursor()
        
        c.execute('DELETE FROM pending_uploads WHERE user_id = ? AND file_name = ?', 
                  (user_id, file_name))
        
        conn.commit()
        conn.close()
        logger.info(f"تم حذف طلب الرفع للمستخدم {user_id} - الملف: {file_name}")
    except Exception as e:
        logger.error(f"فشل في حذف طلب الرفع: {e}")

def cleanup_old_requests():
    """حذف الطلبات الأقدم من 7 أيام والملفات المؤقتة من pending_bots"""
    try:
        conn = sqlite3.connect('bot_data.db')
        c = conn.cursor()
        
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        
        # جلب الطلبات القديمة
        c.execute('SELECT user_id, file_name, temp_path FROM pending_uploads WHERE request_time < ?', (week_ago,))
        old_requests = c.fetchall()
        
        # حذف الملفات المؤقتة من pending_bots
        for user_id, file_name, temp_path in old_requests:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                    logger.info(f"تم حذف الملف المؤقت: {temp_path}")
                except Exception as e:
                    logger.error(f"فشل في حذف الملف المؤقت {temp_path}: {e}")
            
            # أيضاً حذف من مجلد pending_bots إذا كان موجوداً
            pending_file_path = os.path.join(PENDING_BOTS_DIR, file_name)
            if os.path.exists(pending_file_path):
                try:
                    os.remove(pending_file_path)
                    logger.info(f"تم حذف الملف من pending_bots: {pending_file_path}")
                except Exception as e:
                    logger.error(f"فشل في حذف الملف من pending_bots: {e}")
        
        # حذف من قاعدة البيانات
        c.execute('DELETE FROM pending_uploads WHERE request_time < ?', (week_ago,))
        
        deleted_count = len(old_requests)
        conn.commit()
        conn.close()
        
        logger.info(f"تم تنظيف {deleted_count} طلب قديم")
        return deleted_count
    except Exception as e:
        logger.error(f"فشل في تنظيف الطلبات القديمة: {e}")
        return 0
        
def load_data():
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()

    c.execute('SELECT * FROM subscriptions')
    subscriptions = c.fetchall()
    for user_id, expiry in subscriptions:
        user_subscriptions[user_id] = {'expiry': datetime.fromisoformat(expiry)}
    
    c.execute('SELECT * FROM user_files')
    user_files_data = c.fetchall()
    for user_id, file_name in user_files_data:
        if user_id not in user_files:
            user_files[user_id] = []
        user_files[user_id].append(file_name)
    
    c.execute('SELECT * FROM active_users')
    active_users_data = c.fetchall()
    for user_id, in active_users_data:
        active_users.add(user_id)
    
    c.execute('SELECT user_id FROM banned_users')
    banned_users_data = c.fetchall()
    for user_id, in banned_users_data:
        banned_users.add(user_id)
    
    conn.close()
    
    # ✅ هذا هو الجزء الجديد - تحديث دالة تحميل الطلبات المعلقة
    global pending_approvals
    pending_uploads = load_pending_uploads()
    for key, value in pending_uploads.items():
        pending_approvals[key] = value
    
    logger.info(f"تم تحميل {len(pending_approvals)} طلب معلق")
    
    # تنظيف الطلبات القديمة
    cleaned_count = cleanup_old_requests()
    if cleaned_count > 0:
        logger.info(f"تم تنظيف {cleaned_count} طلب قديم عند بدء التشغيل")

def save_subscription(user_id, expiry):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO subscriptions (user_id, expiry) VALUES (?, ?)', 
              (user_id, expiry.isoformat()))
    conn.commit()
    conn.close()

def remove_subscription_db(user_id):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute('DELETE FROM subscriptions WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

def save_user_file(user_id, file_name):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute('INSERT INTO user_files (user_id, file_name) VALUES (?, ?)', 
              (user_id, file_name))
    conn.commit()
    conn.close()

def remove_user_file_db(user_id, file_name):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute('DELETE FROM user_files WHERE user_id = ? AND file_name = ?', 
              (user_id, file_name))
    conn.commit()
    conn.close()

def add_active_user(user_id):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO active_users (user_id) VALUES (?)', (user_id,))
    conn.commit()
    conn.close()

def remove_active_user(user_id):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute('DELETE FROM active_users WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

def ban_user(user_id, reason):
    banned_users.add(user_id)
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO banned_users (user_id, reason, ban_date) VALUES (?, ?, ?)', 
              (user_id, reason, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    logger.warning(f"تم حظر المستخدم {user_id} بسبب: {reason}")

def unban_user(user_id):
    if user_id in banned_users:
        banned_users.remove(user_id)
        conn = sqlite3.connect('bot_data.db')
        c = conn.cursor()
        c.execute('DELETE FROM banned_users WHERE user_id = ?', (user_id,))
        conn.commit()
        conn.close()
        logger.info(f"تم إلغاء حظر المستخدم {user_id}")
        return True
    return False

def is_user_subscribed_to_channel(user_id):
    try:
        chat_member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return chat_member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logger.error(f"فشل في التحقق من اشتراك المستخدم في القناة: {e}")
        return False

def extract_imports_from_file(file_path):
    """
    استخراج جميع المكتبات المستوردة من ملف بايثون
    """
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            content = file.read()
        
        imports = []
        
        # البحث عن استيرادات عادية
        import_patterns = [
            r'^\s*import\s+(\w+)',
            r'^\s*from\s+(\w+)\s+import',
            r'^\s*import\s+(\w+\.\w+)',
            r'^\s*from\s+(\w+\.\w+)\s+import'
        ]
        
        for pattern in import_patterns:
            matches = re.findall(pattern, content, re.MULTILINE)
            imports.extend(matches)
        
        # إزالة التكرارات
        unique_imports = list(set(imports))
        
        # ✅ قائمة المكتبات القياسية (لا تحتاج تثبيت)
        standard_libs = [
            'os', 'sys', 're', 'json', 'time', 'datetime', 'math', 'random',
            'threading', 'subprocess', 'shutil', 'tempfile', 'logging',
            'hashlib', 'socket', 'platform', 'uuid', 'base64', 'sqlite3',
            'urllib', 'itertools', 'collections', 'functools', 'operator',
            'pathlib', 'typing', 'enum', 'calendar', 'csv', 'html', 'http',
            'email', 'ssl', 'zipfile', 'gzip', 'tarfile', 'json', 'pickle',
            'shelve', 'dbm', 'sqlite3', 'xml', 'webbrowser', 'cgi', 'cgitb',
            'wsgiref', 'urllib', 'ftplib', 'poplib', 'imaplib', 'nntplib',
            'smtplib', 'telnetlib', 'uuid', 'socket', 'ssl', 'select',
            'selectors', 'asyncore', 'asynchat', 'signal', 'mmap', 'errno',
            'glob', 'fnmatch', 'linecache', 'shlex', 'macpath', 'stat',
            'filecmp', 'tempfile', 'fileinput', 'statvfs', 'fileinput',
            'ast', 'symtable', 'symbol', 'token', 'keyword', 'tokenize',
            'py_compile', 'compileall', 'dis', 'pickletools', 'formatter',
            'tabnanny', 'pyclbr', 'py_compile', 'compileall', 'dis',
            'pickletools', 'formatter', 'imputil', 'code', 'codeop',
            'pty', 'tty', 'termios', 'resource', 'nis', 'syslog', 'posix',
            'pwd', 'spwd', 'grp', 'crypt', 'dl', 'dbm', 'gdbm', 'termios',
            'tty', 'pty', 'fcntl', 'pipes', 'posixfile', 'resource',
            'nis', 'syslog', 'commands', 'getopt', 'argparse', 'getpass',
            'curses', 'platform', 'errno', 'ctypes', 'struct', 'weakref',
            'types', 'copy', 'pprint', 'reprlib', 'enum', 'numbers', 'math',
            'cmath', 'decimal', 'fractions', 'random', 'statistics', 'itertools',
            'functools', 'operator', 'collections', 'heapq', 'bisect', 'array',
            'weakref', 'copy', 'pprint', 'reprlib', 'enum', 'graphlib'
        ]
        
        # ✅ إرجاع المكتبات غير القياسية فقط
        filtered_imports = []
        for lib in unique_imports:
            # أخذ الجزء الأول فقط (مثلاً urllib.parse → urllib)
            base_lib = lib.split('.')[0]
            if base_lib not in standard_libs:
                filtered_imports.append(lib)
        
        return filtered_imports
        
    except Exception as e:
        logger.error(f"خطأ في استخراج المكتبات من {file_path}: {e}")
        return []
def modify_bot_database_path(script_path, new_db_path, bot_folder):
    """تعديل مسار قاعدة البيانات والملفات ليكون كل شيء في مجلد البوت"""
    try:
        with open(script_path, 'r', encoding='utf-8', errors='ignore') as file:
            content = file.read()
        
        # إنشاء المجلدات الداخلية
        data_dir = os.path.join(bot_folder, 'data')
        logs_dir = os.path.join(bot_folder, 'logs') 
        temp_dir = os.path.join(bot_folder, 'temp')
        assets_dir = os.path.join(bot_folder, 'assets')
        
        for directory in [data_dir, logs_dir, temp_dir, assets_dir]:
            if not os.path.exists(directory):
                os.makedirs(directory)
        
        # 🔴 **تصحيح الأنماط - تجنب استخدام backslash في f-strings**
        patterns = [
            # قواعد البيانات
            (r"sqlite3\.connect\(['\"]([^'\"]*\.db)['\"]\)", f"sqlite3.connect('{new_db_path}')"),
            (r"sqlite3\.connect\(['\"]([^'\"]*\.sqlite)['\"]\)", f"sqlite3.connect('{new_db_path}')"),
            
            # 🔴 **تصحيح الملفات العامة - استخدام format بدلاً من f-string**
            (r"open\(['\"]([^'\"]*\.json)['\"]", r"open('{}' + r'\1'".format(os.path.join(data_dir, ''))),
            (r"open\(['\"]([^'\"]*\.txt)['\"]", r"open('{}' + r'\1'".format(os.path.join(data_dir, ''))),
            (r"open\(['\"]([^'\"]*\.csv)['\"]", r"open('{}' + r'\1'".format(os.path.join(data_dir, ''))),
            
            # 🔴 **تصحيح السجلات**
            (r"logging\.FileHandler\(['\"]([^'\"]*\.log)['\"]\)", r"logging.FileHandler('{}' + r'\1')".format(os.path.join(logs_dir, ''))),
        ]
        
        modified_content = content
        
        for pattern, replacement in patterns:
            modified_content = re.sub(pattern, replacement, modified_content)
        
        # إضافة كود إعداد المسارات في بداية الملف
        setup_code = f"""
# ✅ إعدادات المسارات - مضافة تلقائياً
import os
import sqlite3

# المسارات الأساسية
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
LOGS_DIR = os.path.join(BASE_DIR, 'logs') 
TEMP_DIR = os.path.join(BASE_DIR, 'temp')
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')

# قاعدة البيانات
DB_PATH = os.path.join(BASE_DIR, '{os.path.basename(new_db_path)}')

# تأكد من وجود المجلدات
for directory in [DATA_DIR, LOGS_DIR, TEMP_DIR, ASSETS_DIR]:
    if not os.path.exists(directory):
        os.makedirs(directory)

# اتصال قاعدة البيانات
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

"""
        # إضافة الكود بعد الاستيرادات
        lines = modified_content.split('\n')
        imports_end = 0
        for i, line in enumerate(lines):
            if line.startswith(('import ', 'from ')) or line.strip() == '':
                imports_end = i
            else:
                break
        
        lines.insert(imports_end + 1, setup_code)
        modified_content = '\n'.join(lines)
        
        # حفظ الملف المعدل
        modified_script_path = os.path.join(bot_folder, f"modified_{os.path.basename(script_path)}")
        with open(modified_script_path, 'w', encoding='utf-8') as file:
            file.write(modified_content)
        
        logger.info(f"✅ تم إعداد البوت بمسارات منفصلة في: {bot_folder}")
        return modified_script_path
        
    except Exception as e:
        logger.error(f"❌ فشل في تعديل مسارات البوت: {e}")
        return script_path
def install_libraries(libraries):
    """
    تثبيت قائمة من المكتبات
    """
    results = []
    for lib in libraries:
        try:
            # تثبيت المكتبة
            subprocess.check_call(['pip', 'install', lib])
            results.append(f"✅ {lib} - تم التثبيت بنجاح")
            logger.info(f"تم تثبيت المكتبة {lib} بنجاح")
        except subprocess.CalledProcessError:
            try:
                # محاولة تثبيت مع إصدار أقدم
                subprocess.check_call(['pip', 'install', lib, '--upgrade'])
                results.append(f"✅ {lib} - تم التثبيت مع التحديث")
                logger.info(f"تم تثبيت المكتبة {lib} مع التحديث")
            except subprocess.CalledProcessError as e:
                results.append(f"❌ {lib} - فشل في التثبيت: {e}")
                logger.error(f"فشل في تثبيت المكتبة {lib}: {e}")
        except Exception as e:
            results.append(f"❌ {lib} - خطأ: {e}")
            logger.error(f"خطأ في تثبيت المكتبة {lib}: {e}")
    
    return results

def install_single_library(library_name):
    """
    تثبيت مكتبة واحدة مع حلول بديلة لـ Wesbsite
    """
    try:
        # المحاولة الأولى: تثبيت عادي مع إعدادات آمنة
        result = subprocess.run([
            'pip', 'install', library_name,
            '--no-cache-dir',
            '--timeout', '30',
            '--retries', '1',
            '--user'  # ✅ مهم لـ Wesbsite
        ], capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            return f"✅ تم تثبيت المكتبة {library_name} بنجاح"
        else:
            # المحاولة الثانية: تثبيت بدون تبعيات
            result = subprocess.run([
                'pip', 'install', library_name,
                '--no-dependencies',
                '--no-cache-dir',
                '--user'
            ], capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                return f"✅ تم تثبيت {library_name} (بدون تبعيات)"
            else:
                return f"❌ فشل في تثبيت {library_name}"
                
    except subprocess.TimeoutExpired:
        return f"⏰ انتهى وقت تثبيت {library_name}"
    except Exception as e:
        return f"❌ خطأ في تثبيت {library_name}: {str(e)[:50]}"
def install_libraries_safe(libraries):
    """
    تثبيت المكتبات بشكل آمن لاستضافة Wesbsite
    """
    results = []
    
    for i, lib in enumerate(libraries):
        try:
            # ✅ استراحة بين المكتبات
            if i > 0:
                time.sleep(10)  # 10 ثواني استراحة
            
            # ✅ فحص الذاكرة قبل كل تثبيت
            memory = psutil.virtual_memory()
            if memory.percent > 80:
                results.append(f"🛑 إيقاف التثبيت - الذاكرة {memory.percent}%")
                break
            
            logger.info(f"جاري تثبيت المكتبة {i+1}/{len(libraries)}: {lib}")
            
            # ✅ التثبيت مع إعدادات Wesbsite الآمنة
            result = subprocess.run([
                'python', '-m', 'pip', 'install', lib,
                '--no-cache-dir',
                '--timeout', '45',
                '--user',
                '--no-warn-script-location'
            ], capture_output=True, text=True, timeout=90)
            
            if result.returncode == 0:
                results.append(f"✅ {lib} - ناجح")
                logger.info(f"تم تثبيت {lib} بنجاح")
            else:
                # ✅ محاولة بديلة
                try:
                    result = subprocess.run([
                        'pip3', 'install', lib,
                        '--no-dependencies',
                        '--user'
                    ], capture_output=True, text=True, timeout=60)
                    
                    if result.returncode == 0:
                        results.append(f"✅ {lib} - ناجح (بدون تبعيات)")
                    else:
                        results.append(f"❌ {lib} - فشل")
                except:
                    results.append(f"❌ {lib} - فشل")
                    
        except Exception as e:
            results.append(f"❌ {lib} - خطأ: {str(e)[:30]}")
    
    return results
init_db()
load_data()

def create_main_menu(user_id):
    markup = types.InlineKeyboardMarkup()
    upload_button = types.InlineKeyboardButton('📤 رفـع مـلـف', callback_data='upload', style="primary")
    speed_button = types.InlineKeyboardButton('⚡ سـرعـة الـبـوت', callback_data='speed', style="success")
    install_lib_button = types.InlineKeyboardButton('📚 تـثـبـيـت مـڪـتـبـة', callback_data='install_library', style="primary")
    contact_button = types.InlineKeyboardButton('📞 الـمـطـوࢪ', url=f'https://t.me/{YOUR_USERNAME[1:]}', style="success")
    
    if user_id == ADMIN_ID:
        subscription_button = types.InlineKeyboardButton('💳 VIP ', callback_data='subscription', style="danger")
        stats_button = types.InlineKeyboardButton('📊 الـمـسـتـخـدمـيـن', callback_data='stats', style="primary")
        lock_button = types.InlineKeyboardButton('🔒 قـفـل', callback_data='lock_bot', style="danger")
        unlock_button = types.InlineKeyboardButton('🔓 فـتـح', callback_data='unlock_bot', style="primary")
        free_mode_button = types.InlineKeyboardButton('🔓  تـفـعـيـل', callback_data='free_mode', style="success")
        broadcast_button = types.InlineKeyboardButton('📢 نـشـر', callback_data='broadcast', style="primary")
        ban_button = types.InlineKeyboardButton('🔐 حـظـر', callback_data='ban_user', style="danger")
        unban_button = types.InlineKeyboardButton('🔓 الـغـاء حـظـر', callback_data='unban_user', style="success")
        
        # أضف زر الطلبات المعلقة هنا ✅
        pending_uploads_button = types.InlineKeyboardButton('📋 الطلبات المعلقة', callback_data='pending_uploads', style="primary")
        
        markup.add(upload_button, install_lib_button)
        markup.add(speed_button, subscription_button, stats_button)
        markup.add(lock_button, unlock_button, free_mode_button)
        markup.add(broadcast_button)
        markup.add(ban_button, unban_button)
        markup.add(pending_uploads_button)  # ✅ أضف الزر هنا
    else:
        markup.add(upload_button, install_lib_button)
        markup.add(speed_button)
    
    markup.add(contact_button)
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    
    if user_id in banned_users:
        bot.send_message(message.chat.id, "⛔ أنت محظور من استخدام هذا البوت. يرجى التواصل مع المطور إذا كنت تعتقد أن هذا خطأ.")
        return
    
    if bot_locked:
        bot.send_message(message.chat.id, "⚠️ البوت مقفل حالياً. الرجاء المحاولة لاحقًا.")
        return

    if not is_user_subscribed_to_channel(user_id):
        markup = types.InlineKeyboardMarkup()
        channel_button = types.InlineKeyboardButton('انضم إلى القناة', url=f'https://t.me/{CHANNEL_USERNAME[1:]}', style="success")
        check_button = types.InlineKeyboardButton('✅ تحقق من الاشتراك', callback_data='check_subscription', style="primary")
        markup.add(channel_button, check_button)
        bot.send_message(message.chat.id, "⚠️ يجب عليك الانضمام إلى قناتنا أولاً لاستخدام البوت.", reply_markup=markup)
        return

    user_name = message.from_user.first_name
    user_username = message.from_user.username

    try:
        user_profile = bot.get_chat(user_id)
        user_bio = user_profile.bio if user_profile.bio else "لا يوجد بايو"
    except Exception as e:
        logger.error(f"فشل في جلب البايو: {e}")
        user_bio = "لا يوجد بايو"

    try:
        user_profile_photos = bot.get_user_profile_photos(user_id, limit=1)
        if user_profile_photos.photos:
            photo_file_id = user_profile_photos.photos[0][-1].file_id  
        else:
            photo_file_id = None
    except Exception as e:
        logger.error(f"فشل في جلب صورة المستخدم: {e}")
        photo_file_id = None

    if user_id not in active_users:
        active_users.add(user_id)  
        add_active_user(user_id)  

        try:
            welcome_message_to_admin = f"🎉 انضم مستخدم جديد إلى البوت!\n\n"
            welcome_message_to_admin += f"👤 الاسم: {user_name}\n"
            welcome_message_to_admin += f"📌 اليوزر: @{user_username}\n"
            welcome_message_to_admin += f"🆔 الـ ID: {user_id}\n"
            welcome_message_to_admin += f"📝 البايو: {user_bio}\n"

            if photo_file_id:
                bot.send_photo(ADMIN_ID, photo_file_id, caption=welcome_message_to_admin)
            else:
                bot.send_message(ADMIN_ID, welcome_message_to_admin)
        except Exception as e:
            logger.error(f"فشل في إرسال تفاصيل المستخدم إلى الأدمن: {e}")

    welcome_message = f"〽️┇اهلا بك: {user_name}\n"
    welcome_message += f"🆔┇ايديك: {user_id}\n"
    welcome_message += f"♻️┇يوزرك: @{user_username}\n"
    welcome_message += f"📰┇بايو: {user_bio}\n\n"
    welcome_message += "〽️ أنا بوت استضافة ملفات بايثون 🎗 يمكنك استخدام الأزرار أدناه للتحكم ♻️"

    if photo_file_id:
        bot.send_photo(message.chat.id, photo_file_id, caption=welcome_message, reply_markup=create_main_menu(user_id))
    else:
        bot.send_message(message.chat.id, welcome_message, reply_markup=create_main_menu(user_id))

@bot.callback_query_handler(func=lambda call: call.data == 'check_subscription')
def check_subscription(call):
    user_id = call.from_user.id
    if is_user_subscribed_to_channel(user_id):
        bot.send_message(call.message.chat.id, "✅ شكراً للانضمام إلى قناتنا! يمكنك الآن استخدام البوت.")
        send_welcome(call.message)
    else:
        markup = types.InlineKeyboardMarkup()
        channel_button = types.InlineKeyboardButton('انضم إلى القناة', url=f'https://t.me/{CHANNEL_USERNAME[1:]}', style="success")
        check_button = types.InlineKeyboardButton('✅ تحقق من الاشتراك', callback_data='check_subscription', style="primary")
        markup.add(channel_button, check_button)
        bot.send_message(call.message.chat.id, "⚠️ لم تنضم بعد إلى القناة. يرجى الانضمام أولاً.", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == 'install_library')
def install_library_callback(call):
    user_id = call.from_user.id
    
    if user_id in banned_users:
        bot.send_message(call.message.chat.id, "⛔ أنت محظور من استخدام هذا البوت.")
        return
    
    if bot_locked:
        bot.send_message(call.message.chat.id, "⚠️ البوت مقفل حالياً.")
        return
        
    if not is_user_subscribed_to_channel(user_id):
        markup = types.InlineKeyboardMarkup()
        channel_button = types.InlineKeyboardButton('انضم إلى القناة', url=f'https://t.me/{CHANNEL_USERNAME[1:]}', style="success")
        check_button = types.InlineKeyboardButton('✅ تحقق من الاشتراك', callback_data='check_subscription', style="primary")
        markup.add(channel_button, check_button)
        bot.send_message(call.message.chat.id, "⚠️ يجب عليك الانضمام إلى قناتنا أولاً.", reply_markup=markup)
        return
    
    bot.send_message(call.message.chat.id, "📚 أرسل اسم المكتبة التي تريد تثبيتها:\n\nمثال:\n`telebot`\n`requests`\n`python-telegram-bot`")
    bot.register_next_step_handler(call.message, process_library_installation)
def stop_bot_completely(chat_id):
    """إيقاف البوت تماماً بدون حذف الملفات"""
    if chat_id in bot_scripts:
        try:
            # إيقاف العملية الرئيسية
            if bot_scripts[chat_id].get('process'):
                kill_process_tree(bot_scripts[chat_id]['process'])
            
            # إيقاف أي عمليات أخرى مرتبطة بنفس المسار
            script_path = bot_scripts[chat_id].get('script_path')
            if script_path and os.path.exists(script_path):
                kill_process_by_script_path(script_path)
            
            # تحديث حالة البوت
            bot_scripts[chat_id]['process'] = None
            bot_scripts[chat_id]['status'] = 'stopped'
            
            logger.info(f"تم إيقاف البوت للمستخدم {chat_id}")
            return True
            
        except Exception as e:
            logger.error(f"فشل في إيقاف البوت: {e}")
            return False
    return False


def find_bot_by_token(token):
    """البحث عن البوتات النشطة باستخدام توكن معين"""
    active_bots = []
    
    for chat_id, bot_info in bot_scripts.items():
        if bot_info.get('status') == 'running':
            try:
                script_path = bot_info.get('script_path')
                if script_path and os.path.exists(script_path):
                    current_token = extract_token_from_script(script_path)
                    if current_token == token:
                        active_bots.append({
                            'chat_id': chat_id,
                            'file_name': bot_info.get('file_name'),
                            'process': bot_info.get('process'),
                            'script_path': script_path,
                            'folder_path': bot_info.get('folder_path')
                        })
            except Exception as e:
                logger.error(f"خطأ في البحث عن البوت بالتوكن: {e}")
    
    return active_bots

def stop_and_remove_duplicate_bots(new_token, current_user_id, current_file_name):
    """إيقاف وحذف البوتات القديمة التي تستخدم نفس التوكن"""
    try:
        duplicate_bots = find_bot_by_token(new_token)
        stopped_count = 0
        
        for bot_info in duplicate_bots:
            # تجنب إيقاف البوت الحالي إذا كان مشغلاً
            if (bot_info['chat_id'] == current_user_id and 
                bot_info['file_name'] == current_file_name):
                continue
                
            logger.info(f"وجد بوت مكرر: {bot_info['file_name']} للمستخدم {bot_info['chat_id']}")
            
            # إيقاف البوت
            if stop_bot_completely(bot_info['chat_id']):
                stopped_count += 1
                logger.info(f"تم إيقاف البوت المكرر: {bot_info['file_name']}")
                
                # إرسال إشعار للمستخدم
                try:
                    bot.send_message(
                        bot_info['chat_id'], 
                        f"⚠️ تم إيقاف بوتك ({bot_info['file_name']}) تلقائياً لأنه تم رفع بوت جديد بنفس التوكن"
                    )
                except:
                    pass
                    
                # حذف الملفات
                delete_bot_files(bot_info['chat_id'])
        
        return stopped_count
        
    except Exception as e:
        logger.error(f"خطأ في إيقاف البوتات المكررة: {e}")
        return 0

def delete_bot_files(chat_id):
    """حذف ملفات البوت مع الاحتفاظ بالسجلات"""
    if chat_id in bot_scripts:
        try:
            file_name = bot_scripts[chat_id].get('file_name', '')
            folder_path = bot_scripts[chat_id].get('folder_path', '')
            
            # حذف الملفات فقط
            if folder_path and os.path.exists(folder_path):
                if os.path.isfile(folder_path):
                    # إذا كان ملفاً فردياً
                    os.remove(folder_path)
                    logger.info(f"تم حذف ملف البوت: {folder_path}")
                else:
                    # إذا كان مجلداً، احذف فقط ملفات البايثون الرئيسية
                    py_files = [f for f in os.listdir(folder_path) if f.endswith('.py')]
                    for py_file in py_files:
                        file_path = os.path.join(folder_path, py_file)
                        os.remove(file_path)
                        logger.info(f"تم حذف ملف: {file_path}")
            
            # حذف البيانات من الذاكرة
            if chat_id in user_files and file_name in user_files[chat_id]:
                user_files[chat_id].remove(file_name)
                remove_user_file_db(chat_id, file_name)
            
            # إزالة من bot_scripts
            if chat_id in bot_scripts:
                del bot_scripts[chat_id]
                
            return True
            
        except Exception as e:
            logger.error(f"فشل في حذف ملفات البوت: {e}")
            return False
    return False

def check_token_conflict(new_script_path, user_id, file_name):
    """فحص التعارض في التوكن وإيقاف البوتات المكررة"""
    try:
        new_token = extract_token_from_script(new_script_path)
        if not new_token:
            return False
            
        # البحث عن البوتات التي تستخدم نفس التوكن
        duplicate_bots = find_bot_by_token(new_token)
        
        if duplicate_bots:
            stopped_count = stop_and_remove_duplicate_bots(new_token, user_id, file_name)
            return stopped_count > 0
            
    except Exception as e:
        logger.error(f"خطأ في فحص تعارض التوكن: {e}")
    
    return False
def process_library_installation(message):
    user_id = message.from_user.id
    library_name = message.text.strip()
    
    if not library_name:
        bot.send_message(message.chat.id, "⚠️ يرجى إرسال اسم مكتبة صحيح.")
        return
    
    # فحص اسم المكتبة (تجنب الأوامر الخطيرة)
    dangerous_commands = [';', '&', '|', '&&', '||', '`', '$', '(', ')', '<', '>']
    if any(cmd in library_name for cmd in dangerous_commands):
        bot.send_message(message.chat.id, "❌ اسم المكتبة يحتوي على أحرف خطيرة.")
        return
    
    bot.send_message(message.chat.id, f"🔄 جاري تثبيت المكتبة `{library_name}`...")
    
    # تثبيت المكتبة
    result = install_single_library(library_name)
    bot.send_message(message.chat.id, result)

@bot.callback_query_handler(func=lambda call: call.data == 'broadcast')
def broadcast_callback(call):
    if call.from_user.id == ADMIN_ID:
        bot.send_message(call.message.chat.id, "أرسل الرسالة التي تريد إذاعتها:")
        bot.register_next_step_handler(call.message, process_broadcast_message)
    else:
        bot.send_message(call.message.chat.id, "⚠️ أنت لست المطور.")

def process_broadcast_message(message):
    if message.from_user.id == ADMIN_ID:
        broadcast_message = message.text
        success_count = 0
        fail_count = 0

        for user_id in active_users:
            try:
                bot.send_message(user_id, broadcast_message)
                success_count += 1
            except Exception as e:
                logger.error(f"فشل في إرسال الرسالة إلى المستخدم {user_id}: {e}")
                fail_count += 1

        bot.send_message(message.chat.id, f"✅ تم إرسال الرسالة إلى {success_count} مستخدم.\n❌ فشل إرسال الرسالة إلى {fail_count} مستخدم.")
    else:
        bot.send_message(message.chat.id, "⚠️ أنت لست المطور.")
        
@bot.callback_query_handler(func=lambda call: call.data == 'speed')
def bot_speed_info(call):
    try:
        start_time = time.time()
        response = requests.get(f'https://api.telegram.org/bot{TOKEN}/getMe')
        latency = time.time() - start_time
        if response.ok:
            bot.send_message(call.message.chat.id, f"⚡ سرعة البوت: {latency:.2f} ثانية.")
        else:
            bot.send_message(call.message.chat.id, "⚠️ فشل في الحصول على سرعة البوت.")
    except Exception as e:
        logger.error(f"حدث خطأ أثناء فحص سرعة البوت: {e}")
        bot.send_message(call.message.chat.id, f"❌ حدث خطأ أثناء فحص سرعة البوت: {e}")

@bot.callback_query_handler(func=lambda call: call.data == 'upload')
def ask_to_upload_file(call):
    user_id = call.from_user.id
    
    if user_id in banned_users:
        bot.send_message(call.message.chat.id, "⛔ أنت محظور من استخدام هذا البوت. يرجى التواصل مع المطور إذا كنت تعتقد أن هذا خطأ.")
        return
    
    if bot_locked:
        bot.send_message(call.message.chat.id, "⚠️ البوت مقفل حالياً. الرجاء التواصل مع المطور @n_7_3_a .")
        return
        
    if not is_user_subscribed_to_channel(user_id):
        markup = types.InlineKeyboardMarkup()
        channel_button = types.InlineKeyboardButton('انضم إلى القناة', url=f'https://t.me/{CHANNEL_USERNAME[1:]}', style="success")
        check_button = types.InlineKeyboardButton('✅ تحقق من الاشتراك', callback_data='check_subscription', style="primary")
        markup.add(channel_button, check_button)
        bot.send_message(call.message.chat.id, "⚠️ يجب عليك الانضمام إلى قناتنا أولاً لاستخدام هذه الميزة.", reply_markup=markup)
        return
    
    if free_mode or (user_id in user_subscriptions and user_subscriptions[user_id]['expiry'] > datetime.now()):
        bot.send_message(call.message.chat.id, "📄 من فضلك، أرسل الملف الذي تريد رفعه.")
    else:
        bot.send_message(call.message.chat.id, "⚠️ يجب عليك الاشتراك لاستخدام هذه الميزة. الرجاء التواصل مع المطور @n_7_3_a  .")

@bot.callback_query_handler(func=lambda call: call.data == 'subscription')
def subscription_menu(call):
    if call.from_user.id == ADMIN_ID:
        markup = types.InlineKeyboardMarkup()
        add_subscription_button = types.InlineKeyboardButton('➕ إضافة اشتراك', callback_data='add_subscription', style="primary")
        remove_subscription_button = types.InlineKeyboardButton('➖ إزالة اشتراك', callback_data='remove_subscription', style="danger")
        markup.add(add_subscription_button, remove_subscription_button)
        bot.send_message(call.message.chat.id, "اختر الإجراء الذي تريد تنفيذه:", reply_markup=markup)
    else:
        bot.send_message(call.message.chat.id, "⚠️ أنت لست المطور.")

@bot.callback_query_handler(func=lambda call: call.data == 'stats')
def stats_menu(call):
    if call.from_user.id == ADMIN_ID:
        total_files = sum(len(files) for files in user_files.values())
        total_users = len(user_files)
        active_users_count = len(active_users)
        banned_users_count = len(banned_users)
        bot.send_message(call.message.chat.id, f"📊 الإحصائيات:\n\n📂 عدد الملفات المرفوعة: {total_files}\n👤 عدد المستخدمين: {total_users}\n👥 المستخدمين النشطين: {active_users_count}\n🚫 المستخدمين المحظورين: {banned_users_count}")
    else:
        bot.send_message(call.message.chat.id, "⚠️ أنت لست المطور.")

@bot.callback_query_handler(func=lambda call: call.data == 'add_subscription')
def add_subscription_callback(call):
    if call.from_user.id == ADMIN_ID:
        bot.send_message(call.message.chat.id, "أرسل معرف المستخدم وعدد الأيام بالشكل التالي:\n/add_subscription <user_id> <days>")
    else:
        bot.send_message(call.message.chat.id, "⚠️ أنت لست المطور.")

@bot.callback_query_handler(func=lambda call: call.data == 'remove_subscription')
def remove_subscription_callback(call):
    if call.from_user.id == ADMIN_ID:
        bot.send_message(call.message.chat.id, "أرسل معرف المستخدم بالشكل التالي:\n/remove_subscription <user_id>")
    else:
        bot.send_message(call.message.chat.id, "⚠️ أنت لست المطور.")

@bot.callback_query_handler(func=lambda call: call.data == 'ban_user')
def ban_user_callback(call):
    if call.from_user.id == ADMIN_ID:
        bot.send_message(call.message.chat.id, "أرسل معرف المستخدم وسبب الحظر بالشكل التالي:\n/ban <user_id> <reason>")
    else:
        bot.send_message(call.message.chat.id, "⚠️ أنت لست المطور.")

@bot.callback_query_handler(func=lambda call: call.data == 'unban_user')
def unban_user_callback(call):
    if call.from_user.id == ADMIN_ID:
        bot.send_message(call.message.chat.id, "أرسل معرف المستخدم بالشكل التالي:\n/unban <user_id>")
    else:
        bot.send_message(call.message.chat.id, "⚠️ أنت لست المطور.")

@bot.message_handler(commands=['add_subscription'])
def add_subscription(message):
    if message.from_user.id == ADMIN_ID:
        try:
            user_id = int(message.text.split()[1])
            days = int(message.text.split()[2])
            expiry_date = datetime.now() + timedelta(days=days)
            user_subscriptions[user_id] = {'expiry': expiry_date}
            save_subscription(user_id, expiry_date)
            bot.send_message(message.chat.id, f"✅ تمت إضافة اشتراك لمدة {days} أيام للمستخدم {user_id}.")
        try:
               bot.send_message(user_id, f"🎉 تم تفعيل الاشتراك لك لمدة {days} أيام. يمكنك الآن استخدام البوت!")
        except Exception as e:
    logger.warning(f"فشل إرسال رسالة للمستخدم: {e}")
        except Exception as e:
            logger.error(f"حدث خطأ أثناء إضافة اشتراك: {e}")
            bot.send_message(message.chat.id, f"❌ حدث خطأ: {e}")
    else:
        bot.send_message(message.chat.id, "⚠️ أنت لست المطور.")

@bot.message_handler(commands=['remove_subscription'])
def remove_subscription(message):
    if message.from_user.id == ADMIN_ID:
        try:
            user_id = int(message.text.split()[1])
            if user_id in user_subscriptions:
                del user_subscriptions[user_id]
                remove_subscription_db(user_id)
                bot.send_message(message.chat.id, f"✅ تم إزالة الاشتراك للمستخدم {user_id}.")
                bot.send_message(user_id, "⚠️ تم إزالة اشتراكك. لم يعد بإمكانك استخدام البوت.")
            else:
                bot.send_message(message.chat.id, f"⚠️ المستخدم {user_id} ليس لديه اشتراك.")
        except Exception as e:
            logger.error(f"حدث خطأ أثناء إزالة اشتراك: {e}")
            bot.send_message(message.chat.id, f"❌ حدث خطأ: {e}")
    else:
        bot.send_message(message.chat.id, "⚠️ أنت لست المطور.")

@bot.message_handler(commands=['user_files'])
def show_user_files(message):
    if message.from_user.id == ADMIN_ID:
        try:
            user_id = int(message.text.split()[1])
            if user_id in user_files:
                files_list = "\n".join(user_files[user_id])
                bot.send_message(message.chat.id, f"📂 الملفات التي رفعها المستخدم {user_id}:\n{files_list}")
            else:
                bot.send_message(message.chat.id, f"⚠️ المستخدم {user_id} لم يرفع أي ملفات.")
        except Exception as e:
            logger.error(f"حدث خطأ أثناء عرض ملفات المستخدم: {e}")
            bot.send_message(message.chat.id, f"❌ حدث خطأ: {e}")
    else:
        bot.send_message(message.chat.id, "⚠️ أنت لست المطور.")

@bot.message_handler(commands=['lock'])
def lock_bot(message):
    if message.from_user.id == ADMIN_ID:
        global bot_locked
        bot_locked = True
        bot.send_message(message.chat.id, "🔒 تم قفل البوت.")
    else:
        bot.send_message(message.chat.id, "⚠️ أنت لست المطور.")

@bot.message_handler(commands=['unlock'])
def unlock_bot(message):
    if message.from_user.id == ADMIN_ID:
        global bot_locked
        bot_locked = False
        bot.send_message(message.chat.id, "🔓 تم فتح البوت.")
    else:
        bot.send_message(message.chat.id, "⚠️ أنت لست المطور.")

@bot.callback_query_handler(func=lambda call: call.data == 'lock_bot')
def lock_bot_callback(call):
    if call.from_user.id == ADMIN_ID:
        global bot_locked
        bot_locked = True
        bot.send_message(call.message.chat.id, "🔒 تم قفل البوت.")
    else:
        bot.send_message(call.message.chat.id, "⚠️ أنت لست المطور.")

@bot.callback_query_handler(func=lambda call: call.data == 'unlock_bot')
def unlock_bot_callback(call):
    if call.from_user.id == ADMIN_ID:
        global bot_locked
        bot_locked = False
        bot.send_message(call.message.chat.id, "🔓 تم فتح البوت.")
    else:
        bot.send_message(call.message.chat.id, "⚠️ أنت لست المطور.")

@bot.callback_query_handler(func=lambda call: call.data == 'free_mode')
def toggle_free_mode(call):
    if call.from_user.id == ADMIN_ID:
        global free_mode
        free_mode = not free_mode
        status = "مفتوح" if free_mode else "مغلق"
        bot.send_message(call.message.chat.id, f"🔓 تم تغيير وضع البوت بدون اشتراك إلى: {status}.")
    else:
        bot.send_message(call.message.chat.id, "⚠️ أنت لست المطور.")

@bot.message_handler(commands=['ban'])
def ban_user_command(message):
    if message.from_user.id == ADMIN_ID:
        try:
            parts = message.text.split(maxsplit=2)
            if len(parts) < 3:
                bot.send_message(message.chat.id, "⚠️ الصيغة الصحيحة: /ban <user_id> <reason>")
                return
            
            user_id = int(parts[1])
            reason = parts[2]
            
            ban_user(user_id, reason)
            bot.send_message(message.chat.id, f"✅ تم حظر المستخدم {user_id} بسبب: {reason}")
            try:
                bot.send_message(user_id, f"⛔ تم حظرك من استخدام البوت بسبب: {reason}")
            except:
                pass
        except Exception as e:
            logger.error(f"حدث خطأ أثناء حظر المستخدم: {e}")
            bot.send_message(message.chat.id, f"❌ حدث خطأ: {e}")
    else:
        bot.send_message(message.chat.id, "⚠️ أنت لست المطور.")

@bot.message_handler(commands=['unban'])
def unban_user_command(message):
    if message.from_user.id == ADMIN_ID:
        try:
            user_id = int(message.text.split()[1])
            
            if unban_user(user_id):
                bot.send_message(message.chat.id, f"✅ تم إلغاء حظر المستخدم {user_id}")
                try:
                    bot.send_message(user_id, f"🎉 تم إلغاء الحظر عنك. يمكنك الآن استخدام البوت مرة أخرى.")
                except:
                    pass
            else:
                bot.send_message(message.chat.id, f"⚠️ المستخدم {user_id} غير محظور.")
        except Exception as e:
            logger.error(f"فشل في إلغاء حظر المستخدم: {e}")
            bot.send_message(message.chat.id, f"❌ حدث خطأ: {e}")
    else:
        bot.send_message(message.chat.id, "⚠️ أنت لست المطور.")

# في دالة handle_file، أضف هذا الشرط في البداية:
@bot.message_handler(content_types=['document'])
def handle_file(message):
    user_id = message.from_user.id
    
    if user_id in banned_users:
        bot.reply_to(message, "⛔ أنت محظور من استخدام هذا البوت.")
        return
    
    if bot_locked:
        bot.reply_to(message, "⚠️ البوت مقفل حالياً.")
        return
        
    if not is_user_subscribed_to_channel(user_id):
        markup = types.InlineKeyboardMarkup()
        channel_button = types.InlineKeyboardButton('انضم إلى القناة', url=f'https://t.me/{CHANNEL_USERNAME[1:]}', style="primary")
        check_button = types.InlineKeyboardButton('✅ تحقق من الاشتراك', callback_data='check_subscription', style="success")
        markup.add(channel_button, check_button)
        bot.reply_to(message, "⚠️ يجب عليك الانضمام إلى قناتنا أولاً.", reply_markup=markup)
        return
    
    try:
        file_id = message.document.file_id
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        file_name = message.document.file_name
        
        if not file_name.endswith('.py') and not file_name.endswith('.zip'):
            bot.reply_to(message, "⚠️ هذا البوت خاص برفع ملفات بايثون (.py) أو أرشيفات zip فقط.")
            return

        # حفظ الملف مؤقتاً
        temp_path = os.path.join(PENDING_BOTS_DIR, file_name)
        with open(temp_path, 'wb') as temp_file:
            temp_file.write(downloaded_file)

        # استخراج المكتبات المطلوبة من الملف
        required_libraries = []
        if file_name.endswith('.py'):
            required_libraries = extract_imports_from_file(temp_path)
        elif file_name.endswith('.zip'):
            with tempfile.TemporaryDirectory() as temp_dir:
                with zipfile.ZipFile(temp_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        if file.endswith('.py'):
                            file_path = os.path.join(root, file)
                            required_libraries.extend(extract_imports_from_file(file_path))
        
        # إزالة التكرارات
        required_libraries = list(set(required_libraries))

        # ✅ إذا كان المستخدم هو الإدمن، اقبل الملف تلقائياً
        if user_id == ADMIN_ID:
            bot.reply_to(message, "🔧 جاري معالجة ملف الإدمن تلقائياً...")
            
            try:
                # ✅ إنشاء مجلد منفصل للبوت
                bot_folder_name = f"bot_{user_id}_{file_name.replace('.', '_').replace(' ', '_')}"
                bot_folder_path = os.path.join(ACTIVE_BOTS_DIR, bot_folder_name)
                
                if not os.path.exists(bot_folder_path):
                    os.makedirs(bot_folder_path)
                
                # ✅ تثبيت المكتبات تلقائياً قبل التشغيل
                if required_libraries:
                    bot.reply_to(message, f"📚 جاري تثبيت المكتبات المطلوبة: {', '.join(required_libraries)}")
                    results = install_libraries(required_libraries)
                    
                    # عرض نتائج التثبيت
                    success_count = len([r for r in results if '✅' in r])
                    bot.reply_to(message, f"✅ تم تثبيت {success_count} من {len(required_libraries)} مكتبة بنجاح")
                
                # ✅ نسخ الملف إلى المجلد الجديد
                if file_name.endswith('.zip'):
                    # استخراج الأرشيف مباشرة في المجلد الجديد
                    with zipfile.ZipFile(temp_path, 'r') as zip_ref:
                        zip_ref.extractall(bot_folder_path)
                    
                    # البحث عن ملف البايثون الرئيسي
                    py_files = [f for f in os.listdir(bot_folder_path) if f.endswith('.py')]
                    if py_files:
                        main_script = py_files[0]
                        final_script_path = os.path.join(bot_folder_path, main_script)
                    else:
                        bot.reply_to(message, "❌ لم يتم العثور على أي ملفات بايثون في الأرشيف.")
                        return
                else:
                    # نسخ الملف الفردي إلى المجلد الجديد
                    final_script_path = os.path.join(bot_folder_path, file_name)
                    shutil.copy2(temp_path, final_script_path)
                
                # ✅ تشغيل البوت مباشرة
                run_script_from_approval(final_script_path, user_id, bot_folder_path, file_name, message)
                
                # ✅ تنظيف الملف المؤقت
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                
                # ✅ لا حاجة لحفظ في pending_approvals لأن الإدمن تم قبوله تلقائياً
                return
                
            except Exception as e:
                logger.error(f"❌ فشل في معالجة ملف الإدمن: {e}")
                bot.reply_to(message, f"❌ حدث خطأ أثناء معالجة الملف: {e}")
                return

        # ✅ للمستخدمين العاديين - إرسال طلب الموافقة
        user_info = f"@{message.from_user.username}" if message.from_user.username else str(message.from_user.id)
        approval_message = f"📤 طلب رفع ملف جديد\n\n"
        approval_message += f"👤 المستخدم: {user_info}\n"
        approval_message += f"🆔 ID: {user_id}\n"
        approval_message += f"📄 اسم الملف: {file_name}\n"
        approval_message += f"📏 حجم الملف: {len(downloaded_file)} بايت\n"
        
        if required_libraries:
            approval_message += f"📚 المكتبات المطلوبة: {', '.join(required_libraries)}\n\n"
        else:
            approval_message += f"📚 المكتبات المطلوبة: لا توجد مكتبات إضافية\n\n"
            
        approval_message += "🔍 قم بفحص الملف يدوياً ثم اختر:"
        
        markup = types.InlineKeyboardMarkup()
        approve_button = types.InlineKeyboardButton('✅ الموافقة', callback_data=f'approve_{user_id}_{file_name}', style="primary")
        reject_button = types.InlineKeyboardButton('❌ الرفض', callback_data=f'reject_{user_id}_{file_name}', style="danger")
        
        # ❌ حذف زر تثبيت المكتبات المنفصل
        # if required_libraries:
        #     install_libs_button = types.InlineKeyboardButton('📥 تثبيت المكتبات', callback_data=f'install_libs_{user_id}_{file_name}', style="primary")
        #     markup.add(install_libs_button)
        
        markup.add(approve_button, reject_button)
        
        # حفظ المرجع للملف المؤقت في الذاكرة وقاعدة البيانات
        pending_approvals[(user_id, file_name)] = {
            'temp_path': temp_path,
            'libraries': required_libraries
        }
        
        # أضف هذا السطر لحفظ الطلب في قاعدة البيانات
        save_pending_upload(user_id, file_name, temp_path, required_libraries)
        
        # إرسال الملف للموافقة
        with open(temp_path, 'rb') as file:
            bot.send_document(ADMIN_ID, file, caption=approval_message, reply_markup=markup)
        
        bot.reply_to(message, "⟣━⚡📨 تم إرسال طلب رفع الملف ⚡━⟢.")
        
    except Exception as e:
        logger.error(f"فشل في معالجة الملف: {e}")
        bot.reply_to(message, f"❌ حدث خطأ: {e}")

# 2. تعديل دالة handle_approval لدمج تثبيت المكتبات مع الموافقة
@bot.callback_query_handler(func=lambda call: call.data.startswith(('approve_', 'reject_')))
def handle_approval(call):
    if call.from_user.id == ADMIN_ID:
        # الموافقة أو الرفض
        action, user_id, file_name = call.data.split('_', 2)
        user_id = int(user_id)
        file_key = (user_id, file_name)
        
        # البحث في الذاكرة أولاً، ثم في قاعدة البيانات
        if file_key in pending_approvals:
            temp_path = pending_approvals[file_key]['temp_path']
            libraries = pending_approvals[file_key]['libraries']
        else:
            # تحميل من قاعدة البيانات
            pending_uploads = load_pending_uploads()
            if file_key in pending_uploads:
                temp_path = pending_uploads[file_key]['temp_path']
                libraries = pending_uploads[file_key]['libraries']
                pending_approvals[file_key] = pending_uploads[file_key]
            else:
                bot.send_message(ADMIN_ID, "⚠️ انتهت صلاحية طلب الموافقة أو تم معالجته مسبقاً.")
                return
        
        if action == 'approve':
            try:
                # ✅ تثبيت المكتبات أولاً (إذا وجدت)
                if libraries:
                    bot.send_message(ADMIN_ID, f"📚 جاري تثبيت المكتبات المطلوبة للملف {file_name}...")
                    results = install_libraries(libraries)
                    
                    # عرض نتائج التثبيت
                    success_count = len([r for r in results if '✅' in r])
                    bot.send_message(ADMIN_ID, f"✅ تم تثبيت {success_count} من {len(libraries)} مكتبة بنجاح")
                
                # ✅ إنشاء مجلد منفصل للبوت في ACTIVE_BOTS_DIR
                bot_folder_name = f"bot_{user_id}_{file_name.replace('.', '_').replace(' ', '_')}"
                bot_folder_path = os.path.join(ACTIVE_BOTS_DIR, bot_folder_name)
                
                if not os.path.exists(bot_folder_path):
                    os.makedirs(bot_folder_path)
                
                # ✅ نسخ الملف من pending_bots إلى المجلد الجديد
                if file_name.endswith('.zip'):
                    # استخراج الأرشيف مباشرة في المجلد الجديد
                    with zipfile.ZipFile(temp_path, 'r') as zip_ref:
                        zip_ref.extractall(bot_folder_path)
                    
                    # البحث عن ملف البايثون الرئيسي
                    py_files = [f for f in os.listdir(bot_folder_path) if f.endswith('.py')]
                    if py_files:
                        main_script = py_files[0]
                        final_script_path = os.path.join(bot_folder_path, main_script)
                    else:
                        bot.send_message(ADMIN_ID, f"❌ لم يتم العثور على أي ملفات بايثون في الأرشيف.")
                        bot.send_message(user_id, "❌ لم يتم العثور على أي ملفات بايثون في الأرشيف.")
                        return
                else:
                    # نسخ الملف الفردي إلى المجلد الجديد
                    final_script_path = os.path.join(bot_folder_path, file_name)
                    shutil.copy2(temp_path, final_script_path)

                # ✅ تشغيل البوت من المجلد الجديد
                run_script_from_approval(final_script_path, user_id, bot_folder_path, file_name, call.message)

                # ✅ حفظ في قاعدة البيانات
                if user_id not in user_files:
                    user_files[user_id] = []
                user_files[user_id].append(file_name)
                save_user_file(user_id, file_name)
                
                # ✅ حذف الملف من pending_bots بعد النقل
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                    logger.info(f"✅ تم حذف الملف من pending_bots: {temp_path}")
                
                bot.send_message(ADMIN_ID, f"✅ تمت الموافقة على رفع الملف {file_name} للمستخدم {user_id}.")
                bot.send_message(user_id, f"⟣━✨✅ تمت الموافقة على رفع ملفك {file_name} وتم تشغيله بنجاح — وتم تفعيل الطلب بنظام ملكي ⚔️✨━⟢")
                
            except Exception as e:
                logger.error(f"❌ فشل في معالجة الملف بعد الموافقة: {e}")
                bot.send_message(ADMIN_ID, f"❌ فشل في معالجة الملف بعد الموافقة: {e}")
                bot.send_message(user_id, f"❌ حدث خطأ أثناء معالجة ملفك: {e}")
        else:
            # الرفض
            if os.path.exists(temp_path):
                os.remove(temp_path)
                logger.info(f"✅ تم حذف الملف المرفوض من pending_bots: {temp_path}")
            bot.send_message(ADMIN_ID, f"❌ تم رفض رفع الملف {file_name} للمستخدم {user_id}.")
            bot.send_message(user_id, f"⟢⚡❌ تم رفض ملفك {file_name} يا عيل هكر كرتونة، أبعد عن البوت قبل ما ندفنك ديجيتالياً 👑💀⟣")
        
        # تنظيف الطلب من الذاكرة وقاعدة البيانات
        if file_key in pending_approvals:
            del pending_approvals[file_key]
        remove_pending_upload(user_id, file_name)
    else:
        bot.send_message(call.message.chat.id, "⚠️ أنت لست المطور.")
def run_script_from_approval(script_path, chat_id, folder_path, file_name, original_message):
    """تشغيل البوت بعد الموافقة (بدون إنشاء نسخ إضافية)"""
    try:
        # ✅ إنشاء قاعدة بيانات منفصلة للبوت
        bot_db_path = os.path.join(folder_path, f'bot_{chat_id}.db')
        
        # ✅ تعديل مسار قاعدة البيانات في ملف البوت
        modified_script_path = modify_bot_database_path(script_path, bot_db_path, folder_path)
        
        # ✅ فحص التعارض في التوكن أولاً
        token_conflict = check_token_conflict(modified_script_path, chat_id, file_name)
        if token_conflict:
            bot.send_message(chat_id, "🔄 جاري إيقاف البوت القديم بنفس التوكن...")

        # ✅ تثبيت المتطلبات إذا وجدت
        requirements_path = os.path.join(folder_path, 'requirements.txt')
        if os.path.exists(requirements_path):
            bot.send_message(chat_id, "🔄 جارٍ تثبيت المتطلبات...")
            subprocess.check_call(['pip', 'install', '-r', requirements_path])

        bot.send_message(chat_id, f"🚀 جارٍ تشغيل البوت {file_name}...")
        
        env = os.environ.copy()
        env["PYTHONPATH"] = folder_path
        
        # ✅ تشغيل الملف المعدل
        process = subprocess.Popen(['python3', modified_script_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        
        # ✅ حفظ معلومات البوت مع مسار قاعدة البيانات الجديدة
        bot_scripts[chat_id] = {
            'process': process, 
            'folder_path': folder_path,
            'file_name': file_name,
            'script_path': modified_script_path,
            'status': 'running',
            'start_time': datetime.now(),
            'bot_folder_name': os.path.basename(folder_path),
            'db_path': bot_db_path  # ✅ حفظ مسار قاعدة البيانات المنفصلة
        }

        token = extract_token_from_script(modified_script_path)
        if token:
            try:
                bot_info = requests.get(f'https://api.telegram.org/bot{token}/getMe').json()
                if bot_info.get('ok'):
                    bot_username = bot_info['result']['username']

                    user_info = f"@{original_message.from_user.username}" if original_message.from_user.username else str(original_message.from_user.id)
                    caption = f"📤 قام المستخدم {user_info} برفع ملف بوت جديد. معرف البوت: @{bot_username}"
                    
                    if token_conflict:
                        caption += "\n⚠️ تم إيقاف البوت القديم بنفس التوكن تلقائياً"
                    
                    bot.send_document(ADMIN_ID, open(modified_script_path, 'rb'), caption=caption)

                    # ✅ لوحة التحكم للأدمن
                    admin_markup = create_admin_control_markup(chat_id, file_name, 'running')
                    status_msg = f"🤖 البوت {file_name} يعمل الآن\n📁 المجلد: {os.path.basename(folder_path)}"
                    if token_conflict:
                        status_msg += "\n⚠️ تم إيقاف البوت القديم بنفس التوكن"
                    bot.send_message(ADMIN_ID, status_msg, reply_markup=admin_markup)

                    # ✅ لوحة التحكم للمستخدم
                    user_markup = create_user_control_markup(chat_id, file_name, 'running')
                    user_status_msg = f"🤖 البوت {file_name} يعمل الآن\n📁 المجلد: {os.path.basename(folder_path)}"
                    if token_conflict:
                        user_status_msg += "\n⚠️ تم إيقاف البوت القديم بنفس التوكن"
                    bot.send_message(chat_id, user_status_msg, reply_markup=user_markup)
                    
            except Exception as e:
                logger.error(f"فشل في التحقق من معرف البوت: {e}")
        else:
            user_info = f"@{original_message.from_user.username}" if original_message.from_user.username else str(original_message.from_user.id)
            caption = f"📤 قام المستخدم {user_info} برفع ملف بوت جديد، ولكن لم أتمكن من جلب معرف البوت."
            if token_conflict:
                caption += "\n⚠️ تم إيقاف البوت القديم بنفس التوكن تلقائياً"
            bot.send_document(ADMIN_ID, open(modified_script_path, 'rb'), caption=caption)

        # بدء مراقبة البوت
        threading.Thread(target=monitor_bot_process, args=(process, chat_id, file_name), daemon=True).start()

    except Exception as e:
        logger.error(f"فشل في تشغيل البوت: {e}")
        bot.send_message(chat_id, f"❌ حدث خطأ أثناء تشغيل البوت: {e}")
def run_script(script_path, chat_id, folder_path, file_name, original_message):
    try:
        # ✅ فحص التعارض في التوكن أولاً
        token_conflict = check_token_conflict(script_path, chat_id, file_name)
        if token_conflict:
            bot.send_message(chat_id, "🔄 جاري إيقاف البوت القديم بنفس التوكن...")
        
        # ✅ إنشاء مجلد منفصل للبوت في ACTIVE_BOTS_DIR
        bot_folder_name = f"bot_{chat_id}_{file_name.replace('.', '_')}"
        bot_folder_path = os.path.join(ACTIVE_BOTS_DIR, bot_folder_name)
        
        if not os.path.exists(bot_folder_path):
            os.makedirs(bot_folder_path)
        
        # ✅ نسخ الملفات إلى المجلد الجديد
        if file_name.endswith('.zip'):
            # استخراج الأرشيف في المجلد الجديد
            with zipfile.ZipFile(script_path, 'r') as zip_ref:
                zip_ref.extractall(bot_folder_path)
            
            # البحث عن ملف البايثون الرئيسي
            py_files = [f for f in os.listdir(bot_folder_path) if f.endswith('.py')]
            if py_files:
                main_script = py_files[0]
                final_script_path = os.path.join(bot_folder_path, main_script)
            else:
                raise Exception("لم يتم العثور على أي ملفات بايثون في الأرشيف")
        else:
            # نسخ الملف الفردي
            final_script_path = os.path.join(bot_folder_path, file_name)
            shutil.copy2(script_path, final_script_path)
        
        # ✅ تثبيت المتطلبات إذا وجدت
        requirements_path = os.path.join(bot_folder_path, 'requirements.txt')
        if os.path.exists(requirements_path):
            bot.send_message(chat_id, "🔄 جارٍ تثبيت المتطلبات...")
            subprocess.check_call(['pip', 'install', '-r', requirements_path])

        bot.send_message(chat_id, f"🚀 جارٍ تشغيل البوت {file_name}...")
        
        env = os.environ.copy()
        env["PYTHONPATH"] = bot_folder_path
        
        process = subprocess.Popen(['python3', final_script_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        
        # ✅ حفظ معلومات البوت مع المسار الجديد
        bot_scripts[chat_id] = {
            'process': process, 
            'folder_path': bot_folder_path,  # المسار الجديد
            'file_name': file_name,
            'script_path': final_script_path,  # المسار الجديد
            'status': 'running',
            'start_time': datetime.now(),
            'bot_folder_name': bot_folder_name  # اسم المجلد الجديد
        }

        token = extract_token_from_script(final_script_path)
        if token:
            try:
                bot_info = requests.get(f'https://api.telegram.org/bot{token}/getMe').json()
                if bot_info.get('ok'):
                    bot_username = bot_info['result']['username']

                    user_info = f"@{original_message.from_user.username}" if original_message.from_user.username else str(original_message.from_user.id)
                    caption = f"📤 قام المستخدم {user_info} برفع ملف بوت جديد. معرف البوت: @{bot_username}"
                    
                    if token_conflict:
                        caption += "\n⚠️ تم إيقاف البوت القديم بنفس التوكن تلقائياً"
                    
                    bot.send_document(ADMIN_ID, open(final_script_path, 'rb'), caption=caption)

                    # ✅ لوحة التحكم للأدمن
                    admin_markup = create_admin_control_markup(chat_id, file_name, 'running')
                    status_msg = f"🤖 البوت {file_name} يعمل الآن\n📁 المجلد: {bot_folder_name}"
                    if token_conflict:
                        status_msg += "\n⚠️ تم إيقاف البوت القديم بنفس التوكن"
                    bot.send_message(ADMIN_ID, status_msg, reply_markup=admin_markup)

                    # ✅ لوحة التحكم للمستخدم
                    user_markup = create_user_control_markup(chat_id, file_name, 'running')
                    user_status_msg = f"🤖 البوت {file_name} يعمل الآن\n📁 المجلد: {bot_folder_name}"
                    if token_conflict:
                        user_status_msg += "\n⚠️ تم إيقاف البوت القديم بنفس التوكن"
                    bot.send_message(chat_id, user_status_msg, reply_markup=user_markup)
                    
                else:
                    bot.send_message(chat_id, f"✅ تم تشغيل البوت بنجاح! ولكن لم أتمكن من التحقق من معرف البوت.")
            except Exception as e:
                logger.error(f"فشل في التحقق من معرف البوت: {e}")
                bot.send_message(chat_id, f"✅ تم تشغيل البوت بنجاح! ولكن لم أتمكن من التحقق من معرف البوت.")
        else:
            bot.send_message(chat_id, f"✅ تم تشغيل البوت بنجاح! ولكن لم أتمكن من جلب معرف البوت.")
            user_info = f"@{original_message.from_user.username}" if original_message.from_user.username else str(original_message.from_user.id)
            caption = f"📤 قام المستخدم {user_info} برفع ملف بوت جديد، ولكن لم أتمكن من جلب معرف البوت."
            if token_conflict:
                caption += "\n⚠️ تم إيقاف البوت القديم بنفس التوكن تلقائياً"
            bot.send_document(ADMIN_ID, open(final_script_path, 'rb'), caption=caption)

        # بدء مراقبة البوت في thread منفصل
        threading.Thread(target=monitor_bot_process, args=(process, chat_id, file_name), daemon=True).start()

    except Exception as e:
        logger.error(f"فشل في تشغيل البوت: {e}")
        bot.send_message(chat_id, f"❌ حدث خطأ أثناء تشغيل البوت: {e}")
def create_admin_control_markup(chat_id, file_name, status):
    """إنشاء أزرار تحكم ديناميكية للأدمن"""
    markup = types.InlineKeyboardMarkup()
    
    if status == 'running':
        # إذا البوت شغال - يظهر زر إيقاف
        stop_button = types.InlineKeyboardButton(f"⏹️ إيقاف {file_name}", callback_data=f'stop_{chat_id}_{file_name}')
        delete_button = types.InlineKeyboardButton(f"🗑️ حذف {file_name}", callback_data=f'delete_{chat_id}_{file_name}')
        markup.add(stop_button, delete_button)
    else:
        # إذا البوت متوقف - يظهر زر تشغيل
        start_button = types.InlineKeyboardButton(f"▶️ تشغيل {file_name}", callback_data=f'start_{chat_id}_{file_name}')
        delete_button = types.InlineKeyboardButton(f"🗑️ حذف {file_name}", callback_data=f'delete_{chat_id}_{file_name}')
        markup.add(start_button, delete_button)
    
    return markup

def create_user_control_markup(chat_id, file_name, status):
    """إنشاء أزرار تحكم ديناميكية للمستخدم"""
    markup = types.InlineKeyboardMarkup()
    
    if status == 'running':
        # إذا البوت شغال - يظهر زر إيقاف
        stop_button = types.InlineKeyboardButton(f"⏹️ إيقاف {file_name}", callback_data=f'stop_{chat_id}_{file_name}')
        markup.add(stop_button)
    else:
        # إذا البوت متوقف - يظهر زر تشغيل
        start_button = types.InlineKeyboardButton(f"▶️ تشغيل {file_name}", callback_data=f'start_{chat_id}_{file_name}')
        markup.add(start_button)
    
    return markup

def get_bot_status(chat_id, file_name):
    """الحصول على حالة البوت"""
    if chat_id in bot_scripts:
        script_info = bot_scripts[chat_id]
        if script_info.get('file_name') == file_name:
            return script_info.get('status', 'stopped')
    return 'stopped'
def monitor_bot_process(process, chat_id, file_name):
    """مراقبة عملية البوت لاكتشاف أي توقف مفاجئ"""
    try:
        stdout, stderr = process.communicate(timeout=1)
        
        # إذا وصلنا هنا، فهذا يعني أن البوت توقف
        if process.poll() is not None:
            if chat_id in bot_scripts:
                bot_scripts[chat_id]['status'] = 'crashed'
            
            error_msg = stderr.decode('utf-8') if stderr else "غير معروف"
            logger.warning(f"البوت {file_name} للمستخدم {chat_id} توقف بشكل غير متوقع. الخطأ: {error_msg}")
            
            # إرسال إشعار للمستخدم
            try:
                bot.send_message(chat_id, f"⚠️ البوت {file_name} توقف بشكل غير متوقع.\n\nالخطأ: {error_msg[:500]}")
            except:
                pass
                
    except subprocess.TimeoutExpired:
        # البوت لا يزال يعمل (هذا طبيعي)
        pass
    except Exception as e:
        logger.error(f"خطأ في مراقبة البوت: {e}")

def extract_token_from_script(script_path):
    """استخراج التوكن من ملف البوت"""
    try:
        with open(script_path, 'r', encoding='utf-8', errors='ignore') as script_file:
            file_content = script_file.read()

            # أنماط مختلفة للبحث عن التوكن
            patterns = [
                r"['\"]([0-9]{9,10}:[A-Za-z0-9_-]{35})['\"]",  # التوكن الكلاسيكي
                r"TOKEN\s*=\s*['\"]([0-9]{9,10}:[A-Za-z0-9_-]+)['\"]",
                r"token\s*=\s*['\"]([0-9]{9,10}:[A-Za-z0-9_-]+)['\"]",
                r"BOT_TOKEN\s*=\s*['\"]([0-9]{9,10}:[A-Za-z0-9_-]+)['\"]",
                r"bot\.setWebhook\([^)]*['\"]([0-9]{9,10}:[A-Za-z0-9_-]+)['\"]"
            ]
            
            for pattern in patterns:
                token_match = re.search(pattern, file_content)
                if token_match:
                    return token_match.group(1)
                    
            logger.warning(f"لم يتم العثور على توكن في {script_path}")
    except Exception as e:
        logger.error(f"فشل في استخراج التوكن من {script_path}: {e}")
    return None


def restart_bot(chat_id):
    """إعادة تشغيل البوت المتوقف"""
    if chat_id in bot_scripts and bot_scripts[chat_id].get('status') in ['stopped', 'crashed']:
        try:
            script_path = bot_scripts[chat_id].get('script_path')
            folder_path = bot_scripts[chat_id].get('folder_path')
            file_name = bot_scripts[chat_id].get('file_name')
            
            if script_path and os.path.exists(script_path):
                env = os.environ.copy()
                env["PYTHONPATH"] = os.path.dirname(script_path)
                
                process = subprocess.Popen(['python3', script_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
                
                bot_scripts[chat_id]['process'] = process
                bot_scripts[chat_id]['status'] = 'running'
                bot_scripts[chat_id]['start_time'] = datetime.now()
                
                # بدء مراقبة البوت من جديد
                threading.Thread(target=monitor_bot_process, args=(process, chat_id, file_name), daemon=True).start()
                
                logger.info(f"تم إعادة تشغيل البوت للمستخدم {chat_id}")
                return True
        except Exception as e:
            logger.error(f"فشل في إعادة تشغيل البوت: {e}")
    
    return False
def stop_running_bot(chat_id):
    """إيقاف تشغيل البوت مع الاحتفاظ بالملفات"""
    if stop_bot_completely(chat_id):
        bot.send_message(chat_id, "🔴 تم إيقاف تشغيل البوت بنجاح.")
    else:
        bot.send_message(chat_id, "⚠️ لا يوجد بوت يعمل حالياً أو حدث خطأ في الإيقاف.")
# أضف في القائمة الرئيسية للإدمن
# 4. تعديل دالة show_pending_uploads لإزالة زر تثبيت المكتبات
@bot.callback_query_handler(func=lambda call: call.data == 'pending_uploads')
def show_pending_uploads(call):
    if call.from_user.id == ADMIN_ID:
        try:
            # ✅ تحديث القائمة أولاً من قاعدة البيانات
            pending_uploads = load_pending_uploads()
            for key, value in pending_uploads.items():
                if key not in pending_approvals:
                    pending_approvals[key] = value
            
            if pending_approvals:
                message = "📋 الطلبات المعلقة:\n\n"
                for (user_id, file_name), data in pending_approvals.items():
                    message += f"👤 المستخدم: {user_id}\n"
                    message += f"📄 الملف: {file_name}\n"
                    message += f"📚 المكتبات: {', '.join(data['libraries']) if data['libraries'] else 'لا يوجد'}\n"
                    
                    # ✅ إضافة أزرار للموافقة والرفض فقط
                    markup = types.InlineKeyboardMarkup()
                    approve_button = types.InlineKeyboardButton('✅ الموافقة', callback_data=f'approve_{user_id}_{file_name}', style="success")
                    reject_button = types.InlineKeyboardButton('❌ الرفض', callback_data=f'reject_{user_id}_{file_name}', style="primary")
                    
                    # ❌ حذف زر تثبيت المكتبات المنفصل
                    # if data['libraries']:
                    #     install_button = types.InlineKeyboardButton('📥 تثبيت المكتبات', callback_data=f'install_libs_{user_id}_{file_name}', style="primary")
                    #     markup.add(install_button)
                    
                    markup.add(approve_button, reject_button)
                    
                    message += "─" * 20 + "\n"
                    bot.send_message(call.message.chat.id, message, reply_markup=markup)
                    message = ""  # إعادة تعيين الرسالة للرسالة التالية
                
            else:
                bot.send_message(call.message.chat.id, "✅ لا توجد طلبات معلقة حالياً.")
                
        except Exception as e:
            logger.error(f"خطأ في عرض الطلبات المعلقة: {e}")
            bot.send_message(call.message.chat.id, f"❌ حدث خطأ في عرض الطلبات: {e}")
    else:
        bot.send_message(call.message.chat.id, "⚠️ أنت لست المطور.")
        
def delete_uploaded_file(chat_id):
    """حذف البوت مع إيقافه وحذف مجلده بالكامل بما فيه قاعدة البيانات"""
    if chat_id in bot_scripts:
        try:
            file_name = bot_scripts[chat_id].get('file_name', '')
            folder_path = bot_scripts[chat_id].get('folder_path', '')
            db_path = bot_scripts[chat_id].get('db_path', '')
            
            # 1. أولاً إيقاف البوت تماماً
            stop_bot_completely(chat_id)
            
            # 2. حذف المجلد بالكامل إذا كان موجوداً (بيشمل قاعدة البيانات)
            if folder_path and os.path.exists(folder_path) and folder_path.startswith(ACTIVE_BOTS_DIR):
                shutil.rmtree(folder_path)  # حذف المجلد بالكامل
                logger.info(f"✅ تم حذف مجلد البوت بالكامل: {folder_path}")
            
            # 3. حذف البيانات من الذاكرة وقاعدة البيانات الرئيسية
            if chat_id in user_files and file_name in user_files[chat_id]:
                user_files[chat_id].remove(file_name)
                remove_user_file_db(chat_id, file_name)
            
            # 4. إزالة من bot_scripts
            del bot_scripts[chat_id]
            
            bot.send_message(chat_id, "🗑️ تم حذف البوت وإيقافه تماماً مع جميع بياناته.")
            return True
            
        except Exception as e:
            logger.error(f"❌ فشل في حذف البوت: {e}")
            bot.send_message(chat_id, f"❌ حدث خطأ أثناء حذف البوت: {e}")
            return False
    else:
        bot.send_message(chat_id, "⚠️ لا يوجد بوت لحذفه.")
        return False

def kill_process_tree(process):
    try:
        parent = psutil.Process(process.pid)
        children = parent.children(recursive=True)
        for child in children:
            child.kill()
        parent.kill()
    except Exception as e:
        logger.error(f"فشل في قتل العملية: {e}")
def kill_process_by_script_path(script_path):
    """قتل جميع العمليات المرتبطة بمسار script معين"""
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info['cmdline']
                if cmdline and len(cmdline) > 1:
                    if script_path in cmdline[1]:
                        proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    except Exception as e:
        logger.error(f"فشل في قتل العمليات لـ {script_path}: {e}")
@bot.message_handler(commands=['delete_user_file'])
def delete_user_file(message):
    if message.from_user.id == ADMIN_ID:
        try:
            user_id = int(message.text.split()[1])
            file_name = message.text.split()[2]
            
            if user_id in user_files and file_name in user_files[user_id]:
                file_path = os.path.join(uploaded_files_dir, file_name)
                if os.path.exists(file_path):
                    os.remove(file_path)
                    user_files[user_id].remove(file_name)
                    remove_user_file_db(user_id, file_name)
                    bot.send_message(message.chat.id, f"✅ تم حذف الملف {file_name} للمستخدم {user_id}.")
                else:
                    bot.send_message(message.chat.id, f"⚠️ الملف {file_name} غير موجود.")
            else:
                bot.send_message(message.chat.id, f"⚠️ المستخدم {user_id} لم يرفع الملف {file_name}.")
        except Exception as e:
            logger.error(f"فشل في حذف ملف المستخدم: {e}")
            bot.send_message(message.chat.id, f"❌ حدث خطأ: {e}")
    else:
        bot.send_message(message.chat.id, "⚠️ أنت لست المطور.")

@bot.message_handler(commands=['stop_user_bot'])
def stop_user_bot(message):
    if message.from_user.id == ADMIN_ID:
        try:
            user_id = int(message.text.split()[1])
            file_name = message.text.split()[2]
            
            if user_id in user_files and file_name in user_files[user_id]:
                for chat_id, script_info in bot_scripts.items():
                    if script_info.get('folder_path', '').endswith(file_name.split('.')[0]):
                        kill_process_tree(script_info['process'])
                        bot.send_message(chat_id, f"🔴 تم إيقاف تشغيل البوت {file_name}.")
                        bot.send_message(message.chat.id, f"✅ تم إيقاف تشغيل البوت {file_name} للمستخدم {user_id}.")
                        break
                else:
                    bot.send_message(message.chat.id, f"⚠️ البوت {file_name} غير قيد التشغيل.")
            else:
                bot.send_message(message.chat.id, f"⚠️ المستخدم {user_id} لم يرفع الملف {file_name}.")
        except Exception as e:
            logger.error(f"فشل في إيقاف بوت المستخدم: {e}")
            bot.send_message(message.chat.id, f"❌ حدث خطأ: {e}")
    else:
        bot.send_message(message.chat.id, "⚠️ أنت لست المطور.")
@bot.message_handler(commands=['host_status'])
def host_status(message):
    """فحص حالة استضافة Wesbsite - للادمن فقط"""
    user_id = message.from_user.id
    
    # التحقق من أن المستخدم هو الأدمن
    if user_id != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ هذا الأمر للمطور فقط")
        return
        
    try:
        # فحص الذاكرة
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        cpu = psutil.cpu_percent(interval=1)
        
        # الحصول على عدد العمليات النشطة
        active_bots = len([proc for proc in psutil.process_iter() if 'python' in proc.name()])
        
        status_msg = "🔧 **حالة الاستضافة (للمطور فقط):**\n\n"
        status_msg += f"🧠 **الذاكرة:** {memory.percent}% ({memory.used//1024//1024}MB / {memory.total//1024//1024}MB)\n"
        status_msg += f"💾 **التخزين:** {disk.percent}% ({disk.used//1024//1024}MB / {disk.total//1024//1024}MB)\n"
        status_msg += f"⚡ **المعالج:** {cpu}% مستخدم\n"
        status_msg += f"🤖 **البوتات النشطة:** {active_bots}\n"
        status_msg += f"👥 **المستخدمين النشطين:** {len(active_users)}\n\n"
        
        # تحذيرات مفصلة
        warnings = []
        if memory.percent > 90:
            warnings.append("🔴 **الذاكرة خطيرة** - قد يتوقف الخادم")
        elif memory.percent > 80:
            warnings.append("🟡 **الذاكرة مرتفعة** - تجنب تثبيت مكتبات جديدة")
            
        if disk.percent > 95:
            warnings.append("🔴 **التخزين خطير** - مساحة منخفضة جداً")
        elif disk.percent > 85:
            warnings.append("🟡 **التخزين مرتفع** - مساحة محدودة")
            
        if cpu > 95:
            warnings.append("🔴 **المعالج خطير** - حمل مرتفع جداً")
        elif cpu > 80:
            warnings.append("🟡 **المعالج مرتفع** - حمل عالي")
            
        if warnings:
            status_msg += "⚠️ **التنبيهات:**\n" + "\n".join(warnings) + "\n\n"
        else:
            status_msg += "✅ **الحالة مستقرة**\n\n"
            
        status_msg += "🛠 **أوامر الصيانة:**\n"
        status_msg += "/clean_memory - تنظيف الذاكرة\n"
        status_msg += "/restart_bot - إعادة تشغيل البوت\n"
        status_msg += "/bot_stats - إحصائيات البوت"
        
        bot.send_message(message.chat.id, status_msg)
        
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطأ في فحص الحالة: {str(e)}")

@bot.message_handler(commands=['bot_stats'])
def bot_stats(message):
    """إحصائيات البوت - للادمن فقط"""
    user_id = message.from_user.id
    
    if user_id != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ هذا الأمر للمطور فقط")
        return
        
    try:
        total_files = sum(len(files) for files in user_files.values())
        active_bots = len(bot_scripts)
        pending_requests = len(pending_approvals)
        
        stats_msg = "📊 **إحصائيات البوت (للمطور فقط):**\n\n"
        stats_msg += f"👥 **المستخدمين:** {len(user_files)}\n"
        stats_msg += f"📁 **الملفات:** {total_files}\n"
        stats_msg += f"🤖 **البوتات النشطة:** {active_bots}\n"
        stats_msg += f"⏳ **الطلبات المعلقة:** {pending_requests}\n"
        stats_msg += f"🔨 **المحظورين:** {len(banned_users)}\n"
        stats_msg += f"🆓 **الوضع الحر:** {'مفعل' if free_mode else 'معطل'}\n"
        stats_msg += f"🔒 **قفل البوت:** {'مقفل' if bot_locked else 'مفتوح'}\n\n"
        
        # البوتات النشطة حالياً
        if bot_scripts:
            stats_msg += "🔍 **البوتات النشطة:**\n"
            for user_id, bot_info in list(bot_scripts.items())[:5]:  # أول 5 فقط
                stats_msg += f"• {bot_info.get('file_name', 'غير معروف')} (للمستخدم {user_id})\n"
            if len(bot_scripts) > 5:
                stats_msg += f"• ... و {len(bot_scripts) - 5} بوت آخر\n"
        
        bot.send_message(message.chat.id, stats_msg)
        
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطأ في جلب الإحصائيات: {str(e)}")
@bot.message_handler(commands=['active_bots'])
def show_active_bots(message):
    """عرض البوتات النشطة مع مجلداتها"""
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ هذا الأمر للمطور فقط")
        return
        
    try:
        if not bot_scripts:
            bot.send_message(message.chat.id, "📭 لا توجد بوتات نشطة حالياً")
            return
            
        bots_list = "🤖 **البوتات النشطة:**\n\n"
        
        for chat_id, bot_info in bot_scripts.items():
            status = bot_info.get('status', 'unknown')
            folder_name = bot_info.get('bot_folder_name', 'غير معروف')
            file_name = bot_info.get('file_name', 'غير معروف')
            start_time = bot_info.get('start_time', 'غير معروف')
            
            bots_list += f"📁 **المجلد:** {folder_name}\n"
            bots_list += f"📄 **الملف:** {file_name}\n"
            bots_list += f"👤 **المستخدم:** {chat_id}\n"
            bots_list += f"🟢 **الحالة:** {status}\n"
            bots_list += f"⏰ **بدء التشغيل:** {start_time}\n"
            bots_list += "─" * 30 + "\n"
        
        bot.send_message(message.chat.id, bots_list)
        
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ خطأ في عرض البوتات: {str(e)}")
@bot.message_handler(commands=['clean_memory'])
def clean_memory(message):
    """تنظيف الذاكرة - للادمن فقط"""
    user_id = message.from_user.id
    
    if user_id != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ هذا الأمر للمطور فقط")
        return
        
    try:
        import gc
        memory_before = psutil.virtual_memory().percent
        
        # تنظيف الذاكرة
        gc.collect()
        
        # تنظيف الذاكرة المؤقتة
        if 'pending_approvals' in globals():
            pending_approvals.clear()
            
        memory_after = psutil.virtual_memory().percent
        
        bot.send_message(message.chat.id, 
                        f"🧹 **تم تنظيف الذاكرة:**\n"
                        f"قبل: {memory_before}%\n"
                        f"بعد: {memory_after}%\n"
                        f"التحسن: {memory_before - memory_after:.1f}%")
                        
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ فشل في تنظيف الذاكرة: {str(e)}")

@bot.message_handler(commands=['restart_bot'])
def restart_bot_command(message):
    """إعادة تشغيل البوت - للادمن فقط"""
    user_id = message.from_user.id
    
    if user_id != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ هذا الأمر للمطور فقط")
        return
        
    try:
        bot.send_message(message.chat.id, "🔄 جاري إعادة تشغيل البوت...")
        
        # تنظيف قبل إعادة التشغيل
        import gc
        gc.collect()
        
        # إعادة التشغيل
        python = sys.executable
        os.execl(python, python, *sys.argv)
        
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ فشل في إعادة التشغيل: {str(e)}")
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    chat_id = call.message.chat.id
    
    if 'stop_' in call.data:
        # إيقاف البوت
        _, target_chat_id, file_name = call.data.split('_', 2)
        target_chat_id = int(target_chat_id)
        
        if stop_bot_completely(target_chat_id):
            # ✅ تحديث الرسالة للأدمن
            admin_markup = create_admin_control_markup(target_chat_id, file_name, 'stopped')
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"⏹️ البوت {file_name} متوقف الآن\nاستخدم الأزرار أدناه للتحكم 👇",
                reply_markup=admin_markup
            )
            
            # ✅ إرسال تحديث للمستخدم
            user_markup = create_user_control_markup(target_chat_id, file_name, 'stopped')
            try:
                bot.send_message(target_chat_id, f"⏹️ البوت {file_name} متوقف الآن\nاستخدم الأزرار أدناه للتحكم 👇", reply_markup=user_markup)
            except:
                pass
                
        else:
            bot.answer_callback_query(call.id, "⚠️ لا يمكن إيقاف البوت")
            
    elif 'start_' in call.data:
        # تشغيل البوت
        _, target_chat_id, file_name = call.data.split('_', 2)
        target_chat_id = int(target_chat_id)
        
        if restart_bot(target_chat_id):
            # ✅ تحديث الرسالة للأدمن
            admin_markup = create_admin_control_markup(target_chat_id, file_name, 'running')
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"🤖 البوت {file_name} يعمل الآن\nاستخدم الأزرار أدناه للتحكم 👇",
                reply_markup=admin_markup
            )
            
            # ✅ إرسال تحديث للمستخدم
            user_markup = create_user_control_markup(target_chat_id, file_name, 'running')
            try:
                bot.send_message(target_chat_id, f"🤖 البوت {file_name} يعمل الآن\nاستخدم الأزرار أدناه للتحكم 👇", reply_markup=user_markup)
            except:
                pass
                
        else:
            bot.answer_callback_query(call.id, "⚠️ لا يمكن تشغيل البوت")
            
    elif 'delete_' in call.data:
        # حذف البوت
        _, target_chat_id, file_name = call.data.split('_', 2)
        target_chat_id = int(target_chat_id)
        
        if delete_uploaded_file(target_chat_id):
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"🗑️ تم حذف البوت {file_name} تماماً",
                reply_markup=None
            )
            
            try:
                bot.send_message(target_chat_id, f"🗑️ تم حذف البوت {file_name} تماماً")
            except:
                pass
# تشغيل البوتات الموجود مسبقاً عند بدء التشغيل
if __name__ == "__main__":
    # انتظر قليلاً حتى يتم تهيئة البوت بالكامل
    time.sleep(2)
    
    # تشغيل البوتات المخزنة
    start_existing_bots()
    
    # تشغيل البوت الرئيسي
    logger.info('بدء تشغيل البوت الرئيسي بنجاح')
    print('✅ تم تشغيل البوت الرئيسي')
    
    # بدء الاستطلاع
    bot.infinity_polling()