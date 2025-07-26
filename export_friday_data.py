#!/usr/bin/env python3
"""
Export Friday Analysis Data to CSV
Exports all data from friday_stocks_analysis table in sandbox_recommendations.db to CSV files
"""

import sqlite3
import pandas as pd
import os
from datetime import datetime

def export_friday_data():
    """Export friday_stocks_analysis data to CSV files"""
    
    db_path = "sandbox_recommendations.db"
    
    # Check if database exists
    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        return
    
    print("📊 EXPORTING FRIDAY ANALYSIS DATA TO CSV")
    print("=" * 60)
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        
        # Get all data from friday_stocks_analysis table
        query = """
        SELECT * FROM friday_stocks_analysis 
        ORDER BY friday_date DESC, total_score DESC
        """
        
        print("🔍 Reading data from friday_stocks_analysis table...")
        df = pd.read_sql_query(query, conn)
        
        if df.empty:
            print("📭 No data found in friday_stocks_analysis table")
            conn.close()
            return
        
        print(f"✅ Found {len(df)} records")
        
        # Get unique Friday dates
        unique_dates = df['friday_date'].unique()
        print(f"📅 Found data for {len(unique_dates)} Friday dates:")
        for date in sorted(unique_dates):
            count = len(df[df['friday_date'] == date])
            print(f"   • {date}: {count} stocks")
        
        # Create output directory
        output_dir = "csv_exports"
        os.makedirs(output_dir, exist_ok=True)
        
        # Export all data to one comprehensive CSV
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        all_data_file = f"{output_dir}/friday_analysis_all_data_{timestamp}.csv"
        
        print(f"\n💾 Exporting all data to: {all_data_file}")
        df.to_csv(all_data_file, index=False)
        print(f"✅ Exported {len(df)} records to {all_data_file}")
        
        # Export separate CSV for each Friday date
        print(f"\n📂 Exporting individual Friday files...")
        for date in sorted(unique_dates):
            date_df = df[df['friday_date'] == date].copy()
            date_file = f"{output_dir}/friday_analysis_{date}_{timestamp}.csv"
            date_df.to_csv(date_file, index=False)
            print(f"   ✅ {date}: {len(date_df)} records → {date_file}")
        
        # Export summary statistics
        summary_file = f"{output_dir}/friday_analysis_summary_{timestamp}.csv"
        print(f"\n📊 Creating summary statistics: {summary_file}")
        
        summary_data = []
        for date in sorted(unique_dates):
            date_df = df[df['friday_date'] == date]
            
            summary_data.append({
                'friday_date': date,
                'total_stocks': len(date_df),
                'strong_stocks_67': len(date_df[date_df['total_score'] >= 67]),
                'strong_stocks_75': len(date_df[date_df['total_score'] >= 75]),
                'avg_score': date_df['total_score'].mean(),
                'max_score': date_df['total_score'].max(),
                'min_score': date_df['total_score'].min(),
                'avg_price': date_df['friday_price'].mean(),
                'top_stock': date_df.loc[date_df['total_score'].idxmax(), 'symbol'],
                'top_score': date_df['total_score'].max()
            })
        
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_csv(summary_file, index=False)
        print(f"✅ Summary exported to {summary_file}")
        
        # Show sample data
        print(f"\n📋 SAMPLE DATA (Top 10 records):")
        print("=" * 100)
        sample_columns = ['symbol', 'friday_date', 'total_score', 'recommendation', 'friday_price', 'sector']
        print(df[sample_columns].head(10).to_string(index=False))
        
        # Show column information
        print(f"\n📊 AVAILABLE COLUMNS ({len(df.columns)} total):")
        print("=" * 60)
        for i, col in enumerate(df.columns, 1):
            print(f"{i:2d}. {col}")
        
        conn.close()
        
        print(f"\n✅ EXPORT COMPLETED!")
        print(f"📁 All files saved in: {output_dir}/")
        print(f"📊 Total records exported: {len(df)}")
        print(f"📅 Date range: {min(unique_dates)} to {max(unique_dates)}")
        
    except Exception as e:
        print(f"❌ Error exporting data: {str(e)}")
        if 'conn' in locals():
            conn.close()

def export_specific_date(target_date):
    """Export data for a specific Friday date"""
    
    db_path = "sandbox_recommendations.db"
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        return
    
    print(f"📊 EXPORTING DATA FOR {target_date}")
    print("=" * 50)
    
    try:
        conn = sqlite3.connect(db_path)
        
        query = """
        SELECT * FROM friday_stocks_analysis 
        WHERE friday_date = ?
        ORDER BY total_score DESC
        """
        
        df = pd.read_sql_query(query, conn, params=(target_date,))
        
        if df.empty:
            print(f"📭 No data found for {target_date}")
            conn.close()
            return
        
        # Create output directory
        output_dir = "csv_exports"
        os.makedirs(output_dir, exist_ok=True)
        
        # Export to CSV
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{output_dir}/friday_analysis_{target_date}_{timestamp}.csv"
        
        df.to_csv(filename, index=False)
        
        print(f"✅ Exported {len(df)} records for {target_date}")
        print(f"📁 File saved: {filename}")
        
        # Show top 10 stocks
        print(f"\n🏆 TOP 10 STOCKS FOR {target_date}:")
        print("-" * 80)
        top_10 = df[['symbol', 'total_score', 'recommendation', 'friday_price', 'sector']].head(10)
        print(top_10.to_string(index=False))
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error exporting data for {target_date}: {str(e)}")
        if 'conn' in locals():
            conn.close()

def main():
    """Main function with menu options"""
    
    print("📊 FRIDAY DATA EXPORT UTILITY")
    print("=" * 40)
    print("1. Export all Friday data")
    print("2. Export specific Friday date")
    print("3. Show available dates")
    print("4. Exit")
    
    choice = input("\nSelect option (1/2/3/4): ").strip()
    
    if choice == '1':
        export_friday_data()
        
    elif choice == '2':
        target_date = input("Enter Friday date (YYYY-MM-DD): ").strip()
        if target_date:
            export_specific_date(target_date)
        else:
            print("❌ Invalid date")
            
    elif choice == '3':
        # Show available dates
        db_path = "sandbox_recommendations.db"
        if os.path.exists(db_path):
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT DISTINCT friday_date FROM friday_stocks_analysis ORDER BY friday_date DESC")
                dates = cursor.fetchall()
                
                if dates:
                    print(f"\n📅 AVAILABLE FRIDAY DATES ({len(dates)} total):")
                    print("-" * 30)
                    for i, (date,) in enumerate(dates, 1):
                        cursor.execute("SELECT COUNT(*) FROM friday_stocks_analysis WHERE friday_date = ?", (date,))
                        count = cursor.fetchone()[0]
                        print(f"{i:2d}. {date} ({count} stocks)")
                else:
                    print("📭 No Friday data found")
                    
                conn.close()
            except Exception as e:
                print(f"❌ Error reading dates: {str(e)}")
        else:
            print(f"❌ Database not found: {db_path}")
            
    elif choice == '4':
        print("👋 Goodbye!")
        
    else:
        print("❌ Invalid choice")

if __name__ == "__main__":
    main() 