---
status: observed
scope: GitHub 部署 / Git 远程配置
date: 2025-09-15
---
DeepCareer 的 GitHub 远程仓库已 fork 到 napstablook666/DeepCareer（原上游 Zijie933/DeepCareer），
并配置了 GH_TOKEN（`gh` CLI 使用）和 GITHUB_TOKEN 两个系统环境变量（用户级）用于 HTTPS 认证。

适用：
- git push / gh CLI 操作自动使用该 token 认证，无需手动输入凭据。

不适用：
- 新终端窗口才生效（setx 特性）；当前窗口用 gh keyring 认证。

证据：
- D:/AI/DeepCareer/.git/config（remote origin = napstablook666/DeepCareer）
- Windows 用户环境变量：GH_TOKEN, GITHUB_TOKEN

候选归宿：attention