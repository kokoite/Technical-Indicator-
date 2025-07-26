#!/usr/bin/env python3
"""
Test script for StockListManager
"""

from stock_list_manager import StockListManager
import time

def test_stock_list_manager():
    print("🧪 Testing StockListManager...")
    
    # Create instance
    manager = StockListManager()
    
    # Test 1: Get stock list with cache
    print("\n🔍 Test 1: Get stock list (cached)")
    start = time.time()
    stocks = manager.get_stock_list()
    duration = time.time() - start
    print(f"✅ Got {len(stocks)} stocks in {duration:.2f}s")
    print(f"Sample: {stocks[:5]}...")
    
    # Test 2: Force refresh
    print("\n🔄 Test 2: Force refresh stock list")
    start = time.time()
    stocks = manager.get_stock_list(force_refresh=True)
    duration = time.time() - start
    print(f"✅ Refreshed {len(stocks)} stocks in {duration:.2f}s")
    
    # Test 3: Get limited number of stocks
    print("\n🔢 Test 3: Get limited stocks")
    limit = 10
    limited_stocks = manager.get_stock_list()[:limit]
    print(f"✅ Got {len(limited_stocks)} stocks (limited to {limit})")
    print(f"Stocks: {', '.join(limited_stocks)}")
    
    print("\n🎉 All tests completed!")

if __name__ == "__main__":
    test_stock_list_manager()
