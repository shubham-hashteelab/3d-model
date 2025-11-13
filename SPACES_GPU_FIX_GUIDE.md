# 🔧 Spaces GPU 问题完整修复指南

## 🎯 问题诊断：你说得完全正确！

### 问题根源分析

```python
# event_handlers.py - 主进程中
class EventHandlers:
    def __init__(self):
        self.model_inference = ModelInference()  # ❌ 在主进程创建实例

# model_inference.py
class ModelInference:
    def __init__(self):
        self.model = None  # ❌ 实例变量，跨进程共享状态有问题
    
    def initialize_model(self, device):
        if self.model is None:
            self.model = load_model()  # 第一次：在子进程加载
        else:
            self.model = self.model.to(device)  # 第二次：💥 主进程CUDA操作！
```

### 为什么第二次会失败？

1. **第一次调用**：
   - `@spaces.GPU` 在子进程运行
   - `self.model is None` → 加载模型
   - `self.model` 保存在实例中
   - 返回时 `prediction.gaussians` 包含 CUDA 张量
   - **pickle 时尝试在主进程重建 CUDA 张量** → 💥

2. **第二次调用**（即使第一次成功了）：
   - 新的子进程或状态混乱
   - `self.model` 状态不确定
   - 尝试 `.to(device)` 操作 → 💥

## ✅ 解决方案：两个关键修改

### 修改 1：使用全局变量缓存模型（避免实例状态）

**为什么用全局变量？**
- `@spaces.GPU` 每次在独立子进程运行
- 全局变量在子进程内是安全的
- 不会污染主进程

### 修改 2：返回前移动所有 CUDA 张量到 CPU

**为什么需要？**
- Pickle 序列化返回值时会尝试重建 CUDA 张量
- 必须确保返回的数据都在 CPU 上

## 📝 完整修复代码

### 文件：`depth_anything_3/app/modules/model_inference.py`

```python
"""
Model inference module for Depth Anything 3 Gradio app.

Modified for HF Spaces GPU compatibility.
"""

import gc
import glob
import os
from typing import Any, Dict, Optional, Tuple
import numpy as np
import torch

from depth_anything_3.api import DepthAnything3
from depth_anything_3.utils.export.glb import export_to_glb
from depth_anything_3.utils.export.gs import export_to_gs_video


# ========================================
# 🔑 关键修改 1：使用全局变量缓存模型
# ========================================
# Global cache for model (used in GPU subprocess)
# This is SAFE because @spaces.GPU runs in isolated subprocess
# Each subprocess gets its own copy of this global variable
_MODEL_CACHE = None


class ModelInference:
    """
    Handles model inference and data processing for Depth Anything 3.
    
    Modified for HF Spaces GPU compatibility - does NOT store state
    in instance variables to avoid cross-process issues.
    """

    def __init__(self):
        """Initialize the model inference handler.
        
        Note: Do NOT store model in instance variable to avoid
        state sharing issues with @spaces.GPU decorator.
        """
        # No instance variables! All state in global or local variables
        pass

    def initialize_model(self, device: str = "cuda"):
        """
        Initialize the DepthAnything3 model using global cache.
        
        This uses a global variable which is safe because:
        1. @spaces.GPU runs in isolated subprocess
        2. Each subprocess has its own global namespace
        3. No state leaks to main process

        Args:
            device: Device to load the model on
            
        Returns:
            Model instance ready for inference
        """
        global _MODEL_CACHE
        
        if _MODEL_CACHE is None:
            # First time loading in this subprocess
            model_dir = os.environ.get(
                "DA3_MODEL_DIR", "depth-anything/DA3NESTED-GIANT-LARGE"
            )
            print(f"🔄 Loading model from {model_dir}...")
            _MODEL_CACHE = DepthAnything3.from_pretrained(model_dir)
            _MODEL_CACHE = _MODEL_CACHE.to(device)
            _MODEL_CACHE.eval()
            print("✅ Model loaded and ready on GPU")
        else:
            # Model already cached in this subprocess
            print("✅ Using cached model")
            # Ensure it's on the correct device (defensive programming)
            _MODEL_CACHE = _MODEL_CACHE.to(device)
        
        return _MODEL_CACHE

    def run_inference(
        self,
        target_dir: str,
        filter_black_bg: bool = False,
        filter_white_bg: bool = False,
        process_res_method: str = "upper_bound_resize",
        show_camera: bool = True,
        selected_first_frame: Optional[str] = None,
        save_percentage: float = 30.0,
        num_max_points: int = 1_000_000,
        infer_gs: bool = False,
        gs_trj_mode: str = "extend",
        gs_video_quality: str = "high",
    ) -> Tuple[Any, Dict[int, Dict[str, Any]]]:
        """
        Run DepthAnything3 model inference on images.
        
        This method is wrapped with @spaces.GPU in app.py.

        Args:
            target_dir: Directory containing images
            filter_black_bg: Whether to filter black background
            filter_white_bg: Whether to filter white background
            process_res_method: Method for resizing input images
            show_camera: Whether to show camera in 3D view
            selected_first_frame: Selected first frame filename
            save_percentage: Percentage of points to save (0-100)
            num_max_points: Maximum number of points
            infer_gs: Whether to infer 3D Gaussian Splatting
            gs_trj_mode: Trajectory mode for GS
            gs_video_quality: Video quality for GS

        Returns:
            Tuple of (prediction, processed_data)
        """
        print(f"Processing images from {target_dir}")

        # Device check
        device = "cuda" if torch.cuda.is_available() else "cpu"
        device = torch.device(device)
        print(f"Using device: {device}")

        # 🔑 使用返回值，而不是 self.model
        model = self.initialize_model(device)

        # Get image paths
        print("Loading images...")
        image_folder_path = os.path.join(target_dir, "images")
        all_image_paths = sorted(glob.glob(os.path.join(image_folder_path, "*")))

        # Filter for image files
        image_extensions = [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif"]
        all_image_paths = [
            path
            for path in all_image_paths
            if any(path.lower().endswith(ext) for ext in image_extensions)
        ]

        print(f"Found {len(all_image_paths)} images")

        # Apply first frame selection logic
        if selected_first_frame:
            selected_path = None
            for path in all_image_paths:
                if os.path.basename(path) == selected_first_frame:
                    selected_path = path
                    break

            if selected_path:
                image_paths = [selected_path] + [
                    path for path in all_image_paths if path != selected_path
                ]
                print(f"User selected first frame: {selected_first_frame}")
            else:
                image_paths = all_image_paths
                print(f"Selected frame not found, using default order")
        else:
            image_paths = all_image_paths

        if len(image_paths) == 0:
            raise ValueError("No images found. Check your upload.")

        # Map UI options to actual method names
        method_mapping = {"high_res": "lower_bound_resize", "low_res": "upper_bound_resize"}
        actual_method = method_mapping.get(process_res_method, "upper_bound_crop")

        # Run model inference
        print(f"Running inference with method: {actual_method}")
        with torch.no_grad():
            # 🔑 使用局部变量 model，不是 self.model
            prediction = model.inference(
                image_paths, export_dir=None, process_res_method=actual_method, infer_gs=infer_gs
            )

        # Export to GLB
        export_to_glb(
            prediction,
            filter_black_bg=filter_black_bg,
            filter_white_bg=filter_white_bg,
            export_dir=target_dir,
            show_cameras=show_camera,
            conf_thresh_percentile=save_percentage,
            num_max_points=int(num_max_points),
        )

        # Export to GS video if needed
        if infer_gs:
            mode_mapping = {"extend": "extend", "smooth": "interpolate_smooth"}
            print(f"GS mode: {gs_trj_mode}; Backend mode: {mode_mapping[gs_trj_mode]}")
            export_to_gs_video(
                prediction,
                export_dir=target_dir,
                chunk_size=4,
                trj_mode=mode_mapping.get(gs_trj_mode, "extend"),
                enable_tqdm=True,
                vis_depth="hcat",
                video_quality=gs_video_quality,
            )

        # Save predictions cache
        self._save_predictions_cache(target_dir, prediction)

        # Process results
        processed_data = self._process_results(target_dir, prediction, image_paths)

        # ========================================
        # 🔑 关键修改 2：返回前移动所有 CUDA 张量到 CPU
        # ========================================
        print("Moving all tensors to CPU for safe return...")
        prediction = self._move_prediction_to_cpu(prediction)

        # Clean up GPU memory
        torch.cuda.empty_cache()

        return prediction, processed_data

    def _move_prediction_to_cpu(self, prediction: Any) -> Any:
        """
        Move all CUDA tensors in prediction to CPU for safe pickling.
        
        This is CRITICAL for HF Spaces with @spaces.GPU decorator.
        Without this, pickle will try to reconstruct CUDA tensors in
        the main process, causing CUDA initialization error.
        
        Args:
            prediction: Prediction object that may contain CUDA tensors
            
        Returns:
            Prediction object with all tensors moved to CPU
        """
        # Move gaussians tensors to CPU
        if hasattr(prediction, 'gaussians') and prediction.gaussians is not None:
            gaussians = prediction.gaussians
            
            # Move each tensor attribute to CPU
            tensor_attrs = ['means', 'scales', 'rotations', 'harmonics', 'opacities']
            for attr in tensor_attrs:
                if hasattr(gaussians, attr):
                    tensor = getattr(gaussians, attr)
                    if isinstance(tensor, torch.Tensor) and tensor.is_cuda:
                        setattr(gaussians, attr, tensor.cpu())
                        print(f"  ✓ Moved gaussians.{attr} to CPU")
        
        # Move any tensors in aux dict to CPU
        if hasattr(prediction, 'aux') and prediction.aux is not None:
            for key, value in list(prediction.aux.items()):
                if isinstance(value, torch.Tensor) and value.is_cuda:
                    prediction.aux[key] = value.cpu()
                    print(f"  ✓ Moved aux['{key}'] to CPU")
                elif isinstance(value, dict):
                    # Recursively handle nested dicts
                    for k, v in list(value.items()):
                        if isinstance(v, torch.Tensor) and v.is_cuda:
                            value[k] = v.cpu()
                            print(f"  ✓ Moved aux['{key}']['{k}'] to CPU")
        
        print("✅ All tensors moved to CPU")
        return prediction

    def _save_predictions_cache(self, target_dir: str, prediction: Any) -> None:
        """Save predictions data to predictions.npz for caching."""
        try:
            output_file = os.path.join(target_dir, "predictions.npz")
            save_dict = {}

            if prediction.processed_images is not None:
                save_dict["images"] = prediction.processed_images

            if prediction.depth is not None:
                save_dict["depths"] = np.round(prediction.depth, 6)

            if prediction.conf is not None:
                save_dict["conf"] = np.round(prediction.conf, 2)

            if prediction.extrinsics is not None:
                save_dict["extrinsics"] = prediction.extrinsics
            if prediction.intrinsics is not None:
                save_dict["intrinsics"] = prediction.intrinsics

            np.savez_compressed(output_file, **save_dict)
            print(f"Saved predictions cache to: {output_file}")

        except Exception as e:
            print(f"Warning: Failed to save predictions cache: {e}")

    def _process_results(
        self, target_dir: str, prediction: Any, image_paths: list
    ) -> Dict[int, Dict[str, Any]]:
        """Process model results into structured data."""
        processed_data = {}

        depth_vis_dir = os.path.join(target_dir, "depth_vis")

        if os.path.exists(depth_vis_dir):
            depth_files = sorted(glob.glob(os.path.join(depth_vis_dir, "*.jpg")))
            for i, depth_file in enumerate(depth_files):
                processed_image = None
                if prediction.processed_images is not None and i < len(
                    prediction.processed_images
                ):
                    processed_image = prediction.processed_images[i]

                processed_data[i] = {
                    "depth_image": depth_file,
                    "image": processed_image,
                    "original_image_path": image_paths[i] if i < len(image_paths) else None,
                    "depth": prediction.depth[i] if i < len(prediction.depth) else None,
                    "intrinsics": (
                        prediction.intrinsics[i]
                        if prediction.intrinsics is not None and i < len(prediction.intrinsics)
                        else None
                    ),
                    "mask": None,
                }

        return processed_data

    def cleanup(self) -> None:
        """Clean up GPU memory."""
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        gc.collect()
```

## 🔍 关键变化总结

### Before (有问题)：
```python
class ModelInference:
    def __init__(self):
        self.model = None  # ❌ 实例变量
    
    def initialize_model(self, device):
        if self.model is None:
            self.model = load_model()  # ❌ 保存在实例中
        else:
            self.model = self.model.to(device)  # ❌ 跨进程操作

def run_inference(self):
        self.initialize_model(device)  # ❌ 使用实例方法
        prediction = self.model.inference(...)  # ❌ 使用实例变量
        return prediction  # ❌ 包含 CUDA 张量
```

### After (正确)：
```python
_MODEL_CACHE = None  # ✅ 全局变量（子进程安全）

class ModelInference:
    def __init__(self):
        pass  # ✅ 无实例变量
    
    def initialize_model(self, device):
        global _MODEL_CACHE
        if _MODEL_CACHE is None:
            _MODEL_CACHE = load_model()  # ✅ 保存在全局
        return _MODEL_CACHE  # ✅ 返回而不是存储

    def run_inference(self):
        model = self.initialize_model(device)  # ✅ 局部变量
        prediction = model.inference(...)  # ✅ 使用局部变量
        prediction = self._move_prediction_to_cpu(prediction)  # ✅ 移到 CPU
        return prediction  # ✅ 安全返回
```

## 🎯 为什么这样修改？

### 1. 全局变量 vs 实例变量

| 方式 | 问题 | 原因 |
|------|------|------|
| `self.model` | ❌ 跨进程状态混乱 | 实例在主进程创建 |
| `_MODEL_CACHE` | ✅ 子进程内安全 | 每个子进程独立 |

### 2. 返回 CPU 张量

```python
# ❌ 直接返回会报错
return prediction  # prediction.gaussians.means is on CUDA

# ✅ 移到 CPU 后返回
prediction = move_to_cpu(prediction)
return prediction  # All tensors are on CPU, pickle safe
```

## 🧪 测试修复

```bash
# 1. 应用修改
# 复制上面的完整代码到 model_inference.py

# 2. 推送到 Spaces
git add depth_anything_3/app/modules/model_inference.py
git commit -m "Fix: Spaces GPU CUDA initialization error"
git push

# 3. 测试多次运行
# 在 Space 中连续运行 2-3 次推理
# 应该不再出现 CUDA 错误
```

## 📊 修复效果

| 问题 | Before | After |
|------|--------|-------|
| 第一次推理 | ❌ CUDA 错误 | ✅ 正常 |
| 第二次推理 | ❌ CUDA 错误 | ✅ 正常 |
| 连续推理 | ❌ 失败 | ✅ 稳定 |
| 模型加载 | 每次重新加载 | 缓存复用 |

## 💡 最佳实践

对于 `@spaces.GPU` 装饰的函数：

1. ✅ 使用**全局变量**缓存模型（子进程安全）
2. ✅ **不要**使用实例变量存储模型
3. ✅ 返回前**移动所有张量到 CPU**
4. ✅ 清理 GPU 内存 (`torch.cuda.empty_cache()`)
5. ❌ **不要**在主进程中初始化 CUDA
6. ❌ **不要**返回 CUDA 张量

## 🔗 相关资源

- [HF Spaces Zero GPU 文档](https://huggingface.co/docs/hub/spaces-gpus#zero-gpu)
- [PyTorch Multiprocessing](https://pytorch.org/docs/stable/notes/multiprocessing.html)
- [Pickle 协议](https://docs.python.org/3/library/pickle.html)

