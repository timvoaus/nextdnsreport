import asyncio
from nextdnsapi.api import *
from telegram import Bot
from telegram.constants import ParseMode
import os
import urllib.request
import urllib.error
import json
import datetime
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

# Function to get Cloudflare queries for today
def get_cloudflare_queries(cf_account_id, cf_api_token):
    try:
        now = datetime.datetime.now(datetime.timezone.utc)
        start_time = now.replace(hour=0, minute=0, second=0, microsecond=0).strftime('%Y-%m-%dT%H:%M:%S.000Z')
        end_time = now.strftime('%Y-%m-%dT%H:%M:%S.000Z')

        query = """
        query GetAnalytics($accountTag: String, $datetimeStart: String, $datetimeEnd: String) {
          viewer {
            accounts(filter: { accountTag: $accountTag }) {
              workersInvocationsAdaptive(limit: 10000, filter: {
                datetime_geq: $datetimeStart,
                datetime_leq: $datetimeEnd
              }) {
                sum {
                  requests
                }
              }
              pagesFunctionsInvocationsAdaptiveGroups(limit: 10000, filter: {
                datetime_geq: $datetimeStart,
                datetime_leq: $datetimeEnd
              }) {
                sum {
                  requests
                }
              }
            }
          }
        }
        """

        variables = {
            "accountTag": cf_account_id,
            "datetimeStart": start_time,
            "datetimeEnd": end_time
        }

        data = json.dumps({"query": query, "variables": variables}).encode("utf-8")
        req = urllib.request.Request("https://api.cloudflare.com/client/v4/graphql", data=data)
        req.add_header("Authorization", f"Bearer {cf_api_token}")
        req.add_header("Content-Type", "application/json")
        req.add_header("Accept", "application/json")

        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode())
            
            if "errors" in result and result["errors"]:
                return f"Error: {result['errors'][0].get('message', 'Unknown GraphQL error')}"
                
            accounts = result.get("data", {}).get("viewer", {}).get("accounts", [])
            if not accounts:
                return "Error: No accounts found or access denied"
                
            account_data = accounts[0]
            workers_data = account_data.get("workersInvocationsAdaptive", [])
            pages_data = account_data.get("pagesFunctionsInvocationsAdaptiveGroups", [])
            
            total_requests = 0
            for group in workers_data:
                total_requests += group.get("sum", {}).get("requests", 0)
            for group in pages_data:
                total_requests += group.get("sum", {}).get("requests", 0)
                
            return str(total_requests)
    except Exception as e:
        return f"Exception: {str(e)}"

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
    cf_api_token = os.getenv('CF_API_TOKEN')
    cf_account_id = os.getenv('CF_ACCOUNT_ID')
    
    if cf_api_token and cf_account_id:
        cf_queries = get_cloudflare_queries(cf_account_id, cf_api_token)
        current_date = datetime.datetime.now(datetime.timezone.utc).strftime('%d-%m-%y')
        messages.insert(0, f"<b>Total Cloudflare Workers/Pages Queries today {current_date}:</b>\n<b>{cf_queries}</b>")
    elif cf_api_token or cf_account_id:
        messages.insert(0, "<b>Cloudflare Error:</b> Both CF_API_TOKEN and CF_ACCOUNT_ID must be set.")

    final_message = "\n\n".join(messages)
    await send_telegram_message(final_message)

# Run the async process
if __name__ == "__main__":
    asyncio.run(process_credentials())
