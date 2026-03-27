from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from typing import Any

from core import security
from core.config import settings
from models import get_db, User
from schemas import Token, UserCreate, User as UserSchema

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

@router.post("/login", response_model=Token)
def login_access_token(
    db: Session = Depends(get_db), 
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 兼容的 token 登录接口，获取 Access Token
    """
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="该账号未注册",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    # 检查供应商审核状态（在验证密码之前，或之后，但如果用户希望在没审核时提示没审核而不是密码错误，应该先检查审核状态）
    if user.role == "supplier":
        from models import Supplier
        supplier = db.query(Supplier).filter(Supplier.user_id == user.id).first()
        if not supplier:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Supplier profile not found.",
            )
        if supplier.status == "pending":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您的账号正在审核中，请耐心等待。",
            )
        if supplier.status == "rejected":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您的账号审核未通过或已被停用。",
            )
            
    if not security.verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # 增加 role 字段到 token payload 中
    access_token = security.create_access_token(
        subject=user.username, 
        expires_delta=access_token_expires,
        additional_claims={"role": user.role}
    )
    return {"access_token": access_token, "token_type": "bearer", "role": user.role}

@router.post("/register", response_model=UserSchema)
def register_user(
    *,
    db: Session = Depends(get_db),
    user_in: UserCreate,
) -> Any:
    """
    注册新用户
    """
    user = db.query(User).filter(User.username == user_in.username).first()
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this username already exists in the system.",
        )
    
    user = User(
        username=user_in.username,
        password_hash=security.get_password_hash(user_in.password),
        role=user_in.role
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # 如果是供应商注册，需要同步创建 Supplier 记录
    if user.role == "supplier":
        from models import Supplier
        # 提取注册时传入的额外信息
        supplier = Supplier(
            name=user_in.company_name or user.username, # 优先使用填写的公司名
            contact_person=user_in.contact_person,
            phone=user_in.phone,
            email=user_in.email,
            status="pending",   # 注册后默认为待审核
            user_id=user.id
        )
        db.add(supplier)
        db.commit()

    return user
