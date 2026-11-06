<h1 align="center">Slowly-Penpal-Archive-Skill</h1>
<p align="center">
  <a href="README.md">简体中文</a> |
  <a href="README.en.md">English</a> |
  <a href="README.zh-TW.md">繁體中文</a> |
  <a href="README.ja.md">日本語</a> |
  <a href="README.ko.md">한국어</a> |
  <a href="README.ar.md">العربية</a>
</p>

## 起源
> 认真封存每一份笔友关系。

有些通信渐渐停下，有些笔友需要告别。

但清理笔友列表之前，我们仍想留下那些认真写过、收到过的信。

如果你都下载了PDF之后，如何整理，并会看每一封信件，每一次的笔友关系？

使用Slowly App 的朋友们都知道，如果不是Plus，我们的笔友位只有100个。

如果当你开过了slowly的Plus，当到期，若不愿续充时，需要清理我们的笔友位。

于是我做了这个skills。

本skills：
1. 不会替用户下载网页上的信件
2. 把你保存的信件整理成一座可以搜索、翻阅的本地档案馆，让每一段通信都有地方安放。
   
此应用目前仅针对Slowly进行归档，其他类型可导出信件PDF的App，暂未尝试，欢迎尝试并在issue区进行反馈。

## 使用前准备
进入Slowly网页端，先自行保存任意笔友的信件 PDF，每位笔友放一个文件夹，示例如下：
```
信件目录/
└── 某位笔友/
    ├── Slowly.pdf
    ├── Slowly2.pdf
    ├── 邮票/
    │   └── 邮票一.png
    │   └── 邮票二.png
    └── 个人资料/
        └── 头像.png
```

注：手动导出的实际兼容性，需要你的实际验证。

## 流程
保存信件 PDF → 按笔友建立文件夹（同一笔友的多封信放在一起）→ 可选：让 AI 辅助规范文件名 → 让 skill 生成档案 → 打开阅读。

## 开始使用
1. 下载本仓库（绿色 Code 按钮 → Download ZIP，或 `git clone`），解压后你会得到一个里面有 `SKILL.md` 和 `scripts/` 的文件夹
   （ZIP 下载的叫 `Slowly-Penpal-Archive-Skill-main`）。把这个**文件夹整体**放进你所用工具配置的 skills 目录，
   并把它重命名为 `slowly-penpal-archive`；也可以直接用工具的本地技能导入功能。
   不要只复制 `SKILL.md`——脚本不在旁边时，技能找不到 `scripts/pdf_index.py` 就跑不起来。
2. 对支持 Skills 的办公工具（WorkBuddy、千问办公或豆包工作）或 IDE说：

> 使用 slowly-penpal-archive（slowly离线归档技能），把（你的信件保存路径）里的 PDF 整理成离线档案馆，保留原文件，生成后给我打开入口。

追加信件：

> 用 slowly-penpal-archive，资料目录是（你的信件保存路径），把新信追加进已有档案。 

首次运行仍需要可执行 Python 的宿主环境；若缺少 pypdf，AI 会按该环境允许的方式处理。

首次获取依赖可能联网，归档和阅读流程不访问 Slowly。

生成后，打开本地 index.html 就能阅读，后续无需 AI 或本地服务保持运行。

## 不想用 AI？两条命令也够
```bash
python3 -m pip install -r requirements.txt

python3 scripts/pdf_index.py --root '<信件目录>' --out '<输出目录>'
open '<输出目录>/index.html'    # Windows 用 start，Linux 用 xdg-open
```

- 不传 `--root` 时读 `~/Desktop/笔友库`；目录不存在会直接告诉你改哪里，不会猜。
- 不传 `--out` 时写到 `~/Desktop/Slowly离线档案`。同一资料库以后一直用同一个 `--out`，就是增量追加。
- 常用参数：`--pal '<笔友名>'` 只处理一位，`--full` 强制全量重解析，`--pdf-only` 不读邮票/附件等旁侧本地文件，
  `--verify-data` 与本地导出 JSON 对账正文字数量，`--sql '<查询>'` 只读查询已生成的库。
- 已在 Python 3.9 / 3.12 / 3.14 上跑通同一份数据；自检：
  `python3 -m unittest discover -s scripts -t scripts`（32 项）与 `bash scripts/audit_offline.sh`（离线自证）。

## 生成结果

| 文件 | 用途 |
| --- | --- |
| `index.html` | 可直接打开的离线档案馆 |
| `slowly_pdf.db` | 信件数据库 |
| `letters.jsonl` | 结构化信件记录 |
| `build.json` | 导入统计、失败记录与待确认数量 |
| `media.json` | 本地图文及关联索引 |

## 效果
“笔友档案馆”：图片预览图：

 <img width="1440" height="1000" alt="01-信件列表" src="https://github.com/user-attachments/assets/a36b1725-bb47-465f-8345-772511a49c02" />
<img width="1920" height="1080" alt="更新专用keynote_副本 002" src="https://github.com/user-attachments/assets/c26fa704-91a7-432c-af86-03447fffb644" />
 <img width="1920" height="1080" alt="更新专用keynote_副本 003" src="https://github.com/user-attachments/assets/195632ad-4681-450e-9e95-f1b345cd3767" />

## 数据安全
本skills不联网、不自动操作 Slowly 网页、不读取登录态、无需登录Slowly，只读取你已经保存的“信件 PDF”，用 pypdf 还原正文，产出一个可搜索的 SQLite 库和一个单文件、数据内嵌、双击即开的网页档案馆。 
依赖
pypdf：首次安装需联网，下载此依赖。

这条边界可以自证，不必只听我说：

```bash
bash scripts/audit_offline.sh
```

它扫描脚本、模板与生成页面，命中网络栈、外链或浏览器自动化关键字就报错退出。生成的 `index.html` 里
`link/script/img` 外部引用为 0，浏览器网络面板在断网前提下也不会出现任何请求。

一份提醒：`index.html` 里的“打开 PDF”按钮指向你本机的绝对路径，正文也全部内嵌在文件里。
所以请只在本机阅读，不要把生成页面（以及 `*.db`、`letters.jsonl`、`media.json`）转发给别人或提交到仓库——`.gitignore` 已经默认排除了它们。

## 常见问题
Q：换信件目录时怎么办？

A：回到 IDE／WorkBuddy，告诉 AI 新路径，再生成即可。

## 赞赏
<img width="1920" height="1080" alt="更新专用keynote_副本 004" src="https://github.com/user-attachments/assets/b84194e5-e9d3-4149-81ae-f9d664d9f813" />
