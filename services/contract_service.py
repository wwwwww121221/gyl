from datetime import datetime
from pathlib import Path
from decimal import Decimal

from openpyxl import load_workbook
from openpyxl.cell.cell import MergedCell
from sqlalchemy.orm import Session

from models import InquirySupplier, InquiryTask, InquiryTaskItem, InquiryRequest, Quotation, Supplier, LinkStatus


BASE_DIR = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = BASE_DIR / "static" / "templates"
CONTRACT_DIR = BASE_DIR / "static" / "contracts"


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


def _normalize_template_for_openpyxl(template_path: Path) -> Path:
    normalized_path = CONTRACT_DIR / "_normalized_template.xlsx"
    try:
        from win32com import client as win32
    except Exception as exc:
        raise RuntimeError("模板文件无法被 openpyxl 正常读取，且未检测到 pywin32") from exc

    excel = None
    workbook = None
    try:
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
    return normalized_path


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
    buyer_name = "需方"
    items = []
    total_amount = Decimal("0")

    for idx, q in enumerate(quotes, start=1):
        task_item = db.query(InquiryTaskItem).filter(InquiryTaskItem.id == q.item_id).first()
        req = db.query(InquiryRequest).filter(InquiryRequest.id == task_item.request_id).first() if task_item else None
        material_name = req.material_name if req else ""
        material_code = req.material_code if req else ""
        qty = _to_decimal(req.qty if req and req.qty is not None else q.qty)
        price = _to_decimal(q.price)
        amount = qty * price
        total_amount += amount

        if not project_no and req and req.project_info:
            project_no = str(req.project_info.get("number") or req.project_info.get("name") or "")

        items.append({
            "index": idx,
            "material_name": material_name,
            "material_code": material_code,
            "qty": float(qty),
            "price": float(price),
            "amount": float(amount),
        })

    return {
        "supplier_name": supplier.name,
        "buyer_name": buyer_name,
        "project_no": project_no,
        "task_title": task.title,
        "items": items,
        "total_amount": float(total_amount),
    }


def _fill_template_excel(payload: dict, output_xlsx: Path) -> None:
    template_path = _resolve_template_path()
    wb = load_workbook(template_path)
    if not wb.worksheets:
        normalized_template = _normalize_template_for_openpyxl(template_path)
        wb = load_workbook(normalized_template)
    if not wb.worksheets:
        raise ValueError("模板文件不包含可写工作表")
    ws = wb.active if wb.active else wb.worksheets[0]

    def set_cell_value(cell_ref: str, value):
        cell = ws[cell_ref]
        if isinstance(cell, MergedCell):
            for merged_range in ws.merged_cells.ranges:
                if cell_ref in merged_range:
                    ws.cell(row=merged_range.min_row, column=merged_range.min_col, value=value)
                    return
        ws[cell_ref] = value

    set_cell_value("C3", payload["supplier_name"])
    set_cell_value("C4", payload["buyer_name"])
    set_cell_value("C5", payload["project_no"] or payload["task_title"])
    set_cell_value("F5", datetime.now().strftime("%Y-%m-%d"))

    start_row = 8
    for i, item in enumerate(payload["items"]):
        row = start_row + i
        set_cell_value(f"A{row}", item["index"])
        set_cell_value(f"B{row}", item["material_name"])
        set_cell_value(f"C{row}", item["material_code"])
        set_cell_value(f"D{row}", item["qty"])
        set_cell_value(f"E{row}", item["price"])
        set_cell_value(f"F{row}", item["amount"])

    set_cell_value("F20", payload["total_amount"])

    output_xlsx.parent.mkdir(parents=True, exist_ok=True)
    wb.save(output_xlsx)


def _export_excel_to_pdf(xlsx_path: Path, output_pdf: Path) -> None:
    try:
        from win32com import client as win32
    except Exception as exc:
        raise RuntimeError("请先安装 pywin32，并在 Windows + Excel 环境下执行合同导出") from exc

    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    excel = None
    workbook = None
    try:
        excel = win32.DispatchEx("Excel.Application")
        excel.Visible = False
        excel.DisplayAlerts = False
        workbook = excel.Workbooks.Open(str(xlsx_path.resolve()))
        workbook.ExportAsFixedFormat(0, str(output_pdf.resolve()))
    finally:
        if workbook is not None:
            workbook.Close(False)
        if excel is not None:
            excel.Quit()


async def generate_contract_pdf(db: Session, inquiry_id: int) -> str:
    link = _resolve_deal_link(db, inquiry_id)
    payload = _collect_contract_payload(db, link)

    output_xlsx = CONTRACT_DIR / f"合同_{inquiry_id}.xlsx"
    output_pdf = CONTRACT_DIR / f"合同_{inquiry_id}.pdf"
    _fill_template_excel(payload, output_xlsx)
    _export_excel_to_pdf(output_xlsx, output_pdf)

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
        "supplier_name": mock_data.get("supplier_name", ""),
        "buyer_name": mock_data.get("buyer_name", "需方"),
        "project_no": mock_data.get("project_no", ""),
        "task_title": mock_data.get("task_title", "测试合同"),
        "items": mock_data.get("items", []),
        "total_amount": float(mock_data.get("total_amount", 0)),
    }
    output_pdf = CONTRACT_DIR / output_filename
    output_xlsx = CONTRACT_DIR / f"{output_pdf.stem}.xlsx"
    _fill_template_excel(payload, output_xlsx)
    _export_excel_to_pdf(output_xlsx, output_pdf)
    return str(output_pdf)
