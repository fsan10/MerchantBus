"""Offline simulator for seven platforms; NEVER sends network requests."""
from __future__ import annotations
import copy
import hashlib
import json
import os
from pathlib import Path
from decimal import Decimal, InvalidOperation
from datetime import date
from typing import Any
from uuid import uuid4

from ..errors import MerchantBusError
from ..registry import PLATFORMS


def initial_state() -> dict:
    return {
        "platforms": {
            p.code: {
                "shops": {
                    "DEMO-STORE": {
                        "name": f"{p.display_name} 演示店铺",
                        "products": {
                            "P100": {"id": "P100", "name": "演示咖啡礼盒", "status": "on_shelf",
                                     "skus": {"S100": {"price": "59.90", "stock": 120}, "S101": {"price": "79.90", "stock": 32}}},
                            "P200": {"id": "P200", "name": "演示咖啡豆", "status": "off_shelf",
                                     "skus": {"S200": {"price": "39.90", "stock": 60}}},
                        },
                        "coupons": {
                            "C100": {"id": "C100", "name": "新人优惠", "amount": "5.00",
                                     "quantity": 100, "status": "active", "start": "2026-01-01", "end": "2027-12-31"}
                        },
                    }
                }
            } for p in PLATFORMS
        },
        "idempotency": {},
        "audit": [],
    }


def _positive_money(value: str) -> str:
    try:
        d = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise MerchantBusError("INVALID_PRICE", "金额必须是合法十进制数字")
    if not d.is_finite() or d <= 0 or d.as_tuple().exponent < -2:
        raise MerchantBusError("INVALID_PRICE", "金额必须大于零，最多两位小数")
    return f"{d:.2f}"


def _positive_int(value: Any, *, allow_zero: bool = False) -> int:
    try:
        number = int(value)
        if str(number) != str(value).strip():
            raise ValueError()
    except (TypeError, ValueError):
        raise MerchantBusError("INVALID_QUANTITY", "数量必须是整数")
    if number < 0 or (number == 0 and not allow_zero):
        raise MerchantBusError("INVALID_QUANTITY", "数量不能为负，优惠券数量须大于零")
    return number


class DemoAdapter:
    """Persistent local fixture; not concurrency-safe; never connects to merchant sites."""

    def __init__(self, state_file: str | Path):
        self.path = Path(state_file).expanduser()

    def reset(self) -> dict:
        state = initial_state()
        self._save(state)
        return {"state_file": str(self.path), "platform_count": len(state["platforms"]),
                "note": "已重置本地演示数据，未访问真实平台"}

    def _load(self) -> dict:
        if not self.path.exists():
            return initial_state()
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise MerchantBusError("DEMO_STATE_INVALID", f"无法解析本地演示状态：{type(exc).__name__}") from exc

    def _save(self, state: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_name(f".{self.path.name}.{uuid4().hex}.tmp")
        try:
            tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(tmp, self.path)
        finally:
            if tmp.exists():
                tmp.unlink()

    def invoke(self, *, platform: str, operation: str, shop: str,
               args: dict[str, Any], request_id: str | None) -> dict:
        state = self._load()
        if platform not in state["platforms"]:
            raise MerchantBusError("UNKNOWN_PLATFORM", f"平台不存在：{platform}")
        shops = state["platforms"][platform]["shops"]
        if operation == "shop.list":
            return {"items": [{"id": code, "name": data["name"]} for code, data in shops.items()]}
        if shop not in shops:
            raise MerchantBusError("SHOP_NOT_FOUND", f"演示店铺不存在：{shop}", "使用 --shop DEMO-STORE")
        data = shops[shop]
        args = {k: v for k, v in args.items() if v is not None}
        fingerprint = json.dumps({"platform": platform, "shop": shop, "operation": operation,
                                  "args": args}, sort_keys=True, ensure_ascii=False)
        digest = hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()
        key = f"{platform}:{shop}:{request_id}" if request_id else None
        if key and key in state["idempotency"]:
            record = state["idempotency"][key]
            if record["fingerprint"] != digest:
                raise MerchantBusError("IDEMPOTENCY_CONFLICT", "同一 request-id 已用于不同业务操作")
            return copy.deepcopy(record["result"]) | {"deduplicated": True}

        products = data["products"]
        coupons = data["coupons"]
        modified = False
        if operation == "product.list":
            items = list(products.values())
            status = args.get("status")
            if status:
                items = [x for x in items if x["status"] == status]
            page, limit = args.get("page", 1), args.get("limit", 20)
            result = {"items": copy.deepcopy(items[(page-1)*limit:page*limit]), "total": len(items),
                      "page": page, "limit": limit}
        elif operation in {"product.get", "product.on-shelf", "product.off-shelf", "product.price", "stock.get", "stock.set"}:
            item_id = args.get("item_id")
            if not item_id or item_id not in products:
                raise MerchantBusError("PRODUCT_NOT_FOUND", "商品 ID 不存在", "演示商品 ID：P100 或 P200")
            product = products[item_id]
            if operation == "product.get":
                result = {"product": copy.deepcopy(product)}
            elif operation in {"product.on-shelf", "product.off-shelf"}:
                desired = "on_shelf" if operation == "product.on-shelf" else "off_shelf"
                old = product["status"]
                product["status"] = desired
                result = {"item_id": item_id, "before": old, "after": desired, "verified": True}
                modified = True
            else:
                sku_id = args.get("sku_id")
                if not sku_id or sku_id not in product["skus"]:
                    raise MerchantBusError("SKU_NOT_FOUND", "SKU ID 不存在", "先查询 product get 获取有效 SKU")
                sku = product["skus"][sku_id]
                if operation == "stock.get":
                    result = {"item_id": item_id, "sku_id": sku_id, "stock": sku["stock"]}
                else:
                    field = "price" if operation == "product.price" else "stock"
                    new_value = (_positive_money(args.get("value")) if field == "price" else
                                 _positive_int(args.get("value"), allow_zero=True))
                    old = sku[field]
                    sku[field] = new_value
                    result = {"item_id": item_id, "sku_id": sku_id, "field": field,
                              "before": old, "after": new_value, "verified": True}
                    modified = True
        elif operation == "coupon.list":
            result = {"items": copy.deepcopy(list(coupons.values())), "total": len(coupons)}
        elif operation == "coupon.create":
            amount = _positive_money(args.get("amount"))
            quantity = _positive_int(args.get("quantity"))
            start, end = args.get("start"), args.get("end")
            if not args.get("name") or not start or not end:
                raise MerchantBusError("COUPON_FIELDS_REQUIRED", "需要 --name、--amount、--quantity、--start、--end")
            try:
                if date.fromisoformat(start) > date.fromisoformat(end):
                    raise ValueError("end_before_start")
            except ValueError:
                raise MerchantBusError("INVALID_DATE", "日期必须为 YYYY-MM-DD 且开始日期不能晚于结束日期")
            coupon_id = "C" + uuid4().hex[:10].upper()
            coupons[coupon_id] = {"id": coupon_id, "name": args["name"], "amount": amount,
                                  "quantity": quantity, "start": start, "end": end, "status": "active"}
            result = {"coupon": copy.deepcopy(coupons[coupon_id]), "verified": True}
            modified = True
        elif operation == "coupon.terminate":
            coupon_id = args.get("coupon_id")
            if not coupon_id or coupon_id not in coupons:
                raise MerchantBusError("COUPON_NOT_FOUND", "优惠券 ID 不存在")
            old = coupons[coupon_id]["status"]
            coupons[coupon_id]["status"] = "terminated"
            result = {"coupon_id": coupon_id, "before": old, "after": "terminated", "verified": True}
            modified = True
        else:
            raise MerchantBusError("UNSUPPORTED_CAPABILITY", f"演示适配器暂不支持 {operation}")

        if modified:
            result = result | {"mode": "demo", "executed_remotely": False, "deduplicated": False}
            state["audit"].append({"request_id": request_id, "platform": platform, "shop": shop,
                                   "operation": operation, "input_hash": digest,
                                   "demo_only": True})
            state["idempotency"][key] = {"fingerprint": digest, "result": copy.deepcopy(result)}
            self._save(state)
        else:
            result = result | {"mode": "demo", "executed_remotely": False}
        return result
