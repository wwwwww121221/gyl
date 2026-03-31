import os
import warnings
from datetime import datetime
from pathlib import Path
from decimal import Decimal
from uuid import uuid4

from openpyxl import load_workbook
from openpyxl.cell.cell import MergedCell
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session

from models import InquirySupplier, InquiryTask, InquiryTaskItem, InquiryRequest, Quotation, Supplier, LinkStatus


BASE_DIR = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = BASE_DIR / "static" / "templates"
CONTRACT_DIR = BASE_DIR / "static" / "contracts"
FONT_DIR = BASE_DIR / "static" / "fonts"
SIMSUN_PATH = FONT_DIR / "SimSun.ttf"
SYSTEM_SIMSUN_PATH = Path("C:/Windows/Fonts/simsun.ttc")
os.makedirs("static/contracts", exist_ok=True)
TEMPLATE_CELLS = {
    "supplier_name": "E3",
    "buyer_name": "E4",
    "contract_no": "L3",
    "project_no": "F6",
    "project_name": "H7",
    "total_amount_upper": "H9",
    "total_qty": "P9",
    "total_amount": "AA9",
}


def _resolve_template_path() -> Path:
    candidates = [
        TEMPLATE_DIR / "合同模版.xlsx",
        TEMPLATE_DIR / "合同模版.XLSX",
        BASE_DIR / "合同模版.xlsx",
        BASE_DIR / "合同模版.XLS",
    ]
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError("合同模板文件不存在，请将‘合同模版.xlsx’放入 static/templates 目录")


def _register_pdf_font() -> str:
    font_candidates = [SIMSUN_PATH, SYSTEM_SIMSUN_PATH]
    for font_path in font_candidates:
        if font_path.exists():
            try:
                pdfmetrics.registerFont(TTFont("SimSun", str(font_path.resolve())))
                return "SimSun"
            except Exception:
                continue
    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    return "STSong-Light"


def _import_win32_modules():
    try:
        import pythoncom
        from win32com import client as win32
        return pythoncom, win32
    except Exception:
        return None, None


def _normalize_template_for_openpyxl(template_path: Path) -> Path:
    normalized_path = CONTRACT_DIR / "_normalized_template.xlsx"
    pythoncom, win32 = _import_win32_modules()
    if not pythoncom or not win32:
        raise RuntimeError("模板文件无法被 openpyxl 正常读取，且未检测到 pywin32")

    excel = None
    workbook = None
    try:
        pythoncom.CoInitialize()
        excel = win32.DispatchEx("Excel.Application")
        excel.Visible = False
        excel.DisplayAlerts = False
        workbook = excel.Workbooks.Open(str(template_path.resolve()))
        normalized_path.parent.mkdir(parents=True, exist_ok=True)
        workbook.SaveAs(str(normalized_path.resolve()), FileFormat=51)
    finally:
        if workbook is not None:
            workbook.Close(False)
        if excel is not None:
            excel.Quit()
        pythoncom.CoUninitialize()
    return normalized_path


def _safe_load_workbook(file_path: Path):
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            wb = load_workbook(file_path)
        has_invalid_spec_warning = any("invalid specification" in str(w.message).lower() for w in caught)
        if has_invalid_spec_warning:
            normalized_template = _normalize_template_for_openpyxl(file_path)
            return load_workbook(normalized_template)
        return wb
    except Exception:
        normalized_template = _normalize_template_for_openpyxl(file_path)
        return load_workbook(normalized_template)


def _resolve_deal_link(db: Session, inquiry_id: int) -> InquirySupplier:
    deal_link = db.query(InquirySupplier).filter(
        InquirySupplier.id == inquiry_id,
        InquirySupplier.status == LinkStatus.DEAL
    ).first()
    if deal_link:
        return deal_link

    deal_link = db.query(InquirySupplier).filter(
        InquirySupplier.task_id == inquiry_id,
        InquirySupplier.status == LinkStatus.DEAL
    ).order_by(InquirySupplier.id.desc()).first()
    if deal_link:
        return deal_link

    raise ValueError("未找到已成交的询价记录")


def _to_decimal(val) -> Decimal:
    if val is None:
        return Decimal("0")
    return Decimal(str(val))


def _to_chinese_upper_amount(amount: Decimal) -> str:
    digits = "零壹贰叁肆伍陆柒捌玖"
    units = ["", "拾", "佰", "仟"]
    big_units = ["", "万", "亿", "兆"]
    integer = int(amount.quantize(Decimal("1")))
    if integer == 0:
        return "零圆整"
    groups = []
    while integer > 0:
        groups.append(integer % 10000)
        integer //= 10000
    text_parts = []
    for gi in range(len(groups) - 1, -1, -1):
        group = groups[gi]
        if group == 0:
            if text_parts and not text_parts[-1].endswith("零"):
                text_parts.append("零")
            continue
        group_text = ""
        zero_flag = False
        for pos in range(3, -1, -1):
            divisor = 10 ** pos
            n = group // divisor
            group %= divisor
            if n == 0:
                zero_flag = True
            else:
                if zero_flag and group_text and not group_text.endswith("零"):
                    group_text += "零"
                zero_flag = False
                group_text += digits[n] + units[pos]
        text_parts.append(group_text + big_units[gi])
    return f"{''.join(text_parts).rstrip('零')}圆整"


def _collect_contract_payload(db: Session, link: InquirySupplier) -> dict:
    task = db.query(InquiryTask).filter(InquiryTask.id == link.task_id).first()
    supplier = db.query(Supplier).filter(Supplier.id == link.supplier_id).first()
    if not task or not supplier:
        raise ValueError("询价任务或供应商信息不存在")

    quotes = db.query(Quotation).filter(
        Quotation.inquiry_supplier_id == link.id,
        Quotation.round == link.current_round
    ).all()
    if not quotes:
        quotes = db.query(Quotation).filter(
            Quotation.inquiry_supplier_id == link.id
        ).order_by(Quotation.round.desc(), Quotation.id.asc()).all()
        if quotes:
            max_round = quotes[0].round
            quotes = [q for q in quotes if q.round == max_round]
    if not quotes:
        raise ValueError("未找到该成交供应商的报价数据")

    project_no = ""
    project_name = ""
    buyer_name = "需方"
    items = []
    total_amount = Decimal("0")
    total_qty = Decimal("0")

    for idx, q in enumerate(quotes, start=1):
        task_item = db.query(InquiryTaskItem).filter(InquiryTaskItem.id == q.item_id).first()
        req = db.query(InquiryRequest).filter(InquiryRequest.id == task_item.request_id).first() if task_item else None
        material_name = req.material_name if req else ""
        material_code = req.material_code if req else ""
        qty = _to_decimal(req.qty if req and req.qty is not None else q.qty)
        price = _to_decimal(q.price)
        amount = qty * price
        total_qty += qty
        total_amount += amount

        if not project_no and req and req.project_info:
            project_no = str(req.project_info.get("number") or req.project_info.get("name") or "")
        if not project_name and req and req.project_info:
            project_name = str(req.project_info.get("name") or req.project_info.get("number") or "")

        items.append({
            "index": idx,
            "material_name": material_name,
            "material_code": material_code,
            "qty": float(qty),
            "price": float(price),
            "amount": float(amount),
        })

    return {
        "contract_no": f"HT-{link.task_id}-{link.id}-{datetime.now().strftime('%Y%m%d')}",
        "supplier_name": supplier.name,
        "buyer_name": buyer_name,
        "project_no": project_no,
        "project_name": project_name,
        "task_title": task.title,
        "items": items,
        "total_qty": float(total_qty),
        "total_amount": float(total_amount),
    }


def _fill_template_excel(payload: dict, output_xlsx: Path, template_path: Path = None) -> None:
    template_path = template_path or _resolve_template_path()
    wb = _safe_load_workbook(template_path)
    if not wb.worksheets:
        normalized_template = _normalize_template_for_openpyxl(template_path)
        wb = load_workbook(normalized_template)
    if not wb.worksheets:
        raise ValueError("模板文件不包含可写工作表")
    ws = wb.active if wb.active else wb.worksheets[0]

    def resolve_cell_ref(cell_ref: str) -> str:
        try:
            cell = ws[cell_ref]
            if isinstance(cell, MergedCell):
                for merged_range in ws.merged_cells.ranges:
                    if cell_ref in merged_range:
                        return ws.cell(row=merged_range.min_row, column=merged_range.min_col).coordinate
            return cell_ref
        except Exception:
            return cell_ref

    def set_cell_value(cell_ref: str, value):
        try:
            target_ref = resolve_cell_ref(cell_ref)
            ws[target_ref] = value
        except Exception:
            return

    set_cell_value(TEMPLATE_CELLS["supplier_name"], payload.get("supplier_name", ""))
    set_cell_value(TEMPLATE_CELLS["buyer_name"], payload.get("buyer_name", ""))
    set_cell_value(TEMPLATE_CELLS["contract_no"], payload.get("contract_no", ""))
    set_cell_value(TEMPLATE_CELLS["project_no"], payload.get("project_no") or payload.get("task_title", ""))
    set_cell_value(TEMPLATE_CELLS["project_name"], payload.get("project_name") or payload.get("task_title", ""))

    total_amount = _to_decimal(payload.get("total_amount", 0))
    total_qty = _to_decimal(payload.get("total_qty", 0))
    set_cell_value(TEMPLATE_CELLS["total_amount_upper"], _to_chinese_upper_amount(total_amount))
    set_cell_value(TEMPLATE_CELLS["total_qty"], float(total_qty))
    set_cell_value(TEMPLATE_CELLS["total_amount"], float(total_amount))

    output_xlsx.parent.mkdir(parents=True, exist_ok=True)
    wb.save(output_xlsx)


def _fill_template_to_temp_excel(payload: dict) -> Path:
    template_path = _resolve_template_path()
    temp_xlsx = CONTRACT_DIR / f"temp_filled_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid4().hex[:8]}.xlsx"
    _fill_template_excel(payload, temp_xlsx, template_path=template_path)
    return temp_xlsx


def _export_excel_to_pdf_with_win32(xlsx_path: Path, output_pdf: Path) -> bool:
    pythoncom, win32 = _import_win32_modules()
    if not pythoncom or not win32:
        return False

    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    excel = None
    workbook = None
    try:
        pythoncom.CoInitialize()
        excel = win32.DispatchEx("Excel.Application")
        excel.Visible = False
        excel.DisplayAlerts = False
        workbook = excel.Workbooks.Open(str(xlsx_path.resolve()))
        workbook.ExportAsFixedFormat(0, str(output_pdf.resolve()))
        return True
    except Exception:
        return False
    finally:
        if workbook is not None:
            workbook.Close(False)
        if excel is not None:
            excel.Quit()
        if pythoncom is not None:
            pythoncom.CoUninitialize()


def _export_excel_to_pdf(xlsx_path: Path, output_pdf: Path) -> None:
    if _export_excel_to_pdf_with_win32(xlsx_path, output_pdf):
        return
    _render_pdf_with_reportlab(xlsx_path, output_pdf)


def _render_pdf_with_reportlab(xlsx_path: Path, output_pdf: Path) -> None:
    wb = _safe_load_workbook(xlsx_path)
    ws = wb.active if wb.active else wb.worksheets[0]
    font_name = _register_pdf_font()

    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(output_pdf.resolve()))
    c.setPageSize((595, 842))
    c.setFont(font_name, 11)

    start_x = 40
    y = 800
    base_line_spacing = 20

    c.setFont(font_name, 16)
    c.drawString(start_x + 210, y, "采购合同")
    y -= 32
    c.setFont(font_name, 11)

    header_refs = [
        ("供方", TEMPLATE_CELLS["supplier_name"]),
        ("需方", TEMPLATE_CELLS["buyer_name"]),
        ("合同号", TEMPLATE_CELLS["contract_no"]),
        ("项目号", TEMPLATE_CELLS["project_no"]),
    ]
    for label, ref in header_refs:
        val = ws[ref].value if ws[ref].value is not None else ""
        c.setFont(font_name, 11)
        c.drawString(start_x, y, f"{label}：{val}")
        y -= base_line_spacing

    y -= 10
    table_headers = ["序号", "物料名称", "物料编码", "数量", "单价", "金额"]
    col_widths = [45, 150, 120, 70, 70, 80]
    x = start_x
    for i, h in enumerate(table_headers):
        c.setFont(font_name, 11)
        c.drawString(x, y, str(h))
        x += col_widths[i]
    y -= base_line_spacing

    row = 8
    while row <= ws.max_row and y > 80:
        values = [
            ws[f"A{row}"].value,
            ws[f"B{row}"].value,
            ws[f"C{row}"].value,
            ws[f"D{row}"].value,
            ws[f"E{row}"].value,
            ws[f"F{row}"].value,
        ]
        if all(v in [None, ""] for v in values):
            row += 1
            continue
        x = start_x
        for i, v in enumerate(values):
            c.setFont(font_name, 10)
            c.drawString(x, y, "" if v is None else str(v))
            x += col_widths[i]
        row_height = ws.row_dimensions[row].height or 15
        line_spacing = max(base_line_spacing, int(row_height + 4))
        y -= line_spacing
        row += 1

    c.save()


async def generate_contract_pdf(db: Session, inquiry_id: int) -> str:
    link = _resolve_deal_link(db, inquiry_id)
    payload = _collect_contract_payload(db, link)

    output_pdf = CONTRACT_DIR / f"合同_{inquiry_id}.pdf"
    temp_xlsx = _fill_template_to_temp_excel(payload)
    try:
        _export_excel_to_pdf(temp_xlsx, output_pdf)
    finally:
        if temp_xlsx.exists():
            temp_xlsx.unlink()

    static_pdf_path = f"/static/contracts/{output_pdf.name}"
    link.contract_pdf = static_pdf_path
    if hasattr(link, "contract_pdf_path"):
        link.contract_pdf_path = static_pdf_path
    db.add(link)
    db.commit()
    db.refresh(link)
    return static_pdf_path


async def generate_contract_pdf_from_mock_data(mock_data: dict, output_filename: str = "test_result.pdf") -> str:
    payload = {
        "contract_no": mock_data.get("contract_no", f"TEST-{datetime.now().strftime('%Y%m%d%H%M%S')}"),
        "supplier_name": mock_data.get("supplier_name", ""),
        "buyer_name": mock_data.get("buyer_name", "需方"),
        "project_no": mock_data.get("project_no", ""),
        "task_title": mock_data.get("task_title", "测试合同"),
        "items": mock_data.get("items", []),
        "total_amount": float(mock_data.get("total_amount", 0)),
    }
    output_pdf = CONTRACT_DIR / output_filename
    temp_xlsx = _fill_template_to_temp_excel(payload)
    try:
        _export_excel_to_pdf(temp_xlsx, output_pdf)
    finally:
        if temp_xlsx.exists():
            temp_xlsx.unlink()
    return str(output_pdf)
