# Daily-Tracker

A small email bot I made to help my friends and I be more productive! The bot helps visualize daily-time-spent-doing-something data for me and my friends using a spreadsheet where we document the categories where we spend the most time every day, such as doing HW, working on extracurriculars, building personal projects, etc.

This bot uses the Google Sheets API to manage the spreadsheet automatically, creating a new one at the start of every day. It also uses the API to read the sheet for the previous day and uses Matplotlib generate a graph showing the major categories spent every day. It then sends a personalized email to each person with the graph and an outline of the top time-usage categories.

I'm currently running the bot using a daily Cron job on AWS EC2.

TL;DR technologies used:
- Google Sheets API (sheets processing)
- MatplotLib (graphing)
- SMTPLib (emailing)
- AWS EC2 (hosting)


