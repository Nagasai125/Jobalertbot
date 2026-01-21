---
title: Job Alert Bot
emoji: 🚀
colorFrom: blue
colorTo: purple
sdk: docker
pinned: false
---

# Job Alert Bot

A 24/7 job scraping bot that monitors career pages from top tech companies and sends notifications via Telegram and Email.

## Features
- Scrapes jobs from Amazon, Google, Uber, Stripe, Microsoft, Adobe, LiveRamp
- Filters by keywords, experience level, and location
- Sends real-time Telegram and Email notifications
- Daily summary reports

## Setup
Set these secrets in your Space settings:
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `EMAIL_SENDER`
- `EMAIL_PASSWORD`
- `EMAIL_RECIPIENT`
