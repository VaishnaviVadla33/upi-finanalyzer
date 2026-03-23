# 📧 Simple Email Setup (2 Steps)

## Step 1: Get Gmail App Password

1. Go to https://myaccount.google.com/apppasswords
2. Click "Generate" 
3. Copy the 16-character password (like: `abcd efgh ijkl mnop`)

## Step 2: Update .env File

Open `.env` and change these 2 lines:

```env
SMTP_USER=your-actual-email@gmail.com
SMTP_PASS=abcd-efgh-ijkl-mnop
```

Replace with YOUR email and the app password from Step 1.

## Done!

Restart the app and email invites will work.

## What Gets Sent

Simple email:
```
Subject: Join "Family Group" - Code: ABC123

Hi!

John invited you to join "Family Group" on FinAnalyzer.

Your invite code: ABC123

Go to the Groups page and enter this code to join.

- FinAnalyzer
```

That's it! No complicated setup needed.
