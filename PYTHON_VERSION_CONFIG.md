# Python 版本配置说明

## 📋 Python 版本配置位置

### ✅ 已为你配置的 3 个地方：

---

## 1️⃣ README.md (Hugging Face Spaces) ⭐ **最重要**

```yaml
---
title: Depth Anything 3
sdk: gradio
sdk_version: 5.49.1
app_file: app.py
python_version: 3.11    # 🔑 关键配置
---
```

**作用范围：** Hugging Face Spaces 部署
**优先级：** 🔥 最高（Spaces 专用）

**支持的版本：**
- `3.8`
- `3.9`
- `3.10`
- `3.11` ✅ (你选择的)
- `3.12` (较新，可能有兼容性问题)

**注意：**
- 这是 HF Spaces 唯一识别的配置
- 如果不指定，默认使用 `3.10`
- 必须是精确版本号（如 `3.11`），不能用范围（如 `>=3.11`）

---

## 2️⃣ pyproject.toml (项目配置)

```toml
[project]
requires-python = ">=3.11"  # ✅ 已配置
```

**作用范围：** 
- 本地开发
- pip 安装时版本检查
- 包管理器（poetry, hatch 等）

**优先级：** 中等

**支持格式：**
```toml
requires-python = ">=3.11"           # 最低 3.11
requires-python = ">=3.11, <3.13"    # 3.11 到 3.12
requires-python = "~=3.11"           # 3.11.x 系列
```

**效果：**
```bash
# 如果 Python 版本不符合要求，安装时会报错
$ pip install .
ERROR: Package requires a different Python: 3.9.0 not in '>=3.11'
```

---

## 3️⃣ runtime.txt (备用方式)

```txt
python-3.11
```

**作用范围：** 
- Heroku
- 某些 Docker 构建系统
- HF Spaces (备用，如果 README.md 没有配置)

**优先级：** 低

**格式：**
```txt
python-3.11      # ✅ 精确版本
python-3.11.5    # ✅ 更精确的版本
```

---

## 🎯 配置优先级（Hugging Face Spaces）

```
README.md (python_version) 
    ↓ 最高优先级
runtime.txt
    ↓ 次要优先级
默认版本 (3.10)
    ↓ 兜底
```

**最佳实践：** 同时配置 `README.md` 和 `pyproject.toml`

---

## 🔍 如何验证配置生效？

### 在 Hugging Face Spaces：

部署后，查看构建日志：

```bash
# 日志中会显示
Setting up Python 3.11...
Python 3.11.5
pip 23.2.1
```

### 在本地验证：

```bash
# 检查 Python 版本
python --version
# Python 3.11.5

# 尝试安装（检查 requires-python）
pip install -e .
# 如果版本不符合，会报错
```

---

## 🚨 常见问题

### Q1: 为什么选择 Python 3.11？

**优点：**
- ✅ 性能提升（比 3.10 快 10-60%）
- ✅ 更好的错误信息
- ✅ 新的类型特性
- ✅ Gradio 5+ 完全支持

**注意：**
- ⚠️ 某些老库可能不支持（如 gsplat）
- ⚠️ 需要测试所有依赖是否兼容

### Q2: 如果我想支持多个版本怎么办？

**pyproject.toml 配置：**
```toml
requires-python = ">=3.11, <3.13"  # 支持 3.11 和 3.12
```

**但 HF Spaces 只能选一个：**
```yaml
python_version: 3.11  # 只能指定一个精确版本
```

### Q3: 如何测试不同 Python 版本？

**使用 pyenv：**
```bash
# 安装多个 Python 版本
pyenv install 3.11.5
pyenv install 3.12.0

# 切换版本测试
pyenv local 3.11.5
python --version
pip install -e .
python app.py
```

**使用 Docker：**
```dockerfile
FROM python:3.11
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["python", "app.py"]
```

### Q4: 版本冲突怎么办？

**场景：** 某个依赖不支持 Python 3.11

**解决方法：**

1. **找替代包**
   ```txt
   # requirements.txt
   old-package  # 不支持 3.11
   ↓
   new-package  # 支持 3.11
   ```

2. **降级 Python 版本**
   ```yaml
   python_version: 3.10  # 改回 3.10
   ```

3. **等待上游更新**
   ```bash
   pip install git+https://github.com/xxx/package@main
   ```

---

## 📊 Python 版本兼容性参考

| Python 版本 | Gradio 5 | PyTorch 2.x | Spaces 支持 | 推荐 |
|------------|----------|-------------|------------|------|
| 3.8 | ✅ | ✅ | ✅ | ❌ (太旧) |
| 3.9 | ✅ | ✅ | ✅ | ⚠️ |
| 3.10 | ✅ | ✅ | ✅ | ✅ |
| 3.11 | ✅ | ✅ | ✅ | ⭐ 推荐 |
| 3.12 | ✅ | ⚠️ | ✅ | ⚠️ (较新) |
| 3.13 | ⚠️ | ❌ | ⚠️ | ❌ (太新) |

---

## 🎓 完整配置示例

### 你当前的配置（已完成）✅

**README.md:**
```yaml
---
python_version: 3.11
---
```

**pyproject.toml:**
```toml
requires-python = ">=3.11"
```

**runtime.txt:**
```txt
python-3.11
```

### 如果要降级到 3.10：

**README.md:**
```yaml
python_version: 3.10
```

**pyproject.toml:**
```toml
requires-python = ">=3.10"
```

**runtime.txt:**
```txt
python-3.10
```

---

## 🔧 测试清单

部署前检查：

- [ ] ✅ README.md 有 `python_version: 3.11`
- [ ] ✅ pyproject.toml 有 `requires-python = ">=3.11"`
- [ ] ✅ 本地测试使用 Python 3.11
- [ ] ✅ 所有依赖支持 Python 3.11
- [ ] ✅ requirements.txt 包含所有依赖
- [ ] ✅ app.py 可以正常启动

---

## 📚 参考资料

- [HF Spaces Python 版本文档](https://huggingface.co/docs/hub/spaces-config-reference#python_version)
- [Python 版本发布时间表](https://devguide.python.org/versions/)
- [PyPI 包兼容性查询](https://pypi.org/)

---

## 💡 总结

**对于 Hugging Face Spaces 部署：**

1. **必须配置：** `README.md` 中的 `python_version: 3.11`
2. **推荐配置：** `pyproject.toml` 中的 `requires-python = ">=3.11"`
3. **可选配置：** `runtime.txt`（备用）

**当前配置状态：** ✅ 全部已配置完成！

