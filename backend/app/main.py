"""拼音输入法后端服务 - 命令行接口"""
import json
import sys
from typing import Optional
from .pinyin_engine import get_engine


def print_json(data: dict):
    """输出 JSON 格式数据"""
    print(json.dumps(data, ensure_ascii=False, indent=2))


def handle_query(pinyin: str, limit: int = 10):
    """处理拼音查询"""
    engine = get_engine()
    candidates = engine.get_candidates(pinyin, limit)
    return {
        "pinyin": pinyin,
        "candidates": candidates,
        "count": len(candidates)
    }


def handle_search(query: str):
    """搜索匹配的拼音"""
    engine = get_engine()
    pinyins = engine.search_pinyin(query)
    return {
        "query": query,
        "pinyins": pinyins,
        "count": len(pinyins)
    }


def handle_convert(pinyin_str: str, limit: int = 5):
    """转换拼音句子"""
    engine = get_engine()
    pinyin_list = pinyin_str.split()
    result = engine.convert_sentence(pinyin_list, limit)
    return {
        "input": pinyin_str,
        "result": result
    }


def handle_list():
    """列出所有支持的拼音"""
    engine = get_engine()
    pinyins = engine.get_all_pinyins()
    return {
        "pinyins": pinyins,
        "count": len(pinyins)
    }


def interactive_mode():
    """交互模式"""
    print("拼音输入法引擎 - 交互模式")
    print("输入拼音获取候选字，输入 'quit' 或 'exit' 退出")
    print("-" * 40)
    
    engine = get_engine()
    
    while True:
        try:
            pinyin = input("拼音> ").strip()
            if pinyin.lower() in ('quit', 'exit', 'q'):
                print("再见！")
                break
            if not pinyin:
                continue
            
            candidates = engine.get_candidates(pinyin)
            if candidates:
                print(f"候选: {' '.join(candidates)}")
            else:
                print("未找到匹配的汉字")
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")
            break


def main():
    """主函数"""
    if len(sys.argv) < 2:
        interactive_mode()
        return
    
    command = sys.argv[1].lower()
    
    if command == "query" and len(sys.argv) >= 3:
        pinyin = sys.argv[2]
        limit = int(sys.argv[3]) if len(sys.argv) > 3 else 10
        print_json(handle_query(pinyin, limit))
    
    elif command == "search" and len(sys.argv) >= 3:
        query = sys.argv[2]
        print_json(handle_search(query))
    
    elif command == "convert" and len(sys.argv) >= 3:
        pinyin_str = " ".join(sys.argv[2:])
        print_json(handle_convert(pinyin_str))
    
    elif command == "list":
        print_json(handle_list())
    
    elif command in ("help", "-h", "--help"):
        print_help()
    
    else:
        print_help()
        sys.exit(1)


def print_help():
    """打印帮助信息"""
    help_text = """
拼音输入法引擎

用法:
    python -m app                    交互模式
    python -m app query <拼音> [数量]  查询拼音对应的汉字
    python -m app search <前缀>       搜索匹配的拼音
    python -m app convert <拼音...>   转换拼音句子
    python -m app list               列出所有支持的拼音
    python -m app help               显示帮助信息

示例:
    python -m app query ni
    python -m app query zhong 5
    python -m app search zh
    python -m app convert ni hao shi jie
    python -m app list
"""
    print(help_text)


if __name__ == "__main__":
    main()
