# JobScrapper

job_scapper.py contains script that checks for new job openings from the list of companies mentioned in companies.csv (uploaded to Google Drive)
For personalisation purpose, updates the job title keywords mentioned as 'KEYWORDS'. 'NO_KEYWORDS' contains keywords that you don't want.

output_old.csv file contains the old job postings and get's updated everytime the script is ran. 
You will find the new jobs in output.csv. Also, for 1st run, you might get old positions too, but from 2nd run you will only get latest postings in output.csv

Companies list is being fetched from Google drive - https://drive.google.com/file/d/1oPIqvsKTcXw7zS2gtlrSsFl3bmjbxg17/view?usp=sharing
Please add more comapnies with their urls to it or correct any wrong ones in the list. 
