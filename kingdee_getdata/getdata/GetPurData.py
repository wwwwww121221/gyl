import datetime
import json
import os

from k3cloud_webapi_sdk.main import K3CloudApiSdk

#获取采购订单数据
def get_pur_data():
    api_sdk = K3CloudApiSdk("http://erp.julan.com.cn:8081/k3cloud/")
    # 获取当前文件所在目录
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # conf.ini 在 kingdee_getdata 目录下
    config_path = os.path.abspath(os.path.join(base_dir, "..", "conf.ini"))

    api_sdk.Init(config_path=config_path, config_node="config")

    now = datetime.datetime.now()
    now_str = now.strftime("%Y/%m/%d %H:%M:%S")

    # 请求参数
    #单据类型FBILLTYPEID、项目号F_XJPJ_BASE3.FNUMBER、项目名称F_XJPJ.BASEPROPERTY1、物料编码FMATERIALID.FNUMBER、物料名称FMATERIALNAME、批准数量FAPPROVEQTY、交货日期FDELIVERYDATE
    #单据类型FBILLTYPEID、数据状态FDOCUMENTSTATUS、业务终止FMRPTERMINATESTATUS、订单关联数量FORDERJOINQTY、到货日期FARRIVALDATE
    para =  {"FormId":"PUR_Requisition","FieldKeys":"FBILLTYPEID,F_XJPJ_BASE3.FNUMBER,F_XJPJ_BASEPROPERTY1,FMATERIALID.FNUMBER,FMATERIALNAME,FAPPROVEQTY,FARRIVALDATE",
             "FilterString":[{"Left":"(","FieldName":"FBILLTYPEID","Compare":"=","Value":"93591469feb54ca2b08eb635f8b79de3","Right":")","Logic":"0"},
                             {"Left":"(","FieldName":"FDOCUMENTSTATUS","Compare":"=","Value":"C","Right":")","Logic":"0"},
                             {"Left":"(","FieldName":"FMRPTERMINATESTATUS","Compare":"=","Value":"A","Right":")","Logic":"0"},
                             {"Left":"(","FieldName":"FORDERJOINQTY","Compare":"=","Value":"0","Right":")","Logic":"0"},
                             {"Left":"(","FieldName":"FARRIVALDATE","Compare":">","Value":now_str,"Right":")","Logic":"0"}],"OrderString":"","TopRowCount":0,"StartRow":0,"Limit":2000,"SubSystemId":""}

    # 调用接口
    response = api_sdk.ExecuteBillQuery(para)
    #print("po接口返回结果：" + response)
    res = json.loads(response)
    return res

#get_pur_data()








