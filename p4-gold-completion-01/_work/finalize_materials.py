import json, hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'p4-gold-completion-01'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,o):p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
r=read(OUT/'_work/validation_results.json')
assert r['status']=='passed'
before=read(OUT/'_work/input_hashes_before.json')
changed=[p for p,h in before.items() if not (ROOT/p).exists() or sha(ROOT/p)!=h]
assert not changed
dump(OUT/'input_integrity.json',{'checked_at':'2026-11-05 Asia/Shanghai','protected_files':len(before),'changed':changed,'hashes':before,'note':'本地文件一致性；不声称本轮验证过运行时数据库。'})
(OUT/'validation.md').write_text(f'''# P4离线材料验证

日期：2026-11-05（Asia/Shanghai）。静态与材料检查 **{r['checks_passed']}/{r['checks_total']}通过**。原始结果见`_work/validation_results.json`。

- 236个既有输入文件逐字节SHA-256未变，含3份PDF、冻结语料、原候选、原审核包、既有Gold、P3文件和本轮进入时的检索修复文件。详情见[input_integrity.json](input_integrity.json)。
- 冻结语料SHA-256与Pilot绑定一致：447个唯一Chunk、3文档；每块文本哈希正确。两批Gold源与Pilot所记6个文件哈希一致。
- B01–B57映射与当前review.xlsx的完整candidate_id列逐条一致；72个候选身份无重复。
- B28–B42既有8 Accept/5 Revise/2 Reject得到保留；B43–B57为本轮7 Accept/8 Revise，均为AI建议。
- 15条新题具独立且可重算的candidate_id；32个关键证据短语在冻结Chunk和对应PDF物理页均可定位。初次阅读使用PyMuPDF，复核使用独立pypdf提取引擎；这不是第二位独立审核人。
- 主选28条覆盖27块，与Development的相关/证据Chunk并集交集为0；不含综合单价题。全量46条待签记录及15条新候选的human字段均为空。
- 工作簿导出后用只读openpyxl复核：46条唯一签核行、人工字段全空、初始接受记录数0、签核状态全为待签核、决定下拉有效、冻结窗格存在、ID对应正确、无公式错误或测试身份残留。
- 工作簿输入逻辑在临时值下校验：只填接受但缺审核人/日期仍提示未完成；补全输入得到接受记录完整；Revise接受原题提示需复核。临时值已全部恢复为空后才导出。
- 已渲染并目视检查签核表、备选区、长答案和Development页；另核对9张PDF原页图，覆盖价目表行列、铁路净距、技能列、产品形态、灯态及域名端口映射。
- Markdown交付链接全部可解析。新目录和工作簿为本轮交付，已有代码diff保持原状；没有commit/push。

本轮未执行检索、Embedding、Rerank、模型回答、数据库查询或正式Benchmark；没有自动批准、导出新Gold或冻结Holdout。原始既有Gold未修改。数据集质量仍须人工裁决，静态校验不替代签核。

工作簿用Artifact Tool计算与渲染，并校验XLSX导出后的内容/缓存；未在原生Excel界面中人工打开验收。
''',encoding='utf-8')
files=[p for p in OUT.iterdir() if p.is_file() and p.name!='packet_manifest.json']
files += [ROOT/'outputs/p4-gold-completion-01/human_signoff.xlsx']
dump(OUT/'packet_manifest.json',{'created_at':'2026-11-05 Asia/Shanghai','status':'pending_human_confirmation','purpose':'审核材料版本，不代表Holdout已冻结','formal_benchmark_run':False,'new_approved':0,'frozen_holdout':0,'files':{p.relative_to(ROOT).as_posix():sha(p) for p in sorted(files)}})
print(json.dumps({'material_files':len(files),'protected_files_unchanged':len(before),'new_approved':0,'status':'pending_human_confirmation'},ensure_ascii=False))
