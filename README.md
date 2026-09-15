# 旅行手册网页 · 单文件 + Cloudflare Workers

按小红书教程（[`docs/xhs-video-analysis.md`](docs/xhs-video-analysis.md)）的方法复刻的一份可分享旅行行程网页。

一个链接发到群里，同行的人点开就能看 —— 不用装 App、不用登录、不用加好友。手机、平板、电脑都行。

当前行程：**🍁 北海道秋色自驾**（2026.9.25–9.29 · 4 人 · 新千岁进出 · 全程约 780 公里）。

## 目录结构

```text
.
├── hokkaido/
│   └── index.html          # 本次行程手册：单文件、零外部依赖
├── wrangler.jsonc          # Cloudflare Workers 静态资产配置（Worker 名 = hokkaido）
├── README.md               # 本文件
└── docs/
    └── xhs-video-analysis.md   # 原视频教程的完整拆解文档
```

一个仓库可以放多个行程页面：再去一趟就新建一个 `<行程名>/index.html` 目录。想让每个行程有独立子域，就为每个目录建一个独立的 Worker（各自一份 `wrangler.jsonc`）。

## 页面里有什么

- **「此刻关注 · NOW」卡片** —— 自动找出下一个还没发生的行程事件，配一个每秒跳动的大号倒计时；卡片底部带一条「当前待办」，点「去清单」直接跳到对应条目。
- **章节导航** —— 吸顶的 pill 标签，总览 / 航班 / 每日行程 / 待办清单 / 贴士。
- **行程总览** —— 内联的手绘感 SVG 北海道地图：按天用不同颜色画驾驶路线、标出每晚住哪、虚线航线、指北针与图例。
- **航班** —— 去程 / 回程两张卡片，只写航班号与起降时间。
- **逐日行程** —— 左边时间、右边内容的时间轴；每天顶部能展开一张真实可交互的 Google 地图，也能一键打开当天全部途经点的多点导航；每个地点都是虚线下划线，点一下直接唤起 Google 地图导航。
- **待办清单** —— 分组、编号、带状态徽章与预约入口链接。**故意做成只读、不可勾选**：勾选状态只存在各自浏览器里，同行的人看到的会不一样；办完一项跟 AI 说一声改页面，所有人的链接同时更新。
- **实用贴士** —— 时差、天气、靠左行驶、鹿、加油站关门时间、现金、紧急电话。
- **自动深色模式**（跟随系统）、**响应式**（手机单列 / 桌面并排）、**时区正确**（所有时间带时区，倒计时按北海道当地时间算，在任何时区打开都不会算错）。
- **零外部依赖**：CSS / JS / SVG 全部内联，离线也能看（只有展开的当日地图 iframe 需要联网）。

## 内容与安全约束

页面是公开的，所以：

- **不写**确认号、证件号、房间号、密码 —— 这些留在各自的邮箱和订单 App 里。机票凭确认号 + 姓氏就能改签甚至取消。
- 航班只写航班号与时间；酒店只写名称、地址、电话、入住 / 退房时间。
- 页面永远保持终稿状态，不放修改日志或版本说明。

## 本地预览

零依赖静态页面，随便起个静态服务器就行（端口挑个不常用的，避开 3000 / 5173 / 8080）：

```bash
python3 -m http.server 47821 --directory hokkaido
# 打开 http://127.0.0.1:47821
```

## 部署到 Cloudflare Workers（GitHub 连接，push 即上线）

一次性配置，之后再也不用管。**第 3 步建议坐到电脑前做，这是整条链路里唯一需要手动的环节。**

1. 注册 GitHub 账号（免费），把本仓库推上去，生产分支 `main`。
2. 注册 Cloudflare 账号（免费）。
3. Cloudflare Dashboard → **Workers & Pages** → **Create** → **Workers** → **Import a repository**：
   - 选本仓库，生产分支选 `main`
   - **Build command：留空**
   - **Deploy command：`npx wrangler deploy`**

   它会自动读到仓库根目录的 `wrangler.jsonc`，首次构建完成后网址就上线了。
4. **⚠️ 最大的坑：`workers.dev` 的网址前缀 = Cloudflare 后台里 Worker 的名字，不是 `wrangler.jsonc` 里的 `name`。**
   导入仓库时「名字」那栏默认会填成**仓库名**，所以网址会变成 `<仓库名>.<你的账号子域>.workers.dev`。
   去 **Workers & Pages → 点开这个 Worker → Settings → Rename**，改成 `hokkaido`（要和 `wrangler.jsonc` 里的 `name` 一致，否则后续构建会出问题），网址才会是：

   ```text
   https://hokkaido.<你的Cloudflare账号子域>.workers.dev
   ```

   这个字段只存在于 Cloudflare 账户里，仓库代码改不动它。只有在找不到 Rename 入口时才走「删掉重建」那条保底路径。
5. 之后每次改行程：改完 `hokkaido/index.html` push 进 `main` → GitHub webhook 通知 Cloudflare → 自动 `wrangler deploy` → 几十秒内全球生效，**链接永远不变**。

提交前可以本地校验一下配置识别得对不对：

```bash
npx wrangler deploy --dry-run
```

### 为什么不直接让 AI 跑 `wrangler deploy`

`wrangler login` 是交互式 OAuth，要弹浏览器回跳 `localhost`，在无头远程环境里天然走不通；无头环境下 `wrangler` 只认 `CLOUDFLARE_API_TOKEN` 环境变量。所以走 Git 连接部署最省事。

如果确实想让 AI 在会话里直接部署：给环境注入 `CLOUDFLARE_API_TOKEN`（权限只需 **Workers Scripts: Edit**），并放行 `api.cloudflare.com`。

## 成本

GitHub 免费；Cloudflare Workers 免费额度每天 10 万次请求，一趟旅行用不掉零头。**合计 0 元。**
