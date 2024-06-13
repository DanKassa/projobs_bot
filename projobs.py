import csv
import logging
import os
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler, ConversationHandler

# Token for accessing the Telegram Bot API
TOKEN = "7344637429:AAGMMZ_rIraxp7wWwP6FPnbMreM0Okqdt_E"

# Conversation states
CV, COVER_LETTER, PORTFOLIO = range(3)

# Dictionary to store user applications
user_data = {}

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Directory to store CVs
CV_DIR = "cvs"
os.makedirs(CV_DIR, exist_ok=True)

# Directory to store exported CSV
EXPORT_DIR = "exports"
os.makedirs(EXPORT_DIR, exist_ok=True)

# Database setup
def init_db():
    conn = sqlite3.connect('applicants.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS applicants (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            cv TEXT,
            cover_letter TEXT,
            portfolio TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_applicant(user_id, cv, cover_letter, portfolio):
    conn = sqlite3.connect('applicants.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO applicants (user_id, cv, cover_letter, portfolio)
        VALUES (?, ?, ?, ?)
    ''', (user_id, cv, cover_letter, portfolio))
    conn.commit()
    conn.close()

def fetch_applicants():
    conn = sqlite3.connect('applicants.db')
    c = conn.cursor()
    c.execute('SELECT * FROM applicants')
    applicants = c.fetchall()
    conn.close()
    return applicants

# Bot commands
async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text("Welcome to the Job Application Bot! Type /apply to start applying for jobs.")

async def apply(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text("Please upload your CV.")
    return CV

async def cv_handler(update: Update, context: CallbackContext) -> int:
    user_id = update.message.from_user.id
    file = await context.bot.get_file(update.message.document.file_id)
    file_path = os.path.join(CV_DIR, f'cv_{user_id}.pdf')
    await file.download_to_drive(file_path)
    user_data[user_id] = {'cv': file_path}
    await update.message.reply_text("CV uploaded successfully. Please type your cover letter.")
    return COVER_LETTER

async def cover_letter_handler(update: Update, context: CallbackContext) -> int:
    user_id = update.message.from_user.id
    cover_letter = update.message.text
    user_data[user_id]['cover_letter'] = cover_letter
    await update.message.reply_text("Please provide your portfolio link (optional). If you don't have a portfolio, type 'None'.")
    return PORTFOLIO

async def portfolio_handler(update: Update, context: CallbackContext) -> int:
    user_id = update.message.from_user.id
    portfolio_link = update.message.text
    user_data[user_id]['portfolio'] = portfolio_link if portfolio_link.lower() != 'none' else None
    await update.message.reply_text("Thank you for providing your information. Your application has been submitted.")

    # Save application data to the database
    save_applicant(user_id, user_data[user_id]['cv'], user_data[user_id]['cover_letter'], user_data[user_id]['portfolio'])

    return ConversationHandler.END

async def cancel(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text("Application process cancelled.")
    return ConversationHandler.END

async def job_posting(update: Update, context: CallbackContext) -> None:
    job_info = "Job Title: Software Developer\nLocation: Ethiopia\nDescription: We are hiring experienced software developers."
    keyboard = [[InlineKeyboardButton("Apply Now", callback_data='apply_job')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(job_info, reply_markup=reply_markup)

async def apply_job(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Thank you for your interest in the job. Please upload your CV.")
    return CV

async def error_handler(update: Update, context: CallbackContext) -> None:
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

async def export_data(update: Update, context: CallbackContext) -> None:
    # Fetch applicants from the database
    applicants = fetch_applicants()

    # Generate CSV data from applicants
    csv_data = []
    for applicant in applicants:
        csv_data.append([applicant[1], applicant[2], applicant[3], applicant[4]])

    csv_file_path = os.path.join(EXPORT_DIR, 'applicants.csv')

    # Write CSV data to a file
    with open(csv_file_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['User ID', 'CV', 'Cover Letter', 'Portfolio'])
        for data in csv_data:
            writer.writerow(data)

    logger.info(f"CSV file created at: {csv_file_path}")

    await update.message.reply_document(document=open(csv_file_path, 'rb'))

# New Code
def main() -> None:
    # Initialize the database
    init_db()

    # Set up the application
    application = Application.builder().token(TOKEN).build()

    # Conversation handler for job application process
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("apply", apply)],
        states={
            CV: [MessageHandler(filters.Document.ALL, cv_handler)],
            COVER_LETTER: [MessageHandler(filters.TEXT & ~filters.COMMAND, cover_letter_handler)],
            PORTFOLIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, portfolio_handler)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Add handlers for bot commands and messages
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("job_posting", job_posting))
    application.add_handler(CallbackQueryHandler(apply_job, pattern='apply_job'))
    application.add_handler(CommandHandler("export_data", export_data))
    application.add_handler(conv_handler)

    # Add error handler
    application.add_error_handler(error_handler)

    # Start the bot
    application.run_polling()

if __name__ == '__main__':
    main()
