import datetime

from fastapi import APIRouter

from kingdee_getdata.login.session import session
from kingdee_getdata.getdata.GetPurData import get_pur_data

router = APIRouter()


def build_pur_data(rows):
    """
    中间函数：
    将原始二维数组处理成结构化字典列表
    """
    result = []

    for r in rows:
        bill_type_id = r[0] if len(r) > 0 else ""
        project_number = r[1] if len(r) > 1 else ""
        project_name = r[2] if len(r) > 2 else ""
        material_id = r[3] if len(r) > 3 else ""
        material_name = r[4] if len(r) > 4 else ""
        purchase_qty = float(r[5]) if len(r) > 5 and r[5] is not None else 0.0
        delivery_date = r[6] if len(r) > 6 else ""

        # 单据类型替换
        if bill_type_id == "93591469feb54ca2b08eb635f8b79de3":
            bill_type_id = "标准采购"

        item = {
            "bill_type": bill_type_id,
            "project_number": project_number,
            "project_name": project_name,
            "material_id": material_id,
            "material_name": material_name,
            "purchase_qty": purchase_qty,
            "delivery_date": delivery_date
        }

        result.append(item)

    return result


@router.get("/pur")
def pur():
    """
    采购申请单数据接口
    直接调用 get_pur_data() 获取原始数据并返回
    """
    session()
    rows = get_pur_data()
    data = build_pur_data(rows)

    return {
        "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "count": len(data),
        "total_purchase_qty": sum(item["purchase_qty"] for item in data),
        "list": data
    }