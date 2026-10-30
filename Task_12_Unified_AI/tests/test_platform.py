import io
import json
from datetime import date
from pathlib import Path
import pytest
from PIL import Image
from platform_core.graph import build_graph, ROOT
from platform_core.models import Attachment, PlatformError
from platform_core import budget, ocr


@pytest.fixture(autouse=True)
def local(monkeypatch):
    monkeypatch.setenv('AI_BACKEND','local')


def invoke(question='', files=None, documents=None):
    return build_graph().invoke(dict(question=question, attachments=files or [], documents=documents or []))


def sample_doc():
    p = ROOT/'samples/company_policy.txt'
    return Attachment(p.name,p.read_bytes())


@pytest.mark.parametrize('question,expected',[
    ('What is the annual leave policy?','24 days'),
    ('How many days per week may employees work remotely?','three days per week'),
])
def test_rag_end_to_end(question,expected):
    result = invoke(question,documents=[sample_doc()])
    assert result['trace'] == ['router','rag']
    assert not result['error']
    assert expected in result['response']
    assert result['payload']['sources'][0]['source'] == 'company_policy.txt'


def test_sql_allocation():
    r = invoke('What is the allocated budget for Marketing in Q2 2025?')
    assert r['trace'] == ['router','sql'] and not r['error']
    assert r['payload']['rows'][0]['Allocated_Budget'] == 100000


def test_sql_overspend():
    r = invoke('Which departments overspent in Q2 2025?')
    assert r['trace'] == ['router','sql'] and not r['error']
    assert [(x['Department'],x['Overspend']) for x in r['payload']['rows']] == [('Engineering',30000),('Marketing',20000),('Operations',10000)]


@pytest.mark.ocr
@pytest.mark.parametrize('name',['01_cafe.png','02_stationery.png','03_grocery.png'])
def test_real_ocr(name):
    file = ROOT/'samples/receipts'/name
    r = invoke('Extract this receipt',files=[Attachment(file.name,file.read_bytes())])
    assert r['trace'] == ['router','ocr'] and not r['error'],r['response']
    receipt = r['payload']['receipts'][0]
    expected = json.loads((ROOT/'samples/receipts/expected.json').read_text())[name]
    for key,value in expected.items():
        assert receipt[key] == value,(key,receipt)
    assert not receipt['warnings']


@pytest.mark.parametrize('question,files,route,message',[
    ('What is the leave policy?',[],'rag','No document'),
    ('',[],'clarify','meaningful'),
    ('???',[],'clarify','meaningful'),
    ('What is the total?',[],'clarify','specify'),
    ('Extract this receipt',[],'ocr','Attach'),
    ('Extract this receipt',[Attachment('bad.png',b'not an image')],'ocr','image'),
    ('Read this',[Attachment('data.exe',b'bad')],'clarify','Unsupported'),
    ('Read this',[Attachment('bad.pdf',b'bad')],'rag','Cannot read'),
    ('Read this',[Attachment('a.txt',b'x'),Attachment('a.png',b'x')],'clarify','separate'),
])
def test_errors(question,files,route,message):
    r=invoke(question,files)
    assert r['error'] and r['trace']==['router',route]
    assert message.lower() in r['response'].lower()


def test_missing_key(monkeypatch):
    monkeypatch.setenv('AI_BACKEND','huggingface')
    monkeypatch.delenv('HUGGINGFACEHUB_API_TOKEN',raising=False)
    r=invoke('What is the annual leave policy?',documents=[sample_doc()])
    assert r['error'] and 'Missing Hugging Face API key' in r['response']


def test_wrong_route():
    graph=build_graph(router=lambda s: {'route':'unknown','trace':['router']})
    r=graph.invoke({'question':'hello'})
    assert r['error'] and r['trace']==['router','clarify']


def test_document_budget_policy_not_sql():
    r=invoke('What is the budget approval policy?',documents=[sample_doc()])
    assert r['route']=='rag'


def test_image_precedence():
    r=invoke('Which department overspent?',files=[Attachment('bad.png',b'x')])
    assert r['route']=='ocr'


@pytest.mark.parametrize('sql',[
    'DROP TABLE dept_budgets',
    'SELECT * FROM dept_budgets; DELETE FROM dept_budgets',
    "SELECT load_extension('bad')",
    'SELECT * FROM sqlite_master',
])
def test_readonly_sql(sql):
    db=budget.connect(ROOT/'samples/budget.csv')
    try:
        with pytest.raises(PlatformError):
            budget.execute_readonly(db,sql)
    finally:
        db.close()


def test_current_quarter_is_not_hardcoded():
    sql,params=budget.plan('Which departments overspent this quarter?',today=date(2026,9,16))
    assert params==[2026,'Q3']


def test_no_data():
    r=invoke('What is the total spend in 2020?')
    assert 'No matching' in r['response']


@pytest.mark.ocr
def test_blank_image():
    image=Image.new('RGB',(400,400),'white')
    data=io.BytesIO(); image.save(data,format='PNG')
    r=invoke(files=[Attachment('blank.png',data.getvalue())])
    assert r['error'] and 'no readable' in r['response'].lower()


def test_unknown_fields_not_invented():
    r=ocr.parse_receipt('SHOP\nReceipt 123456\nTotal: 12.00')
    assert r['date'] is None and r['tax'] is None and r['item_count'] is None
    assert r['warnings']


def test_no_match_rag():
    r=invoke('What is quantum entanglement?',documents=[sample_doc()])
    assert 'could not find' in r['response']


def test_upload_document_retained():
    r=invoke('What is the annual leave policy?',files=[sample_doc()])
    assert r['documents']==[sample_doc()]
    assert '24 days' in r['response']


def test_supplied_lecture_pdf():
    file=ROOT/'samples/ai_lecture_notes.pdf'
    r=invoke('What are the science based and engineering based goals of AI?',files=[Attachment(file.name,file.read_bytes())])
    assert r['trace']==['router','rag'] and not r['error']
    assert 'system building' in r['response']
    assert any(s['page']==4 for s in r['payload']['sources'])


def test_receipt_inconsistent_total():
    r=ocr.parse_receipt('SHOP\n02/05/2023\nApple.....30.00\nBread.....30.00\nMilk.....30.00\nTotal.....60.00')
    assert r['line_item_count']==3 and r['item_count'] is None
    assert any('exceed' in w for w in r['warnings'])


def test_missing_tesseract(monkeypatch):
    monkeypatch.setenv('TESSERACT_CMD','/does-not-exist/tesseract')
    p=ROOT/'samples/receipts/01_cafe.png'
    r=invoke(files=[Attachment(p.name,p.read_bytes())])
    assert r['error'] and 'Tesseract OCR is missing' in r['response']
