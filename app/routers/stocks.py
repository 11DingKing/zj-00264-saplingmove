from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app import models, schemas
from app.services.stock_service import StockService

router = APIRouter(prefix="/api/stocks", tags=["苗木库存"])


@router.get("", response_model=List[schemas.NurseryStockWithNursery])
def list_stocks(spec_name: str = None, min_available: int = None, db: Session = Depends(get_db)):
    query = db.query(models.NurseryStock)
    if spec_name:
        query = query.filter(models.NurseryStock.spec_name.contains(spec_name))
    if min_available is not None:
        query = query.filter(models.NurseryStock.available_stock >= min_available)
    return query.all()


@router.get("/{stock_id}", response_model=schemas.NurseryStockWithNursery)
def get_stock(stock_id: int, db: Session = Depends(get_db)):
    stock = db.query(models.NurseryStock).filter(models.NurseryStock.id == stock_id).first()
    if not stock:
        raise HTTPException(status_code=404, detail="库存不存在")
    return stock


@router.put("/{stock_id}", response_model=schemas.NurseryStock)
def update_stock(stock_id: int, data: schemas.NurseryStockUpdate, db: Session = Depends(get_db)):
    stock = db.query(models.NurseryStock).filter(models.NurseryStock.id == stock_id).first()
    if not stock:
        raise HTTPException(status_code=404, detail="库存不存在")
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key != "total_stock":
            setattr(stock, key, value)
    if "total_stock" in update_data:
        stock_service = StockService(db)
        stock_service.adjust_total_stock(stock_id, update_data["total_stock"])
    db.commit()
    db.refresh(stock)
    return stock


@router.delete("/{stock_id}")
def delete_stock(stock_id: int, db: Session = Depends(get_db)):
    stock = db.query(models.NurseryStock).filter(models.NurseryStock.id == stock_id).first()
    if not stock:
        raise HTTPException(status_code=404, detail="库存不存在")
    if stock.locked_stock > 0:
        raise HTTPException(status_code=400, detail="存在锁定库存，无法删除")
    db.delete(stock)
    db.commit()
    return {"message": "删除成功"}
