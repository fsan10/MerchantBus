"""Optional MCP server; only offline-demo read and preview tools are exposed."""
from __future__ import annotations
from .cli import run


def create_server():
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise RuntimeError("缺少 MCP 依赖；执行 pip install -e '.[mcp]'") from exc

    server = FastMCP("MerchantBus")

    @server.tool()
    def merchant_platforms() -> dict:
        """List available merchant platforms and live/demo capability status."""
        return run(["platforms"])[1]

    @server.tool()
    def merchant_capabilities(platform: str) -> dict:
        """Explain operations supported by the selected merchant platform."""
        return run(["platforms", platform])[1]

    @server.tool()
    def merchant_demo_products(platform: str, shop: str = "DEMO-STORE") -> dict:
        """Read only local offline demo products; does not access real shops."""
        return run([platform, "product", "list", "--shop", shop, "--demo"])[1]

    @server.tool()
    def merchant_preview_product_action(platform: str, operation: str,
                                        item_id: str, shop: str = "DEMO-STORE") -> dict:
        """Preview local action without execution. operation = on-shelf or off-shelf."""
        if operation not in {"on-shelf", "off-shelf"}:
            return {"ok": False, "error": {"code": "INVALID_ACTION", "message": "仅支持 on-shelf/off-shelf"}}
        return run([platform, "product", operation, "--shop", shop,
                    "--item-id", item_id, "--dry-run"])[1]
    return server


def main() -> None:
    create_server().run(transport="stdio")


if __name__ == "__main__":
    main()
