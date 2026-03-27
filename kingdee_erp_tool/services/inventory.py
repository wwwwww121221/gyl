import datetime
from kingdee_erp_tool.core.client import client

def get_purchase_order_data():
    """
    获取采购订单数据
    """
    now = datetime.datetime.now()
    now_str = now.strftime("%Y/%m/%d %H:%M:%S")
    future_time = now + datetime.timedelta(days=3)
    future_str = future_time.strftime("%Y/%m/%d %H:%M:%S")

    # 参数配置
    # 项目号F_XJPJ_BASE.FNUMBER、供应商名称FSUPPLIERID.FNAME、物料编码FMATERIALID.FNUMBER、物料名称FMATERIALNAME、采购数量FQTY、交货日期FDELIVERYDATE(大于现在时间、小于现在加三天）
    # 累计收料数量FRECEIVEQTY,剩余收料数量FREMAINRECEIVEQTY,累计入库数量FSTOCKINQTY,剩余入库数量FREMAINSTOCKINQTY
    para = {
        "FormId": "PUR_PurchaseOrder",
        "FieldKeys": "F_XJPJ_BASE.FNUMBER,FSUPPLIERID.FNAME,FMATERIALID.FNUMBER,FMATERIALNAME,FQTY,FDELIVERYDATE,FRECEIVEQTY,FREMAINRECEIVEQTY,FSTOCKINQTY,FREMAINSTOCKINQTY",
        "FilterString": [
            {"Left": "(", "FieldName": "FDELIVERYDATE", "Compare": ">=", "Value": now_str, "Right": ")", "Logic": "0"},
            {"Left": "(", "FieldName": "FDELIVERYDATE", "Compare": "<=", "Value": future_str, "Right": ")", "Logic": "0"},
            {"Left": "(", "FieldName": "FMRPCLOSESTATUS", "Compare": "=", "Value": "A", "Right": ")", "Logic": "0"}  # 业务关闭FMRPCLOSESTATUS(A正常、B业务关闭)
        ],
        "OrderString": "FDELIVERYDATE",
        "TopRowCount": 0,
        "StartRow": 0,
        "Limit": 1000,
        "SubSystemId": ""
    }

    # 使用 client 执行查询
    print(f"Executing query with params: {para}")
    return client.execute_query(para)

def process_warning_data(rows):
    """
    处理采购预警数据：供应商未到货 & 仓库未入库
    """
    supplier_unreceived = []
    warehouse_unstockin = []

    if not isinstance(rows, list):
        print(f"Warning: Expected list of rows, got {type(rows)}: {rows}")
        return [], []

    print(f"Processing {len(rows)} rows...")

    for r in rows:
        try:
            # Check if row is valid list
            if not isinstance(r, list) or len(r) < 9:
                print(f"Skipping invalid row: {r}")
                continue

            project_number = r[0]
            supplier_id = r[1]
            material_id = r[2]
            material_name = r[3]
            qty = float(r[4]) if r[4] is not None else 0.0
            delivery_date = r[5]
            receive_qty = float(r[6]) if r[6] is not None else 0.0
            # r[7] is FREMAINRECEIVEQTY
            stockin_qty = float(r[8]) if r[8] is not None else 0.0
            # r[9] is FREMAINSTOCKINQTY

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
        except Exception as e:
            print(f"Error processing row {r}: {e}")
            continue

    print(f"Found {len(supplier_unreceived)} unreceived items and {len(warehouse_unstockin)} unstockin items.")
    return supplier_unreceived, warehouse_unstockin

def get_inventory_warning_data():
    """
    获取并处理预警数据
    """
    rows = get_purchase_order_data()
    return process_warning_data(rows)
