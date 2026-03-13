"""
期刊文章检索模块

功能：
- 从CrossRef API批量检索Economics/Management B级以上期刊最新文章
- 根据期刊级别、引用数、发布时间进行综合评分
- 支持去重和历史记录管理
"""

import sys
import time
import json
import re
import html
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple

import requests

# ── 路径配置 ────────────────────────────────────────────────
# 使用相对路径，支持不同环境部署
SCRIPT_DIR   = Path(__file__).parent.resolve()
WORK_DIR     = SCRIPT_DIR.parent
CONFIG_FILE  = WORK_DIR / "references" / "journal_ranking.json"
HISTORY_DIR  = WORK_DIR / "output" / "weekly-journal-recommend"

CROSSREF_BASE = "https://api.crossref.org/works"
HEADERS = {"User-Agent": "JournalRecommender/1.0 (mailto:user@example.com)"}

# 期刊级别分数
LEVEL_SCORE = {"A": 100, "A-": 80, "B+": 60, "B": 40}


# ── 工具函数 ─────────────────────────────────────────────────

def clean_abstract(raw: str) -> str:
    """清理JATS XML格式的摘要"""
    if not raw:
        return ""
    # 移除JATS标签
    clean = re.sub(r"<[^>]+>", " ", raw)
    # 还原HTML实体
    clean = html.unescape(clean)
    # 压缩空白
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def parse_date(item: Dict) -> Optional[datetime]:
    """从CrossRef item中解析发布日期"""
    for field in ("published", "published-print", "published-online"):
        parts = item.get(field, {}).get("date-parts", [[]])[0]
        if parts and parts[0]:
            try:
                y = int(parts[0])
                m = int(parts[1]) if len(parts) > 1 and parts[1] else 1
                d = int(parts[2]) if len(parts) > 2 and parts[2] else 1
                return datetime(y, m, d)
            except Exception:
                continue
    return None


def format_authors(item: Dict, max_n: int = 4) -> str:
    """格式化作者列表"""
    authors = item.get("author", [])
    names = []
    for a in authors[:max_n]:
        given = a.get("given", "")
        family = a.get("family", "")
        if family:
            names.append(f"{given} {family}".strip())
    if len(authors) > max_n:
        names.append(f"et al. ({len(authors)} total)")
    return "; ".join(names) if names else "N/A"


# ── CrossRef 检索 ─────────────────────────────────────────────

def fetch_articles_for_journal(
    issn: str,
    journal_name: str,
    level: str,
    days: int = 60,
    max_per_journal: int = 10
) -> List[Dict]:
    """检索单本期刊的最新文章"""
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    params = {
        "filter": f"issn:{issn},from-index-date:{cutoff}",
        "sort": "published",
        "order": "desc",
        "rows": max_per_journal,
        "select": "title,abstract,author,published,published-print,DOI,container-title,is-referenced-by-count,subject,type"
    }
    try:
        resp = requests.get(CROSSREF_BASE, params=params, headers=HEADERS, timeout=20)
        if resp.status_code != 200:
            return []
        items = resp.json().get("message", {}).get("items", [])
        results = []
        for item in items:
            # 只要期刊文章
            if item.get("type") not in ("journal-article", None):
                continue
            title_list = item.get("title", [])
            if not title_list:
                continue
            title = title_list[0]
            # 过滤明显非研究性内容
            skip_keywords = ["erratum", "correction", "retraction", "book review",
                             "editorial", "front matter", "issue information"]
            if any(kw in title.lower() for kw in skip_keywords):
                continue
            pub_date = parse_date(item)
            article = {
                "title":       title,
                "abstract":    clean_abstract(item.get("abstract", "")),
                "authors":     format_authors(item),
                "doi":         item.get("DOI", ""),
                "url":         f"https://doi.org/{item.get('DOI', '')}",
                "journal":     journal_name,
                "issn":        issn,
                "level":       level,
                "citations":   item.get("is-referenced-by-count", 0),
                "pub_date":    pub_date.strftime("%Y-%m-%d") if pub_date else "N/A",
                "pub_datetime": pub_date,
                "data_source": "CrossRef"
            }
            results.append(article)
        return results
    except requests.exceptions.Timeout:
        print(f"   ⏱ 超时: {journal_name}")
        return []
    except Exception as e:
        print(f"   ❌ 失败: {journal_name} — {e}")
        return []


def fetch_all_journals(
    days: int = 60,
    max_per_journal: int = 8,
    subject_filter: List[str] = None,
    level_filter: List[str] = None,
    delay: float = 0.8
) -> List[Dict]:
    """
    批量检索所有配置期刊的文章

    Args:
        days: 最近多少天
        max_per_journal: 每本期刊最多返回多少篇
        subject_filter: 限制学科，如 ["economics", "management"]，None表示全部
        level_filter: 限制级别，如 ["A", "A-"]，None表示全部
        delay: 请求间隔（秒），避免限流
    """
    with open(CONFIG_FILE, encoding="utf-8") as f:
        config = json.load(f)

    subjects = subject_filter or list(config.keys())
    # 过滤掉元数据key（以_开头的key）
    subjects = [s for s in subjects if not s.startswith("_")]

    levels = level_filter or ["A", "A-", "B+", "B"]

    all_articles = []

    def count_journals_in_subject(subj_dict):
        """统计一个学科下所有期刊数量（跳过_开头的元数据key）"""
        total = 0
        for k, v in subj_dict.items():
            if not k.startswith("_") and isinstance(v, list) and k in levels:
                total += len(v)
        return total

    total_journals = sum(
        count_journals_in_subject(config[s])
        for s in subjects if s in config
    )
    processed = 0

    for subject in subjects:
        if subject not in config:
            continue
        print(f"\n{'─'*50}")
        print(f"📚 学科: {subject.upper()}")
        print(f"{'─'*50}")

        for level, journals in config[subject].items():
            # 跳过元数据key（_note等）和非目标级别
            if level.startswith("_") or not isinstance(journals, list):
                continue
            if level not in levels:
                continue
            print(f"\n  [{level}级] {len(journals)} 本期刊")
            for j in journals:
                processed += 1
                name = j["name"]
                issn = j["issn"]
                print(f"  ({processed}/{total_journals}) {name}...", end=" ", flush=True)
                articles = fetch_articles_for_journal(
                    issn, name, level,
                    days=days,
                    max_per_journal=max_per_journal
                )
                for a in articles:
                    a["subject"] = subject
                all_articles.extend(articles)
                print(f"✓ {len(articles)} 篇" if articles else "0 篇")
                time.sleep(delay)

    return all_articles


# ── 评分算法 ──────────────────────────────────────────────────

def score_article(article: Dict, today: datetime = None) -> float:
    """
    综合评分：期刊级别(40%) + 引用次数(20%) + 新鲜度(20%) + 摘要完整度(20%)

    Returns:
        0-100 的综合分数
    """
    if today is None:
        today = datetime.now()

    # 1. 期刊级别
    level_s = LEVEL_SCORE.get(article.get("level", "B"), 40) / 100 * 40

    # 2. 引用次数（对数归一化，上限50分对应100引用）
    citations = article.get("citations", 0) or 0
    import math
    cite_s = min(math.log1p(citations) / math.log1p(100) * 20, 20)

    # 3. 新鲜度（60天衰减到0）
    pub_dt = article.get("pub_datetime")
    if pub_dt and isinstance(pub_dt, datetime):
        days_old = max(0, (today - pub_dt).days)
        freshness_s = max(0, 20 * (1 - days_old / 60))
    else:
        freshness_s = 10  # 无日期给个中间值

    # 4. 摘要完整度（有摘要才方便读者判断）
    abstract = article.get("abstract", "")
    if len(abstract) > 300:
        abstract_s = 20
    elif len(abstract) > 100:
        abstract_s = 12
    elif len(abstract) > 0:
        abstract_s = 6
    else:
        abstract_s = 0

    return round(level_s + cite_s + freshness_s + abstract_s, 2)


# ── 去重与历史过滤 ─────────────────────────────────────────────

def load_doi_history(lookback_days: int = 60) -> set:
    """加载已推荐的DOI历史记录"""
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    cutoff = datetime.now() - timedelta(days=lookback_days)
    dois = set()
    for f in HISTORY_DIR.glob("*.md"):
        try:
            date_str = f.stem[:10]
            file_date = datetime.strptime(date_str, "%Y-%m-%d")
            if file_date < cutoff:
                continue
            text = f.read_text(encoding="utf-8")
            # 提取DOI
            found = re.findall(r"doi\.org/([^\s\)\"]+)", text, re.IGNORECASE)
            dois.update(d.strip() for d in found)
        except Exception:
            continue
    return dois


def deduplicate(articles: List[Dict], history: set) -> List[Dict]:
    """去重：同一DOI只保留一条；过滤历史已推荐"""
    seen_dois = set()
    filtered = []
    skipped = 0
    for a in articles:
        doi = (a.get("doi") or "").strip().lower()
        if not doi:
            filtered.append(a)  # 无DOI也保留
            continue
        if doi in history or doi in seen_dois:
            skipped += 1
            continue
        seen_dois.add(doi)
        filtered.append(a)
    if skipped:
        print(f"   去重过滤: 跳过 {skipped} 篇重复文章")
    return filtered


# ── 主函数 ────────────────────────────────────────────────────

def search_journal_articles(
    days: int = 60,
    top_n: int = 20,
    subject_filter: List[str] = None,
    level_filter: List[str] = None,
    max_per_journal: int = 8,
    delay: float = 0.8
) -> List[Dict]:
    """
    检索并返回推荐文章列表

    Args:
        days: 检索最近多少天
        top_n: 最终推荐多少篇
        subject_filter: 限制学科，None表示全部
        level_filter: 限制级别，None表示全部
        max_per_journal: 每本期刊最多抓取多少篇
        delay: 请求间隔秒数

    Returns:
        排序后的推荐文章列表
    """
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")

    print("\n" + "="*60)
    print("📖 顶级期刊文章检索")
    print(f"   范围: 最近 {days} 天 | 目标: {top_n} 篇")
    print("="*60)

    # 1. 批量检索
    articles = fetch_all_journals(
        days=days,
        max_per_journal=max_per_journal,
        subject_filter=subject_filter,
        level_filter=level_filter,
        delay=delay
    )
    print(f"\n✅ 共检索到 {len(articles)} 篇原始文章")

    # 2. 历史去重
    print("\n📂 加载历史推荐记录...")
    history = load_doi_history(lookback_days=90)
    print(f"   历史记录: {len(history)} 条DOI")
    articles = deduplicate(articles, history)
    print(f"   去重后: {len(articles)} 篇")

    # 3. 评分排序
    today = datetime.now()
    for a in articles:
        a["score"] = score_article(a, today)
    articles.sort(key=lambda x: x["score"], reverse=True)

    return articles[:top_n]


if __name__ == "__main__":
    # 快速测试
    results = search_journal_articles(days=60, top_n=5, subject_filter=["economics"])
    for i, a in enumerate(results, 1):
        print(f"\n{i}. [{a['level']}] {a['title']}")
        print(f"   期刊: {a['journal']} | 日期: {a['pub_date']} | 引用: {a['citations']} | 分数: {a['score']}")
