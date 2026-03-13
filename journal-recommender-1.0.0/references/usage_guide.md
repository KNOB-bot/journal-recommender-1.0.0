# 顶级期刊论文推荐系统使用指南

本文档介绍如何使用 `journal-recommender` Skill 进行论文检索和报告生成。

## 快速开始

### 默认指令

在 Claude Code / WorkBuddy 中说：

```
每周顶刊论文推荐
```

这将自动执行：
- 检索 A 级 + A- 级期刊（经济学 + 管理学）
- 最近 90 天
- 推荐 20 篇
- 自动生成中英双语报告

### 自定义检索

```
检索经济学A级期刊最近60天的论文，推荐15篇
```

```
只看管理学A-级期刊，最近30天
```

## 命令行参数

| 参数 | 说明 | 默认值 | 示例 |
|------|------|--------|------|
| `--days` | 检索最近多少天 | 90 | `--days 60` |
| `--top` | 推荐文章数量 | 20 | `--top 15` |
| `--subject` | 学科筛选 | all | `--subject economics` |
| `--levels` | 期刊级别 | A,A- | `--levels A,A-,B+` |

### 学科选项

- `economics` — 只看经济学期刊
- `management` — 只看管理学期刊
- `all` — 全部学科（默认）

### 级别选项

- `A` — A 级期刊
- `A-` — A- 级期刊
- `B+` — B+ 级期刊
- `B` — B 级期刊

多个级别用逗号分隔，如 `--levels A,A-,B+`

## 使用场景

### 场景 1：每周例行推荐

```
每周顶刊论文推荐
```

适合每周执行一次，追踪顶级期刊最新发表。

### 场景 2：专注于经济学

```
检索经济学期刊最近90天，推荐30篇，包含B+级
```

执行：
```bash
python scripts/generate_journal_report.py --subject economics --levels A,A-,B+ --top 30
```

### 场景 3：快速浏览管理学顶刊

```
管理学A级期刊最近30天推荐10篇
```

执行：
```bash
python scripts/generate_journal_report.py --subject management --levels A --days 30 --top 10
```

## 报告解读

### 报告结构

1. **本期概览**：推荐文章总数、检索时间范围、期刊级别分布
2. **按学科分节**：经济学 → 管理学
3. **按级别分组**：A级 → A-级 → B+级 → B级
4. **每篇文章**：
   - 中文标题翻译
   - 期刊名称和级别
   - 作者列表
   - 发布日期和被引用次数
   - 英文摘要
   - 中文摘要翻译
   - 推荐理由（综合评分）
   - 原文链接和 DOI
5. **Top 5 精华**：本期评分最高的 5 篇
6. **检索来源期刊**：本次检索的所有期刊列表

### 评分算法

综合评分 = 期刊级别分(40%) + 引用次数分(20%) + 新鲜度分(20%) + 摘要完整度分(20%)

| 因素 | 计算方式 |
|------|---------|
| 期刊级别 | A=40分, A-=32分, B+=24分, B=16分 |
| 引用次数 | log(citations+1) / log(101) * 20 |
| 新鲜度 | max(0, 20 * (1 - 发布天数/90)) |
| 摘要完整度 | >300字=20分, >100字=12分, 有摘要=6分, 无=0分 |

## 自定义期刊

### 添加期刊

编辑 `references/journal_ranking.json`：

```json
{
  "economics": {
    "A-": [
      {"name": "新期刊名称", "issn": "1234-5678"}
    ]
  }
}
```

### 删除期刊

直接从配置文件中移除对应条目。

### 修改期刊级别

将期刊移动到对应的级别数组中。

## 故障排除

### 问题：翻译失败

翻译依赖 Google Translate 非官方接口，可能偶尔失败。翻译失败时会静默跳过，不影响报告生成。

### 问题：API 超时

CrossRef API 有速率限制，如果同时检索大量期刊，可能出现超时。建议：
- 减少检索期刊数量
- 增加请求间隔（修改脚本中的 `delay` 参数）

### 问题：重复推荐

系统会自动对比最近 90 天内的历史推荐，基于 DOI 去重。如果仍然出现重复：
- 检查历史报告文件是否损坏
- 确认 DOI 格式是否一致

## 高级用法

### 作为模块调用

```python
from scripts.generate_journal_report import generate_journal_report

result = generate_journal_report(
    days=90,
    top_n=20,
    subject_filter=["economics"],
    level_filter=["A", "A-"]
)

print(f"报告路径: {result['report_path']}")
print(f"推荐篇数: {result['total']}")
```

### 集成到自动化流程

```bash
# crontab 示例（每周一早上 9 点运行）
0 9 * * 1 cd /path/to/journal-recommender && python scripts/generate_journal_report.py --days 90 --top 20 --levels A,A-
```

## 注意事项

1. **网络连接**：需要稳定的网络连接访问 CrossRef API
2. **翻译质量**：机器翻译仅供参考，专业术语可能不准确
3. **引用次数**：CrossRef 的引用数据可能与 Google Scholar 不同
4. **发布时间**：CrossRef 的索引时间可能与期刊官网略有延迟
