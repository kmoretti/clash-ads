# Clash 去广告规则订阅 实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 生成一份适配 Clash Meta for Android 与 FlClash 的"纯大陆去广告" mihomo 配置订阅，规则源为秋风广告规则（AWAvenue），含 custom 拦截/放行自定义，GitHub Actions 每天北京时间凌晨 3 点自动更新。

**Architecture:** 仓库内维护两个纯文本自定义域名列表（`custom/reject.list`、`custom/direct.list`），Python 脚本将秋风 Classical 规则副本 + 自定义规则拼装为完整 mihomo 配置输出到 `dist/`；GitHub Actions 定时构建、mihomo 校验后提交回 main；手机端直接订阅 `dist/config.yaml` 的 raw 直链。

**Tech Stack:** mihomo (Clash.Meta) 配置语法、Python 3 + PyYAML、GitHub Actions。

---

## 已锁定的决策（grill-me 访谈结论）

| 决策点 | 结论 |
| --- | --- |
| 交付形态 | 完整 mihomo 配置文件，两端直接订阅导入 |
| 上游规则 | `Filters/AWAvenue-Ads-Rule-Clash-Classical.yaml`（behavior: classical） |
| 自定义 | `custom/reject.list`（拦截）+ `custom/direct.list`（误杀放行），每行一个域名，`#` 开头为注释 |
| 放行优先级 | custom direct → custom reject → 秋风 RULE-SET → MATCH 全直连 |
| DNS | fake-ip，`nameserver: 223.5.5.5 / 119.29.29.29`，无境外 fallback，无 geodata |
| 工作流 | GitHub Actions，`cron: "0 19 * * *"`（UTC，= 北京 3:00），产物提交 main，无变化跳过 commit |
| 工具链 | Python 生成 + CI 内 `mihomo -t` 校验，校验失败不产出新配置 |
| 关键适配 | rule-provider 的 url 指向**本仓库** `dist/rules/AWAvenue-Ads-Classical.yaml`（每日由 workflow 同步上游），不直连上游 raw——否则大陆手机拉不到规则 |

## 目录结构（最终态）

```text
clash-ads/
├── .github/workflows/update.yml      # 每日构建工作流
├── custom/
│   ├── direct.list                   # 误杀放行（每行一个域名）
│   └── reject.list                   # 额外拦截（每行一个域名）
├── scripts/
│   └── build.py                      # 生成器
├── dist/                             # 生成产物（提交入库，订阅直链指向这里）
│   ├── config.yaml
│   └── rules/AWAvenue-Ads-Classical.yaml
├── docs/plans/                       # 本计划
└── README.md
```

---

### Task 1: 仓库骨架（custom 列表 + README + git 初始化）

**Files:**
- Create: `custom/direct.list`
- Create: `custom/reject.list`
- Create: `README.md`

**Step 1: 写入 `custom/direct.list`**

```text
# 误杀放行列表：每行一个域名，匹配含其所有子域（DOMAIN-SUFFIX）
# 以 # 开头的行为注释。此列表的优先级最高，先于秋风规则生效。
# 示例（去掉行首 # 即生效）：
# example.com
```

**Step 2: 写入 `custom/reject.list`**

```text
# 额外拦截列表：每行一个域名，匹配含其所有子域（DOMAIN-SUFFIX）
# 以 # 开头的行为注释。此列表在秋风规则之前生效。
# 示例（去掉行首 # 即生效）：
# ads.example.com
```

**Step 3: 写入 `README.md`**

````markdown
# clash-ads

仅大陆使用的 Clash Meta（mihomo）去广告规则订阅，规则源为
[秋风广告规则](https://github.com/TG-Twilight/AWAvenue-Ads-Rule)，
每天北京时间凌晨 3 点由 GitHub Actions 自动更新。

无任何节点 / 代理组，全部流量直连，仅广告域名 REJECT。
适配 Clash Meta for Android 与 FlClash。

## 订阅地址

直链：

```text
https://raw.githubusercontent.com/kmoretti-github/clash-ads/main/dist/config.yaml
```

大陆环境若直链拉取失败，在链接前加加速前缀：

```text
https://ghfast.top/https://raw.githubusercontent.com/kmoretti-github/clash-ads/main/dist/config.yaml
```

## 导入方法

- **Clash Meta for Android**：配置 → 右上角「+」→ 从 URL 导入 → 粘贴订阅地址 → 保存后选中。
- **FlClash**：配置 → 新增 → URL → 粘贴订阅地址 → 保存后选中。

规则每日自动更新后，在 App 内下拉刷新配置即可；也可在设置中开启配置自动更新。

## 自定义域名

编辑仓库内两个纯文本文件（每行一个域名，含其全部子域），提交后次日构建生效：

- `custom/reject.list`：额外拦截（秋风规则未覆盖的广告 / 骚扰域名）
- `custom/direct.list`：误杀放行（秋风规则误伤的正常域名，**优先级最高**）

## 仓库结构

```text
custom/     自定义域名列表（手工维护）
scripts/    构建脚本 build.py
dist/       自动生成产物，勿手改；config.yaml 为订阅入口
```
````

**Step 4: git 初始化与首次提交**

```bash
git init
git add custom/ README.md docs/
git commit -m "chore: init repo with custom lists and docs" -m "Made-with: Proma"
```

---

### Task 2: 生成脚本 `scripts/build.py`

**Files:**
- Create: `scripts/build.py`

**Step 1: 写入脚本（完整实现）**

```python
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
    repo = os.environ.get("GITHUB_REPOSITORY", "kmoretti-github/clash-ads")
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
    assert parsed["rules"][0].startswith("DOMAIN-SUFFIX") or len(direct) == 0
    assert parsed["rules"][-1] == "MATCH,DIRECT"
    assert len(parsed["rules"]) == len(direct) + len(reject) + 2

    dist = ROOT / "dist"
    (dist / "rules").mkdir(parents=True, exist_ok=True)
    (dist / "config.yaml").write_text(config, encoding="utf-8")
    (dist / "rules" / "AWAvenue-Ads-Classical.yaml").write_bytes(upstream)
    print(f"OK: {len(direct)} direct / {len(reject)} reject custom rules; config + ruleset written")


if __name__ == "__main__":
    main()
```

**Step 2: 安装依赖并本地运行**

Run: `pip install pyyaml && python scripts/build.py`
Expected: 输出 `OK: 0 direct / 0 reject custom rules; config + ruleset written`

**Step 3: 验证产物**

Run: `grep -c "DOMAIN-SUFFIX" dist/config.yaml && tail -n 3 dist/config.yaml`
Expected: `0`（暂无自定义域名）；末尾三行为 `RULE-SET,AWAvenue-Ads,REJECT` 与 `MATCH,DIRECT`

**Step 4: 提交**

```bash
git add scripts/build.py
git commit -m "feat: add config builder script" -m "Made-with: Proma"
```

---

### Task 3: 每日构建工作流 `.github/workflows/update.yml`

**Files:**
- Create: `.github/workflows/update.yml`

**Step 1: 写入工作流（完整实现）**

```yaml
name: update-rules

on:
  schedule:
    # UTC 19:00 = 北京时间次日 03:00
    - cron: "0 19 * * *"
  workflow_dispatch:

permissions:
  contents: write

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install deps
        run: pip install pyyaml

      - name: Build config
        env:
          GITHUB_REPOSITORY: ${{ github.repository }}
        run: python scripts/build.py

      - name: Validate with mihomo
        run: |
          curl -sSL -o mihomo.gz \
            https://github.com/MetaCubeX/mihomo/releases/latest/download/mihomo-linux-amd64-v3.gz
          gunzip mihomo.gz
          chmod +x mihomo
          ./mihomo -t -d . -f dist/config.yaml

      - name: Commit and push
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add dist
          if git diff --cached --quiet; then
            echo "No changes, skip commit"
            exit 0
          fi
          git commit -m "chore: update ad-block rules ($(date -u +%F))" -m "Made-with: Proma"
          git push
```

**Step 2: 提交**

```bash
git add .github/workflows/update.yml
git commit -m "ci: daily rule update workflow" -m "Made-with: Proma"
```

---

### Task 4: 首次构建、推送并触发验证

**Step 1: 本地生成首次产物**

Run: `python scripts/build.py`
Expected: `OK: ...`

**Step 2: 提交并推送**

```bash
git add dist/
git commit -m "chore: initial generated config" -m "Made-with: Proma"
git push -u origin main
```

若本地未配置远端，先 `git remote add origin git@github.com:kmoretti-github/clash-ads.git`（以实际仓库地址为准）。

**Step 3: 触发工作流验证**

```bash
gh workflow run update-rules && gh run watch
```

Expected: `Build config` 输出 OK；`Validate with mihomo` 输出 `configuration file ... test is successful`；有变更时产生一条 update commit 并推送。

**Step 4: 端到端抽查**

Run: `curl -s https://raw.githubusercontent.com/kmoretti-github/clash-ads/main/dist/config.yaml | tail -n 2`
Expected: `RULE-SET,AWAvenue-Ads,REJECT` 与 `MATCH,DIRECT`

---

### Task 5: 验收（对应已锁决策）

- [ ] `dist/config.yaml`：无 `proxies`、`proxy-groups`、GEOSITE/GEOIP；fake-ip DNS；规则顺序为 custom direct → custom reject → RULE-SET → MATCH
- [ ] `custom/*.list` 中加一条测试域名 → 重跑 workflow → `dist/config.yaml` 出现对应 `DOMAIN-SUFFIX,...,REJECT/DIRECT`
- [ ] 上游规则副本 `dist/rules/AWAvenue-Ads-Classical.yaml` 与上游内容一致
- [ ] CMFA / FlClash 用订阅直链（或 ghfast 前缀链接）导入成功，App 内规则页可见 AWAvenue-Ads 规则集
