import asyncio
from nextdnsapi.api import *
from telegram import Bot
from telegram.constants import ParseMode
import os

# Get the credentials from the environment variable
credentials = os.getenv('CREDENTIALS')
if not credentials:
    raise ValueError("CREDENTIALS environment variable is not set")

# Split credentials into lines
lines = credentials.splitlines()

# Ensure lines are stripped of whitespace
lines = [line.strip() for line in lines]

# Telegram bot token and chat ID from environment variables
telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
chat_id = os.getenv('CHAT_ID')

# Initialize the bot
bot = Bot(token=telegram_bot_token)

# Function to send a message to the Telegram bot
async def send_telegram_message(message):
    await bot.send_message(chat_id=chat_id, text=message, parse_mode=ParseMode.HTML)

# Main function to process the credentials and collect messages
async def process_credentials():
    total_queries = 300000
    messages = []
    for i in range(0, len(lines), 3):
        login = lines[i]
        passwrd = lines[i+1]
        config = lines[i+2]

        try:
            header = account.login(login, passwrd)
            month_data = account.month(header)
            monthly_queries = month_data.get('monthlyQueries', 'No data')
            
            if monthly_queries != 'No data':
                # Calculate the percentage of total queries
                percentage_of_total = (monthly_queries / total_queries) * 100
                percentage_of_total_str = f"{percentage_of_total:.2f}%"
            else:
                percentage_of_total_str = 'No data'
                
            # Prepare the message
            message = (
                f"<b>Login:</b> {login}\n"
                f"<b>Monthly Queries:</b> {monthly_queries}\n"
                f"<b>Percentage of Total Queries:</b> {percentage_of_total_str}"
            )
            messages.append(message)
            
        except Exception as e:
            error_message = f"<b>Failed to process credentials for login:</b> {login}\n<b>Error:</b> {str(e)}"
            messages.append(error_message)
    
    # Send all messages concatenated together
    final_message = "\n\n".join(messages)
    await send_telegram_message(final_message)

# Function to run the async process
def run_async_process():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(process_credentials())

# Run the async process
run_async_process()
