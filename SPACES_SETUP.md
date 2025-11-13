# Hugging Face Spaces 部署指南

## 📋 概述

这个项目已经配置好可以部署到 Hugging Face Spaces，使用 `@spaces.GPU` 装饰器来动态分配 GPU 资源。

## 🎯 关键文件

### 1. `app.py` - 主应用文件

```python
import spaces
from depth_anything_3.app.gradio_app import DepthAnything3App
from depth_anything_3.app.modules.model_inference import ModelInference

# 使用 monkey-patching 将 GPU 装饰器应用到推理函数
original_run_inference = ModelInference.run_inference

@spaces.GPU(duration=120)  # 请求 GPU，最多 120 秒
def gpu_run_inference(self, *args, **kwargs):
    return original_run_inference(self, *args, **kwargs)

ModelInference.run_inference = gpu_run_inference
```

**工作原理：**
- `@spaces.GPU` 装饰器在函数调用时动态分配 GPU
- `duration=120` 表示单次推理最多使用 GPU 120 秒
- 通过 monkey-patching，我们将装饰器应用到已有的推理函数上，无需修改核心代码

### 2. `README.md` - Spaces 配置

```yaml
---
title: Depth Anything 3
sdk: gradio
sdk_version: 5.49.1
app_file: app.py
pinned: false
license: cc-by-nc-4.0
---
```

这个 YAML 前置内容告诉 Hugging Face Spaces：
- 使用 Gradio SDK
- 入口文件是 `app.py`
- 使用的 Gradio 版本

### 3. `pyproject.toml` - 依赖配置

已经更新，包含了 `spaces` 依赖：

```toml
[project.optional-dependencies]
app = ["gradio>=5", "pillow>=9.0", "spaces"]
```

## 🚀 部署步骤

### 方式 1：通过 Hugging Face 网页界面

1. 在 Hugging Face 创建一个新的 Space
2. 选择 **Gradio** 作为 SDK
3. 上传你的代码（包括 `app.py`, `src/`, `pyproject.toml` 等）
4. Space 会自动构建并启动

### 方式 2：通过 Git

```bash
# 克隆你的 Space 仓库
git clone https://huggingface.co/spaces/YOUR_USERNAME/YOUR_SPACE_NAME
cd YOUR_SPACE_NAME

# 添加你的代码
cp -r /path/to/depth-anything-3/* .

# 提交并推送
git add .
git commit -m "Initial commit"
git push
```

## 🔧 配置选项

### GPU 类型

Hugging Face Spaces 支持不同的 GPU 类型：

- **Free (T4)**: 免费，适合小型模型
- **A10G**: 付费，更强大
- **A100**: 付费，最强大

### GPU Duration

在 `app.py` 中可以调整：

```python
@spaces.GPU(duration=120)  # 120 秒
```

- 设置太短：复杂推理可能超时
- 设置太长：浪费资源
- 推荐：根据实际推理时间设置（可以先设长一点，然后根据日志调整）

### 环境变量

可以在 Space 设置中配置环境变量：

- `DA3_MODEL_DIR`: 模型目录路径
- `DA3_WORKSPACE_DIR`: 工作空间目录
- `DA3_GALLERY_DIR`: 图库目录

## 📊 监控和调试

### 查看日志

在 Spaces 界面点击 "Logs" 标签可以看到：

```
🚀 Launching Depth Anything 3 on Hugging Face Spaces...
📦 Model Directory: depth-anything/DA3NESTED-GIANT-LARGE
📁 Workspace Directory: workspace/gradio
🖼️  Gallery Directory: workspace/gallery
```

### GPU 使用情况

在装饰的函数内部，可以检查 GPU 状态：

```python
print(torch.cuda.is_available())  # True
print(torch.cuda.device_count())  # 1 (通常)
print(torch.cuda.get_device_name(0))  # 'Tesla T4' 或其他
```

## 🎓 示例代码

查看 `example_spaces_gpu.py` 了解 `@spaces.GPU` 装饰器的基本用法。

## ❓ 常见问题

### Q: 为什么使用 monkey-patching？

A: 这样可以在不修改核心代码的情况下添加 Spaces 支持。如果你想更优雅的方式，可以：

1. 直接在 `ModelInference.run_inference` 方法上添加装饰器
2. 创建一个继承自 `ModelInference` 的新类

### Q: 如何测试本地是否能运行？

A: 本地运行时，`spaces.GPU` 装饰器会被忽略（如果没有安装 spaces 包），或者会直接执行函数而不做特殊处理。

```bash
# 本地测试
python app.py
```

### Q: 可以装饰多个函数吗？

A: 可以！你可以给任何需要 GPU 的函数添加 `@spaces.GPU` 装饰器。

```python
@spaces.GPU(duration=60)
def function1():
    pass

@spaces.GPU(duration=120)
def function2():
    pass
```

### Q: 如何优化 GPU 使用？

A: 一些建议：

1. **只装饰必要的函数**：不要装饰整个 app，只装饰实际使用 GPU 的推理函数
2. **设置合适的 duration**：根据实际需求设置
3. **清理 GPU 内存**：在函数结束时调用 `torch.cuda.empty_cache()`
4. **批处理**：如果可能，批量处理多个请求

## 🔗 相关资源

- [Hugging Face Spaces 文档](https://huggingface.co/docs/hub/spaces)
- [Spaces GPU 使用指南](https://huggingface.co/docs/hub/spaces-gpus)
- [Gradio 文档](https://gradio.app/docs)

## 📝 许可证

Apache-2.0

