from fastapi import APIRouter
from typing import List, Any
from datetime import datetime

from kingdee_getdata.login.session import session
from kingdee_getdata.getdata.GetPoData import get_po_data

router = APIRouter()


def build_warning_data(rows: List[List[Any]]):
    supplier_unreceived = []
    warehouse_unstockin = []

    for r in rows:
        project_number = r[0]
        supplier_id = r[1]
        material_id = r[2]
        material_name = r[3]
        qty = float(r[4])
        delivery_date = r[5]
        receive_qty = float(r[6])
        stockin_qty = float(r[8])

        # 核心逻辑
        unreceived_qty = max(0, qty - receive_qty)
        unstockin_qty = max(0, receive_qty - stockin_qty)

        base_info = {
            "project_number": project_number,
            "supplier_name": supplier_id,
            "material_id": material_id,
            "material_name": material_name,
            "delivery_date": delivery_date
        }

        if unreceived_qty > 0:
            supplier_unreceived.append({
                **base_info,
                "purchase_qty": qty,
                "received_qty": receive_qty,
                "warning_unreceived_qty": unreceived_qty
            })

        if unstockin_qty > 0:
            warehouse_unstockin.append({
                **base_info,
                "received_qty": receive_qty,
                "stockin_qty": stockin_qty,
                "warning_unstockin_qty": unstockin_qty
            })

    return supplier_unreceived, warehouse_unstockin


@router.get("/warning")
def warning():
    """
    采购预警接口：
    - 供应商未到货
    - 仓库未入库
    """
    session()
    rows = get_po_data()

    supplier_unreceived, warehouse_unstockin = build_warning_data(rows)

    return {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "supplier_unreceived": {
            "count": len(supplier_unreceived),
            "total_qty": sum(i["warning_unreceived_qty"] for i in supplier_unreceived),
            "list": supplier_unreceived
        },
        "warehouse_unstockin": {
            "count": len(warehouse_unstockin),
            "total_qty": sum(i["warning_unstockin_qty"] for i in warehouse_unstockin),
            "list": warehouse_unstockin
        }
    }
