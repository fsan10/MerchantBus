# WebAPI Adapter 接入契约

生产接入前，在有权限的商家测试账号里按平台正常流程执行操作，观察真实请求及修改前后状态；不要提交 Cookie、令牌、签名、个人信息或商家机密数据。

步骤：
1. 核对平台、店铺、商品和 SKU 身份。
2. 确认请求结构、授权会话依赖及平台规则。
3. 实现 `MerchantAdapter.invoke(platform, operation, shop, args, request_id)`。
4. 返回稳定 JSON 和错误码，确保价格和 SKU 规格语义一致。
5. 写请求必须经过服务端授权和审批，保存业务请求幂等 ID。
6. 网络超时先查远端实际状态，再决定是否重试；不确定返回 REMOTE_STATE_UNKNOWN。
7. 使用脱敏 fixture 测试；确认生产可用后按单个平台、单项能力启用。

Demo 模式的 `verified=true` 仅表示本地模拟状态验证，`executed_remotely=false` 表明没有发生真正的平台操作。
