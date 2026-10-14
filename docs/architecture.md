# MerchantBus V0.1 架构

目标是 CatBus 风格独立商家工具。**不是 CatBus Fork，也不是 mock_coffice 的分支。**

### 调用链

- Codex / OpenCode / 终端 / 飞书机器人
- CLI / MCP Server
- Gateway（参数校验、dry-run、显式确认与业务审批注入）
- Adapter Protocol
- 本地 DemoAdapter 或未来真实平台适配器
- 会话提供者（例如授权的 Cloak/CDP 环境）
- 平台 WebAPI

### 核心约束

- 所有平台复用同一套命令和 JSON 数据契约。
- 当前真实平台适配器数量为 0；绝不声称已经连接实际店铺。
- `--demo` 仅操作本地 JSON，业务返回标注 `executed_remotely=false`。
- Demo 写操作使用 `--yes` + `--request-id`；本地幂等缓存**不适用于生产并发**。
- MCP V0.1 只开放只读和预览工具，真实修改功能不予暴露。
- 后续必须补充分店铺授权、审批、生产幂等锁、超时回查和 UNKNOWN 状态。

### 将来如何集成 mock_coffice

通过 CLI 进程、MCP 或 HTTP 服务调用，避免直接 import mock_coffice 内部模块。需要在集成层建立公司商品和平台商品 SKU 映射，并将 mock_coffice 的自动化运行 ID 传入 request-id。
