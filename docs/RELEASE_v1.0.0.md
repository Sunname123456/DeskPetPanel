# 桌宠工作面板 v1.0.0

首个可分享的 Windows x64 版本，包含独立运行环境、Live2D 桌宠、动作、贴纸、语音、工作区以及安装/卸载脚本。

## 下载与安装

1. 下载 Release 附件 `DeskPetPanel-v1.0.0-windows-x64.zip` 和对应 `.sha256` 文件。
2. 校验 SHA-256 后完整解压 ZIP。
3. 双击 `Install-DeskPet.cmd` 安装；也可直接运行 `app\DeskPetPanel.exe`。

朋友电脑无需安装 Python。建议使用 Windows 10/11 x64，并预留至少 700 MiB 磁盘空间。

## 校验值

```text
C9558E27C793ABB792AD9CF4B32577E1F2A97BD3E899CE3AF49A47913C167649  DeskPetPanel-v1.0.0-windows-x64.zip
```

## 本版默认设置

- Live2D 模式
- 桌宠高度：180
- 音量：17%
- 随机互动间隔：180 秒
- 工作区项目：空
- 工作区视频背景：空，请在目标电脑重新选择

## 使用提醒

- 保留完整 `app` 目录；EXE 依赖同目录的 `_internal` 和资源文件。
- 从桌面拖入的项目会设置隐藏属性。卸载前请先选择“全部恢复到桌面”。
- EXE 当前未做代码签名，系统可能提示未知发布者；请核对 SHA-256。
- 配置与日志保存在 `%USERPROFILE%\.workspace_panel`。
- 模型、图片、语音、音乐和 Live2D 运行组件适用各自条款，详情见仓库说明。

完整用法、源码环境、构建流程和故障排查请阅读仓库 [`README.md`](../README.md)。
