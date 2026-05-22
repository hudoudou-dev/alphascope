"""
AlphaScope 数据提供者测试脚本

用于快速测试数据下载和验证功能
"""

from datetime import datetime, timedelta
from pathlib import Path

from src.data.providers.akshare_provider import AKShareProvider
from src.data.providers.baostock_provider import BaoStockProvider
from src.data.schema import DataValidator


def test_akshare_provider():
    print("\n" + "="*60)
    print("测试 AKShare Provider")
    print("="*60)
    
    provider = AKShareProvider(storage_path="./test_data")
    
    test_code = "600000.SH"
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    print(f"\n下载股票数据: {test_code}")
    print(f"时间范围: {start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}")
    
    try:
        df = provider.download_and_save(test_code, start_date, end_date, adjust="qfq")
        
        if not df.empty:
            print(f"\n✅ 成功下载 {len(df)} 条数据")
            print(f"\n数据预览:")
            print(df.head(10))
            print(f"\n数据统计:")
            print(f"  - 日期范围: {df['date'].min()} 至 {df['date'].max()}")
            print(f"  - 价格范围: {df['close_price'].min():.2f} 至 {df['close_price'].max():.2f}")
            print(f"  - 平均成交量: {df['volume'].mean():.0f}")
        else:
            print("⚠️ 未获取到数据")
            
    except Exception as e:
        print(f"❌ 下载失败: {e}")
    
    print("\n" + "-"*60)


def test_baostock_provider():
    print("\n" + "="*60)
    print("测试 BaoStock Provider")
    print("="*60)
    
    with BaoStockProvider(storage_path="./test_data") as provider:
        test_code = "000001.SZ"
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        print(f"\n下载股票数据: {test_code}")
        print(f"时间范围: {start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}")
        
        try:
            df = provider.download_and_save(test_code, start_date, end_date, adjust="qfq")
            
            if not df.empty:
                print(f"\n✅ 成功下载 {len(df)} 条数据")
                print(f"\n数据预览:")
                print(df.head(10))
            else:
                print("⚠️ 未获取到数据")
                
        except Exception as e:
            print(f"❌ 下载失败: {e}")
    
    print("\n" + "-"*60)


def test_data_validation():
    print("\n" + "="*60)
    print("测试数据验证")
    print("="*60)
    
    import pandas as pd
    
    validator = DataValidator()
    
    print("\n1. 测试有效数据")
    valid_data = pd.DataFrame({
        "date": [datetime(2024, 1, 1), datetime(2024, 1, 2)],
        "open_price": [10.0, 10.1],
        "high_price": [10.5, 10.6],
        "low_price": [9.5, 9.6],
        "close_price": [10.2, 10.3],
        "volume": [1000000.0, 1100000.0],
        "amount": [10000000.0, 11000000.0],
        "code": ["600000.SH", "600000.SH"],
    })
    
    try:
        validated = validator.validate(valid_data)
        print("✅ 数据验证通过")
    except Exception as e:
        print(f"❌ 验证失败: {e}")
    
    print("\n2. 测试无效数据（负价格）")
    invalid_data = valid_data.copy()
    invalid_data.loc[0, "open_price"] = -10.0
    
    try:
        validator.validate(invalid_data)
        print("❌ 应该失败但通过了")
    except ValueError as e:
        print(f"✅ 正确捕获错误: {e}")
    
    print("\n3. 测试无效数据（未来日期）")
    future_data = valid_data.copy()
    future_data.loc[0, "date"] = datetime.now() + timedelta(days=10)
    
    try:
        validator.validate(future_data)
        print("❌ 应该失败但通过了")
    except ValueError as e:
        print(f"✅ 正确捕获错误: {e}")
    
    print("\n" + "-"*60)


def test_stock_list():
    print("\n" + "="*60)
    print("测试获取股票列表")
    print("="*60)
    
    provider = AKShareProvider(storage_path="./test_data")
    
    try:
        print("\n正在获取股票列表...")
        stock_list = provider.get_stock_list()
        
        print(f"\n✅ 成功获取 {len(stock_list)} 只股票")
        print(f"\n前 10 只股票:")
        for i, code in enumerate(stock_list[:10], 1):
            print(f"  {i}. {code}")
            
    except Exception as e:
        print(f"❌ 获取失败: {e}")
    
    print("\n" + "-"*60)


def test_incremental_update():
    print("\n" + "="*60)
    print("测试增量更新")
    print("="*60)
    
    provider = AKShareProvider(storage_path="./test_data")
    
    test_code = "600000.SH"
    end_date = datetime.now()
    start_date = end_date - timedelta(days=60)
    
    print(f"\n首次下载: {test_code}")
    print(f"时间范围: {start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}")
    
    try:
        df1 = provider.download_and_save(test_code, start_date, end_date)
        print(f"✅ 首次下载 {len(df1)} 条数据")
        
        print(f"\n执行增量更新...")
        df2 = provider.incremental_update(test_code, end_date)
        print(f"✅ 增量更新后共 {len(df2)} 条数据")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
    
    print("\n" + "-"*60)


def test_parquet_storage():
    print("\n" + "="*60)
    print("测试 Parquet 存储")
    print("="*60)
    
    import pyarrow.parquet as pq
    
    test_dir = Path("./test_data")
    parquet_files = list(test_dir.glob("*.parquet"))
    
    if parquet_files:
        print(f"\n找到 {len(parquet_files)} 个 Parquet 文件:")
        for file in parquet_files:
            print(f"  - {file.name}")
            
            table = pq.read_table(file)
            df = table.to_pandas()
            
            print(f"    行数: {len(df)}")
            print(f"    列数: {len(df.columns)}")
            print(f"    大小: {file.stat().st_size / 1024:.2f} KB")
    else:
        print("\n⚠️ 未找到 Parquet 文件，请先运行数据下载测试")
    
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
    print("AlphaScope 数据提供者测试")
    print("🚀 "*20)
    
    tests = [
        ("数据验证测试", test_data_validation),
        ("AKShare 数据下载测试", test_akshare_provider),
        ("BaoStock 数据下载测试", test_baostock_provider),
        ("股票列表获取测试", test_stock_list),
        ("增量更新测试", test_incremental_update),
        ("Parquet 存储测试", test_parquet_storage),
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
