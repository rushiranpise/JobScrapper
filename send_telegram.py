import sys
import json
import os
import requests
from collections import defaultdict

def main():
    data = sys.stdin.read()
    start = data.find('NEW_JOBS_START')
    end = data.find('NEW_JOBS_END')
    if start == -1 or end == -1:
        print('No new jobs output found.')
        return

    json_str = data[start + len('NEW_JOBS_START'):end].strip()
    if not json_str:
        print('No new jobs.')
        return

    new_jobs = json.loads(json_str)
    if not new_jobs:
        print('No new jobs.')
        return

    # Group jobs by company
    grouped = defaultdict(list)
    for job in new_jobs:
        grouped[job['company']].append(job)

    token = os.environ['TELEGRAM_BOT_TOKEN']
    chat_id = os.environ['TELEGRAM_CHAT_ID']

    # Build the message(s)
    messages = []
    current_message = "📢 **New Jobs Found!**\n\n"
    max_length = 4000  # Leave room for safety, Telegram limit is 4096

    for i, (company, jobs) in enumerate(grouped.items()):
        # Company header
        company_header = f"🏢 *{company}* ({len(jobs)})\n"

        # Check if adding header would exceed limit
        if len(current_message + company_header) > max_length:
            messages.append(current_message)
            current_message = "📢 **New Jobs Found!** (continued)\n\n" + company_header
        else:
            current_message += company_header

        for job in jobs:
            # Individual job lines
            job_line = f"  • *{job['title']}*\n"
            location_line = f"    📍 {job['location']}\n"
            link_line = f"    🔗 [Apply]({job['link']})\n\n"
            candidate = job_line + location_line + link_line

            if len(current_message + candidate) > max_length:
                messages.append(current_message)
                current_message = "📢 **New Jobs Found!** (continued)\n\n" + company_header + candidate
            else:
                current_message += candidate

        # Add a separator between companies (except after the last one)
        if i != len(grouped) - 1:
            current_message += "─" * 20 + "\n\n"

    # Append the last message if not empty
    if current_message:
        messages.append(current_message)

    # Send each message
    url_template = "https://api.telegram.org/bot{}/sendMessage"
    for msg in messages:
        params = {
            'chat_id': chat_id,
            'text': msg,
            'parse_mode': 'Markdown'
        }
        response = requests.post(url_template.format(token), data=params)
        response.raise_for_status()

    print(f'Sent {len(messages)} Telegram message(s).')


if __name__ == '__main__':
    main()