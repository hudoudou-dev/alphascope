"""
Web应用工具函数模块

本模块提供Web应用所需的工具函数，包括股票代码标准化等。
"""

def normalize_stock_code(code: str) -> str:
    """
    标准化股票代码
    
    Args:
        code: 原始股票代码（6位数字或带后缀的格式）
    
    Returns:
        str: 标准化后的股票代码（XXXXXX.EXCHANGE）
    
    Examples:
        >>> normalize_stock_code("600519")
        "600519.SH"
        >>> normalize_stock_code("000001")
        "000001.SZ"
        >>> normalize_stock_code("300750")
        "300750.SZ"
        >>> normalize_stock_code("688001")
        "688001.SH"
    """
    code = code.upper().strip()
    
    # 如果已经包含交易所后缀，直接返回
    if "." in code:
        return code
    
    # 根据股票代码前缀判断交易所
    # 上海主板：600、601、603、605
    # 上海科创板：688
    # 深圳主板：000、001、002、003
    # 深圳创业板：300
    # 北京交易所：8（暂不支持）
    
    if code.startswith(("600", "601", "603", "605", "688")):
        return f"{code}.SH"
    elif code.startswith(("000", "001", "002", "003", "300")):
        return f"{code}.SZ"
    elif code.startswith("8"):
        # 北京交易所暂不支持，默认返回原代码
        return code
    else:
        # 无法识别的代码，默认返回原代码
        return code