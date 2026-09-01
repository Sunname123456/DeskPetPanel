# 桌宠工作面板（DeskPetPanel）

一个面向 Windows 的本地 Live2D 桌宠与快捷工作区。桌宠支持点击互动、动作、表情、贴纸、语音、音量和定时随机互动；工作区可集中管理程序、文件及文件夹，并支持图片或视频背景。

> 本项目为非官方个人项目。应用源码、第三方运行库以及模型、图片、语音、音乐素材适用不同条款；请同时阅读 [许可证与素材说明](#许可证与素材说明)。

## 功能概览

- 透明置顶 Live2D 桌宠，支持鼠标视线跟随。
- 单击桌宠进行随机互动，并打开或收起工作区。
- 拖动改变位置，滚轮以 20 像素步长缩放。
- 可在 Live2D 桌宠与悬浮球之间切换。
- 5 组模型动作、3 组模型表情。
- 8 组二维动作，共 37 帧。
- 28 类贴纸状态、33 个贴纸资源。
- 17 段本地语音，包含问候、电量提醒和互动内容。
- 音量范围 `0%–100%`，默认 `17%`。
- 随机互动间隔可设为关闭、30 秒、1/3/5/10/15/30 分钟，默认 3 分钟。
- 将程序、文件或文件夹拖入桌宠/工作区即可添加。
- 从桌面添加的项目仅设置 Windows“隐藏”属性，原文件仍保留在原位置。
- 支持打开项目、打开所在文件夹、隐藏、恢复以及从面板移除。
- 工作区最大化后可自由拖动排列图标。
- 支持图片和视频工作区背景。
- 桌宠被全屏或最大化窗口覆盖时自动隐藏、静音并暂停渲染。
- 单实例运行；再次启动会唤醒已运行界面。
- 内置桌宠资源均从本地读取，正常启动和互动可离线完成。

## 下载

前往仓库的 [Releases](../../releases) 页面，下载：

```text
DeskPetPanel-v1.0.0-windows-x64.zip
```

平台自动生成的 `Source code` 压缩包是源码快照；可直接运行的 Windows 应用位于 Release 附件中。

### v1.0.0 文件信息

| 项目 | 数值 |
|---|---:|
| ZIP 大小 | 238,098,843 字节（227.07 MiB） |
| 完整解压后 | 约 555.42 MiB |
| 应用目录 | 约 535.58 MiB |
| SHA-256 | `C9558E27C793ABB792AD9CF4B32577E1F2A97BD3E899CE3AF49A47913C167649` |

在 PowerShell 中校验：

```powershell
Get-FileHash -LiteralPath ".\DeskPetPanel-v1.0.0-windows-x64.zip" -Algorithm SHA256
```

重新构建后的哈希会变化，请以对应 Release 页面附带的 `.sha256` 文件为准。

## 系统环境

### 使用预构建版本

| 项目 | 要求 |
|---|---|
| 操作系统 | Windows 10/11 x64 |
| 处理器架构 | x86-64 |
| Python | 已封装在应用中，朋友电脑无需另装 |
| 网络 | 内置桌宠和互动资源支持离线运行 |
| 显卡 | 建议支持 WebGL 2，并使用较新的显卡驱动 |
| 磁盘空间 | 建议至少预留 700 MiB |

发布版采用 `onedir` 结构，解释器、GUI、浏览器、多媒体组件和桌宠资源均位于 `app` 文件夹。

### 源码开发与构建环境

v1.0.0 的实测构建环境：

- Windows 10/11 x64
- Python 3.9.13 AMD64
- PowerShell 5.1 或更新版本
- PyQt6 6.10.2
- PyQt6-WebEngine 6.10.0
- PyInstaller 6.22.2

全部固定版本见 [`requirements-build.txt`](requirements-build.txt)。

## 安装方法

1. 下载 `DeskPetPanel-v1.0.0-windows-x64.zip`。
2. 将 ZIP **完整解压**到普通文件夹；请从解压后的目录启动。
3. 可先按上文方法校验 SHA-256。
4. 双击：

   ```text
   Install-DeskPet.cmd
   ```

5. 安装脚本会将应用复制到：

   ```text
   %LOCALAPPDATA%\Programs\DeskPetPanel
   ```

6. 安装脚本会创建：
   - 桌面快捷方式 `桌宠工作面板`
   - 开始菜单文件夹 `桌宠工作面板`
   - 开始菜单卸载快捷方式
7. 安装完成后应用自动启动。

安装过程只使用当前用户目录，通常不触发管理员权限。添加或隐藏“公共桌面”项目时，系统可能显示 UAC 提示。

安装器使用一次性的：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass
```

该参数仅作用于本次脚本进程，不会永久修改系统执行策略。

## 便携运行

完整解压后也可直接运行：

```text
app\DeskPetPanel.exe
```

请保留整个 `app` 文件夹，特别是 `_internal`、浏览器运行库、模型和资源目录。单独复制 EXE 会出现运行库或桌宠资源缺失。

便携模式的开机启动项保存 EXE 的绝对路径。移动目录前先关闭“开机自启”，移动完成后再开启即可刷新路径。

## 基本操作

| 操作 | 效果 |
|---|---|
| 左键单击桌宠 | 随机互动并打开/收起工作区 |
| 按住左键拖动 | 移动桌宠 |
| 鼠标滚轮 | 调整桌宠大小 |
| 右键桌宠 | 打开动作、表情、语音及设置菜单 |
| 拖入文件或文件夹 | 添加到工作区 |
| 工作区按 `Esc` | 收起工作区；最大化时先还原 |
| 右键工作区图标 | 打开、定位、隐藏、恢复或移除 |
| 工作区右上角 `⛶` | 最大化或还原工作区 |

桌宠高度默认 `180`，最小 `120`，上限取当前屏幕可用高度与程序上限中的较小值。

### 桌宠右键菜单

- 打开工作区
- 切换为悬浮球
- 模型动作 / 二维动作
- 模型表情 / 表情贴纸
- 语音
- 停止当前互动
- 自动互动间隔
- 音量
- 点击图标后收起
- 开机自启
- 全部恢复到桌面
- 退出

### 工作区背景

右键工作区可添加文件、文件夹，选择最大化背景，浏览本机视频壁纸库或清除背景。

支持图片格式：

```text
png jpg jpeg bmp webp gif
```

支持视频格式：

```text
mp4 webm m4v mkv
```

视频解码效果取决于文件编码以及系统多媒体组件。背景路径保存在本机配置中，不会同步到另一台电脑；朋友需要在自己的电脑重新选择背景。

## 桌面项目的隐藏与恢复

从桌面拖入的项目会设置 Windows“隐藏”属性，项目仍位于原路径。

恢复方式：

1. 右键桌宠，选择 **全部恢复到桌面**；或
2. 在工作区中右键单个项目，选择 **恢复到桌面显示**；或
3. 选择 **从面板移除（并恢复桌面显示）**。

卸载、删除配置或手动删除程序目录前，建议先执行一次“全部恢复到桌面”。

程序异常结束后，也可以在资源管理器中显示隐藏项目，再取消文件属性中的“隐藏”；或在终端执行：

```cmd
attrib -h "项目的完整路径"
```

公共桌面中的项目可能需要管理员权限。

## 开机启动

安装器默认保持开机启动关闭状态。

在桌宠或悬浮球上右键，勾选 **开机自启**。程序会写入当前用户注册表：

```text
HKCU\Software\Microsoft\Windows\CurrentVersion\Run
```

值名称：

```text
WorkspacePanel
```

取消勾选或运行卸载脚本会清理该值。

## 配置与日志

用户配置和日志位于：

```text
%USERPROFILE%\.workspace_panel
```

| 文件 | 用途 |
|---|---|
| `config.json` | 桌宠位置、大小、音量、工作区条目和背景 |
| `debug.log` | 调试日志，达到约 2 MiB 后轮转 |
| `debug.log.old` | 上一次轮转日志 |
| `crash.log` | 原生崩溃日志 |

主要默认值：

| 配置项 | 默认值 |
|---|---|
| `entries` | `[]` |
| `trigger_pos` | `null` |
| `close_on_open` | `true` |
| `wallpaper` | `""` |
| `pet_mode` | `"live2d"` |
| `pet_h` | `180` |
| `pet_volume` | `17` |
| `pet_auto_interval_sec` | `180` |

工作区条目和背景使用本机绝对路径，不适合作为跨电脑同步配置。

### 重置设置

1. 执行“全部恢复到桌面”。
2. 右键桌宠并选择“退出”。
3. 备份后重命名 `%USERPROFILE%\.workspace_panel`。
4. 重新启动应用，程序会生成默认设置。

请先恢复隐藏项目再移除配置，配置中保存着自动恢复所需的路径。

## 卸载

从开始菜单打开：

```text
桌宠工作面板 → 卸载桌宠工作面板
```

也可运行安装目录中的：

```text
Uninstall-DeskPet.cmd
```

卸载脚本会：

- 结束安装目录中的应用进程。
- 尝试恢复由程序隐藏的桌面项目。
- 删除开机启动项。
- 删除桌面和开始菜单快捷方式。
- 删除 `%LOCALAPPDATA%\Programs\DeskPetPanel`。

个人配置默认保留在 `%USERPROFILE%\.workspace_panel`。确认桌面项目均恢复后，可以手动删除该目录以清理设置和日志。

## 从源码运行

```powershell
git clone https://github.com/Sunname123456/DeskPetPanel.git
cd DeskPetPanel

py -3.9 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r .\requirements-build.txt
.\.venv\Scripts\pythonw.exe .\panel.py
```

调试时可使用带控制台的入口：

```powershell
.\.venv\Scripts\python.exe .\panel.py
```

源码运行时请保留 `panel.py` 与 `web` 的相对位置。

### 固定依赖

```text
PyQt6==6.10.2
PyQt6-Qt6==6.10.2
PyQt6_sip==13.10.2
PyQt6-WebEngine==6.10.0
PyQt6-WebEngine-Qt6==6.10.2
PyInstaller==6.22.2
```

## 构建应用

在源码根目录运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\build_release.ps1
```

系统存在多个解释器时可显式指定：

```powershell
powershell -ExecutionPolicy Bypass -File .\build_release.ps1 `
  -PythonExe "C:\完整路径\python.exe"
```

脚本会：

1. 校验 Python 3.9+ x64。
2. 创建 `.venv-release`。
3. 安装固定版本依赖。
4. 执行 `windowed`、`onedir`、无 UPX 构建。
5. 打包完整 `web` 目录和浏览器/多媒体隐藏导入。
6. 生成：

   ```text
   dist\DeskPetPanel\DeskPetPanel.exe
   ```

`build_release.ps1` 生成应用目录。发布 ZIP 还应加入安装/卸载脚本、许可证、第三方声明和对应源码。

### Web 页面冒烟测试

```powershell
.\.venv\Scripts\python.exe .\packaging\web_smoke.py
```

正常输出：

```text
loadFinished=True
```

受限沙箱可能阻止浏览器子进程；应在普通 Windows 会话中进行最终验证。

如已安装 Node.js，还可以运行不启动 GUI 的前端交互回归：

```powershell
node .\tests\test_pet_runtime.js
```

该测试检查动作、贴纸、语音清单、定时交互和 Canvas 调用，不属于应用运行时依赖。

## 项目结构

```text
.
├─ panel.py                     # Python 主入口和桌面工作区
├─ web/
│  ├─ pet.html                  # Live2D 前端
│  ├─ libs/                     # Web/Live2D 运行库
│  ├─ model/                    # 模型、动作、纹理和模型语音
│  └─ extras/                   # 二维动作、贴纸、语音和清单
├─ packaging/
│  ├─ Install-DeskPet.cmd
│  ├─ Install-DeskPet.ps1
│  ├─ Uninstall-DeskPet.cmd
│  ├─ Uninstall-DeskPet.ps1
│  ├─ version_info.txt
│  └─ web_smoke.py
├─ tests/
│  └─ test_pet_runtime.js       # 无 GUI 的前端交互回归
├─ build_release.ps1
├─ DeskPetPanel.spec
├─ requirements-build.txt
├─ LICENSE
└─ THIRD_PARTY_NOTICES.md
```

`.gitignore` 已排除虚拟环境、构建结果、冒烟测试配置、日志和发布 ZIP。打包应用作为 Release 附件发布，避免将数百 MiB 运行库写入普通 Git 历史。

## 常见问题

### 双击后没有新窗口

应用为单实例。若进程已经运行，再次启动只会唤醒现有界面。检查任务管理器中的 `DeskPetPanel`，或从桌宠右键菜单退出后重试。

### 单独复制 EXE 后启动失败

本项目采用 `onedir` 构建。请恢复完整 `app` 文件夹，使 EXE、`_internal` 和资源目录保持原有结构。

### 桌宠空白、黑屏或模型未显示

1. 确认 ZIP 已完整解压。
2. 检查 `_internal` 和 `web` 资源是否齐全。
3. 更新显卡驱动。
4. 优先在支持硬件加速的本地桌面会话运行。
5. 查看 `%USERPROFILE%\.workspace_panel\debug.log` 和 `crash.log`。

### 没有声音

- 检查桌宠右键菜单中的音量。
- 检查系统音量合成器。
- 确认音频资源仍在完整目录中。
- 全屏窗口覆盖桌宠时，程序会暂停并静音；离开全屏后恢复。

### 视频背景未播放

- 检查文件扩展名和路径。
- 优先尝试 H.264/AAC 编码的 MP4。
- 场景型或网页型动态背景不在当前视频播放器支持范围内。

### 桌面图标消失

先打开桌宠右键菜单并选择“全部恢复到桌面”。若配置已经丢失，请启用资源管理器的“隐藏的项目”，再取消对应文件的隐藏属性。

### 移动目录后开机启动失效

便携模式的启动项记录绝对路径。关闭旧启动项，将程序移到最终位置，再重新勾选“开机自启”。

### 安全软件提示未知应用

当前 EXE 未做代码签名，安全软件可能显示未知发布者或启发式提示。建议从本仓库 Release 下载、校验 SHA-256、扫描压缩包，并可结合源码自行构建。

提交问题前请先检查日志。日志和 `config.json` 可能包含本机绝对路径，公开上传前应进行脱敏。

## 隐私与网络

当前应用没有遥测、账号系统、自动更新或在线下载逻辑。桌宠、动作、贴纸和语音均从本地文件读取。

应用会在用户主动浏览视频背景库时读取相关本机注册表项和资源目录；配置与日志仅写入 `%USERPROFILE%\.workspace_panel`。

## 验证记录

v1.0.0 发布包已完成：

- 源码语法和安装/卸载脚本解析检查。
- 106 个前端、模型及资源引用完整性检查。
- 8 组二维动作、37 帧、28 类贴纸状态、33 个贴纸文件和 17 段语音清单检查。
- Windows 普通会话下的打包程序冒烟测试。
- Live2D Core、WebGL 2、模型、动作与音频初始化检查。
- ZIP 内 1940 个条目逐项解压读取检查。

冒烟测试关键日志：

```text
PET_EXTRAS_READY 8/37 28/33 17
pet page loaded ok=True
PET_RANDOM_READY 12/28/17
PET_READY 340x480
```

## 许可证与素材说明

仓库随附 [`LICENSE`](LICENSE) 中的 GNU GPL v3 文本，并提供 [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)。

请分别确认以下部分的适用条款：

- 应用源代码。
- GUI 绑定及其 GPL v3/商业许可。
- Qt 和浏览器运行库。
- PixiJS 等 JavaScript 库。
- Live2D Cubism Core 及其单独再分发协议。
- 角色模型、纹理、动作、图片、语音和音乐素材。

仓库根许可证不会自动扩展第三方角色、音乐、语音、模型或运行库的授权范围。公开发布或扩大分发前，应逐项确认复制、修改和再分发条件，并保留相应许可证及署名信息。

## 变更记录

见 [`CHANGELOG.md`](CHANGELOG.md)。
