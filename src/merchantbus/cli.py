"""JSON-first, declarative multi-platform merchant command line interface."""
from __future__ import annotations
import argparse
import json
from typing import Sequence
from . import __version__
from .adapters.demo import DemoAdapter
from .errors import MerchantBusError, result_envelope
from .gateway import DEFAULT_STATE, Gateway
from .registry import OPERATIONS, PLATFORMS, get_platform, platform_capabilities


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="merchantbus", description="MerchantBus 多商家平台统一 CLI (Demo)")
    parser.add_argument("--version", action="version", version=__version__)
    roots = parser.add_subparsers(dest="root", required=True)
    platforms = roots.add_parser("platforms", help="查看七个平台的能力矩阵")
    platforms.add_argument("platform", nargs="?")
    roots.add_parser("doctor", help="运行环境和真实接口状态")
    demo_parser = roots.add_parser("demo", help="本地离线演示数据")
    demo_actions = demo_parser.add_subparsers(dest="demo_action", required=True)
    reset = demo_actions.add_parser("reset", help="重置本地演示数据")
    reset.add_argument("--state-file", default=str(DEFAULT_STATE))
    reset.add_argument("--yes", action="store_true", help="确认重置本地文件")
    for p in PLATFORMS:
        plat = roots.add_parser(p.code, aliases=list(p.aliases), help=p.display_name)
        resources = plat.add_subparsers(dest="resource", required=True)
        for resource in dict.fromkeys(o.resource for o in OPERATIONS):
            group = resources.add_parser(resource)
            actions = group.add_subparsers(dest="action", required=True)
            for op in (o for o in OPERATIONS if o.resource == resource):
                command = actions.add_parser(op.action, help=op.summary)
                command.add_argument("--shop", default="")
                command.add_argument("--demo", action="store_true", help="只使用本地演示数据，不请求平台")
                command.add_argument("--state-file", default=str(DEFAULT_STATE))
                command.add_argument("--item-id")
                command.add_argument("--sku-id")
                command.add_argument("--coupon-id")
                command.add_argument("--value", help="改价或库存的新值")
                command.add_argument("--name", help="优惠券名称")
                command.add_argument("--amount", help="优惠券金额（元）")
                command.add_argument("--quantity", help="优惠券数量")
                command.add_argument("--start", help="优惠券开始日期 YYYY-MM-DD")
                command.add_argument("--end", help="优惠券结束日期 YYYY-MM-DD")
                command.add_argument("--status", choices=["on_shelf", "off_shelf"])
                command.add_argument("--page", type=int, default=1)
                command.add_argument("--limit", type=int, default=20)
                command.add_argument("--dry-run", action="store_true")
                command.add_argument("--yes", "-y", action="store_true")
                command.add_argument("--request-id")
    return parser


def run(argv: Sequence[str] | None = None, *, gateway: Gateway | None = None) -> tuple[int, dict]:
    ns = build_parser().parse_args(argv)
    if ns.root == "platforms":
        if ns.platform:
            platform = get_platform(ns.platform)
            if platform is None:
                err = MerchantBusError("UNKNOWN_PLATFORM", f"未知平台：{ns.platform}")
                return err.exit_code, result_envelope(None, "platforms", error=err)
            return 0, result_envelope(platform.code, "platforms", platform_capabilities(platform))
        return 0, result_envelope(None, "platforms", [platform_capabilities(p) for p in PLATFORMS])
    if ns.root == "doctor":
        return 0, result_envelope(None, "doctor", {
            "version": __version__, "python_stdlib_only": True,
            "merchant_connections": "not_configured", "live_webapi_adapters": 0,
            "mock_coffice_dependency": False, "demo_mode": "ready",
        })
    if ns.root == "demo":
        if not ns.yes:
            err = MerchantBusError("CONFIRM_REQUIRED", "重置演示数据必须 --yes")
            return err.exit_code, result_envelope(None, "demo.reset", error=err)
        return 0, result_envelope(None, "demo.reset", DemoAdapter(ns.state_file).reset())
    platform = get_platform(ns.root)
    assert platform is not None
    operation = f"{ns.resource}.{ns.action}"
    args = {name: getattr(ns, name) for name in (
        "item_id", "sku_id", "coupon_id", "value", "name", "amount", "quantity",
        "start", "end", "status", "page", "limit",
    )}
    try:
        data = (gateway or Gateway()).execute(
            platform=platform.code, operation=operation, shop=ns.shop, args=args,
            demo=ns.demo, state_file=ns.state_file, dry_run=ns.dry_run,
            yes=ns.yes, request_id=ns.request_id,
        )
        return 0, result_envelope(platform.code, operation, data)
    except MerchantBusError as err:
        return err.exit_code, result_envelope(platform.code, operation, error=err)


def main(argv: Sequence[str] | None = None) -> int:
    code, result = run(argv)
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    return code
