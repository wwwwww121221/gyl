import json

from k3cloud_webapi_sdk.main import K3CloudApiSdk

from kingdee_getdata.login.login import execute_login_and_query

import os


def session():
    api_sdk = K3CloudApiSdk("http://erp.julan.com.cn:8081/k3cloud/")
    # 获取当前文件所在目录
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # conf.ini 在 kingdee_getdata 目录下
    config_path = os.path.abspath(os.path.join(base_dir, "..", "conf.ini"))

    api_sdk.Init(config_path=config_path, config_node="config")
    # 请求参数
    para =  {"NeedUpDateFields":[],"NeedReturnFields":[],"IsDeleteEntry":"true","SubSystemId":"","IsVerifyBaseDataField":"false","IsEntryBatchFill":"true","ValidateFlag":"true","NumberSearch":"true","IsAutoAdjustField":"false","InterationFlags":"","IgnoreInterationFlag":"","IsControlPrecision":"false","ValidateRepeatJson":"false","Model":{"FID":0,"FBillNo":"","FDate":"1900-01-01","FOrgID":{"FNumber":""},"FCostDeptID":{"FNUMBER":""},"FPhoneNumber":"","FReason":"","FStaffID":{"FSTAFFNUMBER":""},"FCostOrgID":{"FNumber":""},"FDeptID":{"FNUMBER":""},"FCurrencyID":{"FNUMBER":""},"FCreatorId":{"FUserID":""},"FCreateDate":"1900-01-01","FModifierId":{"FUserID":""},"FModifyDate":"1900-01-01","FAPPROVERID":{"FUserID":""},"FAPPROVEDATE":"1900-01-01","FBillTypeID":{"FNUMBER":""},"FEntity":[{"FENTRYID":0,"FExpenseItemID":{"FNUMBER":""},"FCostDeptIDEntry":{"FNUMBER":""},"FRemark":"","FPushReimbAmount":0,"FReimburseAmount":0,"FRequestAmount":0}]}}
    # 业务对象标识
    formId = "ER_ReasonsRequest"
    # 调用接口
    response = api_sdk.Save(formId, para)
    # print("接口返回结果：" + response)

    # 对返回结果进行解析和校验
    res = json.loads(response)
    msg_code = res.get('Result', {}).get('ResponseStatus', {}).get('MsgCode', '')
    if(msg_code=="1"):
        execute_login_and_query()
        print("正在重新登录")
    else:
        print("会话保持中")


