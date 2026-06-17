import os
import unittest
from unittest import mock

from tools.council import glm_client


class GLMClientTest(unittest.TestCase):
    def test_unavailable_without_key_or_local_url(self) -> None:
        env = dict(os.environ)
        env.pop("GLM_API_KEY", None)
        env.pop("GLM_LOCAL_URL", None)
        with mock.patch.dict(os.environ, env, clear=True):
            with self.assertRaises(glm_client.GLMUnavailableError):
                glm_client.call_glm("system", "user")


if __name__ == "__main__":
    unittest.main()
