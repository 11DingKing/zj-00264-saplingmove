from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/api/nurseries", tags=["苗圃管理"])


@router.get("", response_model=List[schemas.Nursery])
def list_nurseries(db: Session = Depends(get_db)):
    return db.query(models.Nursery).all()


@router.get("/{nursery_id}", response_model=schemas.Nursery)
def get_nursery(nursery_id: int, db: Session = Depends(get_db)):
    nursery = db.query(models.Nursery).filter(models.Nursery.id == nursery_id).first()
    if not nursery:
        raise HTTPException(status_code=404, detail="苗圃不存在")
    return nursery


@router.post("", response_model=schemas.Nursery)
def create_nursery(data: schemas.NurseryCreate, db: Session = Depends(get_db)):
    nursery = models.Nursery(**data.model_dump())
    db.add(nursery)
    db.commit()
    db.refresh(nursery)
    return nursery


@router.put("/{nursery_id}", response_model=schemas.Nursery)
def update_nursery(nursery_id: int, data: schemas.NurseryUpdate, db: Session = Depends(get_db)):
    nursery = db.query(models.Nursery).filter(models.Nursery.id == nursery_id).first()
    if not nursery:
        raise HTTPException(status_code=404, detail="苗圃不存在")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(nursery, key, value)
    db.commit()
    db.refresh(nursery)
    return nursery


@router.delete("/{nursery_id}")
def delete_nursery(nursery_id: int, db: Session = Depends(get_db)):
    nursery = db.query(models.Nursery).filter(models.Nursery.id == nursery_id).first()
    if not nursery:
        raise HTTPException(status_code=404, detail="苗圃不存在")
    db.delete(nursery)
    db.commit()
    return {"message": "删除成功"}


@router.get("/{nursery_id}/stocks", response_model=List[schemas.NurseryStock])
def list_nursery_stocks(nursery_id: int, db: Session = Depends(get_db)):
    nursery = db.query(models.Nursery).filter(models.Nursery.id == nursery_id).first()
    if not nursery:
        raise HTTPException(status_code=404, detail="苗圃不存在")
    return db.query(models.NurseryStock).filter(models.NurseryStock.nursery_id == nursery_id).all()


@router.post("/{nursery_id}/stocks", response_model=schemas.NurseryStock)
def create_nursery_stock(nursery_id: int, data: schemas.NurseryStockCreate, db: Session = Depends(get_db)):
    nursery = db.query(models.Nursery).filter(models.Nursery.id == nursery_id).first()
    if not nursery:
        raise HTTPException(status_code=404, detail="苗圃不存在")
    stock_data = data.model_dump()
    stock_data["nursery_id"] = nursery_id
    stock_data["available_stock"] = data.total_stock
    stock = models.NurseryStock(**stock_data)
    db.add(stock)
    db.commit()
    db.refresh(stock)
    return stock
