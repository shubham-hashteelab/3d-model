# gsplat 安装解决方案

## 🎯 问题描述

`gsplat` 是一个 CUDA 加速的 3D Gaussian Splatting 库，从源码安装可能在 HF Spaces 遇到问题。

## ✅ 解决方案（按推荐顺序）

---

## 方案 1️⃣：直接从 GitHub 安装 ⭐ (已配置)

**requirements.txt:**
```txt
gsplat @ git+https://github.com/nerfstudio-project/gsplat.git@0b4dddf04cb687367602c01196913cde6a743d70
```

**优点：**
- ✅ 使用特定版本，稳定
- ✅ 最新功能
- ✅ 与你的代码兼容

**缺点：**
- ⚠️ 构建时间长（5-15 分钟）
- ⚠️ 需要 CUDA 在构建时
- ⚠️ 可能构建失败

**测试方法：**
```bash
# 本地测试（确保有 GPU）
pip install 'gsplat @ git+https://github.com/nerfstudio-project/gsplat.git@0b4dddf04cb687367602c01196913cde6a743d70'
python -c "import gsplat; print(gsplat.__version__)"
```

**HF Spaces 配置建议：**

如果构建失败，需要在 Space 设置中：
1. 选择 **GPU Space**（不是 CPU Space）
2. GPU 类型选择至少 **T4** 或更高
3. 在构建阶段就需要 GPU

---

## 方案 2️⃣：使用预编译 Wheel（如果可用）

**检查是否有预编译版本：**
```bash
pip index versions gsplat
```

如果有 PyPI 版本，修改 requirements.txt：
```txt
# 使用 PyPI 版本（更快）
gsplat>=0.1.0
```

**优点：**
- ✅ 安装快速（秒级）
- ✅ 不需要编译
- ✅ 更稳定

**缺点：**
- ⚠️ 可能版本较旧
- ⚠️ 可能没有预编译版本

---

## 方案 3️⃣：延迟加载 gsplat（推荐备用方案）⭐

如果构建失败，修改代码让 gsplat 变成可选依赖：

### 步骤 1：修改 requirements.txt

创建两个文件：

**requirements.txt** (基础依赖):
```txt
torch>=2.0.0
gradio>=5.0.0
spaces
# ... 其他基础依赖
```

**requirements-gsplat.txt** (可选依赖):
```txt
-r requirements.txt
gsplat @ git+https://github.com/nerfstudio-project/gsplat.git@0b4dddf04cb687367602c01196913cde6a743d70
```

### 步骤 2：修改代码，使 gsplat 可选

**depth_anything_3/utils/export/gs.py** (或相关文件):
```python
# 在文件开头
try:
    import gsplat
    GSPLAT_AVAILABLE = True
except ImportError:
    GSPLAT_AVAILABLE = False
    print("⚠️ gsplat not installed. 3DGS features will be disabled.")

def export_to_gs_video(*args, **kwargs):
    if not GSPLAT_AVAILABLE:
        raise RuntimeError(
            "gsplat is not installed. Please install it with:\n"
            "pip install 'gsplat @ git+https://github.com/...'"
        )
    # 原有代码...
```

**app.py** (或 gradio_app.py):
```python
from depth_anything_3.utils.export.gs import GSPLAT_AVAILABLE

# 在 UI 中隐藏 3DGS 选项如果不可用
if GSPLAT_AVAILABLE:
    infer_gs = gr.Checkbox(label="Infer 3D Gaussian Splatting")
else:
    infer_gs = gr.Checkbox(
        label="Infer 3D Gaussian Splatting (Not Available - gsplat not installed)",
        interactive=False,
        value=False
    )
```

**优点：**
- ✅ 应用仍然可以启动
- ✅ 其他功能正常工作
- ✅ 用户可以选择性安装

**缺点：**
- ⚠️ 需要修改代码
- ⚠️ 3DGS 功能不可用

---

## 方案 4️⃣：使用 Docker 自定义构建

创建自定义 Docker 镜像，在本地预编译 gsplat：

**Dockerfile:**
```dockerfile
FROM pytorch/pytorch:2.1.0-cuda11.8-cudnn8-runtime

WORKDIR /app

# 安装构建依赖
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 预编译 gsplat
RUN pip install 'gsplat @ git+https://github.com/nerfstudio-project/gsplat.git@0b4dddf04cb687367602c01196913cde6a743d70'

# 安装其他依赖
COPY requirements.txt .
RUN pip install -r requirements.txt

# 复制代码
COPY . .

CMD ["python", "app.py"]
```

**优点：**
- ✅ 完全控制构建环境
- ✅ 可以缓存编译结果
- ✅ 更可靠

**缺点：**
- ⚠️ 需要 Docker 知识
- ⚠️ 镜像较大
- ⚠️ 构建和推送时间长

---

## 方案 5️⃣：使用环境变量控制安装

**requirements.txt:**
```txt
torch>=2.0.0
gradio>=5.0.0
# 基础依赖...
```

**安装脚本** (install_gsplat.sh):
```bash
#!/bin/bash
if [ "$INSTALL_GSPLAT" = "true" ]; then
    echo "Installing gsplat..."
    pip install 'gsplat @ git+https://github.com/nerfstudio-project/gsplat.git@0b4dddf04cb687367602c01196913cde6a743d70'
else
    echo "Skipping gsplat installation"
fi
```

在 HF Spaces 设置中添加环境变量：
```
INSTALL_GSPLAT=true
```

**优点：**
- ✅ 灵活控制
- ✅ 可以快速切换

**缺点：**
- ⚠️ 需要额外脚本
- ⚠️ 不是标准方法

---

## 🔧 当前推荐配置

### 第一次尝试：方案 1（已配置）✅

**requirements.txt:**
```txt
gsplat @ git+https://github.com/nerfstudio-project/gsplat.git@0b4dddf04cb687367602c01196913cde6a743d70
```

**Space 设置：**
- 硬件：**GPU (T4 或更高)**
- Python 版本：3.11

### 如果构建失败：方案 3（延迟加载）

移除 requirements.txt 中的 gsplat，修改代码使其可选。

---

## 🐛 故障排除

### 问题 1：构建超时

**错误信息：**
```
Building wheels for collected packages: gsplat
  Building wheel for gsplat (setup.py) ... [TIMEOUT]
```

**解决方法：**
1. 确认 Space 类型是 **GPU Space**
2. 尝试使用更快的 commit/tag
3. 考虑方案 3（可选依赖）

### 问题 2：CUDA 不可用

**错误信息：**
```
torch.cuda.is_available() returned False
CUDA extension build requires CUDA to be available
```

**解决方法：**
1. 确认构建时就启用 GPU
2. 检查 PyTorch 是否是 CUDA 版本
3. 查看 [HF Spaces GPU 文档](https://huggingface.co/docs/hub/spaces-gpus)

### 问题 3：编译错误

**错误信息：**
```
error: command 'gcc' failed with exit status 1
```

**解决方法：**
1. 添加 packages.txt 安装编译工具：
   ```txt
   build-essential
   ```
2. 使用预编译版本

---

## 📊 方案对比

| 方案 | 构建时间 | 成功率 | 复杂度 | 推荐度 |
|------|---------|--------|--------|--------|
| 1. GitHub 直接安装 | 🐌 10-15分钟 | ⚠️ 70% | 简单 | ⭐⭐⭐ |
| 2. PyPI 预编译 | ⚡ 1分钟 | ✅ 95% | 最简单 | ⭐⭐⭐⭐⭐ |
| 3. 可选依赖 | ⚡ 2分钟 | ✅ 100% | 中等 | ⭐⭐⭐⭐ |
| 4. Docker | 🐌 20-30分钟 | ✅ 95% | 复杂 | ⭐⭐ |
| 5. 环境变量控制 | 🐌 10-15分钟 | ⚠️ 70% | 中等 | ⭐⭐ |

---

## 🎯 实施步骤

### 现在（已完成）✅

1. ✅ requirements.txt 中已启用 gsplat
2. ✅ Python 版本设置为 3.11
3. ✅ README.md 配置完成

### 推送到 HF Spaces 后

1. **观察构建日志**
   - 查看是否成功安装 gsplat
   - 构建时间是否合理

2. **如果构建成功** 🎉
   - 测试 3DGS 功能
   - 完成！

3. **如果构建失败** ⚠️
   - 复制错误信息
   - 根据上面的故障排除指南修复
   - 或者切换到方案 3（可选依赖）

---

## 📝 测试清单

部署前本地测试：

```bash
# 1. 测试 gsplat 安装
pip install 'gsplat @ git+https://github.com/nerfstudio-project/gsplat.git@0b4dddf04cb687367602c01196913cde6a743d70'

# 2. 测试导入
python -c "import gsplat; print('gsplat version:', gsplat.__version__)"

# 3. 测试你的代码
python -c "from depth_anything_3.utils.export.gs import export_to_gs_video; print('✅ import success')"

# 4. 启动应用测试
python app.py
```

---

## 🔗 相关资源

- [gsplat GitHub](https://github.com/nerfstudio-project/gsplat)
- [HF Spaces GPU 文档](https://huggingface.co/docs/hub/spaces-gpus)
- [PyTorch CUDA 安装](https://pytorch.org/get-started/locally/)

---

## 💡 最终建议

1. **先尝试方案 1**（当前配置）- 直接在 HF Spaces 上构建
2. **如果失败**，切换到**方案 3**（可选依赖）- 让应用可以在没有 gsplat 的情况下运行
3. **长期方案**：如果 gsplat 发布 PyPI 版本，立即切换到方案 2

祝你部署顺利！🚀

