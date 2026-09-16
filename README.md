# 旅行手册网页 · 单文件 + Cloudflare Workers

按小红书教程（[`docs/xhs-video-analysis.md`](docs/xhs-video-analysis.md)）的方法复刻的一份可分享旅行行程网页。

一个链接发到群里，同行的人点开就能看 —— 不用装 App、不用登录、不用加好友。手机、平板、电脑都行。

当前行程：**🇮🇹🇮🇸 2026 意大利＋冰岛**（2026.9.25–10.8 · 佛罗伦萨 · 多洛米蒂 · 冰岛南岸）。

## 目录结构

```text
.
├── italy-iceland/
│   └── index.html          # 本次行程手册：单文件、零外部依赖（由 Excel 生成）
├── hokkaido/
│   └── index.html          # 上一版北海道示例（保留参考）
├── scripts/
│   └── generate_italy_iceland.py   # 从两份 Excel 重新生成页面
├── wrangler.jsonc          # Cloudflare Workers 静态资产配置（Worker 名 = italy-iceland）
├── README.md               # 本文件
└── docs/
    └── xhs-video-analysis.md   # 原视频教程的完整拆解文档
```

一个仓库可以放多个行程页面：再去一趟就新建一个 `<行程名>/index.html` 目录。想让每个行程有独立子域，就为每个目录建一个独立的 Worker（各自一份 `wrangler.jsonc`）。

## 页面里有什么

内容**仅**来自两份 Excel：

1. `2026意大利冰岛行程_复核补全版.xlsx` —— 详细行程、核对说明、国际航段
2. `行李物品清单2.xlsx` —— 行李物品清单（只读展示）

- **「此刻关注 · NOW」卡片** —— 自动找出下一个还没发生的行程事件，配每秒跳动的大号倒计时。
- **章节导航** —— 吸顶 pill 标签：总览 / 航班 / 每日行程 / 复核说明 / 行李清单。
- **行程总览** —— 内联 SVG 意大利→冰岛路线概览 + 按天摘要。
- **航班** —— Excel 中出现的 VCE→KEF、FI454、HU7912 航段。
- **逐日行程** —— 左边时间、右边内容的时间轴，含预约要求徽章与执行提示。
- **复核说明** —— Excel《核对说明》表全文。
- **行李清单** —— 只读、不可勾选，按分类列出物品与数量。
- **自动深色模式**、**响应式**、**零外部依赖**（CSS / JS / SVG 全部内联）。

未在 Excel 出现的模块（如实用贴士、可勾选待办、去程抵意航班等）**不会**出现在页面上。

## 内容与安全约束

页面是公开的，所以：

- **不写**确认号、证件号、房间号 —— 即使 Excel 里有也不展示。
- 页面永远保持终稿状态，不放修改日志或版本说明。

## 本地预览

```bash
python3 -m http.server 47821 --directory italy-iceland
# 打开 http://127.0.0.1:47821
```

从 Excel 重新生成页面（需 `openpyxl`）：

```bash
pip install openpyxl
python3 scripts/generate_italy_iceland.py
```

## 部署到 Cloudflare Workers（GitHub 连接，push 即上线）

1. 把本仓库推送到 GitHub，生产分支 `main`。
2. Cloudflare Dashboard → **Workers & Pages** → **Create** → **Workers** → **Import a repository**：
   - 生产分支选 `main`
   - **Build command：留空**
   - **Deploy command：`npx wrangler deploy`**
3. 去 **Workers & Pages → 该 Worker → Settings → Rename**，改成 `italy-iceland`（与 `wrangler.jsonc` 里的 `name` 一致），网址即为：

   ```text
   https://italy-iceland.<你的Cloudflare账号子域>.workers.dev
   ```

4. 之后每次改 `italy-iceland/index.html` 并 push 到 `main`，Cloudflare 会自动部署。

<!-- last verified: 2026-09-16 -->
