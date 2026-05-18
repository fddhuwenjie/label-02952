"""拼音输入法后端服务 - 命令行接口"""
import json
import sys
from typing import Optional

from .config import get_config
from .exceptions import InvalidLimitError, InvalidPinyinError, PinyinError
from .logger import get_logger
from .pinyin_engine import get_engine

logger = get_logger("cli")


def print_json(data: dict):
    """输出 JSON 格式数据"""
    print(json.dumps(data, ensure_ascii=False, indent=2))


def print_error(message: str, detail: str = ""):
    """输出结构化错误信息"""
    err = {"error": message}
    if detail:
        err["detail"] = detail
    print(json.dumps(err, ensure_ascii=False, indent=2), file=sys.stderr)


def handle_query(pinyin: str, limit: int = 10):
    """处理拼音查询（支持连续拼音输入）"""
    engine = get_engine()
    result = engine.get_candidates_continuous(pinyin, limit)

    if len(result["segments"]) > 1:
        return {
            "pinyin": pinyin,
            "segments": result["segments"],
            "candidates": result["candidates"],
            "all_segments": result["all_segments"],
            "phrases": result["phrases"],
            "alternatives": result["alternatives"],
        }

    candidates = result["candidates"][0] if result["candidates"] else []
    return {
        "pinyin": pinyin,
        "candidates": candidates,
        "count": len(candidates),
        "phrases": result["phrases"],
        "alternatives": result["alternatives"],
    }


def handle_search(query: str):
    """搜索匹配的拼音"""
    engine = get_engine()
    pinyins = engine.search_pinyin(query)
    return {"query": query, "pinyins": pinyins, "count": len(pinyins)}


def handle_convert(pinyin_str: str, limit: int = 5):
    """转换拼音句子"""
    engine = get_engine()
    pinyin_list = pinyin_str.split()
    result = engine.convert_sentence(pinyin_list, limit)
    return {"input": pinyin_str, "result": result}


def handle_list():
    """列出所有支持的拼音"""
    engine = get_engine()
    pinyins = engine.get_all_pinyins()
    return {"pinyins": pinyins, "count": len(pinyins)}


def handle_stats():
    """获取引擎统计信息"""
    engine = get_engine()
    return engine.get_stats()


def handle_add_word(pinyin: str, word: str):
    """添加用户词条"""
    engine = get_engine()
    engine.add_user_word(pinyin, word)
    return {"status": "ok", "pinyin": pinyin, "word": word}


def interactive_mode():
    """交互模式"""
    print("拼音输入法引擎 - 交互模式")
    print("输入拼音获取候选字（支持连续输入如 nihao），输入 'quit' 或 'exit' 退出")
    print("-" * 40)

    engine = get_engine()
    logger.info("进入交互模式")

    while True:
        try:
            pinyin = input("拼音> ").strip()
            if pinyin.lower() in ("quit", "exit", "q"):
                print("再见！")
                break
            if not pinyin:
                continue

            if " " in pinyin:
                pinyin_list = pinyin.split()
                result = engine.convert_sentence(pinyin_list)
                for seg, cands in zip(pinyin_list, result):
                    print(f"  {seg}: {' '.join(cands)}")
            else:
                result = engine.get_candidates_continuous(pinyin)
                if len(result["segments"]) > 1:
                    print(f"切分: {' '.join(result['segments'])}")
                    for seg, cands in zip(result["segments"], result["candidates"]):
                        print(f"  {seg}: {' '.join(cands)}")
                elif result["candidates"]:
                    print(f"候选: {' '.join(result['candidates'][0])}")
                else:
                    print("未找到匹配的汉字")
        except PinyinError as e:
            print(f"输入错误: {e}")
            logger.warning("交互模式输入错误: %s", e)
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")
            break

    # 退出时保存用户数据
    engine.save_user_data()
    logger.info("退出交互模式")


def main():
    """主函数"""
    if len(sys.argv) < 2:
        interactive_mode()
        return

    command = sys.argv[1].lower()

    try:
        if command == "query" and len(sys.argv) >= 3:
            pinyin = sys.argv[2]
            limit = get_config().default_candidate_limit
            if len(sys.argv) > 3:
                try:
                    limit = int(sys.argv[3])
                except ValueError:
                    print_error("参数错误", f"'{sys.argv[3]}' 不是有效的数字")
                    sys.exit(1)
            print_json(handle_query(pinyin, limit))

        elif command == "search" and len(sys.argv) >= 3:
            print_json(handle_search(sys.argv[2]))

        elif command == "convert" and len(sys.argv) >= 3:
            pinyin_str = " ".join(sys.argv[2:])
            print_json(handle_convert(pinyin_str))

        elif command == "list":
            print_json(handle_list())

        elif command == "stats":
            print_json(handle_stats())

        elif command == "add" and len(sys.argv) >= 4:
            print_json(handle_add_word(sys.argv[2], sys.argv[3]))

        elif command in ("help", "-h", "--help"):
            print_help()

        else:
            print_help()
            sys.exit(1)

    except InvalidPinyinError as e:
        print_error("拼音输入错误", str(e))
        logger.error("拼音输入错误: %s", e)
        sys.exit(1)
    except InvalidLimitError as e:
        print_error("参数错误", str(e))
        logger.error("参数错误: %s", e)
        sys.exit(1)
    except PinyinError as e:
        print_error("引擎错误", str(e))
        logger.error("引擎错误: %s", e)
        sys.exit(1)
    except Exception as e:
        print_error("未知错误", str(e))
        logger.exception("未知错误")
        sys.exit(1)


def print_help():
    """打印帮助信息"""
    help_text = """
拼音输入法引擎

用法:
    python -m app                        交互模式
    python -m app query <拼音> [数量]      查询拼音对应的汉字
    python -m app search <前缀>           搜索匹配的拼音
    python -m app convert <拼音...>       转换拼音句子
    python -m app list                   列出所有支持的拼音
    python -m app add <拼音> <词>          添加用户词条
    python -m app stats                  查看引擎统计信息
    python -m app help                   显示帮助信息

示例:
    python -m app query ni
    python -m app query zhong 5
    python -m app search zh
    python -m app convert ni hao shi jie
    python -m app add test 测试
    python -m app stats

环境变量:
    PINYIN_CONFIG_PATH       配置文件路径
    PINYIN_CANDIDATE_LIMIT   默认候选词数量
    PINYIN_USER_DICT_PATH    用户词库路径
    PINYIN_LOG_LEVEL         日志级别 (DEBUG/INFO/WARNING/ERROR)
    PINYIN_LOG_FORMAT        日志格式 (json/text)
"""
    print(help_text)


if __name__ == "__main__":
    main()
