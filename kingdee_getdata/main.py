from fastapi import FastAPI
from kingdee_getdata.enquiry.enquiry import router as pur_router
from kingdee_getdata.warning.warning import router as warning_router

app = FastAPI(
    title="金蝶数据api系统",
    version="1.0",
    description="询价需求列表 & 供应商未到货 & 仓库未入库预警服务"
)

# 注册所有模块
app.include_router(pur_router)
app.include_router(warning_router)


@app.get("/")
def root():
    return {"msg": "金蝶数据获取服务已启动"}

#uvicorn kingdee_getdata.main:app --host 0.0.0.0 --port 8001 --reload

