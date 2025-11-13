# 🎯 Spaces GPU 最佳实践指南

## 📚 spaces.GPU 工作原理

### 架构概览

```
┌─────────────────────────────────────────────────────────┐
│ 主进程 (Main Process)                                    │
│ - CPU 环境                                              │
│ - ❌ 不能初始化 CUDA                                     │
│ - ✅ 可以创建 Gradio UI                                 │
│ - ✅ 可以创建 ModelInference 实例（但不加载模型）       │
└─────────────────────────────────────────────────────────┘
                        │
                        │ 调用 @spaces.GPU 装饰的函数
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│ 子进程 (GPU Worker Process)                             │
│ - GPU 环境                                              │
│ - ✅ 可以初始化 CUDA                                     │
│ - ✅ 可以加载模型到 GPU                                  │
│ - ✅ 运行推理                                           │
│ - ✅ 全局变量缓存（每个子进程独立）                      │
└─────────────────────────────────────────────────────────┘
                        │
                        │ pickle 序列化返回值
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│ 主进程接收返回值                                         │
│ - ✅ 必须是 CPU 数据（numpy, 基本类型）                 │
│ - ❌ 不能包含 CUDA 张量                                 │
└─────────────────────────────────────────────────────────┘
```

## ✅ 最佳实践：模型加载策略

### ❌ 错误做法 1：主进程加载模型

```python
# ❌ 错误：在主进程加载模型
class EventHandlers:
    def __init__(self):
        self.model_inference = ModelInference()
        # ❌ 如果在主进程调用这个，会触发 CUDA 初始化错误
        self.model_inference.initialize_model("cuda")  # 💥
```

**为什么错误？**
- 主进程不能初始化 CUDA
- 会立即报错：`CUDA must not be initialized in the main process`

### ❌ 错误做法 2：实例变量存储模型

```python
# ❌ 错误：使用实例变量存储模型
class ModelInference:
    def __init__(self):
        self.model = None  # ❌ 实例变量
    
    def initialize_model(self, device):
        if self.model is None:
            self.model = load_model()  # ❌ 保存在实例中
        return self.model
```

**为什么错误？**
- 实例在主进程创建
- 模型状态可能跨进程混乱
- 第二次调用时状态不确定

### ✅ 正确做法：子进程全局变量缓存

```python
# ✅ 正确：使用全局变量在子进程中缓存
_MODEL_CACHE = None  # 全局变量，每个子进程独立

class ModelInference:
    def __init__(self):
        # ✅ 不存储任何状态
        pass
    
    def initialize_model(self, device: str = "cuda"):
        global _MODEL_CACHE
        
        if _MODEL_CACHE is None:
            # ✅ 在子进程中加载（第一次调用时）
            print("Loading model in GPU subprocess...")
            model_dir = os.environ.get("DA3_MODEL_DIR", "...")
            _MODEL_CACHE = DepthAnything3.from_pretrained(model_dir)
            _MODEL_CACHE = _MODEL_CACHE.to(device)  # ✅ 在子进程中移动
            _MODEL_CACHE.eval()
        else:
            # ✅ 复用缓存的模型
            print("Using cached model")
        
        return _MODEL_CACHE  # ✅ 返回模型，不存储
```

**为什么正确？**
- ✅ 模型只在子进程加载（GPU 环境）
- ✅ 全局变量在子进程内安全（每个子进程独立）
- ✅ 不污染主进程
- ✅ 可以缓存复用（避免重复加载）

## 🎯 完整实现示例

### 文件结构

```
app.py                          # 主入口，配置 @spaces.GPU
depth_anything_3/app/modules/
  ├── model_inference.py        # 模型推理（使用全局变量）
  └── event_handlers.py         # 事件处理（主进程，不加载模型）
```

### 1. app.py - 装饰器配置

```python
import spaces
from depth_anything_3.app.modules.model_inference import ModelInference

# ✅ 装饰 run_inference 方法
original_run_inference = ModelInference.run_inference

@spaces.GPU(duration=120)
def gpu_run_inference(self, *args, **kwargs):
    """
    在 GPU 子进程中运行推理。
    
    这个函数会在独立的 GPU 子进程中执行，
    可以安全地初始化 CUDA 和加载模型。
    """
    return original_run_inference(self, *args, **kwargs)

# 替换原方法
ModelInference.run_inference = gpu_run_inference

# ✅ 主进程：只创建应用，不加载模型
if __name__ == "__main__":
    app = DepthAnything3App(...)
    app.launch(host="0.0.0.0", port=7860)
```

### 2. model_inference.py - 模型管理

```python
import torch
from depth_anything_3.api import DepthAnything3

# ========================================
# ✅ 全局变量缓存（子进程安全）
# ========================================
_MODEL_CACHE = None

class ModelInference:
    def __init__(self):
        """
        初始化 - 不存储任何状态。
        
        注意：这个实例在主进程创建，但模型加载在子进程。
        """
        pass  # ✅ 无实例变量
    
    def initialize_model(self, device: str = "cuda"):
        """
        在子进程中加载模型。
        
        使用全局变量缓存，因为：
        1. @spaces.GPU 在子进程运行
        2. 每个子进程有独立的全局命名空间
        3. 可以安全缓存，避免重复加载
        """
        global _MODEL_CACHE
        
        if _MODEL_CACHE is None:
            # 第一次调用：加载模型
            model_dir = os.environ.get("DA3_MODEL_DIR", "...")
            print(f"🔄 Loading model in GPU subprocess from {model_dir}")
            
            _MODEL_CACHE = DepthAnything3.from_pretrained(model_dir)
            _MODEL_CACHE = _MODEL_CACHE.to(device)  # ✅ 在子进程中移动
            _MODEL_CACHE.eval()
            
            print(f"✅ Model loaded on {device}")
        else:
            # 后续调用：复用缓存
            print("✅ Using cached model")
            # 确保在正确的设备上（防御性编程）
            _MODEL_CACHE = _MODEL_CACHE.to(device)
        
        return _MODEL_CACHE
    
    def run_inference(self, target_dir, ...):
        """
        运行推理 - 在 GPU 子进程中执行。
        
        这个函数被 @spaces.GPU 装饰，会在子进程运行。
        """
        # ✅ 在子进程中获取模型（局部变量）
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = self.initialize_model(device)  # ✅ 返回模型，不存储
        
        # ✅ 运行推理
        with torch.no_grad():
            prediction = model.inference(...)
        
        # ✅ 处理结果
        # ...
        
        # ✅ 关键：返回前移动所有 CUDA 张量到 CPU
        prediction = self._move_to_cpu(prediction)
        
        return prediction, processed_data
    
    def _move_to_cpu(self, prediction):
        """移动所有 CUDA 张量到 CPU，确保 pickle 安全"""
        # ... 实现见下文
        return prediction
```

### 3. event_handlers.py - 主进程代码

```python
class EventHandlers:
    def __init__(self):
        """
        主进程初始化 - 不加载模型。
        
        注意：这里创建 ModelInference 实例是安全的，
        因为它不立即加载模型。模型会在子进程中加载。
        """
        # ✅ 可以创建实例（不加载模型）
        self.model_inference = ModelInference()
        
        # ❌ 不要在这里调用 initialize_model()
        # ❌ 不要在这里加载模型
    
    def gradio_demo(self, ...):
        """
        Gradio 回调 - 在主进程调用。
        
        这个函数会调用 self.model_inference.run_inference，
        而 run_inference 被 @spaces.GPU 装饰，会在子进程运行。
        """
        # ✅ 调用被装饰的方法（自动在子进程运行）
        result = self.model_inference.run_inference(...)
        return result
```

## 🔑 关键原则总结

### ✅ DO（应该做）

1. **主进程：只创建实例，不加载模型**
   ```python
   # ✅ 主进程
   model_inference = ModelInference()  # 安全
   # 不调用 initialize_model()
   ```

2. **子进程：使用全局变量缓存模型**
   ```python
   # ✅ 子进程（@spaces.GPU 装饰的函数内）
   _MODEL_CACHE = None  # 全局变量
   model = initialize_model()  # 在子进程加载
   ```

3. **返回前：移动所有张量到 CPU**
   ```python
   # ✅ 返回前
   prediction = move_all_tensors_to_cpu(prediction)
   return prediction
   ```

4. **清理 GPU 内存**
   ```python
   # ✅ 推理后
   torch.cuda.empty_cache()
   ```

### ❌ DON'T（不应该做）

1. **主进程：不要初始化 CUDA**
   ```python
   # ❌ 主进程
   model.to("cuda")  # 💥 错误
   torch.cuda.is_available()  # 💥 可能触发初始化
   ```

2. **不要用实例变量存储模型**
   ```python
   # ❌
   self.model = load_model()  # 状态混乱
   ```

3. **不要返回 CUDA 张量**
   ```python
   # ❌
   return prediction  # 如果包含 CUDA 张量，会报错
   ```

4. **不要在 __init__ 中加载模型**
   ```python
   # ❌
   def __init__(self):
       self.model = load_model()  # 在主进程执行，会报错
   ```

## 📊 执行流程对比

### ❌ 错误流程

```
主进程启动
  ↓
创建 ModelInference() 实例
  ↓
__init__ 中 self.model = None  # ✅ 安全
  ↓
第一次调用 run_inference
  ↓
@spaces.GPU 创建子进程
  ↓
子进程：self.model = load_model()  # ✅ 在子进程
  ↓
返回 prediction（包含 CUDA 张量）  # ❌ 错误
  ↓
pickle 尝试在主进程重建 CUDA 张量  # 💥 报错
```

### ✅ 正确流程

```
主进程启动
  ↓
创建 ModelInference() 实例（无状态）  # ✅
  ↓
第一次调用 run_inference
  ↓
@spaces.GPU 创建子进程
  ↓
子进程：_MODEL_CACHE = load_model()  # ✅ 全局变量
  ↓
子进程：model = _MODEL_CACHE  # ✅ 局部变量
  ↓
子进程：prediction = model.inference(...)
  ↓
子进程：prediction = move_to_cpu(prediction)  # ✅
  ↓
返回 prediction（所有张量在 CPU）  # ✅
  ↓
主进程：安全接收 CPU 数据  # ✅
```

## 🧪 验证清单

### 主进程检查

```python
# ✅ 应该通过
def test_main_process():
    # 可以创建实例
    model_inference = ModelInference()
    
    # 不应该有模型
    assert not hasattr(model_inference, 'model') or model_inference.model is None
    
    # 不应该初始化 CUDA
    # (这个测试需要在主进程运行)
```

### 子进程检查

```python
# ✅ 应该通过
@spaces.GPU
def test_gpu_subprocess():
    model_inference = ModelInference()
    
    # 可以加载模型
    model = model_inference.initialize_model("cuda")
    assert model is not None
    
    # 模型应该在 GPU
    # (检查模型参数设备)
    
    # 可以运行推理
    # ...
    
    # 返回前应该移到 CPU
    # ...
```

## 🎓 常见问题

### Q1: 为什么不能用实例变量？

**A:** 因为实例在主进程创建，如果存储模型状态，会跨进程混乱。

```python
# ❌ 问题
self.model = load_model()  # 状态可能混乱

# ✅ 解决
_MODEL_CACHE = load_model()  # 每个子进程独立
```

### Q2: 全局变量安全吗？

**A:** 是的！因为：
- 每个子进程有独立的全局命名空间
- 主进程不会访问子进程的全局变量
- 不会跨进程污染

### Q3: 模型会重复加载吗？

**A:** 不会！因为：
- 全局变量在子进程内缓存
- 同一个子进程的多次调用会复用
- 不同子进程各自缓存（如果需要）

### Q4: 如何清理模型？

**A:** 通常不需要手动清理，因为：
- 子进程结束后自动清理
- 如果需要，可以在子进程中：
  ```python
  global _MODEL_CACHE
  _MODEL_CACHE = None
  del model
  torch.cuda.empty_cache()
  ```

## 📝 完整代码模板

```python
# ========================================
# model_inference.py
# ========================================
_MODEL_CACHE = None  # 全局缓存

class ModelInference:
    def __init__(self):
        pass  # 无状态
    
    def initialize_model(self, device="cuda"):
        global _MODEL_CACHE
        if _MODEL_CACHE is None:
            _MODEL_CACHE = load_model().to(device)
        return _MODEL_CACHE
    
    def run_inference(self, ...):
        model = self.initialize_model("cuda")
        prediction = model.inference(...)
        prediction = self._move_to_cpu(prediction)
        return prediction

# ========================================
# app.py
# ========================================
@spaces.GPU(duration=120)
def gpu_run_inference(self, *args, **kwargs):
    return ModelInference.run_inference(self, *args, **kwargs)

ModelInference.run_inference = gpu_run_inference
```

## 🎯 总结

**核心原则：**

1. ✅ **主进程 = CPU 环境**，不加载模型，不初始化 CUDA
2. ✅ **子进程 = GPU 环境**，加载模型，运行推理
3. ✅ **全局变量缓存**，每个子进程独立
4. ✅ **返回 CPU 数据**，确保 pickle 安全

遵循这些原则，你的 Spaces GPU 应用就能稳定运行！🚀

