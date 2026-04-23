import unittest


class ServerImportTests(unittest.TestCase):
    def test_server_module_imports_with_installed_fastmcp(self) -> None:
        from notebooklm_mcp import server

        self.assertTrue(callable(server.main))
