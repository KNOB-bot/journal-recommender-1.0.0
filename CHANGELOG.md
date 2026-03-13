# 更新日志

所有重要的更改都将记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
并且本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [1.0.0] - 2026-03-13

### 首次发布

本 Skill 提供一套完整的顶级期刊论文推荐系统，自动从 CrossRef API 检索经济学与管理学期刊最新论文，生成中英双语推荐报告。

### 新增功能

#### 核心功能

- ✅ 期刊文章检索（`scripts/journal_tracker.py`）
  - 从 CrossRef API 批量检索期刊最新文章
  - 支持按学科（economics/management）和级别（A/A-/B+/B）筛选
  - 自动跳过勘误、更正、书评等非研究性文章
  - 支持自定义时间范围和每本期刊最大检索数

- ✅ 报告生成（`scripts/generate_journal_report.py`）
  - 生成 Markdown 格式的精选推荐报告
  - 中英双语标题和摘要（Google Translate）
  - 综合评分算法（期刊级别 + 引用数 + 时间 + 摘要完整度）
  - Top 5 精华推荐
  - 检索期刊来源列表

- ✅ 智能去重
  - 自动对比最近 90 天内的历史推荐
  - 基于 DOI 去重，避免重复推荐

#### 期刊配置

- ✅ 基于主流经济学/管理学期刊分级方案
- ✅ 精简至约 50 本期刊（原 120+ 本）
- ✅ 按研究方向筛选（市场/区域一体化、城市经济、产业政策、创新等）
- ✅ 支持跨学科期刊（如 Regional Studies）

#### 文档

- ✅ `references/journal_ranking.json` - 期刊 ISSN 配置文件
- ✅ `references/usage_guide.md` - 使用指南

### 技术要点

#### CrossRef API

- 使用 `from-index-date` 参数过滤最近发表的文章
- 请求间隔 0.8 秒避免速率限制
- 支持超时重试和错误处理

#### 翻译功能

- 使用 Google Translate 非官方接口（无需 API Key）
- 自动翻译标题和摘要（最多 600 字符）
- 翻译失败时静默跳过，不影响报告生成

#### 评分算法

```python
综合评分 = 期刊级别分(40%) + 引用次数分(20%) + 新鲜度分(20%) + 摘要完整度分(20%)

其中：
- 期刊级别分: A=100, A-=80, B+=60, B=40
- 引用次数分: log(citations+1) / log(101) * 20
- 新鲜度分: max(0, 20 * (1 - days_old/90))
- 摘要完整度分: 有摘要且>300字=20, >100字=12, 有摘要=6, 无摘要=0
```

### 依赖要求

- Python 3.8+
- requests（必需）
- 无其他外部依赖

### 已知限制

- 翻译依赖 Google Translate 非官方接口，可能偶尔失败
- CrossRef API 有速率限制，检索过多期刊时可能需要等待
- 部分期刊的 ISSN 可能需要更新

---

## 版本说明

- **主版本号（Major）**：不兼容的 API 修改
- **次版本号（Minor）**：向下兼容的功能性新增
- **修订号（Patch）**：向下兼容的问题修正
