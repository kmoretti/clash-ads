# clash-ads

仅大陆使用的 Clash Meta（mihomo）去广告规则订阅，规则源为
[秋风广告规则](https://github.com/TG-Twilight/AWAvenue-Ads-Rule)，
每天北京时间凌晨 3 点由 GitHub Actions 自动更新。

无任何机场节点，全部流量直连，仅广告域名 REJECT。配置内含一个不承载流量的占位节点（客户端要求 profile 非空才能导入）。
适配 Clash Meta for Android 与 FlClash。

## 订阅地址

直链：

```text
https://raw.githubusercontent.com/kmoretti/clash-ads/main/dist/config.yaml
```

大陆环境若直链拉取失败，在链接前加加速前缀：

```text
https://ghfast.top/https://raw.githubusercontent.com/kmoretti/clash-ads/main/dist/config.yaml
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
