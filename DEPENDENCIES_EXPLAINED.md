# 📦 依赖说明文档

## requirements.txt 完整依赖清单

### ✅ 已包含的所有依赖

---

## 🎨 核心依赖

### PyTorch 相关
```txt
torch>=2.0.0        # 深度学习框架
torchvision         # 计算机视觉工具
```

**用途：** 
- 模型训练和推理
- 图像处理
- GPU 加速

**注意：**
- 会自动安装与 CUDA 兼容的版本
- Spaces 上会安装预编译的 CUDA 版本

---

## 🖼️ 图像和视频处理

### 图像处理
```txt
opencv-python       # OpenCV - 图像处理
pillow>=9.0         # PIL - 图像读写
imageio             # 多格式图像 I/O
pillow_heif         # HEIF/HEIC 格式支持（苹果照片）
```

### 视频处理
```txt
moviepy==1.0.3      # 视频处理和编辑
```

**用途：**
- 读取上传的图片和视频
- 视频帧提取
- 结果可视化
- 支持 HEIC 等苹果格式

---

## 🎮 Gradio 和 Spaces

```txt
gradio>=5.0.0       # Web UI 框架
spaces              # HF Spaces GPU 支持
```

**用途：**
- 创建交互式 Web 界面
- 动态 GPU 分配（@spaces.GPU）

**关键：**
- Gradio 5+ 需要 Python 3.10+
- `spaces` 是 HF Spaces 专用包

---

## 🎲 3D 可视化

```txt
trimesh             # 3D 网格处理
open3d              # 3D 数据可视化
plyfile             # PLY 格式支持
```

**用途：**
- 点云可视化
- 3D 网格导出（GLB 格式）
- 相机姿态可视化

---

## 🔢 数学和科学计算

```txt
numpy<2             # 数值计算（限制 v1.x）
einops              # 张量操作简化
e3nn                # 等变神经网络（3D 几何）
```

**注意：**
- `numpy<2` 是因为某些包还不兼容 NumPy 2.0
- `e3nn` 用于 3D 旋转和几何变换

---

## 🌐 Web 框架（可选）

```txt
fastapi             # 现代 Python Web 框架
uvicorn             # ASGI 服务器
```

**用途：**
- 如果需要构建 REST API
- CLI 工具的后端支持

**在 Gradio 应用中：**
- 通常不需要（Gradio 自带服务器）
- 但保留以支持 CLI 模式（`da3` 命令）

---

## 🛠️ 工具库

```txt
requests            # HTTP 请求
omegaconf           # 配置文件管理
typer>=0.9.0        # CLI 框架
huggingface_hub     # HF 模型下载
safetensors         # 安全的模型格式
evo                 # 评估工具（轨迹评估）
```

**用途：**
- 模型下载（从 HF Hub）
- 配置文件解析
- 命令行接口（`da3` 命令）
- 轨迹评估和可视化

---

## 🌟 3D Gaussian Splatting

```txt
gsplat @ https://github.com/nerfstudio-project/gsplat/releases/download/v1.5.3/gsplat-1.5.3+pt24cu124-cp310-cp310-linux_x86_64.whl
```

**⚠️ 重要警告：当前配置问题！**

你的配置使用了 **Python 3.10** 的 wheel (`cp310`)，但 README.md 配置的是 **Python 3.11**！

**需要修改为对应 Python 3.11 的版本：**

### 选项 1：使用 Python 3.11 的预编译 wheel ⭐

```txt
# 需要找到或构建 cp311 版本
gsplat @ https://github.com/nerfstudio-project/gsplat/releases/download/v1.5.3/gsplat-1.5.3+pt24cu124-cp311-cp311-linux_x86_64.whl
```

### 选项 2：从源码安装（原方案）

```txt
gsplat @ git+https://github.com/nerfstudio-project/gsplat.git@0b4dddf04cb687367602c01196913cde6a743d70
```

### 选项 3：降级 Python 到 3.10

修改 `README.md`:
```yaml
python_version: 3.10  # 改为 3.10
```

---

## ❌ 不包含的依赖（故意排除）

### pre-commit
```txt
# NOT included in requirements.txt
pre-commit
```

**原因：**
- 仅用于开发环境
- 生产部署不需要
- 会增加不必要的依赖

**如果本地开发需要：**
```bash
pip install pre-commit
pre-commit install
```

### xformers
```txt
# Commented out
# xformers
```

**原因：**
- 可能与某些 CUDA 版本不兼容
- 构建时间长
- 不是必需的（可选加速）

**如果需要（加速 attention 计算）：**
```bash
# 安装后手动添加
pip install xformers --no-deps
```

---

## 📊 依赖统计

| 类别 | 数量 | 关键包 |
|------|------|--------|
| 核心框架 | 2 | torch, gradio |
| 图像处理 | 4 | opencv, pillow, imageio |
| 3D 处理 | 4 | trimesh, open3d, gsplat |
| 数学计算 | 3 | numpy, einops, e3nn |
| Web/API | 2 | fastapi, uvicorn |
| 工具库 | 6 | requests, typer, etc. |
| **总计** | **21+** | |

---

## 🔍 版本兼容性检查

### Python 版本要求

| 包 | 最低 Python | 推荐 Python |
|----|------------|------------|
| gradio>=5 | 3.10 | 3.11 ✅ |
| torch>=2 | 3.8 | 3.11 ✅ |
| open3d | 3.8 | 3.11 ✅ |
| gsplat | 3.8 | 3.10/3.11 ⚠️ |

### CUDA 版本要求

当前配置假设：
- **CUDA 12.4** (`cu124` in gsplat wheel)
- **PyTorch 2.4** (`pt24` in gsplat wheel)

**验证命令：**
```python
import torch
print(f"PyTorch: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
print(f"CUDA version: {torch.version.cuda}")
```

---

## 🐛 常见问题

### Q1: gsplat wheel 版本不匹配

**错误信息：**
```
ERROR: gsplat-1.5.3+pt24cu124-cp310-cp310-linux_x86_64.whl is not a supported wheel on this platform.
```

**解决方法：**
1. 检查 Python 版本：`python --version`
2. 使用匹配的 wheel（cp310 for 3.10, cp311 for 3.11）
3. 或者从源码安装

### Q2: numpy 版本冲突

**错误信息：**
```
ERROR: package requires numpy<2
```

**解决方法：**
- 确保 `numpy<2` 在 requirements.txt 中
- 某些旧包不支持 NumPy 2.0

### Q3: xformers 构建失败

**解决方法：**
- 保持注释（不安装）
- 或使用预编译版本：
  ```bash
  pip install xformers==0.0.22  # 匹配你的 PyTorch 版本
  ```

---

## ✅ 完整性检查清单

部署前检查：

- [ ] ✅ 所有核心依赖已包含
- [ ] ✅ Python 版本匹配（3.11）
- [ ] ⚠️ gsplat wheel 版本匹配 Python 版本
- [ ] ✅ 不包含开发依赖（pre-commit）
- [ ] ✅ 可选依赖已注释说明（xformers）

---

## 🔧 本地测试安装

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 验证关键包
python -c "import torch; print('✅ PyTorch:', torch.__version__)"
python -c "import gradio; print('✅ Gradio:', gradio.__version__)"
python -c "import trimesh; print('✅ Trimesh OK')"

# 尝试导入 gsplat（可能失败如果 wheel 版本不匹配）
python -c "import gsplat; print('✅ gsplat:', gsplat.__version__)"
```

---

## 📝 总结

### 当前配置状态：

✅ **完整性**：所有必需依赖已包含  
⚠️ **兼容性**：gsplat wheel 需要匹配 Python 3.11  
✅ **文档**：依赖用途已说明  
✅ **备用方案**：提供了 requirements-basic.txt

### 建议：

1. **修复 gsplat 版本不匹配**：
   - 选项 A：找 Python 3.11 的 wheel
   - 选项 B：改回从源码安装
   - 选项 C：降级到 Python 3.10

2. **测试完整安装流程**

3. **监控构建日志**

