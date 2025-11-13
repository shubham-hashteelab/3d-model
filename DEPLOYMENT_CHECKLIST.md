# 🚀 Hugging Face Spaces 部署检查清单

## ✅ 当前配置状态

### 核心文件（必需）

- ✅ **app.py** - 入口文件，带 `@spaces.GPU` 装饰器
- ✅ **requirements.txt** - Python 依赖（包含 gsplat）
- ✅ **README.md** - Space 配置（Python 3.11）
- ✅ **packages.txt** - 系统依赖（build-essential, git）
- ✅ **pyproject.toml** - 项目配置

### 备用文件（可选）

- ✅ **requirements-basic.txt** - 不包含 gsplat 的版本（如果构建失败）
- ✅ **runtime.txt** - Python 版本备用配置
- ✅ **GSPLAT_SOLUTIONS.md** - gsplat 问题解决方案
- ✅ **SPACES_SETUP.md** - 详细部署指南

---

## 📋 部署前检查

### 1. 文件检查

```bash
# 确认所有必需文件存在
[ -f app.py ] && echo "✅ app.py" || echo "❌ app.py missing"
[ -f requirements.txt ] && echo "✅ requirements.txt" || echo "❌ requirements.txt missing"
[ -f README.md ] && echo "✅ README.md" || echo "❌ README.md missing"
[ -d src/depth_anything_3 ] && echo "✅ Source code" || echo "❌ Source code missing"
```

### 2. 配置检查

**README.md 必须包含：**
```yaml
---
sdk: gradio
app_file: app.py
python_version: 3.11
---
```

**requirements.txt 必须包含：**
```txt
torch>=2.0.0
gradio>=5.0.0
spaces
gsplat @ git+https://...  # 如果需要 3DGS
```

**app.py 必须包含：**
```python
import spaces
@spaces.GPU(duration=120)
def gpu_run_inference(self, *args, **kwargs):
    ...
```

### 3. 本地测试（推荐）

```bash
# 测试 Python 版本
python --version  # 应该是 3.11+

# 测试安装依赖
pip install -r requirements.txt

# 测试应用启动
python app.py

# 测试 gsplat（如果需要）
python -c "import gsplat; print('✅ gsplat OK')"
```

---

## 🎯 部署步骤

### 方式 A：通过网页界面

1. **创建 Space**
   - 访问 https://huggingface.co/new-space
   - Space name: 输入名称
   - SDK: 选择 **Gradio**
   - Hardware: 选择 **GPU (T4 或更高)**
   - Visibility: Public/Private

2. **上传文件**
   - 上传所有文件（app.py, requirements.txt, src/, 等）
   - 或者通过 Git 克隆上传

3. **等待构建**
   - 查看 "Build logs" 标签
   - 首次构建可能需要 10-20 分钟（因为 gsplat）

4. **测试应用**
   - 构建成功后自动启动
   - 测试所有功能

### 方式 B：通过 Git

```bash
# 1. 创建 Space（通过网页）

# 2. 克隆 Space 仓库
git clone https://huggingface.co/spaces/YOUR_USERNAME/YOUR_SPACE_NAME
cd YOUR_SPACE_NAME

# 3. 复制文件
cp -r /path/to/depth-anything-3/* .

# 4. 提交并推送
git add .
git commit -m "Initial deployment"
git push

# 5. 查看构建日志
# 在网页界面查看
```

---

## 🐛 常见问题快速解决

### 问题 1：gsplat 构建失败 ⚠️

**症状：**
```
Building wheel for gsplat (setup.py) ... error
```

**快速修复：**
```bash
# 方法 1: 切换到不含 gsplat 的版本
mv requirements.txt requirements-full.txt
mv requirements-basic.txt requirements.txt
git commit -am "Use basic requirements without gsplat"
git push
```

**或者在网页界面：**
1. 打开 requirements.txt
2. 注释掉 gsplat 那行：`# gsplat @ git+...`
3. 提交更改

详见：`GSPLAT_SOLUTIONS.md`

### 问题 2：构建超时

**症状：**
```
Build timeout after 60 minutes
```

**解决方法：**
1. 使用 requirements-basic.txt（不含 gsplat）
2. 或者联系 HF 支持增加构建时间限制

### 问题 3：应用启动失败

**症状：**
```
ModuleNotFoundError: No module named 'depth_anything_3'
```

**解决方法：**
1. 确认 `src/` 目录结构正确
2. 在 app.py 开头添加：
   ```python
   import sys
   sys.path.append('./src')
   ```

### 问题 4：GPU 不可用

**症状：**
```
torch.cuda.is_available() = False
```

**解决方法：**
1. 确认 Space 硬件选择了 **GPU**（不是 CPU）
2. 在 Settings 中切换到 GPU 硬件
3. 可能需要付费 GPU（T4 是最便宜的）

---

## 📊 构建时间预估

| 配置 | 首次构建 | 后续构建 | 启动时间 |
|------|---------|---------|---------|
| 含 gsplat | 15-25 分钟 | 2-5 分钟* | 30-60 秒 |
| 不含 gsplat | 5-10 分钟 | 1-2 分钟* | 20-40 秒 |

*后续构建可能使用缓存

---

## 🎓 部署后测试清单

### 基础功能

- [ ] 应用成功启动
- [ ] 可以访问 Space URL
- [ ] UI 正常显示
- [ ] 可以上传图片/视频

### 深度估计功能

- [ ] 可以运行深度估计
- [ ] 结果正确显示
- [ ] Point Cloud 可视化正常
- [ ] 相机姿态显示正常

### 3DGS 功能（如果启用 gsplat）

- [ ] 3DGS 选项可见
- [ ] 可以生成 3DGS 视频
- [ ] 视频可以播放

### 性能测试

- [ ] GPU 正确识别
- [ ] 推理速度合理（不超时）
- [ ] 内存使用正常

---

## 💾 配置文件快速参考

### README.md
```yaml
---
title: Depth Anything 3
sdk: gradio
sdk_version: 5.49.1
app_file: app.py
python_version: 3.11
---
```

### app.py 关键部分
```python
import spaces
from depth_anything_3.app.gradio_app import DepthAnything3App

original_run_inference = ModelInference.run_inference

@spaces.GPU(duration=120)
def gpu_run_inference(self, *args, **kwargs):
    return original_run_inference(self, *args, **kwargs)

ModelInference.run_inference = gpu_run_inference

if __name__ == "__main__":
    app = DepthAnything3App(...)
    app.launch(host="0.0.0.0", port=7860)
```

### requirements.txt 关键依赖
```txt
torch>=2.0.0
gradio>=5.0.0
spaces
gsplat @ git+https://github.com/nerfstudio-project/gsplat.git@0b4dddf04cb687367602c01196913cde6a743d70
```

### packages.txt
```txt
build-essential
git
```

---

## 🔗 相关文档

本项目的详细文档：

1. **SPACES_SETUP.md** - 完整部署指南和 Spaces 机制说明
2. **GSPLAT_SOLUTIONS.md** - gsplat 安装的各种解决方案
3. **HF_SPACES_BUILD.md** - HF Spaces 构建流程详解
4. **PYTHON_VERSION_CONFIG.md** - Python 版本配置说明

外部资源：

- [HF Spaces 文档](https://huggingface.co/docs/hub/spaces)
- [Gradio 文档](https://gradio.app/docs)
- [gsplat GitHub](https://github.com/nerfstudio-project/gsplat)

---

## 📞 获取帮助

如果遇到问题：

1. **查看构建日志** - Space 页面的 "Build logs" 标签
2. **查看运行日志** - Space 页面的 "Logs" 标签
3. **参考文档** - 本项目的 *.md 文档
4. **HF 论坛** - https://discuss.huggingface.co/
5. **GitHub Issues** - 项目的 Issues 页面

---

## ✨ 成功部署后

恭喜！🎉 你的 Depth Anything 3 应用已经在 HF Spaces 上运行了！

**下一步：**

1. 📝 更新 README.md 添加使用说明
2. 🎨 自定义 UI（如果需要）
3. 📊 监控使用情况
4. 🔄 根据反馈持续改进

**分享你的 Space：**
- Space URL: `https://huggingface.co/spaces/YOUR_USERNAME/YOUR_SPACE_NAME`
- 可以嵌入到网页、博客等

祝你使用愉快！🚀

