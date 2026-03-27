import datetime
import json
import os

from k3cloud_webapi_sdk.main import K3CloudApiSdk

#获取采购订单数据
def get_po_data():
    api_sdk = K3CloudApiSdk("http://erp.julan.com.cn:8081/k3cloud/")
    # 获取当前文件所在目录
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # conf.ini 在 kingdee_getdata 目录下
    config_path = os.path.abspath(os.path.join(base_dir, "..", "conf.ini"))

    api_sdk.Init(config_path=config_path, config_node="config")

    now = datetime.datetime.now()
    now_str = now.strftime("%Y/%m/%d %H:%M:%S")
    future_time = now + datetime.timedelta(days=3)
    future_str = future_time.strftime("%Y/%m/%d %H:%M:%S")

    # 请求参数
    #项目号F_XJPJ_BASE.FNUMBER、供应商名称FSUPPLIERID.FNAME、物料编码FMATERIALID.FNUMBER、物料名称FMATERIALNAME、采购数量FQTY、交货日期FDELIVERYDATE(大于现在时间、小于现在加三天）
    #累计收料数量FRECEIVEQTY,剩余收料数量FREMAINRECEIVEQTY,累计入库数量FSTOCKINQTY,剩余入库数量FREMAINSTOCKINQTY
    para =  {"FormId":"PUR_PurchaseOrder","FieldKeys":"F_XJPJ_BASE.FNUMBER,FSUPPLIERID.FNAME,FMATERIALID.FNUMBER,FMATERIALNAME,FQTY,FDELIVERYDATE,FRECEIVEQTY,FREMAINRECEIVEQTY,FSTOCKINQTY,FREMAINSTOCKINQTY",
             "FilterString":[{"Left":"(","FieldName":"FDELIVERYDATE","Compare":">=","Value":now_str,"Right":")","Logic":"0"},
                             {"Left":"(","FieldName":"FDELIVERYDATE","Compare":"<=","Value":future_str,"Right":")","Logic":"0"},
                             {"Left":"(","FieldName":"FMRPCLOSESTATUS","Compare":"=","Value":"A","Right":")","Logic":"0"}],#业务关闭FMRPCLOSESTATUS(A正常、B业务关闭)
             "OrderString":"FDELIVERYDATE","TopRowCount":0,"StartRow":0,"Limit":1000,"SubSystemId":""}
    # 调用接口
    response = api_sdk.ExecuteBillQuery(para)
    #print("po接口返回结果：" + response)
    res = json.loads(response)
    return res

#get_po_data()








