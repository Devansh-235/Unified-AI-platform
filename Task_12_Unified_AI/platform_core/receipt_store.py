"""Durable receipt results, independent of chat history."""
import os
import csv
import hashlib
import io
import json
import sqlite3
from pathlib import Path
DATABASE = Path(os.environ.get('RECEIPT_DATABASE', str(Path(__file__).resolve().parents[1]/'data/receipts.sqlite3')))

def connect(path=None):
    path = path or DATABASE
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute("CREATE TABLE IF NOT EXISTS receipts (id INTEGER PRIMARY KEY, image_hash TEXT UNIQUE, filename TEXT, vendor TEXT, date TEXT, items TEXT, total_amount REAL, tax REAL, items_quantity INTEGER, currency TEXT, raw_text TEXT, saved_at TEXT DEFAULT CURRENT_TIMESTAMP)")
    columns={r[1] for r in db.execute('PRAGMA table_info(receipts)')}
    for name,kind in [('subtotal','REAL'),('line_item_count','INTEGER')]:
        if name not in columns: db.execute(f'ALTER TABLE receipts ADD COLUMN {name} {kind}')
    db.commit()
    return db

def save(receipt, image, path=None):
    with connect(path) as db:
        digest = hashlib.sha256(image).hexdigest()
        db.execute("INSERT INTO receipts(image_hash,filename,vendor,date,items,total_amount,tax,items_quantity,currency,raw_text) VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(image_hash) DO UPDATE SET vendor=excluded.vendor,date=excluded.date,items=excluded.items,total_amount=excluded.total_amount,tax=excluded.tax,items_quantity=excluded.items_quantity,currency=excluded.currency,raw_text=excluded.raw_text", (digest,receipt['filename'],receipt['vendor'],receipt.get('date'),json.dumps(receipt.get('items',[]),ensure_ascii=False),receipt.get('total'),receipt.get('tax'),receipt.get('item_count'),receipt.get('currency'),receipt.get('raw_text','')))
        db.execute('UPDATE receipts SET subtotal=?,line_item_count=? WHERE image_hash=?',(receipt.get('subtotal'),receipt.get('line_item_count',len(receipt.get('items',[]))),digest))
        return db.execute('SELECT id FROM receipts WHERE image_hash=?',(digest,)).fetchone()[0]

def records(path=None):
    with connect(path) as db:
        return [dict(row) for row in db.execute('SELECT id,filename,vendor,date,items,subtotal,total_amount,tax,items_quantity,line_item_count,currency,saved_at FROM receipts ORDER BY id DESC')]

def export_csv(rows):
    output=io.StringIO(newline='')
    if rows:
        writer=csv.DictWriter(output,fieldnames=list(rows[0]))
        writer.writeheader()
        for row in rows:
            writer.writerow({k:("'"+v if isinstance(v,str) and v.startswith(('=','+','-','@')) else v) for k,v in row.items()})
    return output.getvalue().encode('utf-8-sig')
