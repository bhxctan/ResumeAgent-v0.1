# v0.8 设置反馈优化

- 视觉识别和 JD 改写各自的按钮下显示正在处理、成功或错误结果。
- 获取账户模型及清除密钥也在对应区域反馈；保存设置仍在保存按钮下反馈。
- 修改服务地址、模型或密钥时清除过期反馈。

# v0.7 模型选择更新

- 两个模型配置均提供显式模型下拉框、搜索、手动模型 ID 及“获取账户模型”按钮。
- OpenAI 新增 GPT-6 Astra、GPT-6.1 Sol、GPT-6.1 Terra、GPT-6 Luna 预设；保留旧 ID 供兼容使用（可能已停用）。默认视觉 Terra、JD Luna。详见 https://developers.openai.com/api/docs/models 。
- 获取模型使用所选槽位的 API 地址和密钥发送 GET /models，不上传简历；结果仅表示服务端列出的模型，不保证视觉或 JSON 能力。选择后务必测试连接；不支持此接口的服务商仍可使用预设或手动输入。

# Resume Agent v0.7 · 视觉 AI 简历识别与岗位适配

## Windows / PowerShell 启动

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python server.py
```

打开 http://127.0.0.1:8765 。如果已有虚拟环境与依赖，直接重新启动即可。服务仅绑定本机，不要未经认证暴露到公网。

## 模型设置（导入 PDF 前需配置）

右上角「设置」分别配置视觉识别和 JD 改写。预设 OpenAI、DeepSeek、通义千问（阿里云百炼）、硅基流动和自定义兼容接口，自动填入示例地址和模型，可手工修改。各模型分别保存密钥、独立测试和清除；只配置视觉即可导入，只配置 JD 即可对已保存的项目执行岗位分析。视觉服务须支持 image_url/data URL 和 JSON 输出，文本模型须支持 JSON 输出。具体模型及接口权限以服务商控制台为准。未联调真实服务，不保证所有示例模型均可用。密钥只保存在本地内存；更换地址不会沿用旧密钥。测试不自动保存。

可通过环境变量启动：

```powershell
$env:OPENAI_API_KEY="你的API密钥"
$env:OPENAI_MODEL="你的JD模型"
$env:RESUME_VISION_MODEL="你的视觉模型"
# $env:RESUME_VISION_API_KEY="独立视觉密钥"
# $env:RESUME_VISION_BASE_URL="独立视觉地址"
# $env:OPENAI_BASE_URL="https://api.openai.com/v1"
python server.py
```

API 与 ChatGPT 订阅独立计费，视觉导入可能比文本分析更贵。导入简历及参考模板时，程序会将每页图像（含照片、联系方式等）和 PDF 原生文字/字号样式发送给你配置的服务，上传前会要求确认；仅编辑、预览、打开已保存项目、保存、HTML 导出及打印不需要 API。JD 分析发送文字与 JD。请勿使用不可信服务；请在上传他人模板前获得授权。

## v0.5：视觉 AI 主导识别

1. 本地渲染 PDF 高清整页图片，同时提取原始文字和字号、字体、颜色、粗体等样式证据（不做段落或同行规则识别）。
2. 视觉模型直接判断阅读顺序、行列关系、独立段落、段内软换行、标题、装饰线、照片区域，返回严格 JSON 行列结构。API 错误或结构无效时直接报错，不回退至旧坐标启发式识别器。支持没有文字层的扫描 PDF，但须校对。
3. 本地把结构转换为可编辑 HTML 文档流；原生 PDF 样式优先，照片从原稿局部渲染裁切，不生成新照片。姓名/求职意向同行；三列中间字段居中、两侧对齐；正文整体居中、段内两端对齐，内容高度随编辑变化。模型判断有误时，仍需人工校对。
4. 对原生文字与 AI 输出进行忽略空白的字符数量核对，提示潜在漏字或新增字；此检查不验证文字顺序及语义，也不能检查扫描件原文。使用左右原稿对照检查后再进行 JD 改写。
5. 可选模板学习也走视觉识别，随后提取模板样式迁移到自己的简历；不会把模板个人信息或图片复制到自己的简历。仍是样式迁移，不支持任意复杂版型完整重构。
6. 保留 v0.4 的编辑、撤销、项目保存、恢复、HTML/PDF 导出及 JD 改写，保护同行元数据不被 JD 模型删除或改写。改写以原始事实库为依据，提供证据和数字检查提示，逐条审核。

## 限制

- 视觉模型可能漏字、错读、错误合并段落或误判照片区域。没有真实模型联调或真实简历视觉测试；自动测试通过 mock 验证结构处理和调用流程，不能证明视觉识别准确率。
- PDF 不保证可同时像素级还原与自由重排；复杂多栏、矢量图形、缺失字体、扫描件中的准确字号及多页跨页重排仍有限制。导出前检查分页与照片。照片使用原稿裁切像素，裁切范围由模型预测。
- PDF 文件最多 20MB、10 页，逐页调用模型，可能耗时。API 不兼容时需更换视觉模型/服务，不静默回退。
- 旧版 JSON 可继续打开，但不会恢复之前丢失的结构。请重新导入原始 PDF。
- 首次识别结果作为原始事实库，若有识别错漏，请勿直接用于 JD 改写；需重新识别或人工核验。不能把模型的文字核对提示当作事实证明。
- v0.4 旧解析器保留在 parser.py 作为样式工具和回归测试用途，不用于 Web 导入、模板识别的行段判断。
- 请勿将个人简历、项目 JSON、导出 HTML 或 API 密钥提交到 Git 仓库。

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
