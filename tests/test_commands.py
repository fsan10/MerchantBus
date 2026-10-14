import tempfile
import unittest
from pathlib import Path
from merchantbus.cli import run
from merchantbus.registry import PLATFORMS

class MerchantBusContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state = str(Path(self.tmp.name) / "store.json")

    def tearDown(self):
        self.tmp.cleanup()

    def call(self, *args):
        return run([*args, "--state-file", self.state])

    def test_seven_platforms(self):
        code, out = run(["platforms"])
        self.assertEqual(code, 0)
        self.assertEqual(len(out["data"]), 7)
        self.assertEqual(len(PLATFORMS), 7)

    def test_alias(self):
        code, out = self.call("京麦", "product", "list", "--shop", "DEMO-STORE", "--demo")
        self.assertEqual(code, 0)
        self.assertEqual(out["platform"], "jd")

    def test_live_not_implemented(self):
        code, out = self.call("douyin", "product", "list", "--shop", "DEMO-STORE")
        self.assertNotEqual(code, 0)
        self.assertEqual(out["error"]["code"], "LIVE_NOT_IMPLEMENTED")

    def test_demo_product_list(self):
        code, out = self.call("douyin", "product", "list", "--shop", "DEMO-STORE", "--demo")
        self.assertEqual(code, 0)
        self.assertEqual(out["data"]["total"], 2)

    def test_shops(self):
        code, out = self.call("jd", "shop", "list", "--demo")
        self.assertEqual(out["data"]["items"][0]["id"], "DEMO-STORE")

    def test_preview_does_not_create_state_file(self):
        code, out = self.call("douyin", "product", "off-shelf", "--shop", "DEMO-STORE",
                              "--item-id", "P100", "--dry-run")
        self.assertEqual(code, 0)
        self.assertFalse(out["data"]["executed"])
        self.assertFalse(Path(self.state).exists())

    def test_write_requires_yes(self):
        code, out = self.call("douyin", "product", "off-shelf", "--shop", "DEMO-STORE",
                              "--item-id", "P100", "--demo", "--request-id", "1")
        self.assertEqual(out["error"]["code"], "CONFIRM_REQUIRED")

    def test_write_requires_request_id(self):
        code, out = self.call("douyin", "product", "off-shelf", "--shop", "DEMO-STORE",
                              "--item-id", "P100", "--demo", "--yes")
        self.assertEqual(out["error"]["code"], "REQUEST_ID_REQUIRED")

    def test_demo_listing_change_persists(self):
        code, out = self.call("douyin", "product", "off-shelf", "--shop", "DEMO-STORE",
                              "--item-id", "P100", "--demo", "--yes", "--request-id", "off1")
        self.assertEqual(code, 0)
        self.assertFalse(out["data"]["executed_remotely"])
        _, lookup = self.call("douyin", "product", "get", "--shop", "DEMO-STORE", "--item-id", "P100", "--demo")
        self.assertEqual(lookup["data"]["product"]["status"], "off_shelf")

    def test_idempotent_repeated_write(self):
        flags = ("douyin", "product", "off-shelf", "--shop", "DEMO-STORE", "--item-id", "P100",
                 "--demo", "--yes", "--request-id", "X")
        self.call(*flags)
        _, result = self.call(*flags)
        self.assertTrue(result["data"]["deduplicated"])

    def test_idempotency_conflict(self):
        self.call("douyin", "product", "off-shelf", "--shop", "DEMO-STORE", "--item-id", "P100",
                  "--demo", "--yes", "--request-id", "X")
        _, result = self.call("douyin", "product", "on-shelf", "--shop", "DEMO-STORE", "--item-id", "P100",
                              "--demo", "--yes", "--request-id", "X")
        self.assertEqual(result["error"]["code"], "IDEMPOTENCY_CONFLICT")

    def test_price(self):
        _, out = self.call("tmall", "product", "price", "--shop", "DEMO-STORE", "--item-id", "P100",
                           "--sku-id", "S100", "--value", "89.90", "--demo", "--yes", "--request-id", "price1")
        self.assertEqual(out["data"]["after"], "89.90")

    def test_bad_price(self):
        _, out = self.call("tmall", "product", "price", "--shop", "DEMO-STORE", "--item-id", "P100",
                           "--sku-id", "S100", "--value", "nan", "--demo", "--yes", "--request-id", "price1")
        self.assertEqual(out["error"]["code"], "INVALID_PRICE")

    def test_stock_change(self):
        _, out = self.call("xhs", "stock", "set", "--shop", "DEMO-STORE", "--item-id", "P100",
                           "--sku-id", "S100", "--value", "0", "--demo", "--yes", "--request-id", "stock1")
        self.assertEqual(out["data"]["after"], 0)

    def test_coupon_create_and_terminate(self):
        _, created = self.call("jd", "coupon", "create", "--shop", "DEMO-STORE", "--name", "周末券",
                               "--amount", "10", "--quantity", "50", "--start", "2026-10-01",
                               "--end", "2026-10-31", "--demo", "--yes", "--request-id", "coupon1")
        self.assertTrue(created["ok"])
        coupon_id = created["data"]["coupon"]["id"]
        _, result = self.call("jd", "coupon", "terminate", "--shop", "DEMO-STORE", "--coupon-id", coupon_id,
                              "--demo", "--yes", "--request-id", "coupon2")
        self.assertEqual(result["data"]["after"], "terminated")

    def test_unsupported_demo_operation(self):
        _, result = self.call("jd", "product", "create", "--shop", "DEMO-STORE",
                              "--demo", "--yes", "--request-id", "x")
        self.assertEqual(result["error"]["code"], "UNSUPPORTED_CAPABILITY")

    def test_missing_sku(self):
        _, out = self.call("douyin", "stock", "get", "--shop", "DEMO-STORE", "--item-id", "P100", "--demo")
        self.assertEqual(out["error"]["code"], "SKU_ID_REQUIRED")

    def test_reset_requires_yes(self):
        code, out = run(["demo", "reset", "--state-file", self.state])
        self.assertEqual(out["error"]["code"], "CONFIRM_REQUIRED")

    def test_doctor(self):
        code, out = run(["doctor"])
        self.assertEqual(code, 0)
        self.assertFalse(out["data"]["mock_coffice_dependency"])

if __name__ == "__main__":
    unittest.main()
