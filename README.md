# Resume Agent v0.4 · 智能简历编辑与岗位适配

本地浏览器编辑器，默认不上传简历到任何外部服务。只有主动点击「分析并生成改写建议」才会把简历事实库、当前文字和 JD 发送给你配置的模型 API。请不要将私人简历、项目 JSON、导出 HTML 或 API 密钥提交到公开仓库。

## Windows / PowerShell 启动

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python server.py
```

打开 http://127.0.0.1:8765 。如 PowerShell 禁止激活虚拟环境，直接使用 `.\.venv\Scripts\python.exe -m pip install -r requirements.txt` 和 `.\.venv\Scripts\python.exe server.py`。

## AI 功能（可选）

在网页右上角「设置」中填写 API Base URL、Model 和 API Key，保存设置后即可使用 JD 改写。测试连接只发送一条不含简历的请求，不自动保存。密钥仅存于当前 Python 服务内存，不持久化；关闭服务后可重新输入。也可在启动前设置以下环境变量。API 与 ChatGPT 订阅是独立服务，可能产生费用。

```powershell
$env:OPENAI_API_KEY="你的API密钥"
$env:OPENAI_MODEL="gpt-4o-mini"
# 可选：兼容 OpenAI Chat Completions 的受信任服务地址
# $env:OPENAI_BASE_URL="https://api.openai.com/v1"
python server.py
```

模型需支持 Chat Completions JSON object 输出。服务绑定本机 127.0.0.1，请勿未经身份验证暴露到公网。

## v0.4 布局改进

- 同行判断结合原始基线、垂直重叠与横向位置，支持不同字号的姓名与求职意向同排。
- 正文区整体居中，普通段落不再绑定 PDF 文本框的大小或横向缩进；正文两端对齐，信息行自动分列。三列信息行左右轨等宽，专业等中间字段相对页面居中；日期在宽度允许时不换行。
- 识别编号、项目符号、独立标签（如「传播表现：」）、短行句末及段间距，保留推断出的段落边界。段内软换行由浏览器重新计算。点击文字后可使用 Enter 手动补充遗漏的换行。
- 原稿对照采用左侧可编辑稿、右侧原始 PDF 的同倍率预览；对照时暂时隐藏左侧功能栏，关闭对照后恢复。模板尺寸改变时原图保留原始尺寸。
- 更新后请重新导入原 PDF，旧版保存的 JSON 无法自动恢复此前丢失的段落和行关系。原始 PDF 没有明确段落标记，特殊版式仍需人工校对。

## 工作流

1. 导入可选中文字的 PDF：提取文字、字号、字体名称、颜色、图片和行段。原始 PDF 的预览保留在本地项目中。正文容器居中、文字两端对齐，个人信息左对齐；右上角照片独立于正文，其所在头部预留高度和宽度。正文不采用固定坐标，增删字会正常推动后方内容。
2. 点击文字直接修改，失焦保存。可撤销、恢复、添加段落、保存 JSON 项目或导出 HTML。浏览器打印时选择「另存为 PDF」，建议关闭页眉页脚。若超过一页，需检查分页。
3. （可选，可跳过，默认折叠）导入其他 PDF 模板，只提取统计样式（字体、字号、颜色、装饰线、间距、页面尺寸、照片框），不复制他人的内容或照片。之后检查版面。
4. 粘贴完整 JD：分析岗位真实职责、硬性要求、原始关键词、经验匹配度与缺口。模型根据事实库建议改写或删除段落，保留原文并返回逐字证据；逐条审核、修改、接受或拒绝。数字和证据检查只是辅助提示，不能保证语义正确。开头竞争力建议由用户自行加入。

## 限制与迭代

- PDF 是固定版面，无法保证像素级还原与自由重排同时成立。第一版针对有文字层的单栏简历；扫描件需先 OCR，复杂多栏、嵌入式字体、字形替代、矢量装饰和表格需要进一步适配。不会分发系统字体；本机缺失原字体时回退到其他字体。
- 标题、照片和段落识别基于启发式，建议利用原图对照；多页独立编辑，屏幕上的原始页高为最小高度，浏览器分页需人工检查。模板学习不是训练模型，也不支持任意复杂版型重构。
- LLM 不得编造职责、数据或成果，但技术校验不能杜绝幻觉；最终由用户审核。新增事实不能自动写入原始事实库。
- 本项目未做公网页面部署、数据库、多用户权限或任何自动投递。

## 测试

```powershell
python -m unittest discover -s tests -v
```

## 推送 GitHub

在 GitHub 创建空的私有仓库 `resume-agent`，在解压后的目录运行：

```powershell
git init
git add .
git commit -m "Initial resume agent MVP"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/resume-agent.git
git push -u origin main
```

请检查仓库权限以及 `git status`，不要提交个人简历与密钥。
