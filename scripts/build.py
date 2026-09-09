#!/usr/bin/env python3
"""生成 dist/config.yaml 并同步秋风规则副本到 dist/rules/。

输入:
  custom/direct.list  误杀放行域名（每行一个，# 注释）
  custom/reject.list  额外拦截域名（每行一个，# 注释）
输出:
  dist/config.yaml                     完整 mihomo 配置（订阅入口）
  dist/rules/AWAvenue-Ads-Classical.yaml  上游规则副本（rule-provider 引用）
"""
import os
import pathlib
import urllib.request

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
UPSTREAM_URL = (
    "https://raw.githubusercontent.com/TG-Twilight/AWAvenue-Ads-Rule/"
    "main/Filters/AWAvenue-Ads-Rule-Clash-Classical.yaml"
)

CONFIG_HEADER = """\
# 由 scripts/build.py 自动生成，请勿直接编辑
# 上游规则: AWAvenue 秋风广告规则 https://github.com/TG-Twilight/AWAvenue-Ads-Rule
# 适配: Clash Meta for Android / FlClash（mihomo 内核），无节点，全直连，仅拦截广告

mode: rule
ipv6: true
log-level: info

profile:
  store-fake-ip: true

dns:
  enable: true
  enhanced-mode: fake-ip
  fake-ip-range: 198.18.0.1/16
  fake-ip-filter:
    - "+.lan"
    - "+.local"
    - "+.msftconnecttest.com"
    - "+.msftncsi.com"
  nameserver:
    - 223.5.5.5
    - 119.29.29.29
"""


def read_domains(path: pathlib.Path) -> list[str]:
    if not path.exists():
        return []
    domains = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            domains.append(line)
    return domains


def fetch_upstream() -> bytes:
    req = urllib.request.Request(UPSTREAM_URL, headers={"User-Agent": "clash-ads-builder"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = resp.read()
    # 校验上游仍是合法 YAML 且包含规则列表，格式变更时当场失败
    parsed = yaml.safe_load(data)
    if not isinstance(parsed, dict) or "payload" not in parsed:
        raise SystemExit("ERROR: upstream rule format changed, payload missing")
    return data


def main() -> None:
    repo = os.environ.get("GITHUB_REPOSITORY", "kmoretti/clash-ads")
    rules_url = (
        f"https://raw.githubusercontent.com/{repo}/main/"
        "dist/rules/AWAvenue-Ads-Classical.yaml"
    )

    upstream = fetch_upstream()
    direct = read_domains(ROOT / "custom" / "direct.list")
    reject = read_domains(ROOT / "custom" / "reject.list")

    rules = [f"DOMAIN-SUFFIX,{d},DIRECT" for d in direct]
    rules += [f"DOMAIN-SUFFIX,{d},REJECT" for d in reject]
    rules.append("RULE-SET,AWAvenue-Ads,REJECT")
    rules.append("MATCH,DIRECT")

    config = (
        CONFIG_HEADER
        + f"""
rule-providers:
  AWAvenue-Ads:
    type: http
    behavior: classical
    format: yaml
    url: "{rules_url}"
    path: ./ruleset/AWAvenue-Ads.yaml
    interval: 86400

rules:
"""
        + "\n".join(f"  - {r}" for r in rules)
        + "\n"
    )

    # 自检：生成结果必须是合法 YAML 且规则数正确
    parsed = yaml.safe_load(config)
    assert parsed["rules"][-1] == "MATCH,DIRECT"
    assert len(parsed["rules"]) == len(direct) + len(reject) + 2

    dist = ROOT / "dist"
    (dist / "rules").mkdir(parents=True, exist_ok=True)
    (dist / "config.yaml").write_text(config, encoding="utf-8", newline="\n")
    (dist / "rules" / "AWAvenue-Ads-Classical.yaml").write_bytes(upstream)
    print(f"OK: {len(direct)} direct / {len(reject)} reject custom rules; config + ruleset written")


if __name__ == "__main__":
    main()
