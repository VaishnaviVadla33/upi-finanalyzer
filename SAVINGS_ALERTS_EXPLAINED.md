# 💰 Savings & Alerts System - Complete Explanation

## 📊 SAVINGS GOAL SYSTEM

### What is it?
A monthly savings target that tracks how much money you're saving from your income.

### How it works:

#### Step 1: Check if you have income
```
IF user has NO income (credits) this month:
    → Show: "Add income transactions to track savings"
    → Why: Can't calculate savings without income
ELSE:
    → Continue to Step 2
```

#### Step 2: Check if goal is set
```
IF user has NOT set a savings goal:
    → Show: "Set a monthly savings goal" button
ELSE:
    → Continue to Step 3 (Calculate savings)
```

#### Step 3: Calculate savings
```
Formula: Savings = Total Income - Total Expenses

Example:
- Income this month: ₹80,000
- Expenses this month: ₹45,000
- Savings: ₹80,000 - ₹45,000 = ₹35,000
```

#### Step 4: Compare with target
```
IF Savings >= Target:
    → Status: "Achieved" 🎉
    → Color: Green
    → Message: "Goal achieved!"
    
ELSE IF Savings < 0 (Expenses > Income):
    → Status: "Negative" ⚠️
    → Color: Red
    → Message: "Expenses exceed income"
    
ELSE (0 < Savings < Target):
    → Status: "In Progress" 📊
    → Color: Blue
    → Message: "₹X remaining"
    → Calculate: Remaining = Target - Savings
```

#### Step 5: Calculate percentage
```
Percentage = (Current Savings / Target) × 100

Example:
- Target: ₹50,000
- Current: ₹35,000
- Percentage: (35,000 / 50,000) × 100 = 70%
```

### Visual Display:
```
┌─────────────────────────────────────┐
│ Monthly Savings Goal          [⚙️]  │
├─────────────────────────────────────┤
│ Target: ₹50,000   Current: ₹35,000 │
│ [████████████░░░░░░] 70%           │
│ 📊 ₹15,000 remaining                │
│ Income: ₹80,000 • Expenses: ₹45,000│
│                    [📧 Email Report]│
└─────────────────────────────────────┘
```

---

## 🔔 SPENDING ALERTS SYSTEM

### What is it?
Warnings when your spending exceeds a limit you set for a specific period and/or category.

### How it works:

#### Step 1: User creates an alert
```
User sets:
- Name: "Monthly Budget"
- Limit: ₹30,000
- Period: Monthly
- Category: All Categories (or specific like "Food")
```

#### Step 2: System calculates spending for that period

**Daily Alert:**
```
Period: Today (00:00:00 to now)
Spending = Sum of all expenses today

Example:
- Breakfast: ₹200
- Lunch: ₹350
- Shopping: ₹1,500
- Total: ₹2,050
```

**Weekly Alert:**
```
Period: Monday to Sunday (current week)
Spending = Sum of all expenses from Monday 00:00:00 to now

Example (Today is Wednesday):
- Monday: ₹2,000
- Tuesday: ₹3,500
- Wednesday: ₹1,800
- Total: ₹7,300
```

**Monthly Alert:**
```
Period: 1st to last day of month
Spending = Sum of all expenses from 1st 00:00:00 to now

Example (Today is 15th):
- Days 1-15: ₹45,000
- Total: ₹45,000
```

**Yearly Alert:**
```
Period: January 1st to December 31st
Spending = Sum of all expenses from Jan 1 00:00:00 to now

Example (Today is March 15th):
- January: ₹50,000
- February: ₹48,000
- March (1-15): ₹25,000
- Total: ₹123,000
```

#### Step 3: Check if limit exceeded
```
IF Spending >= Limit:
    → Alert is TRIGGERED
    → Show in "Spending Alerts" widget
    → Calculate how much exceeded
    
ELSE:
    → Alert is NOT triggered
    → Don't show (no warning needed)
```

#### Step 4: Calculate percentage
```
Percentage = (Current Spending / Limit) × 100

Example:
- Limit: ₹30,000
- Current: ₹45,000
- Percentage: (45,000 / 30,000) × 100 = 150%
- Exceeded by: ₹45,000 - ₹30,000 = ₹15,000
```

### Category-Specific Alerts:
```
IF Category = "Food":
    → Only count expenses with payee_type = "Food"
    
Example:
- Food expenses: ₹8,000
- Transport expenses: ₹5,000
- Shopping: ₹10,000
- Alert checks only: ₹8,000 (Food)

IF Category = "All":
    → Count ALL expenses regardless of category
    → Total: ₹8,000 + ₹5,000 + ₹10,000 = ₹23,000
```

### Visual Display:
```
┌─────────────────────────────────────┐
│ Spending Alerts              [+]    │
├─────────────────────────────────────┤
│ ┌─────────────────────────────────┐ │
│ │ Monthly Budget                  │ │
│ │ monthly                         │ │
│ │ ₹45,000 of ₹30,000             │ │
│ │ [████████████████] 150%        │ │
│ └─────────────────────────────────┘ │
└─────────────────────────────────────┘
```

---

## 📧 EMAIL NOTIFICATIONS

### Savings Report Email
**When**: Click "Email Report" button
**To**: Your registered email
**Subject**: "💰 Your Monthly Savings Report - March 2026"

**Content:**
```
Hi there!

Here's your monthly savings report:

📊 Savings Status: In Progress

📊 Summary:
• Income: ₹80,000
• Expenses: ₹45,000
• Savings: ₹35,000
• Target: ₹50,000
• Progress: 70.0%

💪 Keep going! You need ₹15,000 more to reach your goal.

Keep tracking your finances with FinAnalyzer!

- FinAnalyzer Team
```

### Alert Email
**When**: Click email button on alert (or automatic in future)
**To**: Your registered email
**Subject**: "⚠️ Spending Alert: Monthly Budget"

**Content:**
```
Hi there!

⚠️ Your spending alert has been triggered!

Alert: Monthly Budget
Period: Monthly
Category: All Categories

💰 Spending Details:
• Limit: ₹30,000
• Current: ₹45,000
• Exceeded by: ₹15,000
• Percentage: 150.0%

💡 Suggestion: Review your all categories spending and consider adjusting your budget.

Stay on track with FinAnalyzer!

- FinAnalyzer Team
```

---

## 🔄 COMPLETE FLOW EXAMPLE

### Scenario: User wants to save ₹50,000 per month

**Day 1 (March 1st):**
1. User uploads salary transaction: +₹80,000 (Credit)
2. System detects income → Enables savings tracking
3. User clicks "Set Goal" → Enters ₹50,000
4. Widget shows: "₹0 expenses, ₹80,000 saved (160%)" 🎉

**Day 10 (March 10th):**
1. User has spent ₹20,000 on various things
2. Savings = ₹80,000 - ₹20,000 = ₹60,000
3. Widget shows: "Goal achieved! ₹60,000 saved (120%)" 🎉

**Day 20 (March 20th):**
1. User has spent ₹45,000 total
2. Savings = ₹80,000 - ₹45,000 = ₹35,000
3. Widget shows: "₹15,000 remaining (70%)" 📊

**Day 25 (March 25th):**
1. User spends another ₹40,000 (total ₹85,000)
2. Savings = ₹80,000 - ₹85,000 = -₹5,000
3. Widget shows: "Expenses exceed income ⚠️" (Red warning)

### Scenario: User sets monthly spending alert for ₹30,000

**Alert Setup:**
- Name: "Monthly Budget"
- Limit: ₹30,000
- Period: Monthly
- Category: All

**Day 15 (March 15th):**
- Spent: ₹25,000
- Alert: NOT triggered (below limit)
- Widget: Shows "No active alerts"

**Day 20 (March 20th):**
- Spent: ₹32,000
- Alert: TRIGGERED! (exceeded ₹30,000)
- Widget: Shows alert with red bar
- User clicks "Email" → Gets alert email

---

## 🎯 KEY DIFFERENCES

### Savings Goal vs Spending Alert

| Feature | Savings Goal | Spending Alert |
|---------|-------------|----------------|
| **Purpose** | Track how much you're saving | Warn when spending too much |
| **Formula** | Income - Expenses | Sum of expenses only |
| **Good when** | Positive (saving money) | Below limit (not triggered) |
| **Bad when** | Negative (overspending) | Above limit (triggered) |
| **Shows** | How much saved vs target | How much spent vs limit |
| **Color** | Green = good, Red = bad | Red = warning (exceeded) |

---

## 🐛 DUPLICATE ALERTS ISSUE

### Why duplicates appear:
You probably created the same alert multiple times (clicked "Add Alert" 3 times with same settings).

### Solution:
Each alert has a unique ID. The system shows ALL alerts that are triggered. If you have 3 alerts with:
- Name: "Monthbudget"
- Limit: ₹1,000, ₹10,000, ₹10,000
- All triggered

Then all 3 will show up.

### How to fix:
Need to add an "Alert Management" page where you can:
- View all your alerts
- Delete duplicate alerts
- Edit existing alerts
- Toggle alerts on/off

---

## 📸 MULTIPLE PHOTO UPLOAD

### Current System:
```
1 Upload → 1 Photo → 1 Transaction
```

### Proposed System:
```
1 Upload → 10 Photos → 10 Transactions
```

### How it would work:
1. User selects multiple photos (up to 10)
2. System processes each photo one by one
3. Shows progress: "Processing 3/10..."
4. Extracts all transactions
5. Shows list of all extracted transactions
6. User reviews and saves all at once

### Benefits:
- ✅ Faster bulk entry
- ✅ Less clicking
- ✅ Better for monthly statement photos

### Optimization:
- Limit to 10 photos (prevents server overload)
- Process sequentially (not all at once)
- Show progress bar
- Allow individual transaction editing before save

**Recommendation**: YES, implement this! Very useful feature.

---

## 📝 SUMMARY

**Savings Goal** = "Am I saving enough money?"
- Needs income to work
- Shows: Income - Expenses vs Target
- 3 states: Achieved, Negative, In Progress

**Spending Alerts** = "Am I spending too much?"
- Works with expenses only
- Shows: Total spending vs Limit
- Only shows when limit exceeded
- Supports: Daily, Weekly, Monthly, Yearly

**Email Notifications** = "Send me reports"
- Savings report: Monthly summary
- Alert email: When limit exceeded
- Manual trigger (click button)

**Duplicates** = You created same alert multiple times
- Need alert management page to delete duplicates
