#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""探测微信公众平台对本机授权账号是否仍在频控。

用途：取代每周「打开面板逐个点更新」那一步。频控期间点更新必然是 0 条，
纯浪费时间；这个脚本 5 秒内直接给出微信后台的原始返回码。

返回码含义（来自 core/wx/model/web.py 的判断分支）：
    0       正常，可以走自动采集 → python scripts/fetch_vln.py --days 10
    200013  freq control，账号级频控，本地无解，走方式 A 手动喂链接
    200003  Invalid Session，授权过期，需要去面板重新扫码
    200002  Invalid arguments，参数/订阅异常

退出码与返回码对应：0=通，1=频控，2=授权过期，3=其他异常。
"""
import subprocess
import sys

# Windows 控制台默认 GBK，打印 ✗/✓ 会直接 UnicodeEncodeError，强制 UTF-8
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

CONTAINER = "we-mp-rss"
PYBIN = "/app/env_x86_64/bin/python"

# 在容器内跑：复用 we-mp-rss 已保存的 token 与 cookie，直接打一次后台接口。
# 只取 count=1，尽量不消耗配额。
PROBE = r'''
import json, urllib3
import init_sys as init; init.init()
from core.wx.model.web import MpsWeb
urllib3.disable_warnings()
w = MpsWeb()
url = "https://mp.weixin.qq.com/cgi-bin/appmsgpublish"
params = {"sub": "list", "search_field": "null", "begin": "0", "count": "1",
          "query": "", "fakeid": "", "type": "101_1", "free_publish_type": "1",
          "sub_action": "list_ex", "token": w.token, "lang": "zh_CN",
          "f": "json", "ajax": "1"}
import core.db as db
mps = db.DB.get_all_mps()
if mps:
    params["fakeid"] = mps[0].faker_id
try:
    r = w.session.get(url, headers=w.fix_header(url), params=params,
                      verify=False, timeout=(10, 30))
    br = r.json().get("base_resp", {})
    print("PROBE_RESULT " + json.dumps(
        {"ret": br.get("ret"), "err": br.get("err_msg"),
         "mp": mps[0].mp_name if mps else None}, ensure_ascii=False))
except Exception as e:
    print("PROBE_RESULT " + json.dumps(
        {"ret": -1, "err": "%s: %s" % (type(e).__name__, e)}, ensure_ascii=False))
'''


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", **kw)


def main():
    if run(["docker", "info"]).returncode != 0:
        print("✗ Docker 引擎没运行。先启动 Docker Desktop，等托盘图标变绿再重跑。")
        return 3

    ps = run(["docker", "ps", "--filter", f"name={CONTAINER}",
              "--format", "{{.Names}}"])
    if CONTAINER not in ps.stdout:
        print(f"✗ 容器 {CONTAINER} 没在运行。执行：")
        print("    cd we-mp-rss && docker compose up -d")
        return 3

    p = run(["docker", "exec", "-w", "/app", "-e", "PYTHONIOENCODING=utf-8",
             CONTAINER, PYBIN, "-c", PROBE])
    line = next((l for l in (p.stdout + p.stderr).splitlines()
                 if l.startswith("PROBE_RESULT ")), None)
    if not line:
        print("✗ 探针没拿到返回。容器日志：docker logs we-mp-rss --tail 50")
        return 3

    import json
    d = json.loads(line[len("PROBE_RESULT "):])
    ret, err, mp = d.get("ret"), d.get("err"), d.get("mp")
    print(f"探测公众号: {mp}    微信返回: ret={ret} err_msg={err}")

    if ret == 0:
        print("✓ 频控已恢复，可以走自动采集：")
        print("    1) 面板 http://localhost:8001 逐个点「更新」")
        print("    2) python scripts/fetch_vln.py --days 10")
        return 0
    if ret == 200013:
        print("✗ 仍在频控（账号级，本地无解）。走方式 A 手动喂链接：")
        print("    把文章链接贴进 wechat_urls.txt，然后")
        print("    python scripts/fetch_vln.py --urls wechat_urls.txt --no-feeds")
        return 1
    if ret == 200003:
        print("✗ 授权过期。去面板 http://localhost:8001 重新扫码授权。")
        return 2
    print("✗ 未预期的返回码，去容器日志确认：docker logs we-mp-rss --tail 50")
    return 3


if __name__ == "__main__":
    sys.exit(main())
