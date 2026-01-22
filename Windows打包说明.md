# Windows 打包说明

## 方法一：在 Windows 电脑上打包（推荐）

### 步骤 1：安装 Python
1. 下载 Python：https://www.python.org/downloads/
2. 安装时勾选 "Add Python to PATH"

### 步骤 2：安装依赖
打开命令提示符（CMD），运行：
```cmd
pip install requests pandas pyinstaller
```

### 步骤 3：复制文件
将以下文件复制到 Windows 电脑：
- `slp_scraper_simple.py`

### 步骤 4：打包成 exe
在文件所在目录打开命令提示符，运行：
```cmd
pyinstaller --onefile --console --name "SLP商品爬虫" slp_scraper_simple.py
```

### 步骤 5：获取 exe
打包完成后，exe 文件在 `dist` 文件夹中：
```
dist/SLP商品爬虫.exe
```

---

## 方法二：直接运行 Python 脚本

如果不想打包，也可以直接运行 Python 脚本：

1. 安装 Python
2. 安装依赖：`pip install requests pandas`
3. 双击 `slp_scraper_simple.py` 运行

---

## 打包参数说明

| 参数 | 说明 |
|------|------|
| `--onefile` | 打包成单个 exe 文件 |
| `--console` | 显示控制台窗口（查看进度） |
| `--name` | 指定 exe 文件名 |

如果不想显示黑窗口，可以用 `--noconsole` 替代 `--console`，但这样看不到运行进度。

---

## 常见问题

### Q: 杀毒软件报毒？
A: PyInstaller 打包的 exe 可能被误报，添加到白名单即可。

### Q: exe 文件很大？
A: 正常，因为包含了 Python 解释器和所有依赖库。

### Q: 运行后没有生成 CSV？
A: 检查网络连接，确保能访问 slptrading.com.au
