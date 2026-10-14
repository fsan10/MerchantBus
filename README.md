# 🚌 MerchantBus · 商家巴士

**七大电商平台商家端统一 CLI / MCP Demo**

面向抖店、京麦、天猫、小红书商家、视频号小店、快手小店、拼多多商家。参考 [CatBus](https://github.com/cv-cat/catbus) 的统一命令、平台注册表、能力发现和 JSON 输出设计，但这是**独立的 Python 实现**，没有复制 CatBus 平台 API，也不依赖 `mock_coffice`。

> **V0.1 是独立可运行的离线演示项目，不是已经逆向完成的真实商家 WebAPI。** 使用 `--demo` 时，修改只发生在 `.merchantbus/demo-state.json` 本地文件；真实模式全部返回 `LIVE_NOT_IMPLEMENTED`，不会操作真实商品、价格或优惠券。

## 安装

要求 Python >= 3.10。在仓库根目录运行：

```bash
python -m pip install -e .
merchantbus doctor
merchantbus platforms
merchantbus platforms douyin
```

或者不安装，用 `PYTHONPATH=src python -m merchantbus platforms`。Windows PowerShell 先运行 `$env:PYTHONPATH = 'src'`。

## 七个平台统一命令

```bash
# 查询平台支持情况
merchantbus platforms jd

# 查询商品、SKU、库存和优惠券（均为离线 Demo）
merchantbus douyin product list --shop DEMO-STORE --demo
merchantbus jd product get --shop DEMO-STORE --item-id P100 --demo
merchantbus xhs stock get --shop DEMO-STORE --item-id P100 --sku-id S100 --demo
merchantbus wechat_channels coupon list --shop DEMO-STORE --demo

# 本地商品下架预览：不修改任何数据
merchantbus douyin product off-shelf --shop DEMO-STORE --item-id P100 --dry-run

# 真正执行一次本地模拟修改：不会访问外部平台
merchantbus douyin product off-shelf --shop DEMO-STORE --item-id P100 --demo --yes --request-id TEST-OFF-001
merchantbus douyin product get --shop DEMO-STORE --item-id P100 --demo

# 模拟商品价格、库存修改
merchantbus jd product price --shop DEMO-STORE --item-id P100 --sku-id S100 --value 69.90 --demo --yes --request-id TEST-PRICE-001
merchantbus jd stock set --shop DEMO-STORE --item-id P100 --sku-id S100 --value 20 --demo --yes --request-id TEST-STOCK-001

# 创建本地模拟优惠券
merchantbus xhs coupon create --shop DEMO-STORE --name 周末券 --amount 10 --quantity 100 --start 2026-10-01 --end 2026-10-31 --demo --yes --request-id TEST-COUPON-001

# 重置本地演示数据
merchantbus demo reset --yes
```

平台代号：`douyin`、`jd`、`tmall`、`xhs`、`wechat_channels`、`kuaishou`、`pdd`。中文别名也支持。

### 能力状态

`merchantbus platforms` 会明确列出每种操作的 `demo=implemented/planned` 与 `live=not_implemented`，因此 AI 不会误以为所有平台都已经有真正的 WebAPI。

统一 JSON 包含：`ok`、`schema_version`、`platform`、`command`、`data`、`error`。失败时返回非零退出码和可供 AI 处理的 `error.code`。

模拟写操作要求 `--yes` 与唯一 `--request-id`。相同请求 ID 和参数重复调用返回 `deduplicated=true`；相同 ID 传入不同负载返回 `IDEMPOTENCY_CONFLICT`。**这种本地 JSON 幂等只适用于单进程 Demo，不能代替生产数据库事务和并发锁。**

## MCP

```bash
python -m pip install -e '.[mcp]'
python -m merchantbus.mcp_server
```

基于 Python MCP SDK 的 stdio 服务，目前提供 `merchant_platforms`、`merchant_capabilities`、`merchant_demo_products`、`merchant_preview_product_action`。只读和预览，**不开放真实写工具**。

## 架构和目录

```text
src/merchantbus/
  cli.py                  CLI 命令解析与 JSON 输出
  registry.py             平台和能力注册表
  gateway.py              统一校验、预览、写操作显式确认
  errors.py               标准错误码
  adapters/base.py        未来真实平台 WebAPI 适配器协议
  adapters/demo.py        离线七平台本地模拟实现
  mcp_server.py           可选只读 MCP
tests/test_commands.py    19 项离线单元测试
docs/architecture.md     架构及未来集成 mock_coffice 说明
docs/adapter-contract.md 合规商家 WebAPI 适配器接入规则
```

## 测试

```bash
python -m unittest discover -s tests -v
```

本项目不包含自动触发的 GitHub Actions Workflow，不消耗已有项目的 CI 配额。

## 后续工作

首先选择已授权的一个测试抖店，分析商品列表 / 详情 / 上下架的正常 WebAPI 调用链，完成独立适配器和远端状态回查。之后逐平台添加能力，不应绕过验证码、人机验证和平台权限约束。将来可通过 CLI 或 MCP 与 `mock_coffice` 工作台集成，**无需合并原项目源码**。

## License

MIT。另见 `LICENSE`。
