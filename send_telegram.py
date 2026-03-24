import sys
import json
import os
import time
import requests
from collections import defaultdict

def send_message(chat_id, token, text, parse_mode='Markdown', retries=10):
    """Send a Telegram message with fallback to plain text."""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    params = {'chat_id': chat_id, 'text': text}
    if parse_mode:
        params['parse_mode'] = parse_mode

    for attempt in range(retries):
        response = requests.post(url, data=params)
        if response.status_code == 200:
            return
        elif response.status_code == 429:
            retry_after = response.json().get('parameters', {}).get('retry_after', 5)
            print(f"429 Too Many Requests – waiting {retry_after} seconds...")
            time.sleep(retry_after + 1)
        else:
            print(f"Failed to send message (attempt {attempt+1}): {response.status_code}")
            print(f"Response: {response.text}")
            if parse_mode:
                print("Retrying without Markdown...")
                params['parse_mode'] = None  # fallback to plain text
                parse_mode = None
            else:
                response.raise_for_status()
    response.raise_for_status()

def split_messages(text, max_len=4000):
    """Split text into chunks not exceeding max_len, trying to break at newlines."""
    chunks = []
    while text:
        if len(text) <= max_len:
            chunks.append(text)
            break
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
    jobs_chat_id = os.environ['TELEGRAM_CHAT_ID']
    errors_chat_id = os.environ.get('TELEGRAM_ERROR_CHAT_ID')
    
    # Send new jobs message if any
    if new_jobs:
        grouped = defaultdict(list)
        for job in new_jobs:
            grouped[job['company']].append(job)
        
        total_jobs = len(new_jobs)
        messages = []
        current_message = f"📢 **{total_jobs} New Jobs Found!** \n\n"
        max_length = 4000
        
        for i, (company, jobs) in enumerate(grouped.items()):
            company_header = f"🏢 *{company}* ({len(jobs)} jobs)\n"
            if len(current_message + company_header) > max_length:
                messages.append(current_message)
                current_message = f"**{total_jobs} New Jobs Found!** (continued)\n\n" + company_header
            else:
                current_message += company_header
            
            for job in jobs:
                job_line = f"  • *{job['title']}*\n"
                location_line = f"    📍 {job['location']}\n"
                link_line = f"    🔗 [Apply]({job['link']})\n\n"
                candidate = job_line + location_line + link_line
                if len(current_message + candidate) > max_length:
                    messages.append(current_message)
                    current_message = f"📢 **New Jobs Found!** (continued)\n\n" + company_header + candidate
                else:
                    current_message += candidate
            
            if i != len(grouped) - 1:
                current_message += "✨🆕 🆕 🆕 ✨\n\n"
        
        if current_message:
            messages.append(current_message)
        
        for msg in messages:
            send_message(jobs_chat_id, token, msg)
            time.sleep(5)  # avoid rate limits
    
    # Send errors message if any, to a separate chat
    if errors and errors_chat_id:
        error_header = "⚠️ Scraping Errors ⚠️\n\n"
        error_text = error_header
        for err in errors:
            error_text += f"{err}\n"
        chunks = split_messages(error_text)
        for chunk in chunks:
            send_message(errors_chat_id, token, chunk, parse_mode=None)
            time.sleep(5)
    elif errors:
        print("Errors found but no separate error chat ID set.")
        for err in errors:
            print(err)
    
    print("Messages sent.")

if __name__ == '__main__':
    main()
