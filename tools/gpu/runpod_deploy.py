#!/usr/bin/env python3
"""Create or locate the GLM-5.2 RunPod serverless endpoint."""

from __future__ import annotations

from dataclasses import dataclass
import argparse
import json
import os
from pathlib import Path
from typing import Any, Callable
import urllib.request


RUNPOD_GRAPHQL_URL = os.environ.get("RUNPOD_GRAPHQL_URL", "https://api.runpod.io/graphql")
DEFAULT_ENDPOINT_NAME = "glm52-council"
DEFAULT_REGISTRY = Path(os.environ.get("RUNPOD_ENDPOINT_REGISTRY", "/root/.config/fpai/runpod_endpoints.json"))


class RunPodDeployError(RuntimeError):
    """Raised when endpoint deployment cannot continue."""


@dataclass(frozen=True)
class DeploymentStrategy:
    name: str
    model_id: str
    image: str
    gpu_type: str
    gpu_count: int
    env: dict[str, str]


def deployment_strategies() -> list[DeploymentStrategy]:
    adapter = os.environ.get("GLM_FP_LORA_ADAPTER", "/opt/fpai-build/models/glm-fpai-lora/")
    return [
        DeploymentStrategy(
            name="glm52-ktransformers-a100",
            model_id="zai-org/GLM-5.2",
            image=os.environ.get("RUNPOD_GLM_KTRANSFORMERS_IMAGE", "runpod/vllm:latest"),
            gpu_type="NVIDIA A100 80GB PCIe",
            gpu_count=1,
            env={
                "MODEL_ID": "zai-org/GLM-5.2",
                "INFERENCE_BACKEND": "ktransformers",
                "CPU_OFFLOAD": "1",
                "OPENAI_COMPATIBLE": "1",
                "LORA_ADAPTER_PATH": adapter,
            },
        ),
        DeploymentStrategy(
            name="glm52-gguf-q4-a100",
            model_id=os.environ.get("RUNPOD_GLM_GGUF_MODEL", "unsloth/GLM-5-GGUF"),
            image=os.environ.get("RUNPOD_GLM_GGUF_IMAGE", "runpod/vllm:latest"),
            gpu_type="NVIDIA A100 80GB PCIe",
            gpu_count=4,
            env={
                "MODEL_ID": os.environ.get("RUNPOD_GLM_GGUF_MODEL", "unsloth/GLM-5-GGUF"),
                "QUANTIZATION": "Q4_K_M",
                "OPENAI_COMPATIBLE": "1",
                "LORA_ADAPTER_PATH": adapter,
            },
        ),
        DeploymentStrategy(
            name="glm4-9b-a100-fallback",
            model_id="THUDM/glm-4-9b-chat",
            image=os.environ.get("RUNPOD_GLM4_IMAGE", "runpod/vllm:latest"),
            gpu_type="NVIDIA A100 80GB PCIe",
            gpu_count=1,
            env={
                "MODEL_ID": "THUDM/glm-4-9b-chat",
                "OPENAI_COMPATIBLE": "1",
                "LORA_ADAPTER_PATH": adapter,
            },
        ),
    ]


def graphql(
    api_key: str,
    query: str,
    variables: dict[str, Any] | None = None,
    *,
    transport: Callable[[str, dict[str, Any], str], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if transport:
        return transport(query, variables or {}, api_key)
    req = urllib.request.Request(
        RUNPOD_GRAPHQL_URL,
        data=json.dumps({"query": query, "variables": variables or {}}).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    if payload.get("errors"):
        raise RunPodDeployError(str(payload["errors"])[:500])
    return payload.get("data") or payload


def _endpoint_id(endpoint: dict[str, Any]) -> str:
    for key in ("endpoint_id", "endpointId", "id"):
        if endpoint.get(key):
            return str(endpoint[key])
    return ""


def _walk_endpoints(obj: Any) -> list[dict[str, Any]]:
    endpoints: list[dict[str, Any]] = []
    if isinstance(obj, dict):
        if obj.get("name") and _endpoint_id(obj):
            endpoints.append(obj)
        for value in obj.values():
            endpoints.extend(_walk_endpoints(value))
    elif isinstance(obj, list):
        for item in obj:
            endpoints.extend(_walk_endpoints(item))
    return endpoints


def find_endpoint(api_key: str, name: str = DEFAULT_ENDPOINT_NAME, *, transport: Callable | None = None) -> dict[str, Any] | None:
    query = """
    query FpaiServerlessEndpoints {
      myself {
        endpoints { id name endpointId }
        serverlessEndpoints { id name endpointId }
      }
      endpoints { id name endpointId }
    }
    """
    data = graphql(api_key, query, {}, transport=transport)
    for endpoint in _walk_endpoints(data):
        if endpoint.get("name") == name:
            return endpoint
    return None


def create_endpoint(
    api_key: str,
    strategy: DeploymentStrategy,
    *,
    name: str = DEFAULT_ENDPOINT_NAME,
    transport: Callable | None = None,
) -> dict[str, Any]:
    template_id = os.environ.get("RUNPOD_TEMPLATE_ID", "")
    input_payload: dict[str, Any] = {
        "name": name,
        "templateId": template_id or None,
        "imageName": strategy.image,
        "gpuTypeIds": [strategy.gpu_type],
        "gpuCount": strategy.gpu_count,
        "workersMin": 0,
        "workersMax": 1,
        "idleTimeout": 60,
        "env": strategy.env,
    }
    mutation = """
    mutation FpaiCreateEndpoint($input: SaveEndpointInput!) {
      saveEndpoint(input: $input) {
        id
        name
        endpointId
      }
    }
    """
    data = graphql(api_key, mutation, {"input": input_payload}, transport=transport)
    endpoints = _walk_endpoints(data)
    if not endpoints:
        raise RunPodDeployError(f"RunPod did not return an endpoint for strategy {strategy.name}")
    return endpoints[0] | {"strategy": strategy.name}


def write_registry(endpoint: dict[str, Any], path: Path = DEFAULT_REGISTRY) -> None:
    payload = {}
    if path.exists():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = {}
    payload[DEFAULT_ENDPOINT_NAME] = {
        "endpoint_id": _endpoint_id(endpoint),
        "name": endpoint.get("name", DEFAULT_ENDPOINT_NAME),
        "strategy": endpoint.get("strategy", "existing"),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def create_or_get_endpoint(
    *,
    api_key: str | None = None,
    name: str = DEFAULT_ENDPOINT_NAME,
    registry_path: Path = DEFAULT_REGISTRY,
    transport: Callable | None = None,
) -> dict[str, Any]:
    key = api_key or os.environ.get("RUNPOD_API_KEY", "")
    if not key:
        raise RunPodDeployError("RUNPOD_API_KEY is required")
    existing = find_endpoint(key, name=name, transport=transport)
    if existing:
        result = existing | {"strategy": "existing"}
        write_registry(result, registry_path)
        return result
    last_error: Exception | None = None
    for strategy in deployment_strategies():
        try:
            endpoint = create_endpoint(key, strategy, name=name, transport=transport)
            write_registry(endpoint, registry_path)
            return endpoint
        except Exception as exc:
            last_error = exc
            continue
    raise RunPodDeployError(f"all deployment strategies failed: {last_error}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create or locate the GLM-5.2 RunPod endpoint.")
    parser.add_argument("--name", default=DEFAULT_ENDPOINT_NAME)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    args = parser.parse_args(argv)
    endpoint = create_or_get_endpoint(name=args.name, registry_path=args.registry)
    print(json.dumps({"endpoint_id": _endpoint_id(endpoint), "strategy": endpoint.get("strategy")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
