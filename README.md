# Tech Blog

基于 **Hugo + PaperMod** 的静态博客，部署到 GitHub Pages。

- 站点地址：https://zxxsmiles.github.io/tech-blog/
- 仓库：https://github.com/zxxsmiles/tech-blog

## 发布新文章

```bash
# 1. 拉取最新 main
git switch main && git pull

# 2. 建分支
git switch -c post/my-new-post

# 3. 用模板新建文章（自动生成四个字段的 frontmatter）
hugo new posts/my-new-post.md

# 4. 本地预览
hugo server -D
# 打开 http://localhost:1313/tech-blog/

# 5. 提交并提 PR
git add content/posts/my-new-post.md
git commit -m "post: my new post"
git push -u origin post/my-new-post
# 然后在 GitHub 上开 PR，合并到 main
```

合并到 `main` 后，`.github/workflows/deploy.yml` 会自动构建并部署。

## 文章规范

新文章放在 `content/posts/` 下，Markdown 格式，frontmatter **四个字段**：

```yaml
---
title: "文章标题"
date: 2026-09-21T10:30:00+08:00
tags: ["标签一", "标签二"]
author: "zhangxiaoxing"
---
```

## 本地开发

```bash
# 需要 Hugo extended 0.166.0+
brew install hugo

hugo server -D          # 草稿也渲染
hugo --minify           # 生成到 public/
```

## 目录结构

```
.
├── archetypes/posts.md          # 新文章模板（定义四个 frontmatter 字段）
├── content/
│   ├── posts/                   # 文章都在这里
│   └── search.md                # 站内搜索页
├── themes/PaperMod/             # 主题（已 vendored 进仓库）
├── hugo.toml                    # 站点配置
└── .github/workflows/deploy.yml # 自动部署
```

### 关于主题

主题**直接 vendored 进仓库**（不是 git submodule），原因是本机网络常封 `github.com`，
submodule 在本地和 CI 都可能拉取失败。当前版本对应 PaperMod master 的
`d3768854d00a`（2026-08-02）。

更新主题：

```bash
curl -L https://codeload.github.com/adityatelange/hugo-PaperMod/tar.gz/refs/heads/master -o /tmp/pm.tgz
tar -xzf /tmp/pm.tgz -C /tmp
rsync -a --delete --exclude '.git' /tmp/hugo-PaperMod-master/ themes/PaperMod/
```
