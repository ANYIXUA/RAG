# 发布检查清单

本文档用于固定发布前、发布中和发布后的检查动作。

## 发布对象

RAG 项目发布时至少要区分三类版本：

- 代码版本：应用代码、接口、命令行、检索策略和脚本。
- 模型版本：向量化模型、交叉编码器模型、大语言模型配置。
- 知识库版本：知识文档、审核清单、向量库记录和处理清单。

当前应用版本可以查看：

```powershell
python -m rag_app.cli version
```

也可以通过环境变量写入构建信息：

```powershell
$env:RAG_APP_VERSION="0.1.0"
$env:RAG_BUILD_COMMIT="<git-commit-sha>"
$env:RAG_BUILD_TIME="2026-05-08T00:00:00Z"
$env:RAG_IMAGE_TAG="rag-api:0.1.0"
$env:RAG_KNOWLEDGE_VERSION="knowledge-v1"
```

接口 `/health` 会返回 `build` 字段，方便发布后核对当前服务版本。

## 发布前检查

推荐执行：

```powershell
.\scripts\release_check.ps1 -Dataset <生产评测集.jsonl> -SkipDockerBuild
```

如果 Docker Desktop 已启动并且需要验证镜像构建：

```powershell
.\scripts\release_check.ps1 -Dataset <生产评测集.jsonl>
```

脚本会执行：

1. 查看版本信息。
2. Python 编译检查。
3. 单元测试。
4. 离线知识刷新。
5. 解析质量门禁，拦截 `needs_review`、`parse_failed` 或需要 OCR 复核的文档。
6. 检索评测和发布门禁。
7. 可选 Docker 镜像构建。

## 发布后检查

启动服务后检查：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8000/ready
```

执行一次核心问答：

```powershell
$body = [System.Text.Encoding]::UTF8.GetBytes('{"question":"光猫红灯咋办","top_k":2}')
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/query `
  -ContentType "application/json; charset=utf-8" `
  -Body $body
```

执行一次权限过滤问答：

```powershell
$body = [System.Text.Encoding]::UTF8.GetBytes('{"question":"接口超时怎么处理","top_k":2,"tenant_id":"tenant-a","permission_tags":["OPS_L2"]}')
Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8000/query `
  -ContentType "application/json; charset=utf-8" `
  -Body $body
```

查看运行摘要：

```powershell
python -m rag_app.cli ops-summary --limit 200
```

## 回滚策略

如果发布后发现问题，按问题来源回滚：

- 代码问题：回退应用镜像或代码版本。
- 知识问题：通过 `knowledge_active_versions` 切回上一版生效知识集合，必要时重新执行离线刷新。
- 模型问题：恢复 `OPENAI_EMBEDDING_MODEL`、`RAG_EMBEDDING_DIMENSION`、`RAG_RERANK_MODEL` 或大语言模型配置。
- 配置问题：恢复 `.env` 或部署环境变量。
- 数据库问题：优先保留查询日志和反馈表，避免丢失排查线索。

## 发布记录模板

```text
发布时间：
发布人：
代码版本：
镜像标签：
向量化模型：
重排模型：
知识库版本：
评测报告：
命中率 Hit@K：
MRR：
无结果率：
P95 延迟：
解析质量门禁：
权限过滤验证：
发布前检查结果：
发布后健康检查：
回滚方案：
备注：
```
