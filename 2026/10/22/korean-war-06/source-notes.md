# 朝鲜战争06史料与验证记录

核查日期：2026-10-22。只记录本次实际通过 web 搜索或打开看到的材料，不把书目记录等同于全文。

## 来源及用途

| 条目 | URL | 实际访问状态与用途 |
| --- | --- | --- |
| a33 Appleman, Chapter XXXIII: The Chinese Intervene | https://webdoc.sub.gwdg.de/ebook/p/2005/CMH_2/www.army.mil/cmh-pg/books/korea/20-2-1/sn33.htm | 大学镜像章节HTML已打开，核查所引段落及地图链接；美国陆军官方战史，事实整理与敌方判断分开使用。 |
| a34 Appleman, Chapter XXXIV: Unsan | https://webdoc.sub.gwdg.de/ebook/p/2005/CMH_2/www.army.mil/cmh-pg/books/korea/20-2-1/sn34.htm | 大学镜像章节HTML已打开，核查所引段落及地图链接；美国陆军官方战史，事实整理与敌方判断分开使用。 |
| m2 Mossman, Chapter II: The Forces and the Plans | https://webdoc.sub.gwdg.de/ebook/p/2005/CMH_2/www.army.mil/cmh-pg/books/korea/ebb/ch2.htm | 大学镜像章节HTML已打开，核查所引段落及地图链接；美国陆军官方战史，事实整理与敌方判断分开使用。 |
| m3 Mossman, Chapter III: The Enemy | https://webdoc.sub.gwdg.de/ebook/p/2005/CMH_2/www.army.mil/cmh-pg/books/korea/ebb/ch3.htm | 大学镜像章节HTML已打开，核查所引段落及地图链接；美国陆军官方战史，事实整理与敌方判断分开使用。 |
| m4 Mossman, Chapter IV: The Battle of the Ch'ongch'on | https://webdoc.sub.gwdg.de/ebook/p/2005/CMH_2/www.army.mil/cmh-pg/books/korea/ebb/ch4.htm | 大学镜像章节HTML已打开，核查所引段落及地图链接；美国陆军官方战史，事实整理与敌方判断分开使用。 |
| m6 Mossman, Chapter VI: Disengagement in the West | https://webdoc.sub.gwdg.de/ebook/p/2005/CMH_2/www.army.mil/cmh-pg/books/korea/ebb/ch6.htm | 大学镜像章节HTML已打开，核查所引段落及地图链接；美国陆军官方战史，事实整理与敌方判断分开使用。 |
| m8 Mossman, Chapter VIII: Redeployment South | https://webdoc.sub.gwdg.de/ebook/p/2005/CMH_2/www.army.mil/cmh-pg/books/korea/ebb/ch8.htm | 大学镜像章节HTML已打开，核查所引段落及地图链接；美国陆军官方战史，事实整理与敌方判断分开使用。 |
| unsan 美陆军云山战斗回顾，2016 | https://www.army.mil/article/177954/disaster_at_unsan_in_1950_soldiers_faced_chinese_forces_during_the_korean_war | 已打开可读正文；用于对应正文近邻引用所标明的事件、命令、部署或统计。 |
| dpaa DPAA云山战斗与失踪人员核查 | https://dpaa-mil.sites.crmforce.mil/dpaaFamWebInBattleOfUnsan | 已打开可读正文；用于对应正文近邻引用所标明的事件、命令、部署或统计。 |
| pakchon Australian War Memorial: Pakchon, 5 November 1950 | https://www.awm.gov.au/visit/exhibitions/korea/operations/pakchon | 已打开可读正文；用于对应正文近邻引用所标明的事件、命令、部署或统计。 |
| 113 中国军网：第113师三所里、龙源里行动的部队纪念叙述 | https://www.81.mil.cn/yw_208727/16284948.html | 仅检索结果可见，正文直读未成功；仅辅助核对，不单独承担战术细节证据。 |
| intervention Richard W. Stewart, The Chinese Intervention，官方战役册 | https://www.govinfo.gov/content/pkg/GOVPUB-D114-PURL-gpo111375/pdf/GOVPUB-D114-PURL-gpo111375.pdf | 已打开可读正文；用于对应正文近邻引用所标明的事件、命令、部署或统计。 |
| campaign 美陆军朝鲜战争战役阶段概述 | https://history.army.mil/Research/Reference-Topics/Army-Campaigns/Brief-Summaries/Korean-War/ | 仅检索结果可见，正文直读未成功；仅辅助核对，不单独承担战术细节证据。 |

## 争议和证据限制

中美战役分期不同。中国第113师纪念叙述与美军军史路线对读，不采用精确到分钟的提前量。美陆军战役概述与中国军网113师文章本次只检索可见，未将其冒充已读全文。DPAA网页个别地理概述不采用。没有用双方歼敌估算相加得到真实死亡人数。

正文地图采用原始军史章节内地图阅读链接，附具体地名、方向和时间指引。未复制版权不明的历史地图，未生成假地图。

## 落盘前双扫描

1. 草稿：`/private/tmp/korea-06-draft.md`，由 apply_patch 写入，尚未触及 source 时先扫描。
2. anti-ai-tone：执行 `python3 /Users/magicliang/.codex/skills/anti-ai-tone/scripts/check_prose.py --profile essay --json /private/tmp/korea-06-draft.md`，0 个错误、1 个警告。人工复核：冒号主要为导航、标题与参考定义；长句主体明确；地名连接线用于路线；07的跑道、弹药、仓库均为字面军事设施，不是混用比喻。05开头冗长句已改。未以自动零错误代替人工读稿。
3. 随后 anti-persona-fabrication：逐段核查叙述身份、虚构体感与说书过门，并用常见第一人称/体感/说书词扫描；0 命中。历史人物及军事事件描述不伪装作者亲历，没有虚构对话。
4. 完成上述顺序后，使用 apply_patch 新建正式文章。原始扫描结果保存在本素材目录 `scan-evidence.json`。

## 交付界限

正文汉字数（排除frontmatter、导航和参考资料）：8210。未运行构建、提交、推送或部署；由父任务进行整组集成验证。
