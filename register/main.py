import sqlite3
import io
from datetime import datetime
from telegram import (
    InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
)
from telegram.ext import (
    Updater, CommandHandler, MessageHandler, filters,
    CallbackQueryHandler, ConversationHandler, CallbackContext, Filters
)
from openpyxl import Workbook

(
    ASK_JSHSHR, SHOW_INFO,
    ADMIN_PANEL,
    A_ADD_ISM, A_ADD_FAMILYA, A_ADD_BIRTH, A_ADD_JSHSHR, A_ADD_PHONE,
    A_ADD_ADDRESS, A_ADD_SENT_FROM, A_ADD_SENT_TO, A_ADD_DISEASE,
    A_ADD_QUEUE_NUM, A_ADD_STATUS,
    ADMIN_ACTION, ADMIN_FIND_JSHSHR, ADMIN_EDIT_FIELD, ADMIN_EDIT_VALUE
) = range(18)

ADMIN_PASSWORD = "123"
ADMIN_ID = None
DB_NAME = "users.db"
admin_temp = {}
edit_temp = {}

STATUS_OPTIONS = [
    "Proyekt", "PreiAstanovlen", "Analurivan", "Zavershen",
    "Vvedeno oshibko", "Neizvesno", "Nerasmotreno",
    "Patverjdion", "Neispolzivitsa", "Aktivna"
]


def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ism TEXT,
                familya TEXT,
                birth_date TEXT,
                jshshr TEXT UNIQUE,
                phone TEXT,
                address TEXT,
                sent_from TEXT,
                sent_to TEXT,
                disease TEXT,
                queue_num INTEGER,
                status TEXT,
                created_at TEXT
            )
    """)
    conn.commit()
    conn.close()


def add_user_to_db(data: dict):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        INSERT INTO users (
            ism, familya, birth_date, jshshr, phone,
            address, sent_from, sent_to, disease, queue_num,
            status, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get('ism'), data.get('familya'), data.get('birth_date'),
        data.get('jshshr'), data.get('phone'),
        data.get('address'), data.get('sent_from'), data.get('sent_to'),
        data.get('disease'), data.get('queue_num'),
        data.get('status'), datetime.utcnow().isoformat()
    ))
    conn.commit()
    conn.close()


def find_by_jshshr(jshshr):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE jshshr=?", (jshshr,))
    row = c.fetchone()
    conn.close()
    return row


def get_all_users():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM users")
    rows = c.fetchall()
    conn.close()
    return rows


def update_user_field_by_jshshr(jshshr, field, value):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    allowed = {"ism", "familya", "birth_date", "phone", "address", "sent_from", "sent_to", "disease", "queue_num",
               "status"}
    if field not in allowed:
        conn.close()
        return False
    c.execute(f"UPDATE users SET {field}=? WHERE jshshr=?", (value, jshshr))
    conn.commit()
    conn.close()
    return True


def start(update: Update, context: CallbackContext):
    update.message.reply_text("Assalomu alaykum! Iltimos JSHSHR raqamingizni kiriting (masalan: 12345678901234):")
    return ASK_JSHSHR


def ask_jshshr(update: Update, context: CallbackContext):
    jsh = update.message.text.strip()
    user = find_by_jshshr(jsh)
    if user:
        (
            _id, ism, familya, birth_date, jshshr, phone,
            address, sent_from, sent_to, disease, queue_num, status, created_at
        ) = user
        text = (
            f"📋 Ma'lumotlaringiz:\n"
            f"Ism: {ism}\nFamilya: {familya}\nTug'ilgan sana: {birth_date}\nJSHSHR: {jshshr}\n"
            f"Telefon: {phone}\nManzil: {address}\nQayerdan jo‘natildi: {sent_from}\n"
            f"Qayerga jo‘natildi: {sent_to}\nKasallik: {disease}\nNavbat raqami: {queue_num}\n\n<b>Status: {status}</b>"
        )
        update.message.reply_text(text, parse_mode='HTML')
    else:
        update.message.reply_text("❌ Ushbu JSHSHR bo‘yicha ma'lumot topilmadi.", parse_mode='HTML')
    return ConversationHandler.END,


def admin_login(update: Update, context: CallbackContext):
    global ADMIN_ID
    msg = update.message.text.split(maxsplit=1)
    if len(msg) == 2 and msg[1] == ADMIN_PASSWORD:
        ADMIN_ID = update.message.from_user.id
        return show_admin_panel(update, context)
    else:
        update.message.reply_text("❌ Parol noto'g'ri.")
        return ConversationHandler.END


def show_admin_panel(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("➕ Yangi user qo'shish", callback_data='admin_add_user')],
        [InlineKeyboardButton("🔍 JSHSHR bo'yicha qidirish", callback_data='admin_find')],
        [InlineKeyboardButton("📥 Barcha userlarni .xlsx ga eksport qilish", callback_data='admin_export')],
    ]
    if update.callback_query:
        update.callback_query.answer()
        update.callback_query.edit_message_text("Admin panel:", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        update.message.reply_text("Admin panel:", reply_markup=InlineKeyboardMarkup(keyboard))
    return ADMIN_PANEL


def admin_panel_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    data = query.data

    if data == 'admin_add_user' or data == 'add_again':
        admin_temp.clear()
        query.edit_message_text("Foydalanuvchi ismini kiriting:")
        return A_ADD_ISM

    elif data == 'admin_find':
        query.edit_message_text("Qidirilayotgan foydalanuvchi JSHSHR raqamini kiriting:")
        return ADMIN_FIND_JSHSHR

    elif data == 'admin_export':
        query.edit_message_text("Eksport qilinmoqda...")
        return export_users_xlsx(update, context)

    elif data == 'admin_home':
        return show_admin_panel(update, context)


def a_add_ism(update: Update, context: CallbackContext):
    admin_temp['ism'] = update.message.text.strip()
    update.message.reply_text("Familyasini kiriting:")
    return A_ADD_FAMILYA


def a_add_familya(update: Update, context: CallbackContext):
    admin_temp['familya'] = update.message.text.strip()
    update.message.reply_text("Tug'ilgan sana va yilni kiriting (misol: 04.07.2006):")
    return A_ADD_BIRTH


def a_add_birth(update: Update, context: CallbackContext):
    val = update.message.text.strip()
    try:
        datetime.strptime(val, "%d.%m.%Y")
        admin_temp['birth_date'] = val
        update.message.reply_text("JSHSHR raqamini kiriting:")
        return A_ADD_JSHSHR
    except Exception:
        update.message.reply_text("Format noto'g'ri. Iltimos misol: 04.07.2006 tarzida kiriting:")
        return A_ADD_BIRTH


def a_add_jshshr(update: Update, context: CallbackContext):
    val = update.message.text.strip()
    if not val.isdigit():
        update.message.reply_text("JSHSHR faqat raqamlardan iborat bo'lishi kerak. Qayta kiriting:")
        return A_ADD_JSHSHR
    admin_temp['jshshr'] = val
    update.message.reply_text("Telefon raqamini kiriting (masalan: +998901234567 yoki 998901234567):")
    return A_ADD_PHONE


def a_add_phone(update: Update, context: CallbackContext):
    val = update.message.text.strip()
    if not (val.startswith("+998") or val.startswith("998")):
        update.message.reply_text("Telefon +998 yoki 998 bilan boshlanishi kerak. Qayta kiriting:")
        return A_ADD_PHONE
    admin_temp['phone'] = val
    update.message.reply_text("Yashash manzilini kiriting:")
    return A_ADD_ADDRESS


def a_add_address(update: Update, context: CallbackContext):
    admin_temp['address'] = update.message.text.strip()
    update.message.reply_text("Qayerdan jo'natildi (misol: Buxoro viloyati, bolalar shifoxonasi):")
    return A_ADD_SENT_FROM


def a_add_sent_from(update: Update, context: CallbackContext):
    admin_temp['sent_from'] = update.message.text.strip()
    update.message.reply_text("Qayerga jo'nalidi (misol: Toshkent shahar, bolalar tibbiyot markazi):")
    return A_ADD_SENT_TO


def a_add_sent_to(update: Update, context: CallbackContext):
    admin_temp['sent_to'] = update.message.text.strip()
    update.message.reply_text("Qanday kasallik bilan (qisqacha):")
    return A_ADD_DISEASE


def a_add_disease(update: Update, context: CallbackContext):
    admin_temp['disease'] = update.message.text.strip()
    update.message.reply_text("Navbat raqamini kiriting (raqam):")
    return A_ADD_QUEUE_NUM


def a_add_queue_num(update: Update, context: CallbackContext):
    val = update.message.text.strip()
    try:
        admin_temp['queue_num'] = int(val)
    except ValueError:
        update.message.reply_text("Iltimos butun son kiriting (masalan: 5).")
        return A_ADD_QUEUE_NUM

    kb = [[InlineKeyboardButton(s, callback_data=f"status|{s}")] for s in STATUS_OPTIONS]
    update.message.reply_text("Statusni tanlang:", reply_markup=InlineKeyboardMarkup(kb))
    return A_ADD_STATUS


def a_add_status_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    data = query.data

    if data.startswith("status|"):
        status = data.split("|", 1)[1]
        admin_temp['status'] = status

        try:
            add_user_to_db(admin_temp.copy())

            keyboard = [
                [InlineKeyboardButton("➕ Yana user qo‘shish", callback_data='add_again')],
                [InlineKeyboardButton("🏠 Asosiy sahifaga qaytish", callback_data='admin_home')]
            ]

            query.edit_message_text(
                f"✅ Yangi foydalanuvchi muvaffaqiyatli qo‘shildi!\n\n"
                f"📌 JSHSHR: {admin_temp.get('jshshr')}\n"
                f"📌 Ism: {admin_temp.get('ism')} {admin_temp.get('familya')}\n"
                f"📌 Status: {admin_temp.get('status')}\n\n"
                f"Quyidagi amallardan birini tanlang:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        except sqlite3.IntegrityError:
            query.edit_message_text("❌ Xatolik: Ushbu JSHSHR allaqachon mavjud.")

        admin_temp.clear()
        return ADMIN_PANEL

    return ConversationHandler.END


def admin_find_jshshr(update: Update, context: CallbackContext):
    jsh = update.message.text.strip()
    user = find_by_jshshr(jsh)
    if user:
        (
            _id, ism, familya, birth_date, jshshr, phone,
            address, sent_from, sent_to, disease, queue_num, status, created_at
        ) = user
        text = (
            f"📄 Foydalanuvchi:\nIsm: {ism}\nFamilya: {familya}\nTug'ilgan sana: {birth_date}\nJSHSHR: {jshshr}\n"
            f"Telefon: {phone}\nManzil: {address}\nQayerdan: {sent_from}\nQayerga: {sent_to}\nKasallik: {disease}\n"
            f"Navbat: {queue_num}\nStatus: {status}"
        )
        kb = [
            [InlineKeyboardButton("✏️ Ism", callback_data='edit|ism'),
             InlineKeyboardButton("✏️ Familya", callback_data='edit|familya')],
            [InlineKeyboardButton("✏️ Telefon", callback_data='edit|phone'),
             InlineKeyboardButton("✏️ Manzil", callback_data='edit|address')],
            [InlineKeyboardButton("✏️ Kasallik", callback_data='edit|disease'),
             InlineKeyboardButton("✏️ Status", callback_data='edit|status')],
        ]
        update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb))
        edit_temp['jshshr'] = jsh
        return ADMIN_EDIT_FIELD
    else:
        update.message.reply_text("❌ Foydalanuvchi topilmadi.")
        return ConversationHandler.END


def admin_edit_field_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    data = query.data
    if data.startswith('edit|'):
        field = data.split("|", 1)[1]
        edit_temp['field'] = field
        if field == 'status':
            kb = [[InlineKeyboardButton(s, callback_data=f"setstatus|{s}")] for s in STATUS_OPTIONS]
            query.edit_message_text("Yangi statusni tanlang:", reply_markup=InlineKeyboardMarkup(kb))
            return ADMIN_EDIT_VALUE
        else:
            query.edit_message_text(f"Yangi qiymatni kiriting ({field}):", reply_markup=ReplyKeyboardRemove())
            return ADMIN_EDIT_VALUE
    else:
        query.edit_message_text("Noma'lum amal.")
        return ConversationHandler.END


def admin_set_status_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    data = query.data
    if data.startswith("setstatus|"):
        status = data.split("|", 1)[1]
        success = update_user_field_by_jshshr(edit_temp.get('jshshr'), 'status', status)
        if success:
            query.edit_message_text("✅ Status yangilandi.")
        else:
            query.edit_message_text("❌ Yangilashda xatolik yuz berdi.")
        edit_temp.clear()
    return ConversationHandler.END


def admin_edit_value(update: Update, context: CallbackContext):
    value = update.message.text.strip()
    jsh = edit_temp.get('jshshr')
    field = edit_temp.get('field')
    if not (jsh and field):
        update.message.reply_text("Xatolik. Iltimos qayta urinib ko'ring.")
        return ConversationHandler.END
    if field == 'queue_num':
        try:
            value = int(value)
        except ValueError:
            update.message.reply_text("Iltimos raqam kiriting.")
            return ADMIN_EDIT_VALUE
    success = update_user_field_by_jshshr(jsh, field, value)
    if success:
        update.message.reply_text("✅ Ma'lumot yangilandi.")
    else:
        update.message.reply_text("❌ Yangilashda xatolik yuz berdi.")
    edit_temp.clear()
    return ConversationHandler.END


def export_users_xlsx(update: Update, context: CallbackContext):
    if update.callback_query:
        chat = update.callback_query.message.chat_id
    else:
        chat = update.message.chat_id

    rows = get_all_users()
    wb = Workbook()
    ws = wb.active
    ws.title = "Users"

    headers = ["id", "ism", "familya", "birth_date", "jshshr", "phone", "address", "sent_from", "sent_to", "disease",
               "queue_num", "status", "created_at"]
    ws.append(headers)
    for r in rows:
        ws.append(r)

    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)
    context.bot.send_document(chat_id=chat, document=bio, filename="users.xlsx")
    if update.callback_query:
        update.callback_query.edit_message_text("✅ Eksport yakunlandi. Fayl yuborildi.")
    else:
        update.message.reply_text("✅ Eksport yakunlandi. Fayl yuborildi.")
    return ConversationHandler.END


def main():
    init_db()
    updater = Updater("YOUR_BOT_TOKEN_IS_THERE", use_context=True)
    dp = updater.dispatcher

    start_conv = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={

            ASK_JSHSHR: [MessageHandler(Filters.text & ~Filters.command, ask_jshshr)]
        },
        fallbacks=[]
    )

    admin_conv = ConversationHandler(
        entry_points=[CommandHandler('admin', admin_login)],
        states={
            ADMIN_PANEL: [CallbackQueryHandler(admin_panel_callback)],

            A_ADD_ISM: [MessageHandler(Filters.text & ~Filters.command, a_add_ism)],
            A_ADD_FAMILYA: [MessageHandler(Filters.text & ~Filters.command, a_add_familya)],
            A_ADD_BIRTH: [MessageHandler(Filters.text & ~Filters.command, a_add_birth)],
            A_ADD_JSHSHR: [MessageHandler(Filters.text & ~Filters.command, a_add_jshshr)],
            A_ADD_PHONE: [MessageHandler(Filters.text & ~Filters.command, a_add_phone)],
            A_ADD_ADDRESS: [MessageHandler(Filters.text & ~Filters.command, a_add_address)],
            A_ADD_SENT_FROM: [MessageHandler(Filters.text & ~Filters.command, a_add_sent_from)],
            A_ADD_SENT_TO: [MessageHandler(Filters.text & ~Filters.command, a_add_sent_to)],
            A_ADD_DISEASE: [MessageHandler(Filters.text & ~Filters.command, a_add_disease)],
            A_ADD_QUEUE_NUM: [MessageHandler(Filters.text & ~Filters.command, a_add_queue_num)],
            A_ADD_STATUS: [CallbackQueryHandler(a_add_status_callback, pattern=r'^status\|')],

            ADMIN_FIND_JSHSHR: [MessageHandler(Filters.text & ~Filters.command, admin_find_jshshr)],
            ADMIN_EDIT_VALUE: [
                MessageHandler(Filters.text & ~Filters.command, admin_edit_value),
                CallbackQueryHandler(admin_set_status_callback, pattern=r'^setstatus\|')
            ],
        },
        fallbacks=[]
    )

    dp.add_handler(start_conv)
    dp.add_handler(admin_conv)

    dp.add_handler(CommandHandler('export_xlsx', export_users_xlsx))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
