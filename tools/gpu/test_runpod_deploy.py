import json
from pathlib import Path
import tempfile
import unittest

from tools.gpu import runpod_deploy


class RunPodDeployTest(unittest.TestCase):
    def test_endpoint_creation_returns_valid_endpoint_id_and_writes_registry(self):
        root = Path(tempfile.mkdtemp(prefix="fpai-runpod-test-"))
        registry = root / "runpod_endpoints.json"
        calls = []

        def transport(query, variables, api_key):
            calls.append((query, variables, api_key))
            if "query FpaiServerlessEndpoints" in query:
                return {"myself": {"serverlessEndpoints": []}}
            return {"saveEndpoint": {"id": "endpoint-new", "name": "glm52-council", "endpointId": "endpoint-new"}}

        endpoint = runpod_deploy.create_or_get_endpoint(
            api_key="rp_test",
            registry_path=registry,
            transport=transport,
        )

        self.assertEqual(endpoint["endpointId"], "endpoint-new")
        payload = json.loads(registry.read_text(encoding="utf-8"))
        self.assertEqual(payload["glm52-council"]["endpoint_id"], "endpoint-new")
        self.assertEqual(calls[-1][1]["input"]["workersMin"], 0)
        self.assertEqual(calls[-1][1]["input"]["workersMax"], 1)

    def test_existing_endpoint_is_reused(self):
        def transport(query, _variables, _api_key):
            self.assertIn("query FpaiServerlessEndpoints", query)
            return {
                "myself": {
                    "serverlessEndpoints": [
                        {"id": "endpoint-existing", "name": "glm52-council", "endpointId": "endpoint-existing"}
                    ]
                }
            }

        endpoint = runpod_deploy.create_or_get_endpoint(
            api_key="rp_test",
            registry_path=Path(tempfile.mkdtemp(prefix="fpai-runpod-test-")) / "registry.json",
            transport=transport,
        )

        self.assertEqual(runpod_deploy._endpoint_id(endpoint), "endpoint-existing")
        self.assertEqual(endpoint["strategy"], "existing")


if __name__ == "__main__":
    unittest.main()

