# IntelliJ IDEA 打开与配置指南：macOS / Windows

本指南从打开项目开始，完成 Python 插件、虚拟环境、模块解释器、源码目录、Run/Debug 和 DeepSeek 配置。

项目使用 `src` 目录布局，Python 版本要求为 **3.12 及以上**。本机开发环境为 Python 3.12.16。可先运行 `./start.sh graph` 输出流程图，确认环境配置正确。

菜单名称随 IDEA 版本、语言和 Keymap 略有不同；以下以英文菜单为准，可在对应中文菜单中查找。

## 1. 两个平台的关键区别

| 项目 | macOS | Windows |
| --- | --- | --- |
| 本文项目路径 | `/Users/niyongzhe/Code/Ai/agentic` | 示例为 `D:\Code\agentic`，请替换为实际路径 |
| 虚拟环境解释器 | `.venv/bin/python` | `.venv\Scripts\python.exe` |
| 终端 | Terminal / zsh | PowerShell |
| Settings 入口 | `IntelliJ IDEA → Settings` | `File → Settings` |
| SDK / 模块配置入口 | `File → Project Structure` | `File → Project Structure` |
| 终端启动方式 | `./start.sh run ...` 或 `.venv/bin/python -m agentic ...` | `.\.venv\Scripts\python.exe -m agentic ...` |

虚拟环境需要在目标电脑上创建，不能直接将 macOS 的 `.venv` 复制到 Windows 使用。IDEA 中保存的 SDK 名称和路径也需要在另一台电脑重新绑定。[Python 虚拟环境说明](https://docs.python.org/3.12/library/venv.html)

## 2. macOS：从打开项目到成功运行

### 步骤 1：打开项目根目录

1. 启动 IntelliJ IDEA，在欢迎页点击 **Open**；已有窗口时使用 **File → Open**。
2. 选择 `/Users/niyongzhe/Code/Ai/agentic` 文件夹。
3. 打开后，应能看到 `pyproject.toml`、`src`、`tests`、`docs` 和 `.env.example`。

这里应打开包含 `pyproject.toml` 的整个目录，而不是单独打开 `src` 或 `.idea`。[打开项目说明](https://www.jetbrains.com/help/idea/open-close-and-move-projects.html)

### 步骤 2：启用 Python 插件

1. 打开 **IntelliJ IDEA → Settings → Plugins**。
2. 在 Installed 中确认 **Python** 插件已经启用；若未安装，在 Marketplace 中搜索并安装 JetBrains 提供、与当前 IDEA 兼容的 Python 插件。
3. 根据提示重启 IDEA。

重启后，添加 SDK 时应出现 Python 选项，创建运行配置时应出现 Python 类型。

### 步骤 3：确认或创建虚拟环境

**当前这台 Mac 的 `.venv` 已创建、依赖已安装，可以先执行验证命令：**

```bash
cd /Users/niyongzhe/Code/Ai/agentic
.venv/bin/python -V
.venv/bin/python -c 'import agentic, langgraph, langchain_openai; print("imports OK")'
```

预期显示 `Python 3.12.16` 和 `imports OK`。

如果换了电脑或当前目录尚无 `.venv`，使用已有的 pyenv 创建环境：

```bash
cd /Users/niyongzhe/Code/Ai/agentic
pyenv install -s 3.12.16
pyenv local 3.12.16
pyenv exec python -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python -m pip install --no-deps -e .
```

最后一条是将当前项目以可编辑方式安装到虚拟环境，使解释器能够找到 `src/agentic`。

### 步骤 4：将现有虚拟环境添加为 Python SDK

1. 打开 **File → Project Structure → Platform Settings → SDKs**。
2. 点击 **+ → Add Python SDK from disk…**。
3. 选择本机的已有 Python / Existing environment，而不是创建新环境。
4. 解释器指定为：

```text
/Users/niyongzhe/Code/Ai/agentic/.venv/bin/python
```

如果文件选择器里看不到隐藏的 `.venv`，可使用 macOS 文件选择器的 **⌘⇧G** 输入完整路径。

保存后建议将 SDK 命名为 `Python 3.12 (agentic)`，方便后续辨认。[Python SDK 配置说明](https://www.jetbrains.com/help/idea/configuring-python-sdk.html)

### 步骤 5：把 Python SDK 绑定到实际模块

**如果 `agentic` 已是 Python 模块：** 在 **Project Structure → Modules** 中选择 `agentic`，将模块的 SDK / Python Interpreter 设置为刚添加的 `Python 3.12 (agentic)`。纯 Python 项目也可将 **Project → SDK** 设置为该解释器。

**如果 `agentic` 仍是 Java 模块：** 使用 **Project Structure → Facets → + → Python**，选择 `agentic` 模块，再在 Python Interpreter 中选择刚添加的 SDK。

这两种情况选择适合当前模块的一种。Python 模块直接配置 SDK；Java 模块通过 Python facet 获得 Python 支持。Java 模块正确配置 Python facet 后，项目仍显示 Java SDK 并不代表 Python 配置失败。关键是该模块的 Python 解释器已绑定。[非 Python 模块的配置说明](https://www.jetbrains.com/help/idea/configuring-python-sdk.html#add-python-support-to-a-non-python-module)

点击 **Apply → OK**，等待 IDEA 建立索引。

### 步骤 6：检查源码目录

在 **Project Structure → Modules → agentic → Sources** 中，按第 4 节的目录表检查设置。Content Root 应为项目根目录；`src` 是 Sources，`tests` 是 Test Sources。

### 步骤 7：创建运行与调试配置

按第 5 节创建 `Agentic Run` 运行配置。完成后点击 **Run**，应看到报告和最终状态。

## 3. Windows：从打开项目到成功运行

以下命令使用 **PowerShell**，以 `D:\Code\agentic` 为示例路径。请先将代码放到 Windows 的实际项目目录；`.venv` 在 Windows 本机创建。

### 步骤 1：打开项目根目录

1. 启动 IntelliJ IDEA，选择欢迎页的 **Open** 或 **File → Open**。
2. 选择 `D:\Code\agentic`，即包含 `pyproject.toml` 的文件夹。
3. 确认项目树中存在 `src`、`tests`、`docs` 和 `.env.example`。

### 步骤 2：启用 Python 插件

打开 **File → Settings → Plugins**，确认 JetBrains 的 Python 插件已安装并启用；按提示重启 IDEA。

### 步骤 3：创建 Windows 虚拟环境并安装依赖

先确认 Windows 已安装 Python 3.12 和 Python Launcher：

```powershell
py -3.12 -V
```

项目允许 Python 3.12.x。若尚未安装，可参考 [Python 官方 Windows 安装说明](https://docs.python.org/3.12/using/windows.html) 准备 Python 和 Launcher。若只有其他满足要求的 Python 版本，创建环境时使用对应的启动命令，并确认版本至少为 3.12。

已准备 Python 3.12 时，执行：

```powershell
Set-Location 'D:\Code\agentic'
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
.\.venv\Scripts\python.exe -m pip install --no-deps -e .
.\.venv\Scripts\python.exe -V
.\.venv\Scripts\python.exe -c "import agentic, langgraph, langchain_openai; print('imports OK')"
```

已有 Windows 本机的 `.venv` 时，可直接执行最后两条验证，成功后复用现有环境。以上命令显式使用虚拟环境解释器，不需要运行 `Activate.ps1`。

### 步骤 4：添加 Windows Python SDK

1. 打开 **File → Project Structure → Platform Settings → SDKs**。
2. 点击 **+ → Add Python SDK from disk…**。
3. 选择已有的本机 Python 环境，解释器指定为：

```text
D:\Code\agentic\.venv\Scripts\python.exe
```

4. 保存并命名为 `Python 3.12 (agentic)`。

这里选择 `.exe` 文件；不要选择 `.venv` 文件夹或来自另一台电脑的解释器路径。

### 步骤 5：将解释器绑定到模块

Python 模块在 **Project Structure → Modules → agentic** 中选择上述 Python SDK；Java 模块则在 **Project Structure → Facets → + → Python** 中为 `agentic` 添加 Python facet，并选择上述解释器。

点击 **Apply → OK**。仅在 SDKs 中添加解释器，还需要完成这一步的模块绑定。

### 步骤 6：检查目录标记

按第 4 节配置 `src`、`tests` 和 `.venv`，Content Root 使用 Windows 的实际项目路径，例如 `D:\Code\agentic`。

### 步骤 7：运行与调试

按第 5 节创建 Python 运行配置，解释器选择 `.venv\Scripts\python.exe`，Working directory 选择 Windows 项目根目录。

也可以在 PowerShell 直接运行演示：

```powershell
Set-Location 'D:\Code\agentic'
.\.venv\Scripts\python.exe -m agentic run "设计一个客服助手"
```

Windows 原生 PowerShell 使用上面的命令启动；项目的 `start.sh` 是 Bash 脚本。

## 4. 两个平台通用：Content Root 与目录标记

打开 **File → Project Structure → Modules → agentic → Sources**，检查：

| 目录 | 标记 |
| --- | --- |
| 项目根目录 `agentic` | Content Root |
| `src` | Sources / Sources Root |
| `tests` | Test Sources / Test Sources Root |
| `.venv` | Excluded |

Content Root 指向包含 `pyproject.toml` 的目录。标记 `src` 为源码根目录，使包名从其内部的 `agentic` 开始。

也可在左侧项目树中右键相应目录，使用 **Mark Directory As** 修改标记。`.venv` 标记为 Excluded 后，仍可通过选定解释器索引其安装的依赖。[目录标记说明](https://www.jetbrains.com/help/idea/content-roots.html)

保存后应能看到 `src/agentic/cli.py` 等文件。若项目树或路径仍显示旧配置，关闭并重新打开项目，等待索引完成。

## 5. 两个平台通用：Run / Debug 配置

打开 **Run → Edit Configurations… → + → Python**，按下表填写：

| 字段 | 值 |
| --- | --- |
| Name | `Agentic Run` |
| 目标类型 | **Module name**，部分版本由 Script path 旁的下拉菜单切换 |
| Module name | `agentic` |
| Parameters | `run "设计一个客服助手" --output output/idea-report.md` |
| Python Interpreter | 当前项目 `.venv` 对应的 Python SDK |
| Working directory | 项目根目录，可使用目录选择器填写实际绝对路径 |
| Add source roots to PYTHONPATH | 勾选（若该选项可见） |

目标使用模块名 `agentic`，对应终端命令 `python -m agentic`。Working directory 决定 `.env` 的读取位置和相对输出路径。[Python 运行配置说明](https://www.jetbrains.com/help/pycharm/run-debug-configuration-python.html)

点击 **Apply → OK**，然后 **Run → Run 'Agentic Run'**。正常结果是生成 Markdown 报告，末尾显示 `状态：approved` 或 `revision_limit`，并在项目的 `output/idea-report.md` 保存报告。

调试时，在 `src/agentic/cli.py` 的 `state = initial_state(...)` 一行设置断点，再选择 **Run → Debug 'Agentic Run'**。程序应停在断点处，可查看目标等变量。

## 6. 两个平台分别配置 DeepSeek

### macOS

在项目根目录的终端执行：

```bash
cp -n .env.example .env
```

### Windows / PowerShell

在项目根目录执行；已有 `.env` 时保留其内容：

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

### IDEA 中编辑与运行

使用编辑器打开项目根目录的 `.env`，填写 `DEEPSEEK_API_KEY`；其余项目默认配置见 `.env.example`。第 5 节的 `Agentic Run` 配置即可直接调用 DeepSeek，Parameters 为：

```text
run "设计一个企业知识库问答助手" --output output/deepseek-report.md
```

解释器和 Working directory 保持指向本机项目环境。程序会自行读取根目录 `.env`，无需额外安装读取 `.env` 的 IDEA 插件。Run Configuration 中已有的同名环境变量优先于 `.env`。

模型运行需要有效的 DeepSeek API Key；配置与业务流程的详细介绍见 [启动与项目介绍](启动与项目介绍.md)。

## 7. 配置完成后的验收

在 IDEA 的 **Tools → Python Console** 中执行以下代码；部分版本可通过菜单搜索找到 Python Console：

```python
import sys
import agentic
import langgraph
import langchain_openai

print(sys.version)
print(sys.executable)
print(agentic.__file__)
```

应满足以下条件：

- Python 版本至少为 3.12。
- macOS 的 `sys.executable` 指向本项目 `.venv/bin/python`，Windows 指向本项目 `.venv\Scripts\python.exe`。
- `agentic.__file__` 指向本项目 `src/agentic/__init__.py`。
- 所有 import 成功，`Agentic Run` 能运行并生成报告。

终端中激活了虚拟环境，不代表 IDEA 的代码分析器、Python Console 和 Run Configuration 已自动使用同一解释器；分别确认这些位置的设置。

## 8. 常见问题排查顺序

| 现象 | 检查方式 |
| --- | --- |
| 没有 Python SDK 或 Python 运行类型 | 检查 Python 插件是否安装、启用并适配当前 IDEA 版本，安装后重启 |
| `langgraph`、`langchain_openai` 标红 | 检查模块 / facet 解释器是否为项目 `.venv`，并确认依赖安装到了该环境 |
| 只有 `agentic` 标红或运行提示找不到包 | 确认 `src` 是 Sources Root，并已用项目解释器执行 `-m pip install --no-deps -e .` |
| 添加了 SDK 后仍标红 | 检查 SDK 是否绑定到了实际模块或 Python facet，点击 Apply / OK 并等待索引 |
| 仍看到项目 SDK 是 Java | 查看模块是否已有绑定正确解释器的 Python facet；项目 Java SDK 与 Python facet 可以共存 |
| 提示 Invalid environment | 检查本机的解释器文件是否存在，移动项目或更换系统后重新创建 `.venv` 并重新绑定 |
| 终端运行成功，IDEA 运行失败 | 比较两边的解释器、Working directory 和环境变量 |
| 读取不到 DeepSeek 密钥 | 确认 `.env` 在项目根目录，运行配置的 Working directory 也为项目根目录 |
| Windows 提示 `py` 不存在 | 检查 Python Launcher 安装；也可使用已安装且版本满足要求的 `python.exe` 完整路径创建 `.venv` |

本指南的 macOS 解释器与演示命令已在当前项目验证。Windows 部分提供原生 PowerShell 和对应路径的配置步骤，尚未在 Windows 实机执行。
