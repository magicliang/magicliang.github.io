# 朝鲜战争10：来源与核对记录

核查日期：2026-10-22。本文为独立研究写作，未将搜索摘要伪装成整部原著通读。以下链接与正文引用键一致；事实解释之外的分析属于作者综合判断。

## 来源阅读状态与支持范围

| 来源 | 实际阅读状态 | 支持范围与限制 |
| --- | --- | --- |
| [airwar](https://www.pacaf.af.mil/7th-Air-Force/7th-AF-Units/The-Korean-Air-War/) | 已核验官方网页正文搜索摘录 | 早期制空及对地支援背景；未采用未经跨方统一的击落比。 |
| [soviet](https://www.nationalmuseum.af.mil/Visit/Museum-Exhibits/Fact-Sheets/Display/Article/196389/soviet-pilots-over-mig-alley/) | 已核验博物馆正文搜索摘录 | 苏联飞行员1950年11月投入、基地与活动限制。 |
| [hallion](https://press-files.anu.edu.au/downloads/press/n5114/html/ch06.xhtml?page=16&referer=) | 已读ANU章节相关全文段落 | 喷气式空战、遮断限制、电厂及1953水坝行动。章节个别中国入战日期、Cherokee年代叙述不一致，未采用。 |
| [naval-start](https://www.history.navy.mil/research/library/online-reading-room/title-list-alphabetically/h/history-us-naval-operations-korea/chapter3-war-begins.html) | 已核验美国海军史章节搜索正文 | 开战初海军多国编成、日本基地及舰载航空支援。 |
| [rail](https://www.81.cn/js_208592/9928868.html) | 已核验中国军网完整搜索正文相关段；直接打开超时 | 1951年5月后勤指挥、8月联合铁路指挥、12月前方运输抢修防空统合。 |
| [mines](https://www.history.navy.mil/content/history/nhhc/about-us/leadership/director/directors-corner/h-grams/h-gram-050/h-050-1.html) | 已核验官方正文搜索摘录 | 水雷及近岸风险；不采用无完整清单支持的海军总损失。 |
| [wonsan](https://www.history.navy.mil/content/history/nhhc/about-us/leadership/director/directors-corner/h-grams/h-gram-058/h-058-2.html) | 已核验官方正文搜索摘录；直接打开超时 | 1951年2月16日起元山封锁及铁路公路节点作用。 |
| [logistics](https://history.army.mil/portals/143/Images/Publications/catalog/68-3.pdf) | 已核验PDF检索文本相关段 | 釜山主要港口与供应基地、日本后送；未宣称逐页通读整卷。 |
| [haven](https://www.history.navy.mil/research/histories/ship-histories/danfs/h/haven.html) | 已核验舰史正文搜索结果 | 1950年复役、韩国港口接收伤员、1952改装直升机甲板。 |
| [inflation](https://history.state.gov/historicaldocuments/frus1952-54v15p1/d42) | 已打开完整短文件 | 1952年2月27日通胀、韩元提取、救济到货不确定的手写附注。 |
| [aid](https://history.state.gov/historicaldocuments/frus1952-54v15p1/d83) | 已核验FRUS文书搜索正文 | 经济代表团目标与韩国外汇主权争议。 |
| [reconstruction](https://history.state.gov/historicaldocuments/frus1952-54v15p2/d699) | 已核验FRUS文书搜索正文 | 十六师扩二十师的经济负担；不把重建预算等同到货。 |

## 写作流程与证据

- 已在本回合加载 blog-editor、knowledge-evolution、anti-ai-tone及prose-quality、anti-persona-fabrication；先写 /private/tmp/korea-10-draft.md。
- 落盘前先执行 anti-ai-tone：`python3 /Users/magicliang/.codex/skills/anti-ai-tone/scripts/check_prose.py --profile essay --json /private/tmp/korea-10-draft.md`。
- 上述检查完成后，再按 anti-persona-fabrication 人工检查正文：无作者第一人称经历、无虚构对话/内心、无对国家或抽象概念赋予人格、无读者陪伴和说书人话术。正则辅助扫描“我认为|我发现|我们|笔者|陪你|你可能会问|让我们”为零命中。
- 脚本保留1项mixed_metaphors警告：战场、弹药、发动机、仓库均为本文真实军事对象，逐项复核为误报，无借喻。
- 顺序双扫描通过后，才用 apply_patch 将同一稿件写入 source/_posts；未运行提交、构建、推送或部署。

最终结构扫描原始输出：

```json
{
  "profile": "essay",
  "han": 6764,
  "errors": 0,
  "warnings": 1,
  "findings": [
    {
      "code": "mixed_metaphors",
      "severity": "warning",
      "line": 36,
      "message": "八百字内混用 3 套借喻：仓储租赁、机器器官、生死战争",
      "excerpt": "战场、弹药、发动机、仓库"
    }
  ]
}
```

## 交付边界

本文不提供未经核对的全国死亡总数、营地自由意愿比例或跨方损失比。未生成历史地图；既有权威地图/照片仅链接原出处。页面构建、最终链接和本地提交由主代理统一验证，本记录不代替这些验证。
