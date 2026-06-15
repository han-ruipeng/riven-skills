#!/usr/bin/env python3
"""
猎聘 MCP CLI — 通过 MCP 协议调用猎聘求职工具 (v0.2.0)

Usage:
    python liepin_mcp.py search-job --jobName "AI产品经理" --address "上海"
    python liepin_mcp.py apply-job --jobId 12345 --jobKind "1"
    python liepin_mcp.py my-resume
    python liepin_mcp.py update-base-info --realName "张三" --nowWorkStatus "0"
    python liepin_mcp.py add-work-exp --compName "XX公司" --rwTitle "工程师" --workStart "202104" --workEnd "202601"
    python liepin_mcp.py list-tools
"""

import argparse
import json
import os
import sys
import uuid
import urllib.request
import urllib.error
from pathlib import Path

# ── 配置 ──────────────────────────────────────────────────────────────

DEFAULT_MCP_URL = "https://open-agent.liepin.com/mcp/user"

CONFIG_PATH = Path.home() / ".config" / "liepin-mcp" / "config.json"


def load_config():
    """加载配置（token 等）"""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_config(config):
    """保存配置"""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def get_token(config):
    """获取 token（仅需 x-user-token）"""
    token = config.get("user_token") or os.environ.get("LIEPIN_USER_TOKEN", "")

    if not token:
        print("错误: 未配置 token。请先运行: python liepin_mcp.py setup", file=sys.stderr)
        sys.exit(1)

    return token


# ── HTTP 请求（零依赖）────────────────────────────────────────────────

class McpSession:
    """MCP 会话管理，使用 urllib（无需 requests）"""

    def __init__(self, url, user_token):
        self.url = url
        self.user_token = user_token
        self.session_id = None

    def _post(self, payload, timeout=60):
        """发送 POST 请求"""
        data = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "x-user-token": self.user_token,
        }
        if self.session_id:
            headers["mcp-session-id"] = self.session_id

        req = urllib.request.Request(self.url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                # 保存 session ID
                sid = resp.headers.get("mcp-session-id")
                if sid:
                    self.session_id = sid
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            print(f"HTTP {e.code}: {body}", file=sys.stderr)
            sys.exit(1)
        except urllib.error.URLError as e:
            print(f"网络错误: {e.reason}", file=sys.stderr)
            sys.exit(1)

    def initialize(self):
        """MCP 初始化握手"""
        return self._post({
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "liepin-mcp-cli", "version": "0.2.0"},
            },
        })

    def list_tools(self):
        """列出所有可用工具"""
        return self._post({
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "tools/list",
            "params": {},
        })

    def call_tool(self, tool_name, arguments, timeout=60):
        """调用 MCP 工具"""
        return self._post({
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }, timeout=timeout)


def create_session(config):
    """创建并初始化 MCP 会话"""
    url = config.get("mcp_url", DEFAULT_MCP_URL)
    token = get_token(config)
    session = McpSession(url, token)
    session.initialize()
    return session


# ── 命令实现 ──────────────────────────────────────────────────────────

def cmd_setup(args):
    """配置 token"""
    config = load_config()
    print("猎聘 MCP 配置向导")
    print("=" * 40)
    print("请从 https://www.liepin.com/mcp/server 获取 token\n")
    print("登录后在页面找到「x-user-token」字段的值\n")

    user_token = input("x-user-token: ").strip()

    if user_token:
        config["user_token"] = user_token
    config["mcp_url"] = args.url or DEFAULT_MCP_URL

    save_config(config)
    print(f"\n配置已保存到 {CONFIG_PATH}")
    print("正在验证 token 有效性...")
    try:
        session = create_session(config)
        print("Token 验证成功！")
    except SystemExit:
        print("Token 验证失败，请检查 token 是否正确。")


def cmd_list_tools(args):
    """列出可用工具"""
    config = load_config()
    session = create_session(config)
    result = session.list_tools()

    if "result" in result and "tools" in result["result"]:
        tools = result["result"]["tools"]
        if args.json:
            print(json.dumps(tools, indent=2, ensure_ascii=False))
        else:
            print(f"\n共 {len(tools)} 个可用工具:\n")
            for tool in tools:
                print(f"  {tool['name']}")
                print(f"    {tool.get('description', '无描述')}")
                if "inputSchema" in tool:
                    props = tool["inputSchema"].get("properties", {})
                    if props:
                        params = ", ".join(props.keys())
                        required = tool["inputSchema"].get("required", [])
                        req_str = " (必填: " + ", ".join(required) + ")" if required else ""
                        print(f"    参数: {params}{req_str}")
                print()
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False))


def cmd_search_job(args):
    """搜索职位 (user-search-job)"""
    config = load_config()
    session = create_session(config)

    arguments = {}
    for key in ("jobName", "address", "salaryFloor", "salaryCap", "salaryKind",
                "workExperience", "eduLevel", "compNature", "companyName"):
        val = getattr(args, key, None)
        if val:
            arguments[key] = val
    if args.page is not None:
        arguments["page"] = args.page

    result = session.call_tool("user-search-job", arguments)
    _print_result(result, args.json)


def cmd_apply_job(args):
    """投递职位"""
    config = load_config()
    session = create_session(config)
    result = session.call_tool("user-apply-job", {
        "jobId": args.jobId,
        "jobKind": args.jobKind,
    })
    _print_result(result, args.json)


def cmd_my_resume(args):
    """查看简历"""
    config = load_config()
    session = create_session(config)
    result = session.call_tool("my-resume", {})
    _print_result(result, args.json)


# ── 简历更新命令（各模块独立）──────────────────────────────────────────

def _parse_data_arg(data_str):
    """解析 --data 参数，支持 JSON 或 key=value 格式"""
    if not data_str:
        return {}
    if data_str.strip().startswith("{"):
        return json.loads(data_str)
    # key=value,key=value 格式
    result = {}
    for pair in data_str.split(","):
        if "=" in pair:
            k, v = pair.split("=", 1)
            result[k.strip()] = v.strip()
    return result


def cmd_update_base_info(args):
    """更新简历基本信息 (modify-resume-base-info)"""
    config = load_config()
    session = create_session(config)

    arguments = _parse_data_arg(args.data) if args.data else {}
    # 也支持直接命令行参数
    for key in ("realName", "sex", "birthday", "cityCode", "startJob",
                "startJobMonth", "nowWorkStatus", "nowSalary", "nowMonths",
                "nowSalarySecret", "jobName", "nowComp", "nowIndusCode",
                "nowJobTitleCode", "nameSecret", "wechat", "politicalStatusCode"):
        val = getattr(args, key, None)
        if val is not None:
            # 数字类型
            if key in ("nowSalary", "nowMonths"):
                arguments[key] = int(val)
            else:
                arguments[key] = val

    if not arguments:
        print("错误: 请通过 --data 或具体参数指定要更新的字段", file=sys.stderr)
        sys.exit(1)

    result = session.call_tool("modify-resume-base-info", arguments)
    _print_result(result, args.json)


def cmd_update_self_assess(args):
    """更新自我评价 (modify-self-assess)"""
    config = load_config()
    session = create_session(config)
    arguments = _parse_data_arg(args.data) if args.data else {}
    if args.content:
        arguments["selfAssess"] = args.content
    if not arguments:
        print("错误: 请通过 --content 或 --data 指定自我评价内容", file=sys.stderr)
        sys.exit(1)
    result = session.call_tool("modify-self-assess", arguments)
    _print_result(result, args.json)


def cmd_add_edu_exp(args):
    """添加教育经历 (add-edu-exp)"""
    config = load_config()
    session = create_session(config)
    arguments = {
        "school": args.school,
        "degree": args.degree,
        "start": args.start,
        "end": args.end,
    }
    for key in ("major", "tz", "experience"):
        val = getattr(args, key, None)
        if val:
            arguments[key] = val
    result = session.call_tool("add-edu-exp", arguments)
    _print_result(result, args.json)


def cmd_modify_edu_exp(args):
    """修改教育经历 (modify-edu-exp)"""
    config = load_config()
    session = create_session(config)
    arguments = {"eduId": args.eduId}
    for key in ("school", "major", "start", "end", "degree", "tz", "experience"):
        val = getattr(args, key, None)
        if val:
            arguments[key] = val
    result = session.call_tool("modify-edu-exp", arguments)
    _print_result(result, args.json)


def cmd_add_work_exp(args):
    """添加工作经历 (add-work-exp)"""
    config = load_config()
    session = create_session(config)
    arguments = {
        "compName": args.compName,
        "rwTitle": args.rwTitle,
        "workStart": args.workStart,
        "workEnd": args.workEnd,
    }
    for key in ("industry", "jobtitle", "dq", "dept", "report",
                "subordinate", "duty", "months", "salary", "compkind",
                "compscale", "shieldComp", "labels", "workType"):
        val = getattr(args, key, None)
        if val is not None:
            if key in ("subordinate", "months", "salary", "workType"):
                arguments[key] = int(val)
            elif key == "shieldComp":
                arguments[key] = val.lower() in ("true", "1", "yes")
            else:
                arguments[key] = val
    result = session.call_tool("add-work-exp", arguments)
    _print_result(result, args.json)


def cmd_modify_work_exp(args):
    """修改工作经历 (modify-work-exp)"""
    config = load_config()
    session = create_session(config)
    arguments = {"workId": args.workId}
    for key in ("compName", "industry", "workStart", "workEnd", "rwTitle",
                "jobtitle", "dq", "dept", "report", "subordinate", "duty",
                "months", "salary", "compkind", "compscale", "shieldComp",
                "labels", "workType"):
        val = getattr(args, key, None)
        if val is not None:
            if key in ("subordinate", "months", "salary", "workType"):
                arguments[key] = int(val)
            elif key == "shieldComp":
                arguments[key] = val.lower() in ("true", "1", "yes")
            else:
                arguments[key] = val
    result = session.call_tool("modify-work-exp", arguments)
    _print_result(result, args.json)


def cmd_add_project_exp(args):
    """添加项目经历 (add-project-exp)"""
    config = load_config()
    session = create_session(config)
    arguments = {
        "name": args.name,
        "start": args.start,
        "end": args.end,
    }
    for key in ("compName", "position", "descr", "duty", "achievement"):
        val = getattr(args, key, None)
        if val:
            arguments[key] = val
    result = session.call_tool("add-project-exp", arguments)
    _print_result(result, args.json)


def cmd_modify_project_exp(args):
    """修改项目经历 (modify-project-exp)"""
    config = load_config()
    session = create_session(config)
    arguments = {"id": args.id}
    for key in ("name", "start", "end", "compName", "position", "descr", "duty", "achievement"):
        val = getattr(args, key, None)
        if val:
            arguments[key] = val
    result = session.call_tool("modify-project-exp", arguments)
    _print_result(result, args.json)


def cmd_add_job_want(args):
    """添加求职意向 (add-job-want)"""
    config = load_config()
    session = create_session(config)
    arguments = {
        "jobtitle": args.jobtitle,
        "dq": args.dq,
    }
    for key in ("industries", "wantSalaryLow", "wantSalaryHigh",
                "wantSalaryMonths", "workType", "otherExpectDqs",
                "workweek", "practiceMonths"):
        val = getattr(args, key, None)
        if val is not None:
            if key in ("industries", "otherExpectDqs"):
                arguments[key] = [x.strip() for x in val.split(",")]
            elif key in ("wantSalaryLow", "wantSalaryHigh", "wantSalaryMonths", "workweek", "practiceMonths"):
                arguments[key] = int(val) if val else None
            else:
                arguments[key] = val
    result = session.call_tool("add-job-want", arguments)
    _print_result(result, args.json)


def cmd_modify_job_want(args):
    """修改求职意向 (modify-job-want)"""
    config = load_config()
    session = create_session(config)
    arguments = {"id": args.id}
    for key in ("industries", "jobtitle", "dq", "wantSalaryLow", "wantSalaryHigh",
                "wantSalaryMonths", "workType", "otherExpectDqs",
                "workweek", "practiceMonths"):
        val = getattr(args, key, None)
        if val is not None:
            if key in ("industries", "otherExpectDqs"):
                arguments[key] = [x.strip() for x in val.split(",")]
            elif key in ("wantSalaryLow", "wantSalaryHigh", "wantSalaryMonths", "workweek", "practiceMonths"):
                arguments[key] = int(val) if val else None
            else:
                arguments[key] = val
    result = session.call_tool("modify-job-want", arguments)
    _print_result(result, args.json)


def cmd_call(args):
    """通用 MCP 工具调用"""
    config = load_config()
    session = create_session(config)

    arguments = json.loads(args.arguments) if args.arguments else {}
    result = session.call_tool(args.tool, arguments)
    _print_result(result, args.json)


def _print_result(result, as_json=False):
    """输出结果"""
    if "result" in result:
        content = result["result"]
        if as_json:
            print(json.dumps(content, indent=2, ensure_ascii=False))
        else:
            # MCP tool result: {"content": [{"type": "text", "text": "..."}]}
            if isinstance(content, dict) and "content" in content:
                for item in content["content"]:
                    if item.get("type") == "text":
                        text = item["text"]
                        try:
                            parsed = json.loads(text)
                            print(json.dumps(parsed, indent=2, ensure_ascii=False))
                        except (json.JSONDecodeError, TypeError):
                            print(text)
            else:
                print(json.dumps(content, indent=2, ensure_ascii=False))
    elif "error" in result:
        err = result["error"]
        print(f"错误 [{err.get('code', '?')}]: {err.get('message', '未知错误')}", file=sys.stderr)
        sys.exit(1)
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False))


# ── CLI 入口 ──────────────────────────────────────────────────────────

def _add_json_arg(p):
    p.add_argument("--json", action="store_true", help="JSON 格式输出")


def main():
    parser = argparse.ArgumentParser(
        description="猎聘 MCP CLI v0.2.0 — 求职搜索、投递、简历管理",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--url", default=None, help="MCP 服务端 URL")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # setup
    sp_setup = subparsers.add_parser("setup", help="配置 x-user-token")
    sp_setup.set_defaults(func=cmd_setup)

    # list-tools
    sp_list = subparsers.add_parser("list-tools", help="列出所有可用工具")
    _add_json_arg(sp_list)
    sp_list.set_defaults(func=cmd_list_tools)

    # search-job
    sp_search = subparsers.add_parser("search-job", help="搜索职位")
    sp_search.add_argument("--jobName", help="职位名称关键词, 如 'AI产品经理'")
    sp_search.add_argument("--address", help="工作地点, 如 '上海'")
    sp_search.add_argument("--salaryFloor", help="薪资下限, 如 '15000'")
    sp_search.add_argument("--salaryCap", help="薪资上限, 如 '25000'")
    sp_search.add_argument("--salaryKind", help="薪资类型: 月薪/年薪")
    sp_search.add_argument("--workExperience", help="工作经验要求, 如 '3-5年'")
    sp_search.add_argument("--eduLevel", help="学历要求")
    sp_search.add_argument("--compNature", help="公司性质: 外企/国企/民企/合资/外资/私营")
    sp_search.add_argument("--companyName", help="公司名称, 如 '字节跳动'")
    sp_search.add_argument("--page", type=int, help="页码 (0=第1页)")
    _add_json_arg(sp_search)
    sp_search.set_defaults(func=cmd_search_job)

    # apply-job
    sp_apply = subparsers.add_parser("apply-job", help="投递职位")
    sp_apply.add_argument("--jobId", type=int, required=True, help="职位 ID")
    sp_apply.add_argument("--jobKind", required=True, help="职位类型")
    _add_json_arg(sp_apply)
    sp_apply.set_defaults(func=cmd_apply_job)

    # my-resume
    sp_resume = subparsers.add_parser("my-resume", help="查看我的简历")
    _add_json_arg(sp_resume)
    sp_resume.set_defaults(func=cmd_my_resume)

    # update-base-info
    sp_ubi = subparsers.add_parser("update-base-info", help="更新简历基本信息")
    sp_ubi.add_argument("--data", help="更新数据 (JSON字符串 或 key=value,key=value)")
    sp_ubi.add_argument("--realName", help="真实姓名")
    sp_ubi.add_argument("--sex", help="性别: 男/女")
    sp_ubi.add_argument("--birthday", help="生日 yyyyMMdd, 如 '19961201'")
    sp_ubi.add_argument("--cityCode", help="当前所在城市编码")
    sp_ubi.add_argument("--startJob", help="开始工作年份, 如 '2021'")
    sp_ubi.add_argument("--startJobMonth", help="开始工作月份, 如 '04'")
    sp_ubi.add_argument("--nowWorkStatus", help="当前状态: 0=离职-看机会,1=在职-找工作,2=离职-已找到,3=在职-看机会,4=在校-找工作,5=在校-找机会,6=在校-实习,7=在校-已找到")
    sp_ubi.add_argument("--nowSalary", help="当前月薪(元)")
    sp_ubi.add_argument("--nowMonths", help="当前年薪月数")
    sp_ubi.add_argument("--nowSalarySecret", help="薪资保密: 0=显示, 1=保密")
    sp_ubi.add_argument("--jobName", help="当前职位名称")
    sp_ubi.add_argument("--nowComp", help="当前公司名称")
    sp_ubi.add_argument("--nowIndusCode", help="当前行业编码")
    sp_ubi.add_argument("--nowJobTitleCode", help="当前职能编码")
    sp_ubi.add_argument("--nameSecret", help="姓名隐私: 0=全名, 1=X先生/女士")
    sp_ubi.add_argument("--wechat", help="微信号")
    sp_ubi.add_argument("--politicalStatusCode", help="政治面貌: 1=党员,2=预备党员,3=共青团员,4=群众,5=民主党派,6=其他")
    _add_json_arg(sp_ubi)
    sp_ubi.set_defaults(func=cmd_update_base_info)

    # update-self-assess
    sp_usa = subparsers.add_parser("update-self-assess", help="更新自我评价")
    sp_usa.add_argument("--content", help="自我评价内容")
    sp_usa.add_argument("--data", help="更新数据 (JSON: {\"selfAssess\":\"...\"})")
    _add_json_arg(sp_usa)
    sp_usa.set_defaults(func=cmd_update_self_assess)

    # add-edu-exp
    sp_aee = subparsers.add_parser("add-edu-exp", help="添加教育经历")
    sp_aee.add_argument("--school", required=True, help="学校名称")
    sp_aee.add_argument("--degree", required=True, help="学历: 090=初中及以下,080=高中,060=中专/中级,050=大专,040=本科,030=硕士,020=MBA/EMBA,010=博士")
    sp_aee.add_argument("--start", required=True, help="开始时间 YYYYMM, 如 '201509'")
    sp_aee.add_argument("--end", required=True, help="结束时间 YYYYMM, 如 '201906'")
    sp_aee.add_argument("--major", help="专业名称")
    sp_aee.add_argument("--tz", help="统招标志: 0=是, 1=否")
    sp_aee.add_argument("--experience", help="在校经历")
    _add_json_arg(sp_aee)
    sp_aee.set_defaults(func=cmd_add_edu_exp)

    # modify-edu-exp
    sp_mee = subparsers.add_parser("modify-edu-exp", help="修改教育经历")
    sp_mee.add_argument("--eduId", type=int, required=True, help="教育经历 ID")
    sp_mee.add_argument("--school", help="学校名称")
    sp_mee.add_argument("--major", help="专业名称")
    sp_mee.add_argument("--start", help="开始时间 YYYYMM")
    sp_mee.add_argument("--end", help="结束时间 YYYYMM")
    sp_mee.add_argument("--degree", help="学历编码")
    sp_mee.add_argument("--tz", help="统招标志")
    sp_mee.add_argument("--experience", help="在校经历")
    _add_json_arg(sp_mee)
    sp_mee.set_defaults(func=cmd_modify_edu_exp)

    # add-work-exp
    sp_awe = subparsers.add_parser("add-work-exp", help="添加工作经历")
    sp_awe.add_argument("--compName", required=True, help="公司名称")
    sp_awe.add_argument("--rwTitle", required=True, help="职位名称")
    sp_awe.add_argument("--workStart", required=True, help="入职时间 YYYYMM")
    sp_awe.add_argument("--workEnd", required=True, help="离职时间 YYYYMM")
    sp_awe.add_argument("--industry", help="所属行业名称")
    sp_awe.add_argument("--jobtitle", help="职位类别/职能名称")
    sp_awe.add_argument("--dq", help="工作地点城市")
    sp_awe.add_argument("--dept", help="所在部门")
    sp_awe.add_argument("--report", help="汇报对象职位")
    sp_awe.add_argument("--subordinate", type=int, help="下属人数")
    sp_awe.add_argument("--duty", help="职责业绩描述")
    sp_awe.add_argument("--months", type=int, help="年薪月数")
    sp_awe.add_argument("--salary", type=int, help="薪资(元)")
    sp_awe.add_argument("--compkind", help="公司性质编码")
    sp_awe.add_argument("--compscale", help="公司规模编码")
    sp_awe.add_argument("--shieldComp", help="屏蔽该公司: true/false")
    sp_awe.add_argument("--labels", help="技能标签, 英文逗号分隔")
    sp_awe.add_argument("--workType", type=int, help="类型: 1=全职, 2=实习")
    _add_json_arg(sp_awe)
    sp_awe.set_defaults(func=cmd_add_work_exp)

    # modify-work-exp
    sp_mwe = subparsers.add_parser("modify-work-exp", help="修改工作经历")
    sp_mwe.add_argument("--workId", type=int, required=True, help="工作经历 ID")
    sp_mwe.add_argument("--compName", help="公司名称")
    sp_mwe.add_argument("--industry", help="所属行业名称")
    sp_mwe.add_argument("--workStart", help="入职时间 YYYYMM")
    sp_mwe.add_argument("--workEnd", help="离职时间 YYYYMM")
    sp_mwe.add_argument("--rwTitle", help="职位名称")
    sp_mwe.add_argument("--jobtitle", help="职位类别/职能名称")
    sp_mwe.add_argument("--dq", help="工作地点城市")
    sp_mwe.add_argument("--dept", help="所在部门")
    sp_mwe.add_argument("--report", help="汇报对象职位")
    sp_mwe.add_argument("--subordinate", type=int, help="下属人数")
    sp_mwe.add_argument("--duty", help="职责业绩描述")
    sp_mwe.add_argument("--months", type=int, help="年薪月数")
    sp_mwe.add_argument("--salary", type=int, help="薪资(元)")
    sp_mwe.add_argument("--compkind", help="公司性质编码")
    sp_mwe.add_argument("--compscale", help="公司规模编码")
    sp_mwe.add_argument("--shieldComp", help="屏蔽该公司: true/false")
    sp_mwe.add_argument("--labels", help="技能标签, 英文逗号分隔")
    sp_mwe.add_argument("--workType", type=int, help="类型: 1=全职, 2=实习")
    _add_json_arg(sp_mwe)
    sp_mwe.set_defaults(func=cmd_modify_work_exp)

    # add-project-exp
    sp_ape = subparsers.add_parser("add-project-exp", help="添加项目经历")
    sp_ape.add_argument("--name", required=True, help="项目名称")
    sp_ape.add_argument("--start", required=True, help="项目开始时间 YYYYMM")
    sp_ape.add_argument("--end", required=True, help="项目结束时间 YYYYMM")
    sp_ape.add_argument("--compName", help="公司名称")
    sp_ape.add_argument("--position", help="担任职务")
    sp_ape.add_argument("--descr", help="项目描述")
    sp_ape.add_argument("--duty", help="项目职责")
    sp_ape.add_argument("--achievement", help="项目业绩")
    _add_json_arg(sp_ape)
    sp_ape.set_defaults(func=cmd_add_project_exp)

    # modify-project-exp
    sp_mpe = subparsers.add_parser("modify-project-exp", help="修改项目经历")
    sp_mpe.add_argument("--id", type=int, required=True, help="项目经历 ID")
    sp_mpe.add_argument("--name", help="项目名称")
    sp_mpe.add_argument("--start", help="项目开始时间 YYYYMM")
    sp_mpe.add_argument("--end", help="项目结束时间 YYYYMM")
    sp_mpe.add_argument("--compName", help="公司名称")
    sp_mpe.add_argument("--position", help="担任职务")
    sp_mpe.add_argument("--descr", help="项目描述")
    sp_mpe.add_argument("--duty", help="项目职责")
    sp_mpe.add_argument("--achievement", help="项目业绩")
    _add_json_arg(sp_mpe)
    sp_mpe.set_defaults(func=cmd_modify_project_exp)

    # add-job-want
    sp_ajw = subparsers.add_parser("add-job-want", help="添加求职意向")
    sp_ajw.add_argument("--jobtitle", required=True, help="期望职位/职能名称")
    sp_ajw.add_argument("--dq", required=True, help="期望工作城市")
    sp_ajw.add_argument("--industries", help="期望行业列表, 英文逗号分隔")
    sp_ajw.add_argument("--wantSalaryLow", type=int, help="期望薪资下限(元)")
    sp_ajw.add_argument("--wantSalaryHigh", type=int, help="期望薪资上限(元)")
    sp_ajw.add_argument("--wantSalaryMonths", type=int, help="期望年薪月数")
    sp_ajw.add_argument("--workType", help="类型: 0=应届, 1=实习")
    sp_ajw.add_argument("--otherExpectDqs", help="其他感兴趣的城市, 英文逗号分隔")
    sp_ajw.add_argument("--workweek", type=int, help="每周工作天数")
    sp_ajw.add_argument("--practiceMonths", type=int, help="实习月数")
    _add_json_arg(sp_ajw)
    sp_ajw.set_defaults(func=cmd_add_job_want)

    # modify-job-want
    sp_mjw = subparsers.add_parser("modify-job-want", help="修改求职意向")
    sp_mjw.add_argument("--id", type=int, required=True, help="求职意向 ID")
    sp_mjw.add_argument("--industries", help="期望行业列表, 英文逗号分隔")
    sp_mjw.add_argument("--jobtitle", help="期望职位/职能名称")
    sp_mjw.add_argument("--dq", help="期望工作城市")
    sp_mjw.add_argument("--wantSalaryLow", type=int, help="期望薪资下限(元)")
    sp_mjw.add_argument("--wantSalaryHigh", type=int, help="期望薪资上限(元)")
    sp_mjw.add_argument("--wantSalaryMonths", type=int, help="期望年薪月数")
    sp_mjw.add_argument("--workType", help="类型: 0=应届, 1=实习")
    sp_mjw.add_argument("--otherExpectDqs", help="其他感兴趣的城市, 英文逗号分隔")
    sp_mjw.add_argument("--workweek", type=int, help="每周工作天数")
    sp_mjw.add_argument("--practiceMonths", type=int, help="实习月数")
    _add_json_arg(sp_mjw)
    sp_mjw.set_defaults(func=cmd_modify_job_want)

    # call (通用调用)
    sp_call = subparsers.add_parser("call", help="通用 MCP 工具调用")
    sp_call.add_argument("tool", help="工具名称")
    sp_call.add_argument("--arguments", "-a", help="参数 (JSON 字符串)")
    _add_json_arg(sp_call)
    sp_call.set_defaults(func=cmd_call)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
