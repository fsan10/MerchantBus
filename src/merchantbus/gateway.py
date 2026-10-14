"""Dispatch shared by CLI, MCP and future HTTP servers."""
from __future__ import annotations
from pathlib import Path
from typing import Any
from .adapters.base import MerchantAdapter
from .adapters.demo import DemoAdapter
from .errors import MerchantBusError
from .registry import get_operation, get_platform

DEFAULT_STATE = Path(".merchantbus/demo-state.json")

class Gateway:
    def __init__(self, *, adapters: dict[str, MerchantAdapter] | None = None,
                 authorize_write=None):
        # No live adapters shipped: a real adapter must be explicit and approved.
        self.adapters = adapters or {}
        self.authorize_write = authorize_write

    def execute(self, *, platform: str, operation: str, shop: str,
                args: dict[str, Any] | None = None, demo: bool = False,
                state_file: str | Path = DEFAULT_STATE,
                dry_run: bool = False, yes: bool = False,
                request_id: str | None = None) -> dict:
        p = get_platform(platform)
        if p is None:
            raise MerchantBusError("UNKNOWN_PLATFORM", f"未知平台：{platform}", "运行 merchantbus platforms")
        op = get_operation(operation)
        if op is None:
            raise MerchantBusError("UNKNOWN_COMMAND", f"未知业务操作：{operation}", "运行 merchantbus platforms")
        if not shop and operation != "shop.list":
            raise MerchantBusError("SHOP_REQUIRED", "必须指定 --shop", "演示模式使用 --shop DEMO-STORE")
        values = {k: v for k, v in (args or {}).items() if v is not None}
        if operation in {"product.get", "product.on-shelf", "product.off-shelf", "product.price", "stock.get", "stock.set"} and not values.get("item_id"):
            raise MerchantBusError("ITEM_ID_REQUIRED", "此命令必须指定 --item-id")
        if operation in {"product.price", "stock.get", "stock.set"} and not values.get("sku_id"):
            raise MerchantBusError("SKU_ID_REQUIRED", "此命令必须指定 --sku-id")
        if operation in {"product.price", "stock.set"} and values.get("value") is None:
            raise MerchantBusError("VALUE_REQUIRED", "必须指定 --value")
        if operation == "coupon.terminate" and not values.get("coupon_id"):
            raise MerchantBusError("COUPON_ID_REQUIRED", "必须指定 --coupon-id")
        if values.get("page", 1) < 1 or not (1 <= values.get("limit", 20) <= 100):
            raise MerchantBusError("INVALID_PAGINATION", "page >= 1 且 limit 在 1~100 范围内")
        if op.mutates:
            if dry_run:
                return {"mode": "local_preview", "executed": False,
                        "platform": p.code, "operation": op.key, "shop": shop,
                        "args": values, "hint": "预览不访问远端，也不修改本地演示数据"}
            if not yes:
                raise MerchantBusError("CONFIRM_REQUIRED", "写操作需要显式 --yes", "先执行 --dry-run 预览")
            if not request_id:
                raise MerchantBusError("REQUEST_ID_REQUIRED", "写操作需要唯一 --request-id", "避免重复创建操作")
        if demo:
            if not op.demo_supported:
                raise MerchantBusError("UNSUPPORTED_CAPABILITY", f"尚未实现演示操作：{op.key}")
            return DemoAdapter(state_file).invoke(platform=p.code, operation=op.key,
                                                   shop=shop, args=values, request_id=request_id)
        adapter = self.adapters.get(p.code)
        if adapter is None:
            raise MerchantBusError("LIVE_NOT_IMPLEMENTED", f"{p.display_name} 商家 WebAPI 尚未逆向验证并接入",
                                   "先开发经过授权测试和远端状态回查的独立平台适配器")
        if op.mutates and not (self.authorize_write and self.authorize_write(p.code, op.key, shop, values)):
            raise MerchantBusError("APPROVAL_REQUIRED", "生产写操作需要服务端真实业务审批")
        return adapter.invoke(platform=p.code, operation=op.key, shop=shop,
                              args=values, request_id=request_id)
