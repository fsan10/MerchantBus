"""CatBus-inspired registries: stable commands and discoverable capabilities."""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class Platform:
    code: str
    display_name: str
    aliases: tuple[str, ...] = ()

@dataclass(frozen=True)
class Operation:
    resource: str
    action: str
    mutates: bool
    demo_supported: bool
    summary: str

    @property
    def key(self) -> str:
        return f"{self.resource}.{self.action}"

PLATFORMS = (
    Platform("douyin", "抖店", ("dy", "抖店", "抖音")),
    Platform("jd", "京麦", ("jingmai", "京东", "京麦")),
    Platform("tmall", "天猫", ("taobao", "天猫", "淘宝")),
    Platform("xhs", "小红书商家", ("xiaohongshu", "小红书")),
    Platform("wechat_channels", "视频号小店", ("wechat", "视频号", "微信小店")),
    Platform("kuaishou", "快手小店", ("ks", "快手")),
    Platform("pdd", "拼多多商家", ("pinduoduo", "拼多多")),
)

OPERATIONS = (
    Operation("shop", "list", False, True, "查看可访问店铺"),
    Operation("product", "list", False, True, "商品列表"),
    Operation("product", "get", False, True, "商品详情及 SKU"),
    Operation("product", "on-shelf", True, True, "商品上架"),
    Operation("product", "off-shelf", True, True, "商品下架"),
    Operation("product", "price", True, True, "SKU 改价"),
    Operation("product", "create", True, False, "创建商品草稿"),
    Operation("stock", "get", False, True, "SKU 库存查询"),
    Operation("stock", "set", True, True, "SKU 库存修改"),
    Operation("coupon", "list", False, True, "优惠券列表"),
    Operation("coupon", "create", True, True, "创建优惠券活动"),
    Operation("coupon", "terminate", True, True, "结束优惠券活动"),
    Operation("order", "list", False, False, "订单查询"),
    Operation("order", "get", False, False, "订单详情"),
    Operation("promotion", "list", False, False, "促销活动查询"),
)

_BY_PLATFORM = {key.casefold(): p for p in PLATFORMS for key in (p.code, *p.aliases)}
_BY_OPERATION = {op.key: op for op in OPERATIONS}


def get_platform(name: str) -> Platform | None:
    return _BY_PLATFORM.get(name.strip().casefold())


def get_operation(key: str) -> Operation | None:
    return _BY_OPERATION.get(key)


def platform_capabilities(p: Platform) -> dict:
    return {
        "id": p.code, "name": p.display_name, "aliases": list(p.aliases),
        "authentication": "demo-local (real profile integration planned)",
        "capabilities": [{
            "command": op.key,
            "writes": op.mutates,
            "demo": "implemented" if op.demo_supported else "planned",
            "live": "not_implemented",
            "summary": op.summary,
        } for op in OPERATIONS],
    }
