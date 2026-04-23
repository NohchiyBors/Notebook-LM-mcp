import json
import unittest

from notebooklm_mcp.backends.web.parsers import _ANTI_XSSI, parse_batchexecute


class ParseBatchexecuteTests(unittest.TestCase):
    def test_raises_when_rpc_payload_null(self) -> None:
        body = (
            b")]}'\n\n120\n"
            b'[["wrb.fr","wXbhsf",null,null,null,[16],"generic"]]\n'
        )
        with self.assertRaises(ValueError) as ctx:
            parse_batchexecute(body, "wXbhsf")
        self.assertIn("пустой результат", str(ctx.exception))
        self.assertIn("16", str(ctx.exception))

    def test_parses_string_payload(self) -> None:
        inner = [[["My", [], "nid"]]]
        wrb = ["wrb.fr", "wXbhsf", json.dumps(inner, separators=(",", ":"))]
        chunk_json = json.dumps([wrb], separators=(",", ":"))
        body = _ANTI_XSSI + f"\n{len(chunk_json)}\n{chunk_json}\n".encode()
        out = parse_batchexecute(body, "wXbhsf")
        self.assertEqual(out, inner)
