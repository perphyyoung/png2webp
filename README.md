# PNG 转 WEBP（保留 workflow）

简单的图形界面工具，支持批量将 PNG 图片转换为 WEBP，并保留源图的 `workflow` 元数据，适用于 ComfyUI 默认生成的含工作流的图像。

## 功能

- 支持将 PNG 文件拖拽到列表中添加
- 输出目录可选，默认输出到源文件所在目录

## 依赖

- Python 3.x
- Pillow
- piexif
- tkinterdnd2（用于拖拽）
- pyinstaller（用于打包为 exe, 可选）

```bash
uv sync
```

## 运行

```bash
python png2webp.py
```

## 打包

```bash
pyinstaller -F -w png2webp.py
```

## 说明

- 仅接受 `.png` 文件
- 转换失败的文件会提示原因，不影响其余文件继续转换

## License

GPL-3.0
