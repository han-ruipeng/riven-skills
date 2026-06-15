# Skill: File Organizer

## 元信息
- **版本**: 1.0.0
- **作者**: Riven
- **标签**: files, organize, automation, cleanup
- **依赖**: 无（纯 Shell / Python 实现）

---

## 触发条件

当用户表达以下意图时激活此技能：
- "整理这个文件夹"
- "帮我分类这些文件"
- "把下载文件夹清理一下"
- "这些文件太乱了，按类型分一下"
- 或类似的文件整理/归类需求

---

## 目标

将指定文件夹中散乱的文件按扩展名/类型自动归类到子文件夹中，
使目录结构清晰、易于查找。

---

## 规则 / 步骤

### 1. 确认目标文件夹
- 如果用户未明确指定，默认操作当前工作目录。
- 先 `ls` 查看文件夹内容，向用户确认后再执行。

### 2. 分类规则（默认映射）
| 类别 | 目标文件夹 | 扩展名 |
|------|-----------|--------|
| 图片 | `images/` | .jpg .jpeg .png .gif .bmp .svg .webp .ico |
| 文档 | `documents/` | .pdf .doc .docx .xls .xlsx .ppt .pptx .txt .md .csv |
| 压缩包 | `archives/` | .zip .rar .7z .tar .gz .bz2 |
| 代码 | `code/` | .py .js .ts .html .css .java .c .cpp .go .rs .json .xml .yaml |
| 视频 | `videos/` | .mp4 .avi .mkv .mov .wmv .flv |
| 音频 | `audio/` | .mp3 .wav .flac .aac .ogg .wma |
| 安装包 | `installers/` | .exe .msi .dmg .pkg .deb .rpm .apk |
| 其他 | `others/` | 未匹配的扩展名 |

### 3. 执行流程
1. **扫描**：遍历目标文件夹的所有文件（不含子文件夹）。
2. **分类**：根据扩展名匹配类别。
3. **创建**：按需创建子文件夹（不重复创建）。
4. **移动**：将文件移入对应子文件夹。
5. **报告**：输出移动统计。

### 4. 安全规则
- **绝不**移动隐藏文件（以 `.` 开头的文件）除非用户明确要求。
- **绝不**移动 `SKILL.md`、`README.md` 等技能库元文件。
- 如果目标子文件夹中已存在同名文件，询问用户覆盖策略（覆盖/跳过/重命名）。

---

## 示例

### 示例 1：基本整理
```
用户：整理一下当前文件夹
Claude：好的，我先看看当前文件夹的内容...
        [运行 ls]
        发现 15 个文件：图片6张、文档4份、压缩包3个、其他2个。
        我将按以下方式整理：
        - 图片 → images/
        - 文档 → documents/
        - 压缩包 → archives/
        - 其他 → others/
        确认执行吗？
用户：确认
Claude：[执行移动操作]
        整理完成！移动了 15 个文件到 4 个类别文件夹。
```

### 示例 2：指定文件夹
```
用户：把 ~/Downloads 里的文件按类型分一下
Claude：好的，我先看看 ~/Downloads 里有什么...
        [扫描后给出分类方案，确认后执行]
```

---

## 附带脚本

本 skill 提供了 `sort_files.py` 脚本，可以直接运行：
```bash
python skills/file-organizer/sort_files.py <目标文件夹>
```

Claude 也可以直接编写 Shell 命令来快速实现，无需 Python 环境。
