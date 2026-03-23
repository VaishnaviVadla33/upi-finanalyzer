import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def get_savings_suggestions(transactions):
    """Generate AI-powered savings suggestions"""
    try:
        if transactions.empty:
            return []
        
        suggestions = []
        
        # Analyze spending by category
        if 'payee_type' in transactions.columns:
            category_spending = transactions.groupby('payee_type')['amount'].sum().sort_values(ascending=False)
            
            for category, amount in category_spending.head(3).items():
                if amount > 1000:
                    potential_savings = amount * 0.15
                    suggestions.append({
                        'title': f'Optimize {category} Spending',
                        'message': f'You spent ₹{amount:,.0f} on {category}. Consider saving ₹{potential_savings:,.0f} (15%)',
                        'amount': potential_savings,
                        'category': category
                    })
        
        return suggestions[:5]
    except Exception as e:
        return []

def compare_spending(transactions):
    """Compare spending across months and years"""
    try:
        if transactions.empty:
            return {}
        
        # Check if date column exists and has valid data
        if 'date' not in transactions.columns:
            return {}
        
        # Create a copy to avoid modifying original data
        df = transactions.copy()
        
        # Parse dates with proper error handling
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df = df.dropna(subset=['date'])
        
        if df.empty:
            return {}
        
        # Ensure we have amount column
        if 'amount' not in df.columns:
            return {}
        
        # Group by year and month
        df['year'] = df['date'].dt.year
        df['month'] = df['date'].dt.month
        
        monthly_data = df.groupby(['year', 'month'])['amount'].sum().reset_index()
        
        # Format for frontend
        result = {}
        for _, row in monthly_data.iterrows():
            year = str(int(row['year']))
            month = int(row['month'])
            amount = float(row['amount'])
            
            if year not in result:
                result[year] = {}
            result[year][month] = amount
        
        return result
    except Exception as e:
        return {}

def cash_flow_analysis(credit_df, debit_df):
    """Analyze cash inflows and outflows"""
    try:
        inflows = float(credit_df['amount'].sum()) if not credit_df.empty else 0.0
        outflows = float(debit_df['amount'].sum()) if not debit_df.empty else 0.0
        return inflows, outflows
    except Exception as e:
        return 0.0, 0.0

def spending_alerts(transactions):
    """Generate spending alerts and warnings"""
    try:
        if transactions.empty:
            return []
        
        alerts = []
        
        # Check if amount column exists
        if 'amount' not in transactions.columns:
            return []
        
        # High spending alert
        try:
            high_transactions = transactions[transactions['amount'] > 10000]
            for _, transaction in high_transactions.iterrows():
                alerts.append({
                    'title': 'High Spending Alert',
                    'message': f'Large transaction of ₹{transaction["amount"]:,.0f}',
                    'type': 'warning',
                    'amount': float(transaction['amount'])
                })
        except Exception as e:
            pass
        
        # Frequent transactions alert
        if len(transactions) > 20:
            alerts.append({
                'title': 'High Transaction Volume',
                'message': f'You made {len(transactions)} transactions this period',
                'type': 'info'
            })
        
        return alerts[:5]
    except Exception as e:
        return []

def get_top_time_intervals(credit_df, debit_df):
    """Get peak transaction time intervals"""
    try:
        # Combine dataframes safely
        dfs_to_concat = []
        if not credit_df.empty:
            dfs_to_concat.append(credit_df.copy())
        if not debit_df.empty:
            dfs_to_concat.append(debit_df.copy())
        
        if not dfs_to_concat:
            return []
        
        all_transactions = pd.concat(dfs_to_concat, ignore_index=True)
        
        if all_transactions.empty:
            return []
        
        # Check for required columns
        date_column = None
        if 'date' in all_transactions.columns:
            date_column = 'date'
        elif 'created_at' in all_transactions.columns:
            date_column = 'created_at'
        else:
            return []
        
        # Parse datetime with proper error handling
        all_transactions[date_column] = pd.to_datetime(all_transactions[date_column], errors='coerce')
        all_transactions = all_transactions.dropna(subset=[date_column])
        
        if all_transactions.empty:
            return []
        
        # Extract hour from datetime
        all_transactions['hour'] = all_transactions[date_column].dt.hour
        
        # Group by hour and count
        time_counts = all_transactions.groupby('hour').size().reset_index(name='transaction_count')
        
        # Convert to 12-hour format with AM/PM
        def format_12hour(hour):
            if hour == 0:
                return "12 AM - 1 AM"
            elif hour < 12:
                return f"{hour} AM - {hour+1} AM"
            elif hour == 12:
                return "12 PM - 1 PM"
            else:
                return f"{hour-12} PM - {hour-11 if hour < 23 else 12} {'PM' if hour < 23 else 'AM'}"
        
        time_counts['time_interval'] = time_counts['hour'].apply(format_12hour)
        
        # Get top 5 intervals
        result = time_counts.sort_values('transaction_count', ascending=False).head(5)
        
        return [
            {
                'time_interval': row['time_interval'],
                'transaction_count': int(row['transaction_count'])
            }
            for _, row in result.iterrows()
        ]
    except Exception as e:
        return []