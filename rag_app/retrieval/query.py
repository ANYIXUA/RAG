"""用户查询理解模块。"""

from __future__ import annotations

import re
from dataclasses import dataclass

from rag_app.core.models import IntentRecognitionResult, QueryRewriteResult


ERROR_CODE_RE = re.compile(r"\b[A-Za-z]\d{2,6}\b")
WORK_ORDER_RE = re.compile(r"\b(?:WO|GD|ORDER)[-_]?\d{4,}\b", re.IGNORECASE)


NORMALIZATION_RULES = (
    ("咋办", "怎么处理", "口语处理问法标准化"),
    ("咋处理", "怎么处理", "口语处理问法标准化"),
    ("怎么弄", "怎么处理", "口语处理问法标准化"),
    ("搞不定", "无法处理", "口语异常表达标准化"),
    ("装不了机", "装机失败", "装机问题标准化"),
    ("办不了装机", "装机失败", "装机问题标准化"),
    ("地址不对", "地址校验失败", "地址问题标准化"),
    ("地址错", "地址校验失败", "地址问题标准化"),
    ("派不了单", "派单失败", "派单问题标准化"),
    ("红灯", "LOS 红灯", "故障现象标准化"),
    ("los灯", "LOS 灯", "设备指示灯标准化"),
    ("pon灯", "PON 灯", "设备指示灯标准化"),
    ("网慢", "网络速率慢", "故障现象标准化"),
)


SYNONYM_EXPANSIONS = {
    "光猫": ("ONU", "ONT", "家庭网关", "用户侧终端"),
    "LOS": ("LOS 红灯", "光路异常", "无光信号"),
    "PON": ("PON 不亮", "PON 口", "光接入端口"),
    "光功率": ("收光功率", "光衰", "光信号强度"),
    "地址": ("标准地址", "地址资源", "地址校验"),
    "工单": ("装维工单", "工单流转", "工单状态"),
    "派单": ("智能派单", "装维人员分配", "派单策略"),
    "异常码": ("错误码", "返回码", "接口异常"),
    "错误码": ("异常码", "返回码", "接口异常"),
    "设备": ("终端设备", "设备信息", "设备状态"),
}


INTENT_SEMANTIC_EXPANSIONS = {
    "query_order_status": ("工单状态", "流转记录", "派单记录", "处理进度", "闭环状态"),
    "explain_error": ("异常原因", "接口返回说明", "错误码说明", "处理建议", "失败原因"),
    "recommend_solution": ("故障原因", "排查步骤", "处理步骤", "解决办法", "现场处理建议"),
    "query_rule": ("业务规则", "办理条件", "操作规范", "校验标准", "派单规则"),
    "similar_case": ("历史案例", "相似工单", "故障案例", "处理经验", "根因分析"),
    "need_human": ("转人工", "人工兜底", "专家处理", "无法闭环", "补充信息"),
    "general_knowledge": ("业务说明", "知识库", "常见问题"),
}


@dataclass(frozen=True)
class IntentRule:
    """一个可解释的意图识别规则。"""

    label: str
    keywords: tuple[str, ...]
    reason: str


INTENT_RULES = (
    IntentRule(
        label="query_order_status",
        keywords=("工单状态", "进度", "到哪", "处理到哪", "派到谁", "谁处理", "是否完成", "闭环", "查工单"),
        reason="问题包含工单进度、处理人或闭环状态相关表达。",
    ),
    IntentRule(
        label="explain_error",
        keywords=("异常码", "错误码", "报错", "返回码", "接口返回", "失败原因", "为什么失败", "什么意思"),
        reason="问题包含异常码、接口返回或失败原因解释相关表达。",
    ),
    IntentRule(
        label="recommend_solution",
        keywords=(
            "怎么处理",
            "如何处理",
            "怎么办",
            "咋办",
            "咋处理",
            "处理步骤",
            "解决办法",
            "建议",
            "排查",
            "修复",
            "红灯",
            "不亮",
            "光衰",
            "装不了机",
            "装机失败",
            "地址不对",
        ),
        reason="问题在询问现场处理办法、排查步骤或修复建议。",
    ),
    IntentRule(
        label="query_rule",
        keywords=("规则", "能不能", "是否可以", "可不可以", "要求", "规范", "条件", "标准", "派单规则", "地址校验"),
        reason="问题在询问业务规则、办理条件或操作规范。",
    ),
    IntentRule(
        label="similar_case",
        keywords=("类似", "历史", "案例", "以前", "同类", "相似", "参考", "经验"),
        reason="问题在寻找历史案例或相似故障经验。",
    ),
    IntentRule(
        label="need_human",
        keywords=("转人工", "人工处理", "专家", "无法判断", "看不懂", "不明确"),
        reason="问题表达了需要人工兜底或专家介入。",
    ),
)


def recognize_intent(query: str) -> IntentRecognitionResult:
    """识别一线人员自然语言查询的业务意图。"""

    normalized_query = " ".join(query.strip().split())#数据清洗
    if not normalized_query:
        return IntentRecognitionResult(
            intent_label="unknown",
            confidence=0.0,
            matched_keywords=[],
            reason="用户查询为空，无法识别意图。",
        )

    error_code_match = ERROR_CODE_RE.search(normalized_query)
    if error_code_match: #用正则匹配异常码。
        return IntentRecognitionResult(
            intent_label="explain_error",
            confidence=0.92,
            matched_keywords=[error_code_match.group(0)],
            reason="问题中包含疑似异常码，优先识别为异常解释意图。",
        )

    work_order_match = WORK_ORDER_RE.search(normalized_query)
    if work_order_match: #用正则匹配工单号。
        return IntentRecognitionResult(
            intent_label="query_order_status",
            confidence=0.9,
            matched_keywords=[work_order_match.group(0)],
            reason="问题中包含疑似工单号，优先识别为工单状态查询意图。",
        )

    #然后走关键词规则匹配
    scored_results: list[tuple[int, IntentRule, list[str]]] = []
    for rule in INTENT_RULES:
        matched = [keyword for keyword in rule.keywords if keyword in normalized_query]
        if matched:
            scored_results.append((len(matched), rule, matched))

    #如果没有命中任意规则，按通用知识处理
    if not scored_results:
        return IntentRecognitionResult(
            intent_label="general_knowledge",
            confidence=0.35,
            matched_keywords=[],
            reason="未命中明确业务意图，按通用知识问答处理。",
        )

    scored_results.sort(key=lambda item: item[0], reverse=True)#按照命中关键词数量排序
    matched_count, rule, matched_keywords = scored_results[0]#取排序后的第一项
    confidence = min(0.95, 0.55 + matched_count * 0.15)#根据命中计算置信度
    #返回最终意图识别的结果
    return IntentRecognitionResult(
        intent_label=rule.label,
        confidence=round(confidence, 2),
        matched_keywords=matched_keywords,
        reason=rule.reason,
    )


def rewrite_query(
    query: str,
    intent: IntentRecognitionResult | None = None,
) -> QueryRewriteResult:
    """将用户口语化查询改写为更适合检索的标准查询。"""

    normalized_query = normalize_query(query)
    #获取意图
    actual_intent = intent or recognize_intent(normalized_query)

    rewritten_query = normalized_query
    applied_rules: list[str] = []#记录用了哪些规则

    #规则替换
    for source, target, rule_name in NORMALIZATION_RULES:
        if source in rewritten_query:
            rewritten_query = rewritten_query.replace(source, target)
            applied_rules.append(rule_name)

    #标准化异常码
    rewritten_query = _normalize_error_codes(rewritten_query)
    rewritten_query = _normalize_work_orders(rewritten_query)
    rewritten_query = _normalize_domain_spacing(rewritten_query)
    rewritten_query = normalize_query(rewritten_query)

    #收集同义词扩展
    synonym_expansions = _collect_synonym_expansions(rewritten_query)
    #根据意图补充语义扩展此
    semantic_expansions = list(
        INTENT_SEMANTIC_EXPANSIONS.get(actual_intent.intent_label, ())
    )
    #构建最终检索的query
    retrieval_query = build_retrieval_query(
        rewritten_query=rewritten_query,
        synonym_expansions=synonym_expansions,
        semantic_expansions=semantic_expansions,
    )
    #返回重写后的结果
    return QueryRewriteResult(
        original_query=query,
        normalized_query=normalized_query,
        rewritten_query=rewritten_query,
        retrieval_query=retrieval_query,
        synonym_expansions=synonym_expansions,
        semantic_expansions=semantic_expansions,
        applied_rules=_dedupe(applied_rules),
    )


def normalize_query(query: str) -> str:
    """清理多余空白，保留用户原始语义。"""

    return " ".join(query.strip().split())


def build_retrieval_query(
    rewritten_query: str,
    synonym_expansions: list[str],
    semantic_expansions: list[str],
) -> str:
    """拼接最终用于向量化和检索的查询文本。"""

    terms = [rewritten_query, *synonym_expansions, *semantic_expansions]
    return " ".join(_dedupe([term for term in terms if term]))


def _collect_synonym_expansions(query: str) -> list[str]:
    expansions: list[str] = []
    upper_query = query.upper()
    for keyword, synonyms in SYNONYM_EXPANSIONS.items():
        if keyword.upper() in upper_query:
            expansions.extend(synonyms)
    return _dedupe(expansions)


def _normalize_error_codes(query: str) -> str:
    return ERROR_CODE_RE.sub(lambda match: match.group(0).upper(), query)


def _normalize_work_orders(query: str) -> str:
    return WORK_ORDER_RE.sub(lambda match: match.group(0).upper(), query)


def _normalize_domain_spacing(query: str) -> str:
    query = re.sub(r"(?<![A-Za-z])LOS\s*红灯", "LOS 红灯", query, flags=re.IGNORECASE)
    query = re.sub(r"(?<![A-Za-z])PON\s*灯", "PON 灯", query, flags=re.IGNORECASE)
    query = query.replace("光猫LOS", "光猫 LOS")
    query = query.replace("光猫PON", "光猫 PON")
    return query


def _dedupe(items: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result
