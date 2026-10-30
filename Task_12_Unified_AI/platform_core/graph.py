import re
from pathlib import Path
from langgraph.graph import StateGraph, START, END
from .models import State, PlatformError
from . import rag, budget, ocr, receipt_store

ROOT = Path(__file__).resolve().parents[1]
IMAGES = {'.jpg', '.jpeg', '.png'}
DOCS = {'.pdf', '.txt'}


def supervisor(state: State):
    query = state.get('question', '').strip()
    attachments = state.get('attachments', [])
    docs = list(state.get('documents', []))
    route, reason = 'clarify', 'Ask a document question, a budget question, or attach a receipt.'
    if len(query) > 4000:
        reason = 'Question is too long. Please keep it under 4,000 characters.'
    elif len(attachments) > 5 or any(len(f.data) > 10 * 1024 * 1024 for f in attachments):
        reason = 'Upload up to five files, each no larger than 10 MB.'
    elif any(Path(f.name).suffix.lower() not in IMAGES | DOCS for f in attachments):
        reason = 'Unsupported file. Attach a PDF/TXT document or PNG/JPEG receipt.'
    else:
        images = [f for f in attachments if Path(f.name).suffix.lower() in IMAGES]
        new_docs = [f for f in attachments if Path(f.name).suffix.lower() in DOCS]
        if images and new_docs:
            reason = 'Send receipts and documents in separate messages so the intended task is clear.'
        elif images:
            route, reason = 'ocr', 'An image attachment is treated as a receipt.'
        elif not query or not re.search(r'[a-zA-Z]{2,}', query):
            reason = 'Enter a meaningful question, or attach a receipt image. For a document upload, include a question.'
        else:
            # New documents replace same-name documents in this browser session.
            for document in new_docs:
                docs = [d for d in docs if d.name != document.name] + [document]
            q = query.lower()
            if re.search(r'\b(receipt|merchant|vendor|scan|ocr)\b', q):
                route, reason = 'ocr', 'The question explicitly refers to a receipt.'
            elif new_docs or re.search(r'\b(policy|handbook|document|notes|pdf|explain|define)\b', q):
                route, reason = 'rag', 'The question requests information from documents.'
            elif re.search(r'\b(budget|budgets|allocated|allocation|department|departments|overspent|overspend|spend|spending|spent|fiscal)\b', q):
                route, reason = 'sql', 'The question requests budget data.'
            elif re.search(r'\b(total|amount|tax|items|date)\b', q):
                reason = 'Please specify whether you mean a receipt or department budget, or name the document topic.'
            elif re.search(r'\b(what|which|how|when|where|why|summarize|describe|tell)\b', q):
                route, reason = 'rag', 'A general knowledge question is checked against the loaded documents.'
    return dict(route=route, reason=reason, documents=docs, trace=['router'], error=False, payload={})


def choose(state):
    # Unknown supervisor output is never silently sent to a capability.
    return state.get('route') if state.get('route') in {'rag', 'sql', 'ocr'} else 'clarify'


def build_graph(csv_path=None, router=supervisor):
    csv_path = csv_path or ROOT / 'samples' / 'budget.csv'
    builder = StateGraph(State)
    builder.add_node('router', router)
    def handler(name):
        def run(state):
            try:
                if name == 'rag':
                    response, payload = rag.answer(state['question'], state.get('documents', []))
                elif name == 'sql':
                    response, payload = budget.answer(state['question'], csv_path)
                else:
                    response, payload = ocr.answer([f for f in state.get('attachments', []) if Path(f.name).suffix.lower() in IMAGES])
                    images = [f for f in state.get('attachments', []) if Path(f.name).suffix.lower() in IMAGES]
                    for receipt, image in zip(payload.get('receipts', []), images):
                        receipt['database_id'] = receipt_store.save(receipt, image.data)
                return dict(response=response, payload=payload, error=False, trace=state.get('trace', []) + [name])
            except PlatformError as exc:
                return dict(response=str(exc), payload={}, error=True, trace=state.get('trace', []) + [name])
            except Exception:
                return dict(response='The request could not be processed. Check the input file and configuration, then retry.', payload={}, error=True, trace=state.get('trace', []) + [name])
        return run
    for name in ('rag', 'sql', 'ocr'):
        builder.add_node(name, handler(name))
        builder.add_edge(name, END)
    builder.add_node('clarify', lambda s: dict(response=s.get('reason', 'Unknown route. Rephrase your request.'), error=True, payload={}, trace=s.get('trace', []) + ['clarify']))
    builder.add_edge('clarify', END)
    builder.add_edge(START, 'router')
    builder.add_conditional_edges('router', choose, {name: name for name in ('rag', 'sql', 'ocr', 'clarify')})
    return builder.compile()
