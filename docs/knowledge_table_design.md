# 装维 RAG 项目数据表设计

本项目按生产链路设计。RAG 知识库负责文档解析、切片、向量索引、检索生成和反馈闭环；工单状态等实时业务信息通过 PostgreSQL 业务表查询。

## 一、业务数据层

在线工具当前接入 `query_order_status`，直接读取 PostgreSQL 中的三张业务表：

- `work_orders`：工单主表，保存工单号、工单类型、状态、优先级、地址、设备、故障类型、异常码和问题描述。
- `work_order_flow_logs`：工单流转记录表，保存状态变更、操作名称、操作角色、操作说明和操作时间。
- `dispatch_records`：派单记录表，保存派单编号、装维人员、派单策略、派单原因和派单状态。

后续如果继续接入设备信息、地址校验、异常码解释等工具，也应按同样方式读取真实业务库或企业内部服务。

## 二、核心表

### `work_orders`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | `BIGSERIAL` | 主键 |
| `work_order_no` | `VARCHAR(64)` | 工单号，唯一 |
| `order_type` | `VARCHAR(32)` | 工单类型，例如装机、移机、修障、退单 |
| `status` | `VARCHAR(32)` | 当前状态，例如待派单、已派单、处理中、已完成、已转人工 |
| `priority` | `INTEGER` | 优先级 |
| `area_code` | `VARCHAR(64)` | 地市、区县或网格编码 |
| `address_text` | `VARCHAR(500)` | 用户报装或报障地址 |
| `device_sn` | `VARCHAR(128)` | 关联设备编号 |
| `fault_type` | `VARCHAR(64)` | 故障类型 |
| `error_code` | `VARCHAR(64)` | 关联异常码 |
| `description` | `TEXT` | 用户问题描述 |
| `created_at` | `TIMESTAMPTZ` | 创建时间 |
| `updated_at` | `TIMESTAMPTZ` | 更新时间 |

### `work_order_flow_logs`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | `BIGSERIAL` | 主键 |
| `work_order_no` | `VARCHAR(64)` | 工单号 |
| `from_status` | `VARCHAR(32)` | 变更前状态 |
| `to_status` | `VARCHAR(32)` | 变更后状态 |
| `action_name` | `VARCHAR(64)` | 操作名称 |
| `operator_role` | `VARCHAR(64)` | 操作角色 |
| `action_note` | `TEXT` | 操作说明 |
| `created_at` | `TIMESTAMPTZ` | 操作时间 |

### `dispatch_records`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | `BIGSERIAL` | 主键 |
| `dispatch_no` | `VARCHAR(64)` | 派单编号，唯一 |
| `work_order_no` | `VARCHAR(64)` | 工单号 |
| `technician_id` | `VARCHAR(64)` | 装维人员编号 |
| `dispatch_strategy` | `VARCHAR(64)` | 派单策略 |
| `dispatch_reason` | `TEXT` | 派单原因 |
| `dispatch_status` | `VARCHAR(32)` | 派单状态 |
| `created_at` | `TIMESTAMPTZ` | 派单时间 |

## 三、RAG 核心层

RAG 核心层保存知识文档、切片、召回日志、工具调用日志和人工反馈。

- `rag_documents`：原始资料表，记录进入知识库的业务手册、接口说明、故障案例和异常码资料。
- `rag_knowledge_chunks`：知识切片表，保存可检索知识单元、Embedding、业务标签和版本信息。
- `rag_query_logs`：用户问题日志，记录意图识别、Query 改写、回答结果和兜底类型。
- `rag_retrieval_logs`：召回明细日志，记录每次查询命中的知识切片和分数。
- `rag_tool_call_logs`：工具调用日志，记录 `query_order_status` 等在线工具的入参、出参、状态和错误。
- `rag_feedback`：人工反馈表，用于评估回答准确性和建议可执行性。

## 四、在线工具查询边界

`query_order_status` 只读取 PostgreSQL 业务表：

1. 根据用户问题提取工单号。
2. 查询 `work_orders` 获取主状态。
3. 查询 `work_order_flow_logs` 获取最近流转。
4. 查询 `dispatch_records` 获取最近派单。
5. 将工具结果写入增强上下文、trace、查询日志和 `rag_tool_call_logs`。

这条链路的重点是“知识库回答 + 业务库实时状态”分离：知识库回答处理规则和经验，PostgreSQL 工具查询处理实时业务事实。
