"""Rebuild fictional budget and receipt fixtures. Never imports application answers."""
import csv
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]


def main():
    target = ROOT / 'samples'
    (target / 'receipts').mkdir(parents=True, exist_ok=True)
    departments = [('Marketing', 100000, 120000), ('Sales', 150000, 140000),
                   ('Engineering', 300000, 330000), ('HR', 80000, 75000),
                   ('Finance', 90000, 90000), ('Operations', 200000, 210000)]
    with (target / 'budget.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Department','Fiscal_Year','Quarter','Allocated_Budget','Actual_Spend'])
        for year in (2025, 2026):
            for quarter in range(1, 5):
                for name, allocated, actual in departments:
                    factor = 1 + (year - 2025) * 0.1 + (quarter - 2) * 0.05
                    writer.writerow([name,year,f'Q{quarter}',round(allocated*factor),round(actual*factor)])
    specs = [
        ('01_cafe.png', 'NORTHSTAR CAFE', '2026-06-15', [('Latte',2,150),('Sandwich',1,200)],25),
        ('02_stationery.png','PAPER TRAIL','2026-06-16',[('Notebook',3,80),('Pen',2,20)],14),
        ('03_grocery.png','GREEN BASKET','2026-06-17',[('Apples',2,120),('Bread',1,60),('Milk',2,50)],20),
    ]
    expected = {}
    fonts = ['C:/Windows/Fonts/consola.ttf','/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf','/System/Library/Fonts/Menlo.ttc']
    font_path = next((p for p in fonts if Path(p).exists()), None)
    font = ImageFont.truetype(font_path, 30) if font_path else ImageFont.load_default(size=30)
    heading = ImageFont.truetype(font_path, 40) if font_path else ImageFont.load_default(size=40)
    for filename, vendor, date, items, tax in specs:
        image = Image.new('RGB',(1000,1080),'white')
        draw = ImageDraw.Draw(image)
        draw.text((60,50),vendor,font=heading,fill='black')
        subtotal = sum(q*p for _,q,p in items)
        lines = ['12 Demo Road, Bengaluru', f'Date: {date}', 'Currency: INR',
                 'Receipt: DEMO-' + filename[:2], '', 'QTY x ITEM          UNIT      AMOUNT', '-'*44]
        lines += [f'{qty} x {name:<16} {price:7.2f} {qty*price:9.2f}' for name,qty,price in items]
        lines += ['-'*44,f'Subtotal: {subtotal:.2f}',f'Tax: {tax:.2f}',f'Total: INR {subtotal+tax:.2f}',
                  f'Number of items: {sum(q for _,q,_ in items)}','', 'SYNTHETIC SAMPLE - NOT A VALID INVOICE']
        for i,line in enumerate(lines):
            draw.text((60,125+i*45),line,font=font,fill='black')
        image.save(target/'receipts'/filename)
        expected[filename] = dict(vendor=vendor,date=date,currency='INR',subtotal=subtotal,tax=tax,total=subtotal+tax,item_count=sum(q for _,q,_ in items),line_item_count=len(items))
        expected[filename]['items'] = [dict(name=name, quantity=qty, unit_price=price, amount=qty*price) for name,qty,price in items]
    (target/'receipts'/'expected.json').write_text(json.dumps(expected,indent=2),encoding='utf-8')


if __name__ == '__main__':
    main()
