# Daily-Tracker

A small project I made to help my friends and I be more productive! We currently keep a spreadsheet where we document the categories where we spend the most time every day, such as sleeping, going to class, doing HW, studying for interviews, etc.

This bot uses the Google Sheets API to manage the spreadsheet automatically, creating a new one at the start of every day. It also reads the sheet for the previous day and generates a graph showing the major categories spent every day. It then sends a personalized email to each person with the graph and an outline of the top time-usage categories.

I'm currently running the bot using a daily Cron job on AWS EC2.


