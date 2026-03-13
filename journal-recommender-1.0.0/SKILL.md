---
name: journal-recommender
description: |
  顶级期刊论文推荐系统。从 CrossRef API 检索经济学与管理学顶级期刊的最新论文，
  自动生成中英双语推荐报告，支持自定义检索范围（学科、期刊级别、时间范围）。
  Use when: 用户请求定期检索顶级期刊论文、生成每周论文推荐报告、追踪特定期刊最新发表。
license: MIT
metadata:
  author: Academic Butler
  version: "1.0.0"
---

# 顶级期刊论文推荐系统 (Journal Recommender)

自动从 CrossRef 检索经济学与管理学 B 级及以上期刊的最新论文，生成精选推荐报告。

## 核心功能

### 1. 默认指令：每周顶刊论文推荐

当用户说"每周顶刊论文推荐"、"推荐顶级期刊论文"、"检索顶级期刊"时，执行：

```bash
python scripts/generate_journal_report.py --days 90 --top 20 --levels A,A-
```

这将检索 **A 级 + A- 级** 期刊（经济学 + 管理学），最近 90 天，推荐 20 篇。

### 2. 自定义检索

支持以下参数组合：

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--days N` | 检索最近 N 天 | 90 |
| `--top N` | 推荐 N 篇文章 | 20 |
| `--subject` | 学科：`economics` / `management` / `all` | all |
| `--levels` | 级别：`A` / `A-` / `B+` / `B`，逗号分隔 | A,A-（仅A/A-级）|

#### 示例用法

```bash
# 只看经济学 A/A-级（默认）
python scripts/generate_journal_report.py --subject economics --levels A,A-

# 只看管理学 A级
python scripts/generate_journal_report.py --subject management --levels A

# 全部学科 A+B+级
python scripts/generate_journal_report.py --levels A,A-,B+

# 检索最近30天，推荐10篇
python scripts/generate_journal_report.py --days 30 --top 10
```

### 3. 期刊配置

已配置的期刊（基于主流经济学/管理学期刊分级方案，已按研究方向精简）：

**Economics A 级 (5本)**
- American Economic Review (AER)
- Econometrica
- Journal of Political Economy (JPE)
- Quarterly Journal of Economics (QJE)
- Review of Economic Studies (RES)

**Economics A- 级 (15本)**
- Economic Journal
- AEJ: Applied Economics
- AEJ: Economic Policy
- AEJ: Macroeconomics
- AEJ: Microeconomics
- Journal of European Economic Association
- Journal of International Economics
- Journal of Labor Economics
- Journal of Development Economics
- Journal of Economic Growth
- Journal of Environmental Economics and Management
- Journal of Public Economics
- Journal of Urban Economics
- Review of Economics and Statistics
- International Journal of Industrial Organization

**Economics B+/B 级 (精选相关)**
- China Economic Review
- Economic Development and Cultural Change
- Journal of Comparative Economics
- Journal of Economic Behavior & Organization
- Journal of Population Economics
- Journal of Regional Science
- World Economy
- World Development
- Regional Studies (跨学科)
- 等等...

**Management A/A- 级**
- Journal of International Business Studies
- Strategic Management Journal
- Journal of Business Venturing
- Journal of Management Studies
- Research Policy

详细配置见：`references/journal_ranking.json`

## 报告特性

1. **自动去重**：对比最近 90 天内的历史推荐，避免重复推荐同一篇文章
2. **双语摘要**：每篇文章提供英文摘要 + 中文翻译，方便快速了解内容
3. **综合评分**：基于期刊级别 (40%) + 引用次数 (20%) + 发布时间 (20%) + 摘要完整度 (20%)
4. **Top 5 精华**：自动选出本期评分最高的 5 篇
5. **检索来源**：报告末尾列出本次检索的所有期刊及检索结果

## 输出位置

- 报告保存：`output/weekly-journal-recommend/YYYY-MM-DD-顶级期刊精选推荐.md`

## 定期运行建议

如需每周自动运行，可创建自动化任务：

```bash
# 每周一早上9点运行
python scripts/generate_journal_report.py --days 90 --top 20 --levels A,A-
```

## 故障排除

- **翻译失败**：静默跳过，不影响报告生成
- **API 超时**：单本期刊跳过，不影响其他
- **去重失败**：检查历史报告文件是否损坏

---

**使用示例**

```
用户: 推荐一些顶级期刊论文
AI: 好的，为您检索 A/A-级经济学和管理学期刊最近90天的最新论文...
（执行 generate_journal_report.py）
✅ 已生成 20 篇推荐，报告保存在：...
```
