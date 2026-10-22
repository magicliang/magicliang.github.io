# 朝鲜战争07史料与验证记录

核查日期：2026-10-22。只记录本次实际通过 web 搜索或打开看到的材料，不把书目记录等同于全文。

## 来源及用途

| 条目 | URL | 实际访问状态与用途 |
| --- | --- | --- |
| 1 Ebb and Flow，第5章：The Battle of the Changjin Reservoir | https://webdoc.sub.gwdg.de/ebook/p/2005/CMH_2/www.army.mil/cmh-pg/books/korea/ebb/ch5.htm | 大学镜像章节HTML已打开，核查所引段落及地图链接；美国陆军官方战史，事实整理与敌方判断分开使用。 |
| 2 第3章：The Enemy | https://webdoc.sub.gwdg.de/ebook/p/2005/CMH_2/www.army.mil/cmh-pg/books/korea/ebb/ch3.htm | 大学镜像章节HTML已打开，核查所引段落及地图链接；美国陆军官方战史，事实整理与敌方判断分开使用。 |
| 3 第7章：Concentration at Hungnam | https://webdoc.sub.gwdg.de/ebook/p/2005/CMH_2/www.army.mil/cmh-pg/books/korea/ebb/ch7.htm | 大学镜像章节HTML已打开，核查所引段落及地图链接；美国陆军官方战史，事实整理与敌方判断分开使用。 |
| 4 第8章：Redeployment South | https://webdoc.sub.gwdg.de/ebook/p/2005/CMH_2/www.army.mil/cmh-pg/books/korea/ebb/ch8.htm | 大学镜像章节HTML已打开，核查所引段落及地图链接；美国陆军官方战史，事实整理与敌方判断分开使用。 |
| 5 Battle of Chosin Reservoir | https://dpaa-mil.sites.crmforce.mil/dpaaFamWebInChosinRsrv | 已打开可读正文；用于对应正文近邻引用所标明的事件、命令、部署或统计。 |
| 6 《中美军人亲历朝鲜战争：零下30度的长津湖血战》 | https://www.dswxyjy.org.cn/n1/2016/0226/c396983-28153370.html | 已打开可读正文；用于对应正文近邻引用所标明的事件、命令、部署或统计。 |
| 7 《志愿军三炸水门桥》 | https://www.dswxyjy.org.cn/n1/2022/0328/c244516-32385865.html | 已打开可读正文；用于对应正文近邻引用所标明的事件、命令、部署或统计。 |
| 8 Task Force Faith veteran remembers heroic leader | https://www.army.mil/article/99795/Task_Force_Faith_veteran_remembers_heroic_leader/ | 已打开可读正文；用于对应正文近邻引用所标明的事件、命令、部署或统计。 |
| 9 History of United States Naval Operations: Korea，第9章：Retreat to the South | https://www.history.navy.mil/research/library/online-reading-room/title-list-alphabetically/h/history-us-naval-operations-korea/chapter9-retreat-south.html | 检索索引可读相关段落；网页端点超时或502，未读全文；由Mossman第8章交叉核对。 |
| 10 The Hungnam and Chinnampo Evacuations | https://www.history.navy.mil/research/library/online-reading-room/title-list-alphabetically/h/the-hungnam-and-chinnampo-evacuations.html | 检索索引可读相关段落；网页端点超时或502，未读全文；由Mossman第8章交叉核对。 |
| 11 第1章：The Mission | https://webdoc.sub.gwdg.de/ebook/p/2005/CMH_2/www.army.mil/cmh-pg/books/korea/ebb/ch1.htm | 大学镜像章节HTML已打开，核查所引段落及地图链接；美国陆军官方战史，事实整理与敌方判断分开使用。 |
| 12 第2章：The Forces and the Plans | https://webdoc.sub.gwdg.de/ebook/p/2005/CMH_2/www.army.mil/cmh-pg/books/korea/ebb/ch2.htm | 大学镜像章节HTML已打开，核查所引段落及地图链接；美国陆军官方战史，事实整理与敌方判断分开使用。 |

## 争议和证据限制

水门桥美中叙述对空投、架桥日期不同，保留分歧；兴南难民统计区分兴南本港与元山、城津合计。海军两网页仅检索索引可读，直读失败，不计入全文来源。中文回忆文章对湖东部分战斗过程与美军记录不符，未采用麦克莱恩当场死亡、全体湖冰陷落等说法。气温与冻伤不能写为全战区统一值。核心战术细节以Mossman官方军史为主，中方原始战斗详报缺乏公开全文，属于来源不对称。

正文地图采用原始军史章节内地图阅读链接，附具体地名、方向和时间指引。未复制版权不明的历史地图，未生成假地图。

## 落盘前双扫描

1. 草稿：`/private/tmp/korea-07-draft.md`，由 apply_patch 写入，尚未触及 source 时先扫描。
2. anti-ai-tone：执行 `python3 /Users/magicliang/.codex/skills/anti-ai-tone/scripts/check_prose.py --profile essay --json /private/tmp/korea-07-draft.md`，0 个错误、4 个警告。人工复核：冒号主要为导航、标题与参考定义；长句主体明确；地名连接线用于路线；07的跑道、弹药、仓库均为字面军事设施，不是混用比喻。05开头冗长句已改。未以自动零错误代替人工读稿。
3. 随后 anti-persona-fabrication：逐段核查叙述身份、虚构体感与说书过门，并用常见第一人称/体感/说书词扫描；0 命中。历史人物及军事事件描述不伪装作者亲历，没有虚构对话。
4. 完成上述顺序后，使用 apply_patch 新建正式文章。原始扫描结果保存在本素材目录 `scan-evidence.json`。

## 交付界限

正文汉字数（排除frontmatter、导航和参考资料）：8978。未运行构建、提交、推送或部署；由父任务进行整组集成验证。
