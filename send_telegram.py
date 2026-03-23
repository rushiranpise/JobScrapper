import sys
import json
import os
import requests
from collections import defaultdict

def send_message(chat_id, token, text, parse_mode='Markdown'):
    """Send a Telegram message, optionally with Markdown."""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    params = {'chat_id': chat_id, 'text': text}
    if parse_mode:
        params['parse_mode'] = parse_mode
    response = requests.post(url, data=params)
    response.raise_for_status()

def split_messages(text, max_len=4000):
    """Split text into chunks not exceeding max_len, trying to break at newlines."""
    chunks = []
    while text:
        if len(text) <= max_len:
            chunks.append(text)
            break
        # Try to split at a newline within the limit
        split_pos = text.rfind('\n', 0, max_len)
        if split_pos == -1:
            split_pos = max_len
        chunks.append(text[:split_pos])
        text = text[split_pos:]
    return chunks

def main():
    data = sys.stdin.read()
    
    # Parse new jobs
    jobs_start = data.find('NEW_JOBS_START')
    jobs_end = data.find('NEW_JOBS_END')
    new_jobs = []
    if jobs_start != -1 and jobs_end != -1:
        json_str = data[jobs_start + len('NEW_JOBS_START'):jobs_end].strip()
        if json_str:
            new_jobs = json.loads(json_str)
    
    # Parse errors
    errors_start = data.find('ERRORS_START')
    errors_end = data.find('ERRORS_END')
    errors = []
    if errors_start != -1 and errors_end != -1:
        error_text = data[errors_start + len('ERRORS_START'):errors_end].strip()
        if error_text:
            errors = error_text.split('\n')
    
    token = os.environ['TELEGRAM_BOT_TOKEN']
    chat_id = os.environ['TELEGRAM_CHAT_ID']
    
    # Send new jobs message if any
    if new_jobs:
        grouped = defaultdict(list)
        for job in new_jobs:
            grouped[job['company']].append(job)
        
        messages = []
        current_message = "📢 **New Jobs Found!**\n\n"
        max_length = 4000
        
        for i, (company, jobs) in enumerate(grouped.items()):
            company_header = f"🏢 *{company}* ({len(jobs)})\n"
            if len(current_message + company_header) > max_length:
                messages.append(current_message)
                current_message = "📢 **New Jobs Found!** (continued)\n\n" + company_header
            else:
                current_message += company_header
            
            for job in jobs:
                job_line = f"  • *{job['title']}*\n"
                location_line = f"    📍 {job['location']}\n"
                link_line = f"    🔗 [Apply]({job['link']})\n\n"
                candidate = job_line + location_line + link_line
                if len(current_message + candidate) > max_length:
                    messages.append(current_message)
                    current_message = "📢 **New Jobs Found!** (continued)\n\n" + company_header + candidate
                else:
                    current_message += candidate
            
            if i != len(grouped) - 1:
                current_message += "─" * 20 + "\n\n"
        
        if current_message:
            messages.append(current_message)
        
        for msg in messages:
            send_message(chat_id, token, msg)
    
    # Send errors message if any
    if errors:
        error_header = "⚠️ Scraping Errors ⚠️\n\n"
        error_text = error_header
        for err in errors:
            error_text += f"{err}\n"
        # Split into multiple plain text messages
        chunks = split_messages(error_text)
        for chunk in chunks:
            send_message(chat_id, token, chunk, parse_mode=None)  # plain text
    
    print("Messages sent.")

if __name__ == '__main__':
    main()