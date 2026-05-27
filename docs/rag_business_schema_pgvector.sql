CREATE EXTENSION IF NOT EXISTS vector;

-- =========================
-- 一、业务数据层
-- =========================

CREATE TABLE IF NOT EXISTS work_orders (
    id BIGSERIAL PRIMARY KEY,
    work_order_no VARCHAR(64) NOT NULL UNIQUE,
    order_type VARCHAR(32) NOT NULL,
    status VARCHAR(32) NOT NULL,
    priority INTEGER NOT NULL DEFAULT 50,
    area_code VARCHAR(64),
    address_text VARCHAR(500),
    device_sn VARCHAR(128),
    fault_type VARCHAR(64),
    error_code VARCHAR(64),
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS work_order_flow_logs (
    id BIGSERIAL PRIMARY KEY,
    work_order_no VARCHAR(64) NOT NULL,
    from_status VARCHAR(32),
    to_status VARCHAR(32) NOT NULL,
    action_name VARCHAR(64) NOT NULL,
    operator_role VARCHAR(64),
    action_note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS dispatch_records (
    id BIGSERIAL PRIMARY KEY,
    dispatch_no VARCHAR(64) NOT NULL UNIQUE,
    work_order_no VARCHAR(64) NOT NULL,
    technician_id VARCHAR(64),
    dispatch_strategy VARCHAR(64),
    dispatch_reason TEXT,
    dispatch_status VARCHAR(32) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS technicians (
    id BIGSERIAL PRIMARY KEY,
    technician_id VARCHAR(64) NOT NULL UNIQUE,
    technician_name VARCHAR(64) NOT NULL,
    area_code VARCHAR(64),
    skill_tags TEXT[],
    workload INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(32) NOT NULL DEFAULT 'online'
);

CREATE TABLE IF NOT EXISTS service_addresses (
    id BIGSERIAL PRIMARY KEY,
    address_id VARCHAR(64) NOT NULL UNIQUE,
    raw_address VARCHAR(500),
    standard_address VARCHAR(500) NOT NULL,
    area_code VARCHAR(64),
    resource_status VARCHAR(32) NOT NULL,
    validation_result VARCHAR(32) NOT NULL,
    validation_message TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS customer_devices (
    id BIGSERIAL PRIMARY KEY,
    device_sn VARCHAR(128) NOT NULL UNIQUE,
    device_type VARCHAR(64) NOT NULL,
    model VARCHAR(128),
    address_id VARCHAR(64),
    online_status VARCHAR(32) NOT NULL,
    pon_port VARCHAR(64),
    signal_power NUMERIC(8, 2),
    last_seen_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS error_codes (
    id BIGSERIAL PRIMARY KEY,
    error_code VARCHAR(64) NOT NULL UNIQUE,
    system_name VARCHAR(64) NOT NULL,
    error_message VARCHAR(500) NOT NULL,
    reason TEXT,
    handling_advice TEXT,
    severity VARCHAR(32) NOT NULL DEFAULT 'medium',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS fault_cases (
    id BIGSERIAL PRIMARY KEY,
    case_id VARCHAR(64) NOT NULL UNIQUE,
    fault_type VARCHAR(64) NOT NULL,
    symptoms TEXT NOT NULL,
    root_cause TEXT,
    handling_steps TEXT[],
    related_error_code VARCHAR(64),
    related_order_type VARCHAR(64),
    resolved BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =========================
-- 二、RAG 核心层
-- =========================

CREATE TABLE IF NOT EXISTS rag_documents (
    id BIGSERIAL PRIMARY KEY,
    collection_name VARCHAR(128) NOT NULL DEFAULT 'default',
    document_id VARCHAR(64) NOT NULL,
    source_type VARCHAR(32) NOT NULL,
    source_name VARCHAR(255),
    business_module VARCHAR(64),
    title VARCHAR(255),
    raw_path VARCHAR(500),
    content_hash VARCHAR(64) NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_rag_documents_status CHECK (
        status IN ('active', 'inactive', 'deleted')
    ),
    CONSTRAINT uq_rag_documents_collection_document
        UNIQUE (collection_name, document_id)
);

CREATE TABLE IF NOT EXISTS rag_knowledge_chunks (
    id BIGSERIAL PRIMARY KEY,
    collection_name VARCHAR(128) NOT NULL DEFAULT 'default',
    chunk_id VARCHAR(64) NOT NULL,
    document_id VARCHAR(64) NOT NULL,
    chunk_index INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    summary TEXT,
    keywords TEXT[],
    tags TEXT[],
    intent_labels TEXT[],
    business_module VARCHAR(64),
    error_code VARCHAR(64),
    fault_type VARCHAR(64),
    order_type VARCHAR(64),
    area_code VARCHAR(64),
    priority INTEGER NOT NULL DEFAULT 50,
    embedding VECTOR(1536) NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
    content_hash VARCHAR(64) NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_rag_chunks_document
        FOREIGN KEY (collection_name, document_id)
        REFERENCES rag_documents(collection_name, document_id),
    CONSTRAINT ck_rag_chunks_status CHECK (
        status IN ('active', 'inactive', 'deleted')
    ),
    CONSTRAINT uq_rag_chunks_collection_chunk
        UNIQUE (collection_name, chunk_id)
);

CREATE TABLE IF NOT EXISTS rag_query_logs (
    id BIGSERIAL PRIMARY KEY,
    query_id VARCHAR(64) NOT NULL UNIQUE,
    user_question TEXT NOT NULL,
    normalized_question TEXT,
    intent_label VARCHAR(64),
    query_rewrite TEXT,
    query_expansions TEXT[],
    top_k INTEGER NOT NULL DEFAULT 4,
    answer_text TEXT,
    hit_count INTEGER NOT NULL DEFAULT 0,
    fallback_type VARCHAR(64),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS rag_retrieval_logs (
    id BIGSERIAL PRIMARY KEY,
    query_id VARCHAR(64) NOT NULL,
    chunk_id VARCHAR(64) NOT NULL,
    rank_no INTEGER NOT NULL,
    similarity_score NUMERIC(10, 6),
    rerank_score NUMERIC(10, 6),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_rag_retrieval_query
        FOREIGN KEY (query_id) REFERENCES rag_query_logs(query_id),
    CONSTRAINT fk_rag_retrieval_chunk
        FOREIGN KEY (chunk_id) REFERENCES rag_knowledge_chunks(chunk_id)
);

CREATE TABLE IF NOT EXISTS rag_tool_call_logs (
    id BIGSERIAL PRIMARY KEY,
    query_id VARCHAR(64),
    tool_name VARCHAR(128) NOT NULL,
    input_json JSONB NOT NULL DEFAULT '{}'::JSONB,
    output_json JSONB NOT NULL DEFAULT '{}'::JSONB,
    status VARCHAR(32) NOT NULL,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS rag_feedback (
    id BIGSERIAL PRIMARY KEY,
    query_id VARCHAR(64) NOT NULL,
    rating INTEGER,
    is_solved BOOLEAN,
    feedback_text TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_rag_feedback_query
        FOREIGN KEY (query_id) REFERENCES rag_query_logs(query_id),
    CONSTRAINT ck_rag_feedback_rating CHECK (
        rating IS NULL OR rating BETWEEN 1 AND 5
    )
);

-- =========================
-- 三、常用索引
-- =========================

CREATE INDEX IF NOT EXISTS idx_work_orders_status
    ON work_orders (status);

CREATE INDEX IF NOT EXISTS idx_work_orders_order_type
    ON work_orders (order_type);

CREATE INDEX IF NOT EXISTS idx_work_orders_error_code
    ON work_orders (error_code)
    WHERE error_code IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_work_order_flow_logs_work_order
    ON work_order_flow_logs (work_order_no, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_dispatch_records_work_order
    ON dispatch_records (work_order_no);

CREATE INDEX IF NOT EXISTS idx_service_addresses_area_status
    ON service_addresses (area_code, resource_status);

CREATE INDEX IF NOT EXISTS idx_customer_devices_status
    ON customer_devices (online_status);

CREATE INDEX IF NOT EXISTS idx_fault_cases_fault_type
    ON fault_cases (fault_type);

CREATE INDEX IF NOT EXISTS idx_rag_documents_collection_status
    ON rag_documents (collection_name, status);

CREATE INDEX IF NOT EXISTS idx_rag_documents_source_type
    ON rag_documents (collection_name, source_type);

CREATE INDEX IF NOT EXISTS idx_rag_chunks_embedding
    ON rag_knowledge_chunks
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_rag_chunks_business_module
    ON rag_knowledge_chunks (collection_name, business_module);

CREATE INDEX IF NOT EXISTS idx_rag_chunks_error_code
    ON rag_knowledge_chunks (collection_name, error_code)
    WHERE error_code IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_rag_chunks_fault_type
    ON rag_knowledge_chunks (collection_name, fault_type)
    WHERE fault_type IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_rag_chunks_status_priority
    ON rag_knowledge_chunks (collection_name, status, priority DESC);

CREATE INDEX IF NOT EXISTS idx_rag_chunks_metadata
    ON rag_knowledge_chunks
    USING GIN (metadata);

CREATE INDEX IF NOT EXISTS idx_rag_chunks_keywords
    ON rag_knowledge_chunks
    USING GIN (keywords);

CREATE INDEX IF NOT EXISTS idx_rag_query_logs_intent
    ON rag_query_logs (intent_label, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_rag_retrieval_logs_query
    ON rag_retrieval_logs (query_id, rank_no);

CREATE INDEX IF NOT EXISTS idx_rag_tool_call_logs_query
    ON rag_tool_call_logs (query_id, created_at DESC);

-- =========================
-- 四、中文注释
-- =========================

COMMENT ON TABLE work_orders IS '业务表：装维工单主表，用于记录工单创建、状态查询和工单闭环。';
COMMENT ON TABLE work_order_flow_logs IS '业务表：工单流转记录，用于记录工单状态变化。';
COMMENT ON TABLE dispatch_records IS '业务表：派单记录，用于记录智能派单结果。';
COMMENT ON TABLE technicians IS '业务表：装维人员信息，用于记录派单人员和技能标签。';
COMMENT ON TABLE service_addresses IS '业务表：地址资源信息，用于记录地址校验。';
COMMENT ON TABLE customer_devices IS '业务表：设备信息，用于记录设备状态查询和维护。';
COMMENT ON TABLE error_codes IS '业务表：异常码说明，用于记录接口异常解释。';
COMMENT ON TABLE fault_cases IS '业务表：历史故障案例，用于记录常见故障处理记录。';

COMMENT ON TABLE rag_documents IS 'RAG 核心表：原始资料表，记录进入知识库的业务手册、历史工单、故障案例、接口说明和异常码资料。';
COMMENT ON TABLE rag_knowledge_chunks IS 'RAG 核心表：知识切片表，存储可被语义检索召回的最小知识单元。';
COMMENT ON TABLE rag_query_logs IS 'RAG 核心表：用户问题日志，记录意图识别、Query 改写、回答结果和兜底类型。';
COMMENT ON TABLE rag_retrieval_logs IS 'RAG 核心表：召回明细日志，记录每次查询命中的知识切片和相似度分数。';
COMMENT ON TABLE rag_tool_call_logs IS 'RAG 核心表：智能体工具调用日志，记录对业务表的查询过程。';
COMMENT ON TABLE rag_feedback IS 'RAG 核心表：回答反馈表，用于评估回答准确性和建议可执行性。';
