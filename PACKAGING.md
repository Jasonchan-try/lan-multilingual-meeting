# Windows 打包说明（PyInstaller）

## 1. 安装 Python 与依赖
1. 安装 Python 3.10+，勾选“Add Python to PATH”。
2. 在项目目录执行：
   - `python -m venv .venv`
   - `.venv\Scripts\activate`
   - `pip install -r requirements.txt`
   - `pip install pyinstaller`

## 2. 推荐打包命令
```bash
pyinstaller --noconfirm --onefolder --name lan-ai-meeting-room \
  --add-data "app/templates;app/templates" \
  --add-data "app/static;app/static" \
  app/main.py
```

## 3. 运行打包结果
- 进入 `dist/lan-ai-meeting-room/`
- 运行 `lan-ai-meeting-room.exe`

## 4. 需要保留文件
- `dist/lan-ai-meeting-room/` 整个目录
- `.env`（与 exe 同目录，存放 API 配置）

## 5. 说明
- 模板与静态资源必须通过 `--add-data` 打入包。
- 若端口冲突，可在 `.env` 修改 `PORT`。
