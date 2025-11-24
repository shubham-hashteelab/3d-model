"""GPU memory helper utilities used by the backend service.

Provides lightweight implementations for:
- get_gpu_memory_info()
- cleanup_cuda_memory()
- check_memory_availability(required_gb)
- estimate_memory_requirement(num_images, process_res)

These functions are intentionally conservative and have no external
runtime dependencies other than torch (optional). They fall back to
CPU-only behavior when CUDA is unavailable.
"""

import gc
from typing import Dict, Optional, Tuple


def _safe_import_torch():
    try:
        import torch

        return torch
    except Exception:
        return None


def get_gpu_memory_info() -> Optional[Dict[str, float]]:
    """Return basic GPU memory statistics.

    Returns a dict with keys: total_gb, allocated_gb, reserved_gb, free_gb, utilization
    or None if CUDA / torch is not available.
    """
    torch = _safe_import_torch()
    if torch is None or not torch.cuda.is_available():
        return None

    try:
        # Use device 0 as representative device
        dev = torch.device("cuda:0")
        props = torch.cuda.get_device_properties(dev)
        total_bytes = props.total_memory

        allocated = torch.cuda.memory_allocated(dev)
        reserved = torch.cuda.memory_reserved(dev)

        total_gb = total_bytes / (1024 ** 3)
        allocated_gb = allocated / (1024 ** 3)
        reserved_gb = reserved / (1024 ** 3)
        free_gb = max(total_gb - reserved_gb, 0.0)

        # Try to get utilization via pynvml if installed, otherwise leave as 0.0
        utilization = 0.0
        try:
            import pynvml

            pynvml.nvmlInit()
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            util = pynvml.nvmlDeviceGetUtilizationRates(handle)
            utilization = float(util.gpu)
            pynvml.nvmlShutdown()
        except Exception:
            # ignore if pynvml not available
            pass

        return {
            "total_gb": total_gb,
            "allocated_gb": allocated_gb,
            "reserved_gb": reserved_gb,
            "free_gb": free_gb,
            "utilization": utilization,
        }
    except Exception:
        return None


def cleanup_cuda_memory() -> None:
    """Attempt to free GPU memory and run garbage collection.

    This is safe to call on CPU-only systems.
    """
    gc.collect()
    torch = _safe_import_torch()
    if torch is None:
        return

    try:
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        # Don't fail callers if cleanup fails
        pass


def check_memory_availability(required_gb: float) -> Tuple[bool, str]:
    """Check if there appears to be at least `required_gb` of free GPU memory.

    Returns (available: bool, message: str).
    """
    info = get_gpu_memory_info()
    if info is None:
        return False, "CUDA not available or torch not installed"

    free = info.get("free_gb", 0.0)
    total = info.get("total_gb", 0.0)

    if free >= required_gb:
        return True, f"Sufficient GPU memory: free={free:.2f}GB total={total:.2f}GB"

    return False, f"Insufficient GPU memory: required={required_gb:.2f}GB free={free:.2f}GB total={total:.2f}GB"


def estimate_memory_requirement(num_images: int, process_res: int = 504) -> float:
    """Estimate GPU memory requirement (in GB) for a job.

    This is a heuristic estimate used for early OOM checks. It scales roughly
    with the number of images and the square of the processing resolution.

    - Base minimum memory: 1.0 GB
    - Per-image memory at 504 px: ~0.6 GB
    - Scale per-image by (process_res / 504)^2
    """
    if num_images <= 0:
        return 1.0

    per_image_at_504_gb = 0.6
    scale = (process_res / 504) ** 2 if process_res > 0 else 1.0
    per_image = per_image_at_504_gb * scale

    # Add an overhead for model parameters and buffers
    overhead_gb = 1.0

    estimated = overhead_gb + num_images * per_image
    # Clamp to a reasonable minimum
    return max(estimated, 1.0)
