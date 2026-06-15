---
name: liepin-jobs
description: |
  猎聘求职工具 — 在猎聘上搜索职位、投递简历、查看/编辑简历（基本信息/教育/工作/项目/求职意向/自我评价）。
  触发词: 找工作, 搜职位, 投简历, 猎聘, liepin, 求职, 招聘, 简历
version: 0.2.0
author: xllin
license: MIT
homepage: https://github.com/xllinbupt/MCP2skill
repository: https://github.com/xllinbupt/MCP2skill
keywords:
  - jobs
  - liepin
  - resume
  - mcp
  - chinese
requires:
  bins: python3
allowed-tools: Bash(python3:*),Bash(python:*)
---

# 猎聘求职工具 (liepin-jobs) v0.2.0

在猎聘平台上搜索职位、投递简历、查看和编辑简历的完整工具集。基于猎聘官方 MCP Server，零外部依赖。

**脚本位置**: 本 skill 目录下的 `liepin_mcp.py`
**MCP 端点**: `https://open-agent.liepin.com/mcp/user`

---

## !! 首次使用必读：获取 Token

使用此工具前，用户必须先获取猎聘的认证 Token。**没有 Token 无法使用任何功能。**

### 获取步骤

1. **打开猎聘 MCP 配置页**: 引导用户在浏览器访问 https://www.liepin.com/mcp/server
2. **登录猎聘账号**: 用户需要有猎聘账号并登录
3. **获取 x-user-token**: 页面会显示 `x-user-token` 的值（JWT 格式，以 `eyJ` 开头）
4. **配置 Token**: 运行 setup 命令保存 token

```bash
python3 "<skill_dir>/liepin_mcp.py" setup
# 按提示输入 x-user-token
```

### 或通过环境变量配置

```bash
export LIEPIN_USER_TOKEN="eyJhbGciOiJIUzI1NiJ9..."
```

### Token 过期

- Token 有效期约 **90 天**
- 过期后会收到 HTTP 401/403 认证错误，需引导用户重新访问上述页面获取新 Token
- 重新生成 Token 会立即使旧 Token 失效

**如果用户还没有配置 Token，必须先引导他们完成上述步骤，再执行任何操作。**

---

## 命令速查

```bash
SCRIPT="<skill_dir>/liepin_mcp.py"

# ── 搜索与投递 ──

# 搜索职位（参数全部可选）
python3 "$SCRIPT" search-job --jobName "AI产品经理" --address "上海"
python3 "$SCRIPT" search-job --jobName "前端开发" --address "北京" --salaryFloor "15000" --salaryCap "25000"
python3 "$SCRIPT" search-job --jobName "数据分析" --companyName "字节跳动" --page 0
python3 "$SCRIPT" search-job --jobName "产品经理" --compNature "外企" --workExperience "3-5年" --json

# 投递职位（需要先搜索获取 jobId 和 jobKind）
python3 "$SCRIPT" apply-job --jobId 12345 --jobKind "1"

# ── 查看简历 ──

python3 "$SCRIPT" my-resume
python3 "$SCRIPT" my-resume --json

# ── 更新基本信息 ──

python3 "$SCRIPT" update-base-info --realName "张三" --sex "男" --birthday "19961201" --nowWorkStatus "0"
python3 "$SCRIPT" update-base-info --data '{"realName":"张三","nowSalary":15000}'

# ── 更新自我评价 ──

python3 "$SCRIPT" update-self-assess --content "5年互联网产品经验，擅长用户增长..."
python3 "$SCRIPT" update-self-assess --data '{"selfAssess":"内容..."}'

# ── 教育经历 ──

# 添加教育经历
python3 "$SCRIPT" add-edu-exp --school "北京大学" --degree "040" --start "201509" --end "201906" --major "计算机科学"

# 修改教育经历（通过 eduId）
python3 "$SCRIPT" modify-edu-exp --eduId 123456 --major "软件工程"

# ── 工作经历 ──

# 添加工作经历
python3 "$SCRIPT" add-work-exp --compName "字节跳动" --rwTitle "高级前端工程师" --workStart "202104" --workEnd "202601" --duty "负责核心业务开发"

# 修改工作经历（通过 workId）
python3 "$SCRIPT" modify-work-exp --workId 200349374176 --duty "更新后的职责描述"

# ── 项目经历 ──

# 添加项目经历
python3 "$SCRIPT" add-project-exp --name "XX管理系统" --start "202203" --end "202306" --descr "项目描述" --duty "负责前端架构"

# 修改项目经历（通过 id）
python3 "$SCRIPT" modify-project-exp --id 200125925383 --duty "更新后的项目职责"

# ── 求职意向 ──

# 添加求职意向
python3 "$SCRIPT" add-job-want --jobtitle "WEB前端开发" --dq "上海" --wantSalaryLow 15000 --wantSalaryHigh 25000

# 修改求职意向（通过 id）
python3 "$SCRIPT" modify-job-want --id 200173385195 --wantSalaryHigh 30000

# ── 工具发现 ──

# 列出所有可用工具（查看猎聘最新 API 能力）
python3 "$SCRIPT" list-tools
python3 "$SCRIPT" list-tools --json

# 通用调用（适用于猎聘新增的工具）
python3 "$SCRIPT" call <tool-name> -a '{"key": "value"}' --json
```

---

## 典型求职流程

当用户说"帮我找工作"、"搜一下猎聘上的XX职位"时，按以下流程执行：

1. **检查 Token** → 如果未配置，先引导用户获取（见上方"首次使用必读"）
2. **查看简历** (`my-resume`) → 确认简历信息完整，提醒用户补充缺失项
3. **搜索职位** (`search-job`) → 根据用户意向搜索，用表格展示结果
4. **分析匹配度** → 结合简历和职位要求，帮用户筛选最合适的
5. **投递职位** (`apply-job`) → **必须先向用户展示职位详情并获得明确确认后再投递**

---

## 搜索参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `--jobName` | 职位名称关键词 | "AI产品经理"、"前端开发" |
| `--address` | 工作地点 | "上海"、"北京"、"深圳" |
| `--salaryFloor` | 薪资下限 | "15000" |
| `--salaryCap` | 薪资上限 | "25000" |
| `--salaryKind` | 薪资类型 | "月薪"、"年薪" |
| `--workExperience` | 工作经验要求 | "3-5年"、"5-10年"、"应届生" |
| `--eduLevel` | 学历要求 | "本科"、"硕士"、"博士" |
| `--compNature` | 公司性质 | "外企"、"国企"、"民企"、"合资"、"外资"、"私营" |
| `--companyName` | 公司名称 | "字节跳动"、"阿里巴巴"、"腾讯" |
| `--page` | 页码 (0=第1页) | `0`, `1`, `2` |

---

## 简历操作完整参考

### 基本信息 (`update-base-info` → `modify-resume-base-info`)

| 参数 | 说明 | 示例 |
|------|------|------|
| `--realName` | 真实姓名 | "张三" |
| `--sex` | 性别 | "男" / "女" |
| `--birthday` | 生日 | "19961201" (yyyyMMdd) |
| `--cityCode` | 当前所在城市编码 | "020" (上海) |
| `--startJob` | 开始工作年份 | "2021" |
| `--startJobMonth` | 开始工作月份 | "04" |
| `--nowWorkStatus` | 当前状态 | 0=离职-看机会, 1=在职-找工作, 2=离职-已找到, 3=在职-看机会, 4=在校-找工作, 5=在校-找机会, 6=在校-实习, 7=在校-已找到 |
| `--nowSalary` | 当前月薪(元) | 15000 |
| `--nowMonths` | 年薪月数 | 13 |
| `--nowSalarySecret` | 薪资保密 | 0=显示, 1=保密 |
| `--jobName` | 当前职位名称 | "前端开发工程师" |
| `--nowComp` | 当前公司名称 | "XX科技有限公司" |
| `--nameSecret` | 姓名隐私 | 0=显示全名, 1=显示X先生/女士 |
| `--wechat` | 微信号 | "wxid_xxx" |

### 教育经历 (`add-edu-exp` / `modify-edu-exp`)

| 参数 | 说明 |
|------|------|
| `--school` | 学校名称 |
| `--degree` | 学历编码: 090=初中及以下, 080=高中, 060=中专/中级, 050=大专, 040=本科, 030=硕士, 020=MBA/EMBA, 010=博士 |
| `--start` / `--end` | 起止时间 YYYYMM (如 "201509") |
| `--major` | 专业名称 |
| `--tz` | 统招标志: 0=是, 1=否 |

### 工作经历 (`add-work-exp` / `modify-work-exp`)

| 参数 | 说明 |
|------|------|
| `--compName` ⭐必填 | 公司名称 |
| `--rwTitle` ⭐必填 | 职位名称 |
| `--workStart` ⭐必填 | 入职时间 YYYYMM |
| `--workEnd` ⭐必填 | 离职时间 YYYYMM |
| `--duty` | 职责业绩描述 |
| `--industry` | 所属行业 |
| `--dept` | 所在部门 |
| `--salary` | 薪资(元) |
| `--months` | 年薪月数 |
| `--workType` | 1=全职, 2=实习 |
| `--labels` | 技能标签(英文逗号分隔) |

### 项目经历 (`add-project-exp` / `modify-project-exp`)

| 参数 | 说明 |
|------|------|
| `--name` ⭐必填 | 项目名称 |
| `--start` ⭐必填 | 开始时间 YYYYMM |
| `--end` ⭐必填 | 结束时间 YYYYMM |
| `--compName` | 公司名称 |
| `--position` | 担任职务 |
| `--descr` | 项目描述 |
| `--duty` | 项目职责 |
| `--achievement` | 项目业绩 |

### 求职意向 (`add-job-want` / `modify-job-want`)

| 参数 | 说明 |
|------|------|
| `--jobtitle` ⭐必填 | 期望职位/职能名称 |
| `--dq` ⭐必填 | 期望工作城市 |
| `--wantSalaryLow` | 期望薪资下限(元) |
| `--wantSalaryHigh` | 期望薪资上限(元) |
| `--wantSalaryMonths` | 期望年薪月数 |
| `--industries` | 期望行业, 英文逗号分隔 |
| `--otherExpectDqs` | 其他感兴趣城市, 英文逗号分隔 |

### 自我评价 (`update-self-assess` → `modify-self-assess`)

| 参数 | 说明 |
|------|------|
| `--content` | 自我评价内容 |

---

## 输出格式

- 默认输出人类可读格式（JSON pretty-print）
- 加 `--json` 输出原始 JSON，方便程序化处理
- 搜索结果建议以表格形式展示给用户，包含：职位名、公司、薪资、地点、经验要求

---

## 注意事项

- **投递不可撤回**: 执行 `apply-job` 前必须获得用户明确确认
- **修改操作需 ID**: 修改教育/工作/项目/求职意向前，需先通过 `my-resume` 获取对应项的 ID
- **频率限制**: 所有操作共享 60 次/分钟，避免短时间批量调用
- **Token 安全**: 不要在日志或对话中暴露完整的 Token 内容
- **数据来源**: 所有数据来自猎聘平台，实时同步

---

## 错误处理

| 错误 | 原因 | 解决方案 |
|------|------|---------|
| "未配置 token" | 没有运行 setup | 引导用户获取 Token 并运行 `setup` |
| HTTP 401 / 403 | Token 过期或无效 | 引导用户重新访问 https://www.liepin.com/mcp/server 获取新 Token |
| HTTP 406 | Accept 头不正确 | 已内置处理，正常不会触发 |
| HTTP 429 | 频率限制 | 等待 1 分钟后重试 |
| 网络超时 | 网络问题 | 重试一次 |
