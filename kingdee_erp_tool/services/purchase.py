import datetime
from kingdee_erp_tool.core.client import client

def get_purchase_requisition_data():
    """
    获取采购申请单数据
    """
    now = datetime.datetime.now()
    now_str = now.strftime("%Y/%m/%d %H:%M:%S")

    # 参数配置
    # 单据类型FBILLTYPEID、项目号F_XJPJ_BASE3.FNUMBER、项目名称F_XJPJ.BASEPROPERTY1、物料编码FMATERIALID.FNUMBER、物料名称FMATERIALNAME、批准数量FAPPROVEQTY、交货日期FARRIVALDATE、单据编号FBILLNO、创建日期FCREATEDATE
    para = {
        "FormId": "PUR_Requisition",
        "FieldKeys": "FBILLTYPEID,F_XJPJ_BASE3.FNUMBER,F_XJPJ_BASEPROPERTY1,FMATERIALID.FNUMBER,FMATERIALNAME,FAPPROVEQTY,FARRIVALDATE,FBILLNO,FCREATEDATE",
        "FilterString": [
            {"Left": "(", "FieldName": "FBILLTYPEID", "Compare": "=", "Value": "93591469feb54ca2b08eb635f8b79de3", "Right": ")", "Logic": "0"},
            {"Left": "(", "FieldName": "FDOCUMENTSTATUS", "Compare": "=", "Value": "C", "Right": ")", "Logic": "0"},
            {"Left": "(", "FieldName": "FMRPTERMINATESTATUS", "Compare": "=", "Value": "A", "Right": ")", "Logic": "0"},
            {"Left": "(", "FieldName": "FORDERJOINQTY", "Compare": "=", "Value": "0", "Right": ")", "Logic": "0"},
            {"Left": "(", "FieldName": "FARRIVALDATE", "Compare": ">", "Value": now_str, "Right": ")", "Logic": "0"}
        ],
        "OrderString": "",
        "TopRowCount": 0,
        "StartRow": 0,
        "Limit": 2000,
        "SubSystemId": ""
    }

    # 使用 client 执行查询
    return client.execute_query(para)

def process_purchase_data(rows):
    """
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
        bill_no = r[7] if len(r) > 7 else ""
        created_date = r[8] if len(r) > 8 else ""

        # 单据类型替换
        if bill_type_id == "93591469feb54ca2b08eb635f8b79de3":
            bill_type_id = "标准采购"

        item = {
            "bill_type": bill_type_id,
            "bill_no": bill_no,
            "project_number": project_number,
            "project_name": project_name,
            "material_id": material_id,
            "material_name": material_name,
            "purchase_qty": purchase_qty,
            "delivery_date": delivery_date,
            "created_date": created_date
        }

        result.append(item)

    return result

def get_processed_purchase_data():
    """
    获取并处理采购申请单数据
    """
    rows = get_purchase_requisition_data()
    return process_purchase_data(rows)
