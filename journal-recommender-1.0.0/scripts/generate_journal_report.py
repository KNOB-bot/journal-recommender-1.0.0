"""
顶级期刊文章推荐报告生成器（正式版）

使用方法：
    python scripts/generate_journal_report.py
    python scripts/generate_journal_report.py --days 60 --top 20 --subject economics

参数：
    --days      检索最近多少天（默认90）
    --top       推荐文章数量（默认20）
    --subject   限定学科：economics / management / all（默认all）
    --levels    限定级别：A / A- / B+ / B，逗号分隔（默认所有级别）
"""

import sys, json, re, html, math, time, shutil, argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict
from collections import defaultdict

import requests

# ── 路径配置 ──────────────────────────────────────────────────
# 使用相对路径，支持不同环境部署
SCRIPT_DIR   = Path(__file__).parent.resolve()
WORK_DIR     = SCRIPT_DIR.parent  # 默认为 scripts 的父目录
CONFIG_FILE  = WORK_DIR / "references" / "journal_ranking.json"
OUTPUT_DIR   = WORK_DIR / "output" / "weekly-journal-recommend"
OBSIDIAN_DIR = None  # 可通过环境变量或参数配置
CROSSREF_BASE = "https://api.crossref.org/works"
HEADERS = {"User-Agent": "JournalRecommender/1.0 (mailto:user@example.com)"}

LEVEL_SCORE  = {"A": 100, "A-": 80, "B+": 60, "B": 40}
LEVEL_LABELS = {"A": "⭐⭐⭐⭐ A级", "A-": "⭐⭐⭐ A-级", "B+": "⭐⭐ B+级", "B": "⭐ B级"}
SUBJ_LABELS  = {"economics": "经济学 Economics", "management": "管理学 Management"}
LEVEL_ORDER  = ["A", "A-", "B+", "B"]


# ── 工具函数 ──────────────────────────────────────────────────

def clean_abstract(raw: str) -> str:
    if not raw: return ""
    clean = re.sub(r"<[^>]+>", " ", raw)
    clean = html.unescape(clean)
    return re.sub(r"\s+", " ", clean).strip()


def parse_date(item: dict):
    for field in ("published", "published-print", "published-online"):
        parts = item.get(field, {}).get("date-parts", [[]])[0]
        if parts and parts[0]:
            try:
                y = int(parts[0])
                m = int(parts[1]) if len(parts) > 1 and parts[1] else 1
                d = int(parts[2]) if len(parts) > 2 and parts[2] else 1
                return datetime(y, m, d)
            except: continue
    return None


def format_authors(item: dict, max_n: int = 4) -> str:
    authors = item.get("author", [])
    names = [f"{a.get('given','')} {a.get('family','')}".strip()
             for a in authors[:max_n] if a.get("family")]
    if len(authors) > max_n:
        names.append("et al.")
    return "; ".join(names) or "N/A"


# ── CrossRef 检索 ─────────────────────────────────────────────

def fetch_journal(issn: str, name: str, level: str, days: int = 90, rows: int = 8) -> List[Dict]:
    """检索单本期刊近期文章"""
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    params = {
        "filter": f"issn:{issn},from-index-date:{cutoff}",
        "sort": "published", "order": "desc", "rows": rows,
        "select": "title,abstract,author,published,published-print,DOI,is-referenced-by-count,type"
    }
    skip_kw = ["erratum","correction","retraction","book review",
               "editorial","front matter","issue information","corrigendum"]
    try:
        r = requests.get(CROSSREF_BASE, params=params, headers=HEADERS, timeout=20)
        if r.status_code != 200: return []
        items = r.json().get("message", {}).get("items", [])
        results = []
        for item in items:
            if item.get("type") not in ("journal-article", None): continue
            tlist = item.get("title", [])
            if not tlist: continue
            t = tlist[0]
            if any(k in t.lower() for k in skip_kw): continue
            pub_dt = parse_date(item)
            results.append({
                "title":        t,
                "abstract":     clean_abstract(item.get("abstract", "")),
                "authors":      format_authors(item),
                "doi":          item.get("DOI", ""),
                "url":          f"https://doi.org/{item.get('DOI','')}",
                "journal":      name,
                "issn":         issn,
                "level":        level,
                "citations":    item.get("is-referenced-by-count", 0) or 0,
                "pub_date":     pub_dt.strftime("%Y-%m-%d") if pub_dt else "N/A",
                "pub_datetime": pub_dt,
            })
        return results
    except requests.exceptions.Timeout:
        print(f"  ⏱ 超时跳过: {name}")
        return []
    except Exception as e:
        print(f"  ❌ 失败: {name} — {type(e).__name__}")
        return []


def fetch_all(days: int, subjects: List[str], levels: List[str],
              max_per_journal: int = 8, delay: float = 0.8):
    """
    批量检索所有配置期刊。
    Returns:
        (all_articles, searched_journals)
        searched_journals: List[Dict] 每项含 name/issn/level/subject/count
    """
    with open(CONFIG_FILE, encoding="utf-8") as f:
        config = json.load(f)

    all_articles = []
    searched_journals = []   # 记录本次检索了哪些期刊

    # 统计总期刊数（跳过 _note 等元数据key）
    def _count(subj):
        return sum(len(v) for k, v in config[subj].items()
                   if not k.startswith("_") and isinstance(v, list) and k in levels)

    total = sum(_count(s) for s in subjects if s in config)
    n = 0

    for subj in subjects:
        if subj not in config: continue
        print(f"\n{'─'*50}")
        print(f"📚 {SUBJ_LABELS.get(subj, subj)}")
        print(f"{'─'*50}")
        for level in LEVEL_ORDER:
            if level not in levels: continue
            if level not in config[subj]: continue
            journals = config[subj][level]
            if not isinstance(journals, list): continue
            print(f"\n  [{level}级] {len(journals)} 本期刊")
            for j in journals:
                n += 1
                name, issn = j["name"], j["issn"]
                print(f"  ({n}/{total}) {name[:48]}...", end=" ", flush=True)
                arts = fetch_journal(issn, name, level, days=days, rows=max_per_journal)
                for a in arts: a["subject"] = subj
                all_articles.extend(arts)
                count = len(arts)
                print(f"✓ {count} 篇" if count else "0 篇")
                searched_journals.append({
                    "name": name, "issn": issn,
                    "level": level, "subject": subj, "count": count
                })
                time.sleep(delay)

    return all_articles, searched_journals


# ── 评分 & 去重 ───────────────────────────────────────────────

def score_article(a: dict, today: datetime = None) -> float:
    if today is None: today = datetime.now()
    level_s = LEVEL_SCORE.get(a.get("level", "B"), 40) / 100 * 40
    cite_s  = min(math.log1p(a.get("citations", 0) or 0) / math.log1p(100) * 20, 20)
    pub_dt  = a.get("pub_datetime")
    if pub_dt and isinstance(pub_dt, datetime):
        fresh_s = max(0, 20 * (1 - max(0, (today - pub_dt).days) / 90))
    else:
        fresh_s = 10
    abstr   = a.get("abstract", "")
    abstr_s = 20 if len(abstr) > 300 else 12 if len(abstr) > 100 else 6 if abstr else 0
    return round(level_s + cite_s + fresh_s + abstr_s, 2)


def load_doi_history(lookback: int = 90) -> set:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    cutoff = datetime.now() - timedelta(days=lookback)
    dois = set()
    for f in OUTPUT_DIR.glob("*.md"):
        try:
            file_date = datetime.strptime(f.stem[:10], "%Y-%m-%d")
            if file_date < cutoff: continue
            for m in re.findall(r"doi\.org/([^\s\)\"]+)", f.read_text(encoding="utf-8")):
                dois.add(m.strip().lower())
        except: continue
    return dois


def deduplicate(articles: List[Dict], history: set) -> List[Dict]:
    seen, out, skipped = set(), [], 0
    for a in articles:
        doi = (a.get("doi") or "").strip().lower()
        if doi and (doi in history or doi in seen):
            skipped += 1; continue
        if doi: seen.add(doi)
        out.append(a)
    if skipped: print(f"   历史去重: 跳过 {skipped} 篇")
    return out


# ── 翻译 ──────────────────────────────────────────────────────

def try_translate(text: str, max_len: int = 600) -> str:
    """
    调用 Google 翻译非官方接口，将英文翻译为中文。
    无需 API Key，免费使用。失败时静默返回空字符串。
    """
    if not text or not text.strip():
        return ""
    snippet = text[:max_len].strip()
    try:
        url = "https://translate.googleapis.com/translate_a/single"
        params = {
            "client": "gtx",
            "sl": "en",
            "tl": "zh-CN",
            "dt": "t",
            "q": snippet,
        }
        resp = requests.get(url, params=params,
                            headers={"User-Agent": "Mozilla/5.0"},
                            timeout=10)
        if resp.status_code != 200:
            return ""
        data = resp.json()
        # 结构: [ [[translated, original, ...], ...], ... ]
        parts = []
        for block in data[0]:
            if block and block[0]:
                parts.append(block[0])
        result = "".join(parts).strip()
        return result if result and result != snippet else ""
    except Exception:
        return ""


# ── 报告生成 ──────────────────────────────────────────────────

def generate_report(articles: List[Dict], days: int,
                    searched_journals: List[Dict] = None) -> str:
    today_str  = datetime.now().strftime("%Y-%m-%d")
    today_full = datetime.now().strftime("%Y年%m月%d日")

    grouped = defaultdict(lambda: defaultdict(list))
    for a in articles:
        grouped[a.get("subject", "economics")][a.get("level", "B")].append(a)

    level_count = {}
    for a in articles:
        lv = a.get("level","B"); level_count[lv] = level_count.get(lv,0)+1
    subj_count = {}
    for a in articles:
        s = a.get("subject","economics"); subj_count[s] = subj_count.get(s,0)+1

    # ── 报告头 ────────────────────────────────────────────────
    report = f"""# 顶级期刊精选文章推荐

**日期**: {today_str}

**数据来源**: CrossRef API（经济学与管理学 B 级及以上英文期刊）

> 基于期刊学术分级、引用次数、发布时效，从经济学与管理学顶级期刊中精选推荐

---

## 📊 本期概览

| 指标 | 数值 |
|------|------|
| 推荐文章总数 | **{len(articles)} 篇** |
| 检索时间范围 | 最近 **{days}** 天 |
| 涵盖学科 | {" / ".join(SUBJ_LABELS.get(s,s) for s in subj_count)} |
| 生成日期 | {today_full} |

### 期刊级别分布

| 级别 | 数量 |
|------|------|
"""
    for lv in LEVEL_ORDER:
        cnt = level_count.get(lv, 0)
        if cnt: report += f"| {LEVEL_LABELS[lv]} | {cnt} 篇 |\n"
    report += "\n---\n\n"

    # ── 按学科分节 ────────────────────────────────────────────
    num = 0
    for subj in ["economics", "management"]:
        if subj not in grouped: continue
        subj_arts = [a for a in articles if a.get("subject") == subj]
        report += f"## 🎯 {SUBJ_LABELS.get(subj, subj)}\n\n共 **{len(subj_arts)}** 篇推荐\n\n"
        for level in LEVEL_ORDER:
            if level not in grouped[subj]: continue
            lvl_arts = grouped[subj][level]
            report += f"### {LEVEL_LABELS[level]} 期刊（{len(lvl_arts)} 篇）\n\n"
            for a in lvl_arts:
                num += 1
                title    = a["title"]
                journal  = a.get("journal","")
                authors  = a.get("authors","N/A")
                pub_date = a.get("pub_date","N/A")
                doi      = a.get("doi","")
                url      = a.get("url", f"https://doi.org/{doi}")
                cites    = a.get("citations",0) or 0
                abstract = a.get("abstract","")
                score    = a.get("score",0)

                report += f"#### {num}. {title}\n\n"

                # 翻译标题
                print(f"   [{num}/{len(articles)}] 翻译标题...", end=" ", flush=True)
                title_cn = try_translate(title, 300)
                if title_cn:
                    report += f"**【{title_cn}】**\n\n"
                    print("✓")
                else:
                    print("跳过")

                report += f"**期刊**: {journal} | **级别**: {LEVEL_LABELS[level]}\n\n"
                report += f"**作者**: {authors}\n\n"
                report += f"**发布日期**: {pub_date}"
                if cites > 0: report += f" | **被引用**: {cites} 次"
                report += "\n\n"

                # 摘要
                if abstract:
                    disp = abstract[:600]+"..." if len(abstract)>600 else abstract
                    report += f"**摘要（英文）**: {disp}\n\n"
                    print(f"   [{num}/{len(articles)}] 翻译摘要...", end=" ", flush=True)
                    abstract_cn = try_translate(abstract, 600)
                    if abstract_cn:
                        cn_disp = abstract_cn[:400]+"..." if len(abstract_cn)>400 else abstract_cn
                        report += f"**摘要（中文参考）**: {cn_disp}\n\n"
                        print("✓")
                    else:
                        print("跳过")
                else:
                    report += "*（摘要不可用，请访问原文）*\n\n"

                report += f"**推荐理由**: 发表于{level}级权威期刊《{journal}》；综合评分 {score:.1f}\n\n"
                report += f"**链接**: [原文]({url})"
                if doi: report += f" | DOI: `{doi}`"
                report += "\n\n---\n\n"

    # ── Top 5 精华 ────────────────────────────────────────────
    report += "## 🏆 本期 Top 5 精华推荐\n\n"
    top5 = sorted(articles, key=lambda x: x.get("score",0), reverse=True)[:5]
    for i, a in enumerate(top5, 1):
        report += f"**{i}. {a['title']}**\n"
        report += f"- 期刊: {a['journal']} {LEVEL_LABELS.get(a['level'],'')}\n"
        report += f"- 发布: {a.get('pub_date','N/A')} | 被引: {a.get('citations',0) or 0} 次 | 综合分: {a.get('score',0):.1f}\n\n"

    report += "\n---\n\n"

    # ── 本次检索期刊列表 ──────────────────────────────────────
    report += "## 📋 本次检索来源期刊\n\n"
    if searched_journals:
        # 按学科 → 级别分组展示
        from collections import defaultdict as _dd
        sj_grouped = _dd(lambda: _dd(list))
        for j in searched_journals:
            sj_grouped[j["subject"]][j["level"]].append(j)

        for subj in ["economics", "management", "interdisciplinary"]:
            if subj not in sj_grouped:
                continue
            subj_label = SUBJ_LABELS.get(subj, subj.capitalize())
            report += f"### {subj_label}\n\n"
            for level in LEVEL_ORDER:
                if level not in sj_grouped[subj]:
                    continue
                jlist = sj_grouped[subj][level]
                label = LEVEL_LABELS[level]
                report += f"**{label}**（{len(jlist)} 本）\n\n"
                for j in jlist:
                    hit = f"，本期检索到 {j['count']} 篇" if j['count'] > 0 else "，本期无新文章"
                    report += f"- {j['name']}（ISSN: {j['issn']}{hit}）\n"
                report += "\n"
    else:
        report += "*（检索期刊信息不可用）*\n\n"

    report += f"---\n\n*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n"
    report += "*由学术管家 (Academic Butler) 自动生成*\n"
    return report


# ── 保存 ──────────────────────────────────────────────────────

def save_report(content: str) -> str:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    filename = f"{today}-顶级期刊精选推荐.md"
    out_path = OUTPUT_DIR / filename
    out_path.write_text(content, encoding="utf-8")
    print(f"\n✅ 报告已保存: {out_path}")
    if OBSIDIAN_DIR:
        try:
            OBSIDIAN_DIR.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(out_path), str(OBSIDIAN_DIR / filename))
            print(f"📋 已同步到 Obsidian: {OBSIDIAN_DIR / filename}")
        except Exception as e:
            print(f"⚠️  Obsidian同步失败: {e}")
    return str(out_path)


# ── 主入口 ────────────────────────────────────────────────────

def generate_journal_report(
    days: int = 90,
    top_n: int = 20,
    subject_filter: List[str] = None,
    level_filter: List[str] = None,
    max_per_journal: int = 8,
    delay: float = 0.8
) -> dict:
    """
    主函数：检索 → 去重 → 评分 → 生成报告

    Args:
        days:             检索最近多少天
        top_n:            推荐篇数
        subject_filter:   学科列表 ["economics","management"]，None=全部
        level_filter:     级别列表 ["A","A-","B+","B"]，None=全部
        max_per_journal:  每本期刊最多拉取篇数
        delay:            请求间隔秒数
    """
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")

    subjects = subject_filter or ["economics", "management"]
    levels   = level_filter or LEVEL_ORDER

    print("\n" + "="*60)
    print("📖 顶级期刊精选文章推荐报告")
    print("="*60)
    print(f"检索范围: 最近 {days} 天 | 目标推荐: {top_n} 篇")
    print(f"学科: {', '.join(subjects)} | 级别: {', '.join(levels)}")
    print()

    # 1. 批量检索
    articles, searched_journals = fetch_all(days, subjects, levels, max_per_journal, delay)
    print(f"\n✅ 共检索到 {len(articles)} 篇原始文章，来自 {len(searched_journals)} 本期刊")

    # 2. 历史去重
    print("\n📂 加载历史推荐记录...")
    history = load_doi_history(lookback=90)
    print(f"   历史DOI记录: {len(history)} 条")
    articles = deduplicate(articles, history)
    print(f"   去重后: {len(articles)} 篇")

    if not articles:
        print("⚠️  无可用文章")
        return {"error": "no articles"}

    # 3. 评分排序
    today = datetime.now()
    for a in articles:
        a["score"] = score_article(a, today)
    articles.sort(key=lambda x: x["score"], reverse=True)
    top_articles = articles[:top_n]

    # 4. 生成报告
    print(f"\n📝 生成报告 ({len(top_articles)} 篇)...")
    report = generate_report(top_articles, days, searched_journals)

    # 5. 保存
    path = save_report(report)

    # 统计
    level_count = {}
    for a in top_articles:
        lv = a.get("level","B"); level_count[lv] = level_count.get(lv,0)+1

    print("\n" + "="*60)
    print("✅ 报告生成完成!")
    print("="*60)
    for lv in LEVEL_ORDER:
        cnt = level_count.get(lv, 0)
        if cnt: print(f"  {LEVEL_LABELS.get(lv,lv)}: {cnt} 篇")
    print(f"\n📄 {path}")

    return {"report_path": path, "total": len(top_articles), "level_breakdown": level_count}


# ── CLI ───────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="顶级期刊文章推荐报告生成器")
    parser.add_argument("--days",    type=int, default=90,  help="检索最近多少天（默认90）")
    parser.add_argument("--top",     type=int, default=20,  help="推荐篇数（默认20）")
    parser.add_argument("--subject", type=str, default="all", help="学科: economics/management/all")
    parser.add_argument("--levels",  type=str, default="all", help="级别: A,A-,B+,B 或 all")
    args = parser.parse_args()

    subj = None if args.subject == "all" else [args.subject]
    lvls = None if args.levels == "all" else [l.strip() for l in args.levels.split(",")]

    generate_journal_report(
        days=args.days,
        top_n=args.top,
        subject_filter=subj,
        level_filter=lvls,
    )
