# Screenshots Guide for README

To complete the README documentation, you need to add screenshots to your repository.

## Required Screenshots

Based on the images you provided, create a `screenshots` folder in your repository root and add the following images:

### 1. Landing Page (landing.png)
- Screenshot of the home page (index.html)
- Shows the hero section with "Track your UPI spending effortlessly"
- Includes the navigation bar and call-to-action buttons
- Displays the dashboard preview mockup

### 2. Dashboard (dashboard.png)
- Screenshot of the main dashboard page
- Shows total balance, income, and expenses cards
- Displays monthly savings goal progress
- Shows spending alerts section
- Includes recent transactions list

### 3. OCR Scan (ocr-scan.png)
- Screenshot of the upload page (upload.html)
- Shows the upload zone with drag-and-drop area
- Displays the transaction details form on the right
- Shows the disclaimer warning message
- Includes the "Bulk Upload" button

### 4. Analytics (analytics.png)
- Screenshot of the analytics page
- Shows savings opportunities section
- Displays important alerts
- Shows transaction history chart
- Includes monthly spending by year graph

## How to Add Screenshots

### Option 1: Using GitHub Web Interface

1. Go to your repository on GitHub
2. Click "Add file" > "Create new file"
3. Type `screenshots/landing.png` in the filename field
4. Upload the landing page screenshot
5. Commit the file
6. Repeat for other screenshots

### Option 2: Using Git Command Line

```bash
# Create screenshots folder
mkdir screenshots

# Copy your screenshot files to this folder
# Rename them as: landing.png, dashboard.png, ocr-scan.png, analytics.png

# Add to git
git add screenshots/
git commit -m "Add application screenshots for README"
git push origin main
git push origin deployment
```

## Screenshot Requirements

- Format: PNG (preferred) or JPG
- Resolution: At least 1920x1080 for desktop views
- Quality: High quality, clear text
- Content: Should show the actual application interface
- Privacy: Remove any personal/sensitive information

## Current Screenshot Paths in README

The README references screenshots at:
```
https://raw.githubusercontent.com/VaishnaviVadla33/upi-finanalyzer/main/screenshots/landing.png
https://raw.githubusercontent.com/VaishnaviVadla33/upi-finanalyzer/main/screenshots/dashboard.png
https://raw.githubusercontent.com/VaishnaviVadla33/upi-finanalyzer/main/screenshots/ocr-scan.png
https://raw.githubusercontent.com/VaishnaviVadla33/upi-finanalyzer/main/screenshots/analytics.png
```

Once you add the screenshots to the `screenshots` folder in your repository, they will automatically display in the README.

## Alternative: Use Imgur or Other Image Hosting

If you prefer not to store images in the repository:

1. Upload screenshots to Imgur or another image hosting service
2. Get the direct image URLs
3. Update the README.md file to use those URLs instead

Example:
```markdown
![Landing Page](https://i.imgur.com/your-image-id.png)
```

## Tips for Taking Screenshots

1. **Landing Page**: Open http://localhost:5000/ or https://upi-finanalyzer.onrender.com/
2. **Dashboard**: Login and navigate to /dashboard
3. **OCR Scan**: Navigate to /upload
4. **Analytics**: Navigate to /analytics

Use browser developer tools (F12) to set viewport to 1920x1080 for consistent screenshots.

## Verification

After adding screenshots, verify they display correctly by:
1. Viewing the README on GitHub
2. Checking that all images load properly
3. Ensuring images are clear and readable
