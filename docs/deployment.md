# 当前发布约定

自 2026-09-24 起，意大利／冰岛行程更新默认同步本 GitHub 仓库与硅谷服务器。香港保留历史网页，自动拉取定时器和 webhook 已按用户确认停用。

- 硅谷入口：http://43.130.36.14/italy-iceland/
- 部署文件：`/opt/travel-handbook/italy-iceland/index.html`
- 页面需与 GitHub 同一提交一致，发布后检查公网正文、脚本与文件 SHA256。
- 当前内容来源：`2026意大利冰岛行程（26日旧宫塔楼调整版）.xlsx`，提取快照为 `docs/itinerary-20260925.json`；9/26–27按用户确认的餐厅优先原则调整，执行安排见 `docs/itinerary-adjustments-20260925.json`，保留 Excel 行号。
- 用户确认：10/7 按主表 11:00 从 KEF 起飞、15:10 抵达 LHR T5；航班号未明确，不沿用旧 FI454 标识。9/29 用餐与返酒店重叠标待确认。
- 原行李清单保留。无开始时间的餐厅不得丢弃；跨午夜和次日抵达应使用正确日期。
- `scripts/generate_italy_iceland.py` 是旧版生成器，包含旧路径、旧航班时间及缺失开始时间即跳过的逻辑；不能直接用于重建当前页面。再次更新须以最新材料及现网页为基线，同时核对每日行程、航班卡片、倒计时数据与复核说明。

## 地点导航（2026-09-25）

- 明确地点名称使用 Apple 官方 Map Links：`https://maps.apple.com/?daddr=...`，不固定起点或交通方式，由地图从当前位置规划路线；iOS 打开 Apple 地图，开始逐向导航需在地图内确认。
- 地点与导航查询名在 `docs/navigation-places.json`；中文景点采用当地名称并添加国家/城市，未确认的酒店、接客点不推测地址。查询名不等同于已核验坐标，具体集合点仍按订单。
- `scripts/link_navigation.py` 只给可见文字加链接，保留现有参考链接和行程数据；可重复执行。修改现有映射后需同步修改已有链接（脚本跳过已有链接）。
- 验证：`python3 -m unittest discover -s tests`；发布前检查 13 天、134 条活动（含新增转场和用餐安排）、手机横向溢出、链接目的地及公网 SHA256。
- 协议依据：https://developer.apple.com/library/archive/featuredarticles/iPhoneURLScheme_Reference/MapLinks/MapLinks.html
