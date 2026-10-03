"""Opt-in benchmark device selection; product/CI defaults remain CPU."""

import importlib
from typing import Any

from aegis.intelligence.config import Profile, profile


def device_profile(name: str, device: str) -> Profile:
    if device not in {"cpu", "cuda:0"} or (name == "offline" and device != "cpu"):
        raise ValueError("select cpu or cuda:0; offline is CPU-only")
    specs = profile(name)
    return Profile.model_validate(
        {
            key: spec.model_copy(update={"device": device}) if spec.backend != "baseline" else spec
            for key, spec in specs
        }
    )


def cuda_module(device: str) -> Any:
    if device == "cpu":
        return None
    torch = importlib.import_module("torch")
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but torch.cuda.is_available() is false")
    return torch


def synchronize(torch: Any) -> None:
    if torch is not None:
        torch.cuda.synchronize()
