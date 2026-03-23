import sys
import json
import os
import requests

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

    token = os.environ['TELEGRAM_BOT_TOKEN']
    chat_id = os.environ['TELEGRAM_CHAT_ID']

    message = '📢 New jobs found:\n\n'
    for job in new_jobs:
        message += f"*{job['company']}*: {job['title']}\n"
        message += f"  {job['location']}\n"
        message += f"  [Link]({job['link']})\n\n"

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    params = {'chat_id': chat_id, 'text': message, 'parse_mode': 'Markdown'}
    response = requests.post(url, data=params)
    response.raise_for_status()
    print('Telegram message sent.')

if __name__ == '__main__':
    main()