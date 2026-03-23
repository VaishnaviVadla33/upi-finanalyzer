# 📧 Email Setup Guide for Group Invitations

## Current Status
✅ Email sending functionality is now implemented!
⚠️ You need to configure SMTP settings in `.env` file

## Setup Instructions

### Option 1: Gmail (Recommended)

1. **Enable 2-Factor Authentication**
   - Go to https://myaccount.google.com/security
   - Enable 2-Step Verification

2. **Generate App Password**
   - Go to https://myaccount.google.com/apppasswords
   - Select "Mail" and "Windows Computer" (or Other)
   - Click "Generate"
   - Copy the 16-character password

3. **Update `.env` file**
   ```env
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=your-actual-email@gmail.com
   SMTP_PASS=your-16-char-app-password
   APP_URL=http://localhost:5000
   ```

### Option 2: Outlook/Hotmail

```env
SMTP_HOST=smtp-mail.outlook.com
SMTP_PORT=587
SMTP_USER=your-email@outlook.com
SMTP_PASS=your-password
APP_URL=http://localhost:5000
```

### Option 3: Yahoo Mail

```env
SMTP_HOST=smtp.mail.yahoo.com
SMTP_PORT=587
SMTP_USER=your-email@yahoo.com
SMTP_PASS=your-app-password
APP_URL=http://localhost:5000
```

### Option 4: Custom SMTP Server

```env
SMTP_HOST=your-smtp-server.com
SMTP_PORT=587
SMTP_USER=your-email@domain.com
SMTP_PASS=your-password
APP_URL=http://localhost:5000
```

## Email Features

### What Gets Sent
- ✅ Beautiful HTML email with branding
- ✅ Plain text fallback
- ✅ Invite code prominently displayed
- ✅ Direct join link
- ✅ Step-by-step instructions
- ✅ Sender information

### Email Template Preview
```
Subject: You're invited to join 'Family Group' on FinAnalyzer

🎉 You're Invited!

[Inviter Name] has invited you to join the group "Family Group" on FinAnalyzer.

Your Invite Code: ABC123

[Join Group Now Button]

To join:
1. Visit FinAnalyzer Groups
2. Click "Join Group"
3. Enter the invite code above
```

## Fallback Behavior

If email is not configured or fails:
- ❌ Email won't be sent
- ✅ User gets error message with invite code
- ✅ Can manually share the invite code
- ✅ Copy invite code/link buttons still work

## Testing

1. Update `.env` with your SMTP credentials
2. Restart the Flask app
3. Go to Groups page
4. Open a group
5. Click "Invite" tab
6. Enter an email and click "Send"
7. Check the recipient's inbox

## Troubleshooting

### "Email authentication failed"
- Check SMTP_USER and SMTP_PASS are correct
- For Gmail, make sure you're using App Password, not regular password
- Verify 2FA is enabled on Gmail

### "Email not configured"
- Make sure SMTP_USER is not "your-email@gmail.com"
- Make sure SMTP_PASS is not "your-app-password"
- Update `.env` with real credentials

### Email not received
- Check spam/junk folder
- Verify recipient email is correct
- Check SMTP server allows sending
- Some email providers have daily limits

### Connection timeout
- Check SMTP_HOST and SMTP_PORT
- Verify firewall isn't blocking port 587
- Try port 465 with SSL (requires code change)

## Security Notes

⚠️ **Never commit `.env` file to Git!**
- `.env` is in `.gitignore` by default
- App passwords are sensitive credentials
- Use environment variables in production

## Production Deployment

For production, use environment variables instead of `.env`:
```bash
export SMTP_HOST=smtp.gmail.com
export SMTP_PORT=587
export SMTP_USER=your-email@gmail.com
export SMTP_PASS=your-app-password
export APP_URL=https://your-domain.com
```

Or use a dedicated email service:
- SendGrid
- Mailgun
- Amazon SES
- Postmark

## Current Configuration

Your `.env` file currently has:
```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com  ← UPDATE THIS
SMTP_PASS=your-app-password     ← UPDATE THIS
APP_URL=http://localhost:5000
```

**Action Required**: Update SMTP_USER and SMTP_PASS with your actual credentials!
