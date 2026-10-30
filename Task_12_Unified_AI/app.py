from pathlib import Path
import io
import os
import streamlit as st
from PIL import Image
from dotenv import load_dotenv
from platform_core.graph import build_graph, ROOT
from platform_core.models import Attachment
from platform_core import receipt_store
import json

load_dotenv(ROOT / '.env', override=True)
st.set_page_config(page_title='Unify · AI workspace', page_icon='◈', layout='wide')
st.markdown('''<style>
.block-container {max-width:1100px;padding-top:2.2rem;}
[data-testid="stChatMessage"] {border:1px solid #dfe5ef;border-radius:14px;}
h1 {letter-spacing:-1.3px;} .eyebrow {color:#64748b;letter-spacing:3px;font-size:12px;}
</style>''', unsafe_allow_html=True)

def workflow():
    return build_graph()

def show_result(result):
    trace = ' → '.join(['START'] + result['trace'] + ['END'])
    st.caption(trace)
    if result.get('error'):
        st.warning(result['response'])
    else:
        st.markdown(result['response'])
    payload = result.get('payload', {})
    if payload.get('sources'):
        st.markdown('### References')
        st.caption(payload.get('reference_note', 'Source passages used to answer your question.'))
        for source in payload['sources']:
            location = f"{source['source']} - Page {source['page']}"
            if source.get('line_start') is not None:
                location += f" - Lines {source['line_start']}-{source['line_end']}"
            with st.expander(location):
                st.write(source['text'])
    if 'rows' in payload:
        st.dataframe(payload['rows'], hide_index=True, use_container_width=True)
        with st.expander('SQL and query parameters'):
            st.code(payload['sql'], language='sql')
            st.write(payload['parameters'])
    for receipt in payload.get('receipts', []):
        st.subheader(receipt['vendor'])
        fields = [('Date', receipt['date']),
                  ('Total', f"{receipt['currency'] or ''} {receipt['total']:.2f}" if receipt['total'] is not None else None),
                  ('Tax', f"{receipt['tax']:.2f}" if receipt['tax'] is not None else None),
                  ('Item quantity', receipt['item_count'])]
        for start in (0, 2):
            for col, (label, value) in zip(st.columns(2), fields[start:start+2]):
                col.metric(label, str(value) if value is not None else 'Not recognized')
        st.caption(f"{receipt['filename']} · {receipt['line_item_count']} parsed line items · Date shown as printed")
        if receipt['items']:
            st.dataframe(receipt['items'], hide_index=True, use_container_width=True)
        for warning in receipt['warnings']:
            st.warning(warning)
        with st.expander('Raw OCR text'):
            st.text(receipt['raw_text'])
    with st.expander('Routing details / structured result'):
        st.write(result.get('reason', ''))
        st.json(payload)

with st.sidebar:
    st.markdown('### ◈ Unify')
    st.caption('TASK 12 · UNIFIED AI PLATFORM')
    use_sample = st.checkbox('Use bundled policy document', value=True)
    st.caption('Attach a PDF/TXT in chat to add your own knowledge. Attach a PNG/JPEG for receipt extraction.')
    st.divider()
    st.markdown('**Workspace**')
    st.write('Budget data: Q1–Q4 · 2025–2026 · INR')
    st.write('Backend: ' + os.getenv('AI_BACKEND', 'local'))
    st.caption('Local mode: excerpt retrieval, constrained SQL planning and real Tesseract OCR. No API key needed.')
    if st.button('Clear conversation'):
        st.session_state.clear()
        st.rerun()
    st.markdown('**Try asking**')
    st.caption('What is the annual leave policy?')
    st.caption('Which departments overspent in Q2 2025?')
    st.caption('Attach samples/receipts/01_cafe.png and ask “Extract this receipt”.')

st.markdown('<div class="eyebrow">ONE CONVERSATION · THREE CAPABILITIES</div>', unsafe_allow_html=True)
st.title('Your documents. Your numbers. One workspace.')
st.write('Ask a question or attach a receipt. The graph chooses the right tool.')
st.session_state.setdefault('messages', [])
st.session_state.setdefault('documents', [])
for message in st.session_state.messages:
    with st.chat_message(message['role']):
        if message['role'] == 'user':
            st.write(message['text'])
            for attachment in message.get('images', []):
                try:
                    with Image.open(io.BytesIO(attachment.data)) as preview:
                        if preview.width * preview.height > 25_000_000:
                            raise ValueError('Oversized preview')
                        preview.verify()
                    st.image(attachment.data, caption=attachment.name, width=260)
                except Exception:
                    st.caption(f'{attachment.name} · preview unavailable')
        else:
            show_result(message['result'])

with st.expander('Saved receipts - database and downloads'):
    try:
        saved = receipt_store.records()
        if saved:
            st.dataframe(saved, hide_index=True, use_container_width=True)
            st.download_button('Download receipts CSV', receipt_store.export_csv(saved), 'receipts.csv', 'text/csv')
            st.download_button('Download receipts JSON', json.dumps(saved, ensure_ascii=False, indent=2), 'receipts.json', 'application/json')
            st.caption('Saved locally in data/receipts.sqlite3. Clearing the conversation does not delete these records.')
        else:
            st.info('Upload a receipt to save its extracted fields here automatically.')
    except Exception:
        st.warning('Cannot open the receipt database. Check write permission for the data folder.')

submission = st.chat_input('Ask about documents, budgets, or attach a receipt…', accept_file='multiple', file_type=['pdf', 'txt', 'png', 'jpg', 'jpeg'])
if submission:
    question = submission.text or ''
    files = [Attachment(Path(f.name).name, f.getvalue()) for f in submission.files]
    documents = list(st.session_state.documents)
    if use_sample:
        sample = ROOT / 'samples' / 'company_policy.txt'
        documents = [Attachment(sample.name, sample.read_bytes())] + documents
    with st.spinner('Routing through LangGraph…'):
        result = workflow().invoke(dict(question=question, attachments=files, documents=documents))
    st.session_state.documents = [d for d in result.get('documents', []) if d.name != 'company_policy.txt']
    images = [f for f in files if Path(f.name).suffix.lower() in {'.png', '.jpg', '.jpeg'}]
    st.session_state.messages.extend([
        dict(role='user', text=question or 'Extract attached receipt', images=images),
        dict(role='assistant', result={k:v for k,v in result.items() if k not in {'documents','attachments'}}),
    ])
    st.rerun()
