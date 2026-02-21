"""
Bridge script: runs PSXNewsAgent and outputs JSON to stdout for Next.js API.
Usage: python scripts/api_news.py <mode> [args...]
  mode=fetch: api_news.py fetch [hours]
  mode=recent: api_news.py recent [hours] [limit]
  mode=symbols: api_news.py symbols <comma_separated_symbols> [days]
  mode=macro: api_news.py macro [hours]
"""
import sys
import os
import json
from datetime import datetime
from dataclasses import asdict

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from psx_news_agent import PSXNewsAgent, NewsSummary


def main():
    if len(sys.argv) < 2:
        print(json.dumps({
            "success": False,
            "error": "Missing mode: fetch | recent | symbols | macro",
            "timestamp": datetime.now().isoformat(),
        }))
        sys.exit(1)

    mode = (sys.argv[1] or "").strip().lower()
    if mode not in ("fetch", "recent", "symbols", "macro"):
        print(json.dumps({
            "success": False,
            "error": f"Invalid mode: {mode}. Use fetch | recent | symbols | macro",
            "timestamp": datetime.now().isoformat(),
        }))
        sys.exit(1)

    storage_path = "news_data/news.db"
    try:
        agent = PSXNewsAgent(storage_path=storage_path)
    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }))
        sys.exit(1)

    try:
        if mode == "fetch":
            hours = int(sys.argv[2]) if len(sys.argv) > 2 else 48
            devnull = open(os.devnull, "w", encoding="utf-8")
            old_stdout = sys.stdout
            sys.stdout = devnull
            try:
                articles = agent.fetch_recent_news(hours=hours)
                summary = agent.process_articles(articles)
            finally:
                sys.stdout = old_stdout
                devnull.close()
            summary_dict = asdict(summary)
            recent = agent.storage.get_recent_articles(hours=hours, limit=20)
            recent_list = [a.to_dict() for a in recent if agent._is_business_related(a)]
            data = {
                "summary": summary_dict,
                "recent_articles": recent_list,
            }
        elif mode == "recent":
            hours = int(sys.argv[2]) if len(sys.argv) > 2 else 24
            limit = int(sys.argv[3]) if len(sys.argv) > 3 else 50
            articles = agent.storage.get_recent_articles(hours=hours, limit=limit)
            articles = [a for a in articles if agent._is_business_related(a)]
            data = {"articles": [a.to_dict() for a in articles]}
        elif mode == "symbols":
            symbols_arg = sys.argv[2] if len(sys.argv) > 2 else ""
            days = int(sys.argv[3]) if len(sys.argv) > 3 else 7
            if not symbols_arg.strip():
                print(json.dumps({
                    "success": False,
                    "error": "symbols mode requires comma-separated symbols",
                    "timestamp": datetime.now().isoformat(),
                }))
                sys.exit(1)
            symbols_list = [s.strip().upper().replace(".KA", "") for s in symbols_arg.split(",") if s.strip()]
            news_by_symbol = agent.get_news_for_symbols(symbols_list, days=days)
            data = {
                symbol: [a.to_dict() for a in articles if agent._is_business_related(a)]
                for symbol, articles in news_by_symbol.items()
            }
        else:  # macro
            hours = int(sys.argv[2]) if len(sys.argv) > 2 else 48
            summary = agent.get_macro_news_summary(hours=hours)
            data = {
                category_id: [a.to_dict() for a in articles if agent._is_business_related(a)]
                for category_id, articles in summary.items()
            }

        out = {
            "success": True,
            "data": data,
            "timestamp": datetime.now().isoformat(),
        }
        print(json.dumps(out))
    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }))
        sys.exit(1)


if __name__ == "__main__":
    main()
