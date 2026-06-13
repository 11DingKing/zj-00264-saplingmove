from sqlalchemy.orm import Session
from fastapi import HTTPException
from typing import Optional

from app import models


class StockService:

    def __init__(self, db: Session):
        self.db = db

    def _get_stock(self, stock_id: int) -> models.NurseryStock:
        stock = self.db.query(models.NurseryStock).filter(
            models.NurseryStock.id == stock_id
        ).first()
        if not stock:
            raise HTTPException(status_code=400, detail=f"库存记录不存在(stock_id={stock_id})")
        return stock

    def _recalculate_available(self, stock: models.NurseryStock) -> None:
        stock.available_stock = stock.total_stock - stock.locked_stock

    def _safely_subtract(self, current: int, amount: int) -> int:
        return max(0, current - amount)

    def check_available(self, stock_id: int, quantity: int) -> models.NurseryStock:
        stock = self._get_stock(stock_id)
        if stock.available_stock < quantity:
            raise HTTPException(
                status_code=400,
                detail=f"规格[{stock.spec_name}]可用库存不足: 需{quantity}株, 仅剩{stock.available_stock}株"
            )
        return stock

    def lock_stock(self, stock_id: int, quantity: int) -> models.NurseryStock:
        if quantity <= 0:
            raise HTTPException(status_code=400, detail="锁定数量必须大于0")
        stock = self.check_available(stock_id, quantity)
        stock.locked_stock += quantity
        self._recalculate_available(stock)
        return stock

    def unlock_stock(self, stock_id: int, quantity: int) -> Optional[models.NurseryStock]:
        if quantity <= 0:
            return None
        stock = self._get_stock(stock_id)
        stock.locked_stock = self._safely_subtract(stock.locked_stock, quantity)
        self._recalculate_available(stock)
        return stock

    def consume_stock(self, stock_id: int, quantity: int) -> Optional[models.NurseryStock]:
        if quantity <= 0:
            return None
        stock = self._get_stock(stock_id)
        stock.locked_stock = self._safely_subtract(stock.locked_stock, quantity)
        stock.total_stock = self._safely_subtract(stock.total_stock, quantity)
        self._recalculate_available(stock)
        return stock

    def adjust_total_stock(self, stock_id: int, new_total: int) -> models.NurseryStock:
        stock = self._get_stock(stock_id)
        if new_total < stock.locked_stock:
            raise HTTPException(status_code=400, detail="总库存不能小于已锁定库存")
        stock.total_stock = new_total
        self._recalculate_available(stock)
        return stock

    def verify_consistency(self, stock_id: int) -> bool:
        stock = self._get_stock(stock_id)
        expected_available = stock.total_stock - stock.locked_stock
        return stock.available_stock == expected_available
