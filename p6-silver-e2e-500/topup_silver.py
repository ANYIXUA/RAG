"""Independent, local-only, append-audited Silver topup. See TOPUP_PLAN.md.

Only completed, validated, nonduplicate candidates consume quotas. Immutable
event files are authoritative; JSONL and reports are recoverable projections.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import os
import random
import tempfile
from collections import Counter
from contextlib import contextmanager
from difflib import SequenceMatcher
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('p6_original_generator', HERE / 'generate_silver.py')
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)
VERSION = 'p6-silver-topup-v1'
SEED = 20261106
BASELINE_COUNTS = {'exact_fact': 180, 'procedure': 96, 'multi_condition': 99,
                   'colloquial': 50, 'unanswerable': 41}
RISK = ('Unanswerability has only passed the original automated token overlap '
        'screen; corpus-wide semantic answerability and human review remain pending.')


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def encode_rows(rows) -> bytes:
    return b''.join((json.dumps(r, ensure_ascii=False, sort_keys=True) + '\n').encode('utf-8') for r in rows)


def json_bytes(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')


def read_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def immutable_write(path: Path, payload: bytes) -> None:
    """Atomically publish a complete file; never replace different existing bytes."""
    if path.exists():
        if path.read_bytes() != payload:
            raise ValueError(f'output conflict: {path}')
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.pending-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(payload)
            f.flush()
            os.fsync(f.fileno())
        try:
            if os.name == 'nt':
                # Windows rename is atomic and refuses an existing destination.
                os.rename(temporary, path)
            else:
                os.link(temporary, path)
        except FileExistsError:
            if path.read_bytes() != payload:
                raise ValueError(f'output conflict: {path}') from None
    finally:
        Path(temporary).unlink(missing_ok=True)


def projection(path: Path, payload: bytes) -> None:
    """Update a derived view with immutable content-addressed history."""
    if path.exists() and path.read_bytes() == payload:
        return
    history = path.parent / 'topup_history' / path.name
    if path.exists():
        old = path.read_bytes()
        immutable_write(history / (sha(old) + '.snapshot'), old)
    immutable_write(history / (sha(payload) + '.snapshot'), payload)
    fd, temporary = tempfile.mkstemp(prefix='.pending-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(payload)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


@contextmanager
def writer_lock(directory: Path):
    import msvcrt
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / 'silver_topup.lock').open('a+b') as f:
        if f.tell() == 0:
            f.write(b'0')
            f.flush()
        f.seek(0)
        try:
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            raise ValueError('another topup writer is running') from None
        try:
            yield
        finally:
            f.seek(0)
            msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)


class Store:
    def __init__(self, directory: Path):
        self.directory = directory
        self.events_dir = directory / 'topup_events'

    def events(self) -> list[dict]:
        events, previous = [], None
        for i, path in enumerate(sorted(self.events_dir.glob('*.json')), 1):
            data = path.read_bytes()
            envelope = json.loads(data)
            if path.name != f'{i:06d}.json' or envelope['previous_sha256'] != previous:
                raise ValueError('journal sequence/hash chain mismatch')
            events.append(envelope['record'])
            previous = sha(data)
        return events

    def append(self, record: dict):
        self.events()  # Fail closed before writing to an invalid journal.
        paths = sorted(self.events_dir.glob('*.json'))
        previous = sha(paths[-1].read_bytes()) if paths else None
        immutable_write(self.events_dir / f'{len(paths)+1:06d}.json',
                        json_bytes({'previous_sha256': previous, 'record': record}))

    def project(self):
        payload = encode_rows(self.events())
        path = self.directory / 'silver_topup_raw.jsonl'
        if path.exists() and not payload.startswith(path.read_bytes()):
            raise ValueError('raw projection conflict with authoritative journal')
        projection(path, payload)


def load_inputs():
    manifest = json.loads((HERE / 'silver_baseline_sha256.json').read_text(encoding='utf-8'))
    if manifest['errors'] or manifest['validation_errors'] or not manifest['baseline_rebuild_matches']:
        raise ValueError('baseline manifest is not valid')
    for name, digest in manifest['sha256'].items():
        path = Path(name)
        if not path.is_absolute():
            path = g.ROOT / path
        if sha(path.read_bytes()) != digest:
            raise ValueError(f'baseline hash mismatch: {path}')
    baseline = read_rows(HERE / 'silver_cases.jsonl')
    if len(baseline) != 466 or Counter(r['question_type'] for r in baseline) != BASELINE_COUNTS:
        raise ValueError('baseline counts mismatch')
    if [r['case_id'] for r in baseline] != [f'p6s-{i:04d}' for i in range(1, 467)]:
        raise ValueError('baseline IDs mismatch')
    corpus, gold = g._load_corpus(), g._load_prior_gold_queries()
    if len(gold) != 50 or len({r['chunk_id'] for r in corpus}) != 447:
        raise ValueError('frozen input counts mismatch')
    summary = json.loads((HERE / 'generation_summary.json').read_text(encoding='utf-8'))
    if summary['model'] != f'ollama/{g.MODEL_NAME}' or summary['seed'] != SEED:
        raise ValueError('generation configuration mismatch')
    return baseline, corpus, gold, summary['model_digest']


class Engine:
    def __init__(self, baseline, corpus, gold, targets, digest):
        self.rows = copy.deepcopy(baseline)
        self.baseline_size = len(baseline)
        self.corpus = {r['chunk_id']: r for r in corpus}
        self.texts = {cid: r['chunk_text'] for cid, r in self.corpus.items()}
        self.gold = [g._norm(q) for q in gold]
        self.targets = dict(targets)
        self.digest = digest
        self.semantic_rejected_norms = []
        self.counts = Counter(r['question_type'] for r in self.rows)
        self.norms = [g._norm(r['question']) for r in self.rows]
        self.pairs = [(tuple(sorted(r['source_chunk_ids'])), g._norm(r['reference_answer']), g._norm(r['question']))
                      for r in self.rows if r['question_type'] != 'unanswerable']

    def remaining(self):
        return {k: max(0, v - self.counts[k]) for k, v in self.targets.items()}

    def consider(self, raw, kind, batch, seed, packet_ids):
        def reject(reason):
            return {'status': 'rejected', 'reason': reason}

        if kind not in self.targets:
            return reject('unknown_type')
        if not isinstance(raw, dict):
            return reject('invalid_schema')
        if raw.get('question_type', kind) != kind:
            return reject('question_type_mismatch')
        if any(cid not in self.corpus for cid in packet_ids):
            return reject('unknown_packet_chunk')
        try:
            if kind == 'unanswerable':
                item, reason = g._validate_unanswerable(raw, list(self.texts.values()))
            else:
                # Same whitespace treatment as the original generator's passage packets.
                packet_texts = {cid: g._one_line(self.texts[cid]) for cid in packet_ids}
                item, reason = g._validate_candidate(raw, packet_texts, kind)
                if item is not None and not item['excerpt']:
                    return reject('missing_evidence')
        except (TypeError, ValueError, AttributeError):
            return reject('invalid_schema')
        if item is None:
            return reject(reason)
        if self.counts[kind] >= self.targets[kind]:
            return reject('quota_full')
        nq = g._norm(item['question'])
        if any(SequenceMatcher(None, nq, q, autojunk=False).ratio() >= .80 for q in self.semantic_rejected_norms):
            return reject('previous_semantic_rejection')
        if any(SequenceMatcher(None, nq, q, autojunk=False).ratio() >= .80 for q in self.gold):
            return reject('duplicate_gold')
        if any(SequenceMatcher(None, nq, q, autojunk=False).ratio() >= .80 for q in self.norms):
            return reject('duplicate_silver')
        if kind != 'unanswerable':
            key, na = tuple(sorted(item['chunk_ids'])), g._norm(item['answer'])
            if any(key == ck and na[:80] == answer[:80] and
                   SequenceMatcher(None, nq, q, autojunk=False).ratio() >= .60
                   for ck, answer, q in self.pairs):
                return reject('duplicate_evidence_answer')
        used_ids = {r['case_id'] for r in self.rows}
        next_id = next(f'p6s-{i:04d}' for i in range(1, len(self.rows)+2) if f'p6s-{i:04d}' not in used_ids)
        row = {
            'case_id': next_id, 'question': item['question'],
            'question_type': kind, 'label_type': 'silver',
            'generation_model': f'ollama/{g.MODEL_NAME}', 'generation_version': self.digest,
            'generation_model_digest': self.digest, 'generation_seed': seed,
            'generation_batch': batch, 'prompt_version': g.PROMPT_VERSION,
            'topup_version': VERSION,
            'generation_corpus_sha256': sha(g.CORPUS_JSONL.read_bytes()),
        }
        if kind == 'unanswerable':
            row.update(reference_answer=None, source_evidence=[], source_chunk_ids=[],
                       source_document=None, source_page=None, expected_behavior='refuse_or_qualify',
                       out_of_scope_category=item['category'], assumed_out_of_scope_reason=item['reason'],
                       answerability_verification='not_semantically_verified', quality_risks=[RISK])
        else:
            ids = item['chunk_ids']
            row.update(reference_answer=item['answer'], source_evidence=item['excerpt'], source_chunk_ids=ids,
                       source_document=sorted({self.corpus[cid]['source'] for cid in ids}),
                       source_page=max((self.corpus[cid].get('page_number') for cid in ids
                                        if self.corpus[cid].get('page_number') is not None), default=None),
                       expected_behavior='answer')
            self.pairs.append((key, na, nq))
        self.rows.append(row)
        self.rows.sort(key=lambda r: r['case_id'])
        self.norms.append(nq)
        self.counts[kind] += 1
        return {'status': 'accepted', 'reason': None, 'case': copy.deepcopy(row)}

    def reject_last(self, case):
        if len(self.rows) <= self.baseline_size:
            raise ValueError('cannot reject immutable baseline')
        if self.rows[-1] != case:
            raise ValueError('semantic rejection must identify the last new case exactly')
        self.reject_case(case)

    def reject_case(self, case):
        if case not in self.rows[self.baseline_size:]:
            raise ValueError('cannot reject immutable baseline or unknown new case')
        self.rows.remove(case)
        self.semantic_rejected_norms.append(g._norm(case['question']))
        self.counts = Counter(r['question_type'] for r in self.rows)
        self.norms = [g._norm(r['question']) for r in self.rows]
        self.pairs = [(tuple(sorted(r['source_chunk_ids'])), g._norm(r['reference_answer']), g._norm(r['question']))
                      for r in self.rows if r['question_type'] != 'unanswerable']


def replay(store, engine):
    starts, finished = {}, set()
    for record in store.events():
        batch = record['batch']
        if record['event'] == 'start':
            if batch != len(starts) + 1 or record['digest'] != engine.digest or record['model'] != g.MODEL_NAME:
                raise ValueError('journal batch/model mismatch')
            if record['kind'] not in engine.targets or any(c not in engine.corpus for c in record['packet_chunk_ids']):
                raise ValueError('journal packet/type mismatch')
            if record != make_start(engine, batch):
                raise ValueError('journal inference provenance mismatch')
            starts[batch] = record
        elif record['event'] == 'semantic_rejection':
            if batch not in finished or not record.get('reason'):
                raise ValueError('semantic rejection without completed batch/reason')
            engine.reject_case(record['case'])
        elif record['event'] in ('result', 'error'):
            if batch not in starts or batch in finished:
                raise ValueError('journal result without unique start')
            finished.add(batch)
            if record['event'] == 'result':
                start = starts[batch]
                decisions = [engine.consider(raw, start['kind'], batch, start['seed'], start['packet_chunk_ids'])
                             for raw in record['candidates']]
                if decisions != record['decisions']:
                    raise ValueError('journal decision replay mismatch')
        else:
            raise ValueError('unknown journal event')
    return len(starts)


def reconcile_quarantine(store):
    """Finish archiving a superseded publication even if review was interrupted."""
    final = store.directory / 'silver_cases_500.jsonl'
    if not final.exists():
        return
    payload = final.read_bytes()
    digest = sha(payload)
    rejected_publications = {r.get('published_sha256') for r in store.events()
                             if r['event'] == 'semantic_rejection'}
    if digest in rejected_publications:
        archive = store.directory / 'topup_quarantine' / f'silver_cases_500.{digest}.jsonl'
        immutable_write(archive, payload)
        if final.read_bytes() != payload:
            raise ValueError('publication changed during quarantine')
        final.unlink()  # Exact checked file; complete bytes retained in immutable archive.


def quarantine_last(store, engine, case_id, reason):
    if len(engine.rows) <= engine.baseline_size:
        raise ValueError('cannot reject immutable baseline')
    if engine.rows[-1]['case_id'] != case_id or not reason:
        raise ValueError('review must identify last new case and rejection reason')
    quarantine_case(store, engine, case_id, reason)


def quarantine_case(store, engine, case_id, reason):
    matches = [r for r in engine.rows[engine.baseline_size:] if r['case_id'] == case_id]
    if len(matches) != 1 or not reason:
        raise ValueError('cannot reject immutable baseline or unknown new case without reason')
    final = store.directory / 'silver_cases_500.jsonl'
    if final.exists() and read_rows(final) != engine.rows:
        raise ValueError('publication does not match reviewed state')
    case = copy.deepcopy(matches[0])
    record = {'event': 'semantic_rejection', 'batch': case['generation_batch'],
              'case': case, 'reason': reason, 'reviewer': 'automated_agent_inspection',
              'human_signoff': 'not_performed',
              'published_sha256': sha(final.read_bytes()) if final.exists() else None}
    store.append(record)
    engine.reject_case(case)
    reconcile_quarantine(store)
    store.project()


def summarize(store, engine, max_batches):
    events = store.events()
    starts = [r for r in events if r['event'] == 'start']
    results = [r for r in events if r['event'] == 'result']
    finished = {r['batch'] for r in events if r['event'] in ('result', 'error')}
    reasons = Counter(d['reason'] for r in results for d in r['decisions'] if d['status'] == 'rejected')
    reviewed = [r for r in events if r['event'] == 'semantic_rejection']
    reasons.update('semantic_review:' + r['reason'] for r in reviewed)
    total = sum(len(r['candidates']) for r in results)
    duplicate_count = sum(v for k, v in reasons.items() if k.startswith('duplicate_'))
    complete = not any(engine.remaining().values())
    return {
        'status': 'ready' if complete else ('exhausted' if len(starts) >= max_batches else 'incomplete'),
        'model': f'ollama/{g.MODEL_NAME}', 'model_digest': engine.digest, 'seed': SEED,
        'topup_version': VERSION, 'prompt_version': g.PROMPT_VERSION,
        'baseline_count': engine.baseline_size, 'final_count': len(engine.rows),
        'new_candidates': total, 'new_accepted': len(engine.rows) - engine.baseline_size,
        'rejected': sum(reasons.values()), 'rejections': dict(reasons),
        'duplicates_rejected': duplicate_count,
        'deduplication_rate': duplicate_count / total if total else 0,
        'deduplication_rate_denominator': 'all returned incremental candidates',
        'by_type': {k: engine.counts[k] for k in engine.targets}, 'targets': engine.targets,
        'shortfall': engine.remaining(), 'attempted_batches': len(starts), 'max_batches': max_batches,
        'interrupted_batches': [r['batch'] for r in starts if r['batch'] not in finished],
        'semantic_rejections': len(reviewed),
        'superseded_publication_sha256': [r['published_sha256'] for r in reviewed if r.get('published_sha256')],
        'model_errors': dict(Counter(r['reason'] for r in events if r['event'] == 'error')),
        'raw_sha256': sha(encode_rows(events)),
        'unanswerable_quality_risk': RISK,
        'unanswerable_pending_verification': engine.counts['unanswerable'],
    }


def validate(engine, baseline):
    errors = []
    rows = engine.rows
    if len(rows) != 500:
        errors.append('total_not_500')
    if Counter(r['question_type'] for r in rows) != engine.targets:
        errors.append('type_quota_mismatch')
    if rows[:len(baseline)] != baseline:
        errors.append('baseline_modified')
    if [r['case_id'] for r in rows] != [f'p6s-{i:04d}' for i in range(1, len(rows)+1)]:
        errors.append('case_id_not_unique_sequential')
    seen = list(engine.gold)
    pairs = []
    for r in rows:
        cid, kind = r['case_id'], r['question_type']
        if not r['question'].strip():
            errors.append(f'{cid}:empty_question')
        nq = g._norm(r['question'])
        if any(SequenceMatcher(None, nq, q, autojunk=False).ratio() >= .80 for q in seen):
            errors.append(f'{cid}:duplicate_question')
        seen.append(nq)
        if kind == 'unanswerable':
            _, reason = g._validate_unanswerable({'question': r['question'], 'category': r['out_of_scope_category'],
                                                 'assumed_out_of_scope': r['assumed_out_of_scope_reason']}, list(engine.texts.values()))
            if r['reference_answer'] is not None or r['source_evidence'] or r['source_chunk_ids']:
                errors.append(f'{cid}:unanswerable_schema')
        else:
            _, reason = g._validate_candidate({'question': r['question'], 'answer': r['reference_answer'],
                                               'evidence': r['source_evidence']}, engine.texts, kind)
            ids = list(dict.fromkeys(e['chunk_id'] for e in r['source_evidence']))
            if not ids or ids != r['source_chunk_ids']:
                errors.append(f'{cid}:evidence_ids_mismatch')
            if all(i in engine.corpus for i in ids):
                docs = sorted({engine.corpus[i]['source'] for i in ids})
                page = max((engine.corpus[i].get('page_number') for i in ids if engine.corpus[i].get('page_number') is not None), default=None)
                if r['source_document'] != docs or r['source_page'] != page:
                    errors.append(f'{cid}:source_mismatch')
            key, na = tuple(sorted(ids)), g._norm(r['reference_answer'])
            if any(key == ck and na[:80] == a[:80] and SequenceMatcher(None, nq, q, autojunk=False).ratio() >= .60
                   for ck, a, q in pairs):
                errors.append(f'{cid}:duplicate_evidence_answer')
            pairs.append((key, na, nq))
        if reason:
            errors.append(f'{cid}:{reason}')
        if not r.get('generation_model') or not r.get('generation_version') or not isinstance(r.get('generation_seed'), int) or not isinstance(r.get('generation_batch'), int):
            errors.append(f'{cid}:generation_provenance_missing')
    return {'status': 'passed' if not errors else 'failed', 'errors': errors,
            'total': len(rows), 'by_type': dict(Counter(r['question_type'] for r in rows)),
            'baseline_preserved': rows[:len(baseline)] == baseline,
            'checks': ['exact_total_500', 'strict_type_quotas', 'original_466_fields_and_ids',
                       'unique_sequential_ids', 'nonempty_questions', 'original_evidence_validation',
                       'chunk_ids_exist', 'source_document_page_consistency', 'multi_two_distinct_chunks',
                       'verbatim_quotes_original_whitespace_rules', 'gold_and_silver_similarity_0.80',
                       'same_evidence_answer_similarity_0.60', 'generation_provenance'],
            'quality_risks': [RISK, 'Automated evidence checks do not establish full semantic entailment or two-chunk reasoning.'],
            'human_signoff': 'not_performed', 'rag_e2e': 'not_run'}


def make_start(engine, batch):
    """Reconstruct the exact request from accepted state and global batch number."""
    packets = list(g.build_packets(list(engine.corpus.values()), random.Random(SEED)))
    seed = SEED + 10000 + batch
    rng = random.Random(seed)
    remaining = engine.remaining()
    if not any(remaining.values()):
        raise ValueError('journal provenance: batch after quotas complete')
    kind = max((k for k in remaining if remaining[k]), key=lambda k: (remaining[k], rng.random()))
    packet = packets[(batch - 1) % len(packets)] if kind != 'unanswerable' else []
    block, texts = g._passage_block(packet)
    count = min(3, remaining[kind])
    if kind == 'unanswerable':
        topic = list(g._UNANSWERABLE_TOPICS)[(batch - 1) % len(g._UNANSWERABLE_TOPICS)]
        prompt = (f'知识库真实业务主题词（仅可用于场景包装）：{topic}\n'
                  f'超出知识库范围的类别（category 必须逐一对应取自该列表）：'
                  f'{"、".join(g._UNANSWERABLE_TOPICS)}\ncount: {count}\n' + g._PROMPT_UNANSWERABLE)
    else:
        prompt = (f'任务：{g._TASKS[kind]}\ncount: {count}\n\nchunks 如下：\n{block}\n\n' + g._PROMPT_ANSWERABLE)
    return {'event': 'start', 'batch': batch, 'kind': kind, 'seed': seed,
            'packet_chunk_ids': list(texts), 'model': g.MODEL_NAME, 'digest': engine.digest,
            'topup_version': VERSION, 'options': {**g._BASE_OPTIONS, 'seed': seed},
            'prompt_sha256': sha(prompt.encode('utf-8')), 'prompt': prompt,
            'corpus_sha256': sha(g.CORPUS_JSONL.read_bytes())}


def generate(store, engine, max_batches, timeout):
    batch = replay(store, engine)
    if not any(engine.remaining().values()) or batch >= max_batches:
        return
    client = g.LocalOllama(g.ENDPOINT, g.MODEL_NAME, timeout=timeout)
    if client.local_digest() != engine.digest:
        raise ValueError('installed model digest differs from baseline')
    consecutive_errors = 0
    while any(engine.remaining().values()) and batch < max_batches:
        batch += 1
        start = make_start(engine, batch)
        kind, seed, ids = start['kind'], start['seed'], start['packet_chunk_ids']
        store.append(start)
        store.project()
        try:
            if kind != 'unanswerable' and len(ids) < 3:
                store.append({'event': 'error', 'batch': batch, 'reason': 'thin_packet'})
            else:
                items = client.generate(start['prompt'], start['options'], engine.digest, schema=g._schema_for(kind))
                if not isinstance(items, list):
                    raise g.ModelError('invalid_model_inference_output')
                decisions = [engine.consider(raw, kind, batch, seed, ids) for raw in items]
                store.append({'event': 'result', 'batch': batch, 'candidates': items, 'decisions': decisions})
                consecutive_errors = 0
        except g.ModelError as exc:
            store.append({'event': 'error', 'batch': batch, 'reason': str(exc)})
            consecutive_errors += 1
        store.project()
        projection(store.directory / 'silver_topup_summary.json', json_bytes(summarize(store, engine, max_batches)))
        print(json.dumps({'batch': batch, 'counts': dict(engine.counts), 'remaining': engine.remaining()}, ensure_ascii=False), flush=True)
        if consecutive_errors >= 5:
            break


def publish(store, engine, baseline, max_batches):
    reconcile_quarantine(store)
    store.project()
    report = validate(engine, baseline)
    load_inputs()  # Recheck frozen inputs immediately before publication.
    base_bytes = (HERE / 'silver_cases.jsonl').read_bytes()
    if not base_bytes.endswith(b'\n'):
        raise ValueError('baseline JSONL has no final newline')
    payload = base_bytes + encode_rows(engine.rows[len(baseline):])
    final = store.directory / 'silver_cases_500.jsonl'
    if report['status'] == 'passed':
        if [json.loads(x) for x in payload.decode('utf-8').splitlines()] != engine.rows:
            raise ValueError('final JSONL roundtrip mismatch')
        immutable_write(final, payload)
        report.update(final_sha256=sha(final.read_bytes()), jsonl_valid=True,
                      baseline_byte_prefix_preserved=final.read_bytes().startswith(base_bytes))
    else:
        if final.exists():
            raise ValueError('existing final file conflicts with incomplete/invalid journal')
        report.update(final_sha256=None, jsonl_valid=None, baseline_byte_prefix_preserved=None)
    manifest = json.loads((HERE / 'silver_baseline_sha256.json').read_text(encoding='utf-8'))
    report['baseline_sha256'] = manifest['sha256']
    report['baseline_manifest_sha256'] = sha((HERE / 'silver_baseline_sha256.json').read_bytes())
    report['topup_raw_sha256'] = sha((store.directory / 'silver_topup_raw.jsonl').read_bytes())
    report['topup_script_sha256'] = sha(Path(__file__).read_bytes())
    summary = summarize(store, engine, max_batches)
    if report['status'] == 'passed':
        summary['status'] = 'complete'
        summary['final_sha256'] = report['final_sha256']
    elif not any(engine.remaining().values()):
        summary['status'] = 'validation_failed'
    projection(store.directory / 'silver_topup_summary.json', json_bytes(summary))
    projection(store.directory / 'silver_500_validation.json', json_bytes(report))
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument('--generate', action='store_true')
    mode.add_argument('--build', action='store_true')
    mode.add_argument('--check', action='store_true')
    mode.add_argument('--reject-last', action='store_true', help='Audit a semantic rejection of the last NEW case; preserve superseded publication')
    mode.add_argument('--reject-case', action='store_true', help='Audit a semantic rejection of a NEW case; retain all other IDs')
    ap.add_argument('--case-id')
    ap.add_argument('--reason')
    ap.add_argument('--max-batches', type=int, default=200, help='Cumulative limit across restarts')
    ap.add_argument('--timeout', type=float, default=240)
    args = ap.parse_args()
    if args.max_batches < 0:
        ap.error('max-batches must be nonnegative')
    with writer_lock(HERE):
        baseline, corpus, gold, digest = load_inputs()
        engine = Engine(baseline, corpus, gold, g.TARGETS, digest)
        store = Store(HERE)
        replay(store, engine)
        reconcile_quarantine(store)
        if args.check:
            print(json.dumps({'baseline': len(baseline), 'shortfall': engine.remaining(), 'model_digest': digest}, ensure_ascii=False))
            return 0
        if args.reject_last or args.reject_case:
            action = quarantine_last if args.reject_last else quarantine_case
            action(store, engine, args.case_id, args.reason)
            publish(store, engine, baseline, args.max_batches)
            print(json.dumps({'status': 'review_rejected', 'case_id': args.case_id,
                              'shortfall': engine.remaining()}, ensure_ascii=False), flush=True)
            return 3
        immutable_write(HERE / 'silver_topup_config.json', json_bytes({
            'seed': SEED, 'model': g.MODEL_NAME, 'digest': digest, 'version': VERSION,
            'targets': g.TARGETS, 'options': g._BASE_OPTIONS,
            'baseline_manifest_sha256': sha((HERE / 'silver_baseline_sha256.json').read_bytes()),
        }))
        if args.generate:
            # generate() performs replay itself so use a fresh engine.
            engine = Engine(baseline, corpus, gold, g.TARGETS, digest)
            try:
                generate(store, engine, args.max_batches, args.timeout)
            except (KeyboardInterrupt, g.ModelError) as exc:
                print(f'Generation stopped: {type(exc).__name__}: {exc}', flush=True)
                engine = Engine(baseline, corpus, gold, g.TARGETS, digest)
                replay(store, engine)
                report = publish(store, engine, baseline, args.max_batches)
                return 3 if report['status'] == 'failed' else 0
        report = publish(store, engine, baseline, args.max_batches)
        print(json.dumps({'status': report['status'], 'total': report['total'], 'errors': report['errors'],
                          'final_sha256': report['final_sha256']}, ensure_ascii=False), flush=True)
        return 0 if report['status'] == 'passed' else 3


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, OSError) as exc:
        print(f'STOP: {exc}', flush=True)
        raise SystemExit(4)
