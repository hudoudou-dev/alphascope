"""
AlphaScope 交易日历测试脚本

用于快速测试交易日历功能
"""

from datetime import datetime, date
from pathlib import Path

from src.calendar.trading_calendar import TradingCalendarService


def test_download_trading_calendar():
    print("\n" + "="*60)
    print("测试下载交易日历")
    print("="*60)
    
    calendar_service = TradingCalendarService(calendar_path="./test_data/calendar/trading_days.parquet")
    
    start_date = "2024-01-01"
    end_date = datetime.now().strftime("%Y-%m-%d")
    
    print(f"\n下载交易日历: {start_date} 至 {end_date}")
    
    try:
        df = calendar_service.download_trading_days(start_date, end_date, source="akshare")
        
        if not df.empty:
            print(f"\n✅ 成功下载 {len(df)} 个交易日")
            print(f"\n数据预览:")
            print(df.head(10))
            print(f"\n数据统计:")
            print(f"  - 日期范围: {df['date'].min()} 至 {df['date'].max()}")
            print(f"  - 交易日数量: {len(df[df['is_trading_day']])}")
        else:
            print("⚠️ 未获取到数据")
            
    except Exception as e:
        print(f"❌ 下载失败: {e}")
    
    print("\n" + "-"*60)


def test_is_trading_day():
    print("\n" + "="*60)
    print("测试判断交易日")
    print("="*60)
    
    calendar_service = TradingCalendarService(calendar_path="./test_data/calendar/trading_days.parquet")
    
    test_dates = [
        datetime(2024, 1, 2),
        datetime(2024, 1, 6),
        datetime.now(),
    ]
    
    for test_date in test_dates:
        try:
            is_trading = calendar_service.is_trading_day(test_date)
            weekday = test_date.strftime("%A")
            
            print(f"\n{test_date.strftime('%Y-%m-%d')} ({weekday})")
            if is_trading:
                print("  ✅ 是交易日")
            else:
                print("  ❌ 不是交易日")
                
        except Exception as e:
            print(f"\n{test_date.strftime('%Y-%m-%d')}")
            print(f"  ⚠️ 查询失败: {e}")
    
    print("\n" + "-"*60)


def test_previous_next_trading_day():
    print("\n" + "="*60)
    print("测试前后交易日")
    print("="*60)
    
    calendar_service = TradingCalendarService(calendar_path="./test_data/calendar/trading_days.parquet")
    
    test_date = datetime.now()
    
    try:
        prev_day = calendar_service.previous_trading_day(test_date)
        print(f"\n当前日期: {test_date.strftime('%Y-%m-%d')}")
        print(f"前一个交易日: {prev_day.strftime('%Y-%m-%d')}")
        
        next_day = calendar_service.next_trading_day(test_date)
        print(f"下一个交易日: {next_day.strftime('%Y-%m-%d')}")
        
    except Exception as e:
        print(f"❌ 查询失败: {e}")
    
    print("\n" + "-"*60)


def test_market_status():
    print("\n" + "="*60)
    print("测试市场状态")
    print("="*60)
    
    calendar_service = TradingCalendarService(calendar_path="./test_data/calendar/trading_days.parquet")
    
    test_times = [
        datetime.now(),
        datetime.now().replace(hour=10, minute=0),
        datetime.now().replace(hour=14, minute=0),
        datetime.now().replace(hour=20, minute=0),
    ]
    
    for test_time in test_times:
        try:
            is_open = calendar_service.is_market_open(test_time)
            is_closed = calendar_service.is_market_closed(test_time)
            
            print(f"\n时间: {test_time.strftime('%Y-%m-%d %H:%M')}")
            if is_open:
                print("  ✅ 市场开盘")
            else:
                print("  ❌ 市场关闭")
                
        except Exception as e:
            print(f"\n时间: {test_time.strftime('%Y-%m-%d %H:%M')}")
            print(f"  ⚠️ 查询失败: {e}")
    
    print("\n" + "-"*60)


def test_latest_closed_trading_day():
    print("\n" + "="*60)
    print("测试最近收盘交易日")
    print("="*60)
    
    calendar_service = TradingCalendarService(calendar_path="./test_data/calendar/trading_days.parquet")
    
    try:
        latest_closed = calendar_service.latest_closed_trading_day()
        print(f"\n最近收盘的交易日: {latest_closed.strftime('%Y-%m-%d')}")
        
    except Exception as e:
        print(f"❌ 查询失败: {e}")
    
    print("\n" + "-"*60)


def test_get_trading_days_range():
    print("\n" + "="*60)
    print("测试获取交易日区间")
    print("="*60)
    
    calendar_service = TradingCalendarService(calendar_path="./test_data/calendar/trading_days.parquet")
    
    start_date = "2024-01-01"
    end_date = "2024-01-31"
    
    try:
        trading_days = calendar_service.get_trading_days(start_date, end_date)
        count = calendar_service.get_trading_days_count(start_date, end_date)
        
        print(f"\n区间: {start_date} 至 {end_date}")
        print(f"交易日数量: {count}")
        print(f"\n前 10 个交易日:")
        for i, day in enumerate(trading_days[:10], 1):
            print(f"  {i}. {day.strftime('%Y-%m-%d')}")
        
    except Exception as e:
        print(f"❌ 查询失败: {e}")
    
    print("\n" + "-"*60)


def test_incremental_update():
    print("\n" + "="*60)
    print("测试增量更新")
    print("="*60)
    
    calendar_service = TradingCalendarService(calendar_path="./test_data/calendar/trading_days.parquet")
    
    end_date = datetime.now()
    
    try:
        df = calendar_service.update_trading_days(end_date)
        
        if not df.empty:
            print(f"\n✅ 更新成功，共 {len(df)} 个交易日")
            print(f"  - 最新日期: {df['date'].max()}")
        
    except Exception as e:
        print(f"❌ 更新失败: {e}")
    
    print("\n" + "-"*60)


def cleanup_test_data():
    print("\n" + "="*60)
    print("清理测试数据")
    print("="*60)
    
    import shutil
    
    test_dir = Path("./test_data")
    if test_dir.exists():
        shutil.rmtree(test_dir)
        print("✅ 测试数据已清理")
    else:
        print("⚠️ 测试数据目录不存在")
    
    print("\n" + "-"*60)


def main():
    print("\n" + "🚀 "*20)
    print("AlphaScope 交易日历测试")
    print("🚀 "*20)
    
    tests = [
        ("下载交易日历测试", test_download_trading_calendar),
        ("判断交易日测试", test_is_trading_day),
        ("前后交易日测试", test_previous_next_trading_day),
        ("市场状态测试", test_market_status),
        ("最近收盘交易日测试", test_latest_closed_trading_day),
        ("交易日区间测试", test_get_trading_days_range),
        ("增量更新测试", test_incremental_update),
    ]
    
    print("\n可用测试:")
    for i, (name, _) in enumerate(tests, 1):
        print(f"  {i}. {name}")
    print(f"  0. 运行所有测试")
    print(f"  -1. 清理测试数据")
    
    try:
        choice = input("\n请选择测试 (默认运行所有): ").strip()
        
        if choice == "":
            choice = "0"
        
        choice = int(choice)
        
        if choice == -1:
            cleanup_test_data()
        elif choice == 0:
            for name, test_func in tests:
                test_func()
        elif 1 <= choice <= len(tests):
            tests[choice - 1][1]()
        else:
            print("❌ 无效选择")
            
    except ValueError:
        print("❌ 请输入数字")
    except KeyboardInterrupt:
        print("\n\n⚠️ 测试已取消")
    
    print("\n" + "🎉 "*20)
    print("测试完成")
    print("🎉 "*20 + "\n")


if __name__ == "__main__":
    main()