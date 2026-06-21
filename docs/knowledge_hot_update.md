# 知识热更新

热上传文档会先进入上传目录并登记到 PostgreSQL。构建任务使用独立知识集合名称写入 `rag_knowledge_chunks`，成功后更新 `knowledge_active_versions` 指针。

在线服务读取生效指针；检测到生效知识集合变化后重新初始化在线流程，因此可以做到不覆盖当前线上知识库、失败不影响现网、成功后快速切换和回滚。

主要接口：

- `POST /knowledge/uploads/text`
- `POST /knowledge/build-jobs`
- `GET /knowledge/build-jobs`
- `GET /knowledge/versions`
- `POST /knowledge/versions/{version}/activate`
- `POST /knowledge/rollback`

版本状态、构建任务、上传记录和生效指针全部保存在 PostgreSQL。
