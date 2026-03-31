from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from core.config import settings
from routers import auth, erp_sync, inquiry, supplier, warning
from models import Base, engine
import traceback
import os
from models import SessionLocal, User
from core.security import get_password_hash

# 初始化数据库
# 注意：在生产环境中通常使用 Alembic 进行迁移，这里为了简单直接创建
Base.metadata.create_all(bind=engine)

def ensure_admin_user():
    username = os.getenv("ADMIN_USERNAME")
    password = os.getenv("ADMIN_PASSWORD")
    if not username or not password:
        return
    db = SessionLocal()
    try:
        exists = db.query(User).filter(User.username == username).first()
        if not exists:
            u = User(username=username, password_hash=get_password_hash(password), role="admin")
            db.add(u)
            db.commit()
    finally:
        db.close()

ensure_admin_user()

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Exception Handler Middleware
@app.middleware("http")
async def catch_exceptions_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        print(f"Unhandled exception: {e}")
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"detail": "Internal Server Error", "error": str(e)})

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # 生产环境请修改为前端域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["Auth"])
app.include_router(erp_sync.router, prefix=f"{settings.API_V1_STR}/erp", tags=["ERP"])
app.include_router(inquiry.router, prefix=f"{settings.API_V1_STR}/inquiry", tags=["Inquiry"])
app.include_router(supplier.router, prefix=f"{settings.API_V1_STR}/supplier", tags=["Supplier"])
app.include_router(warning.router, prefix=f"{settings.API_V1_STR}/warning", tags=["Warning"])

@app.get("/")
def root():
    return {"message": "Welcome to Supply Chain Agent API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
