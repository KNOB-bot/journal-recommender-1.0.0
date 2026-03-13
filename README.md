# Journal Recommender - 期刊论文推荐系统

[![版本](https://img.shields.io/badge/版本-1.0.0-blue.svg)](https://github.com)
[![Python](https://img.shields.io/badge/Python-3.8+-green.svg)](https://www.python.org/)
[![许可证](https://img.shields.io/badge/许可证-MIT-orange.svg)](LICENSE)

> 自动检索经济学与管理学顶级期刊最新论文，生成中英双语推荐报告

## 功能特点

- 🔍 **自动检索**：从 CrossRef API 检索 50+ 本顶级期刊的最新论文
- 🌐 **双语报告**：每篇论文提供英文摘要 + 中文翻译，方便快速了解
- 🔄 **智能去重**：自动对比历史推荐，避免重复推荐同一篇文章
- 📊 **综合评分**：基于期刊级别、引用次数、发布时间、摘要完整度综合排序
- ⚙️ **灵活配置**：支持按学科、期刊级别、时间范围自定义检索
- 📋 **完整来源**：报告末尾列出本次检索的所有期刊及检索结果

## 快速开始

### 安装依赖

```bash
pip install requests
```

### 使用方法

在 Claude Code / WorkBuddy / Openclaw / ... 中使用：

```
每周顶刊论文推荐
```

或自定义检索：

```
检索经济学A级期刊最近60天的论文，推荐15篇
```

### 命令行使用

```bash
# 默认检索 A/A-级期刊，最近90天，推荐20篇
python scripts/generate_journal_report.py --days 90 --top 20 --levels A,A-

# 只看经济学
python scripts/generate_journal_report.py --subject economics --levels A,A-

# 只看管理学A级
python scripts/generate_journal_report.py --subject management --levels A

# 包含B+级
python scripts/generate_journal_report.py --levels A,A-,B+
```

## 目录结构

```
journal-recommender/
├── SKILL.md                 # Skill 说明文档
├── CHANGELOG.md             # 更新日志
├── README.md                # 本文件
├── _meta.json               # Skill 元数据
├── _validate.py             # 脚本验证工具
├── scripts/
│   ├── generate_journal_report.py  # 主报告生成脚本
│   └── journal_tracker.py          # 期刊检索核心模块
├── references/
│   ├── journal_ranking.json        # 期刊配置文件（ISSN + 级别）
│   └── usage_guide.md              # 使用指南
└── config/                  # 配置文件目录
```

## 已配置期刊

基于主流经济学/管理学期刊分级方案，已精简至约 50 本：

### Economics

| 级别 | 期刊数 | 代表期刊 |
|------|--------|---------|
| A 级 | 5 本 | AER, Econometrica, JPE, QJE, RES |
| A- 级 | 15 本 | Economic Journal, AEJ 系列, JEEA, JIE, JLE, JUE 等 |
| B+ 级 | 10 本 | China Economic Review, World Economy, Journal of Regional Science 等 |
| B 级 | 10 本 | Journal of Economic Geography, World Development, Regional Studies 等 |

### Management

| 级别 | 期刊数 | 代表期刊 |
|------|--------|---------|
| A 级 | 2 本 | JIBS, SMJ |
| A- 级 | 3 本 | JBV, JMS, Research Policy |
| B+/B 级 | 10 本 | Technovation, Entrepreneurship & Regional Development 等 |

## 报告特性

1. **双语摘要**：每篇文章提供英文摘要 + 中文翻译（Google Translate）
2. **自动去重**：对比最近 90 天内的历史推荐，避免重复
3. **综合评分**：
   - 期刊级别 (40%)
   - 引用次数 (20%)
   - 发布时间 (20%)
   - 摘要完整度 (20%)
4. **Top 5 精华**：自动选出本期评分最高的 5 篇
5. **检索来源**：报告末尾列出本次检索的所有期刊及检索结果

## 输出位置

- 报告保存：`output/weekly-journal-recommend/YYYY-MM-DD-顶级期刊精选推荐.md`
- 自动同步到 Obsidian：`Documents/Obsidian Vault/10_Daily/`

## 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--days N` | 检索最近 N 天 | 90 |
| `--top N` | 推荐 N 篇文章 | 20 |
| `--subject` | 学科：`economics` / `management` / `all` | all |
| `--levels` | 级别：`A` / `A-` / `B+` / `B`，逗号分隔 | A,A- |

## 自定义期刊配置

编辑 `references/journal_ranking.json` 可添加或删除期刊：

```json
{
  "economics": {
    "A": [
      {"name": "American Economic Review", "issn": "0002-8282"}
    ]
  }
}
```

## 已知限制

- 翻译依赖 Google Translate 非官方接口，可能偶尔失败
- CrossRef API 有速率限制，检索过多期刊时可能需要等待
- 部分期刊的 ISSN 可能需要更新

## 贡献指南

欢迎提交 Issue 和 Pull Request！

## 许可证

[MIT License](LICENSE)

## 更新日志

查看 [CHANGELOG.md](./CHANGELOG.md) 了解版本更新历史。
