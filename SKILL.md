---
name: slowly-penpal-archive
description: 将已保存的 Slowly 信件 PDF 增量整理为可搜索的离线档案馆，展示已有本地邮票、附件和笔友资料。用于手动 PDF 归档、离线读信、指定或切换资料目录、追加新信和索引更新。不获取线上信件。
version: 1.0.0
display_name: Slowly Penpal Archive
display_name_en: Slowly Penpal Archive
description_zh: 将已保存的 Slowly 信件 PDF 整理为可搜索、可翻阅的本地离线档案馆，支持增量追加新信，展示已有本地邮票、附件和笔友资料。需自行保存 PDF，不自动下载线上信件。
description_en: Organize saved Slowly letter PDFs into a searchable local offline archive. Add new letters incrementally and view existing local stamps, attachments, and pen-pal profiles. Requires PDFs you have saved yourself; does not download letters from Slowly.
author: Penghao Xiong
---

# Slowly Penpal Archive

这是由 IDE／WorkBuddy 执行的免费 skill。用户通过自然语言提供需求和资料路径；不要把编译原生应用、安装 Swift、启动服务或手动执行终端命令作为使用前提。

## 执行流程

1. 从用户消息确定资料目录。相对位置如“下载/某文件夹”按用户本机目录解析，先只读检查实际结构；没有可推断路径时询问资料存在哪里。
2. 检查可用 Python 和 `pypdf`。优先用宿主已有环境；缺依赖时按宿主允许的方式补齐。首次安装依赖可能需要联网，与离线归档分开说明。不要宣称没有 Python 也能执行建库。
3. 为资料库选择独立且稳定的输出目录。新来源不要沿用另一资料库的数据库；检查现有 `build.json.meta.source_root` 后再决定是否复用输出目录。路径作为参数传递，不把用户真实路径写进公共配置或技能包。
4. 在本 skill 目录执行：

   ```bash
   python3 scripts/pdf_index.py --root '<资料目录>' --out '<该资料库的输出目录>'
   ```

5. 检查退出码和 `build.json`。报告导入总量、新增、更新、失败、元数据待确认数量；不要把待确认记录说成已识别。返回生成的 `index.html` 路径，用户要求打开时用宿主支持的本地文件预览方式打开。
6. 追加新信时沿用同一资料库的输出目录。切换路径时再次检查来源，直接执行脚本，不要求用户重新安装 skill。

## 输入与解析

- 支持 `<root>/<笔友>/来往信件/*.pdf` 和 `<root>/<笔友>/*.pdf`。
- 标准文件名：`YYYY-MM-DD HHMM-写信人[（已读）].pdf`，日期与写信人优先来自文件名。
- 手动文件如 `Slowly.pdf`：仅从开头明确的“写信人 + 日期”页眉读取；不从正文猜测日期。缺失时保留正文及原件入口，日期和方向标为待确认，计入 `unknown_metadata`。
- 合集、书信集不重复入库；单份解析失败记录在 `build.json.errors`，已有旧记录保留。
- 正文只来自 PDF 文本层。页眉按写信人、日期、地区、公开信角标顺序处理；多页重复页眉和应用字数页脚剥除。不要因修改规则而吞掉正文。
- `metadata_source` 表明来源；未知年份为 0、方向为 `unknown`，不能归为去信。已读后缀只来自文件名，不根据笔友目录备注推断每封信的状态。
- 解析规则变更时更新脚本内 `PARSER_VERSION`；已有库按版本重解析并保留源目录已移走的历史记录。

## 图文与本地状态

- `邮票/` 展示本地邮票图片。`.data/<信件名>.json` 的 `stampFile` / `stampName` 用来关联信件，没有关联记录不猜测。
- `photoFiles` 及 `.data/附件/<信件名>-图N.*` 提供附件图片；`个人资料/profile.json` 和 `头像.png` 提供笔友资料。
- 图片内嵌到 HTML；原 PDF、合集及资料 Word 提供本地文件链接。
- `.slowly-pal` 只读，用于通信状态和完整性提示；不修改已读、离别信、仍在通信等标记。
- 不从 PDF 图片层提取邮票，不做 OCR，不要求在线登录，不读取浏览器登录态。

## 参数

```bash
python3 scripts/pdf_index.py --root '<资料目录>' --out '<输出目录>' --pal '<笔友名>'
python3 scripts/pdf_index.py --root '<资料目录>' --out '<输出目录>' --pdf-only
python3 scripts/pdf_index.py --root '<资料目录>' --out '<输出目录>' --full
python3 scripts/pdf_index.py --root '<资料目录>' --out '<输出目录>' --verify-data
python3 scripts/pdf_index.py --out '<输出目录>' --sql 'select pal,count(*) from letters group by pal'
```

`--pdf-only` 不读旁车图文和状态；`--full` 强制重解析；`--verify-data` 与本地导出 JSON 对账正文量。

## 边界与验证

- 只读资料源；所有派生产物落在输出目录。归档不访问网络、不起端口、不调用浏览器自动化；预览本地 HTML 可以打开浏览器。
- 依赖安装不等于归档联网：缺少环境时如实处理，不把“零网络归档”说成“安装无需下载依赖”。
- 正文和资料通过 `textContent` 渲染；图片和链接限定本地安全来源，拒绝越界路径、远端资源和可执行图像。
- SQLite 增量更新，不删旧数据库；网页、JSONL 和统计按合并后档案刷新。
- 原 PDF、数据库、生成网页、`media.json`、JSONL 和真实用户配置均不打包进公开技能。
- 修改脚本后运行 `python3 -m unittest discover -s scripts -t scripts` 与 `bash scripts/audit_offline.sh`。测试用临时合成数据，不能用用户真实信件做公开演示素材。
