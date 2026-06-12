import sqlite3
import os
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app import models

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "saplingmove.db")


def column_exists(cursor, table_name, column_name):
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns


def migrate():
    print("开始数据库迁移：添加 received_quantity 字段...")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        if not column_exists(cursor, "plot_requirements", "received_quantity"):
            cursor.execute("""
                ALTER TABLE plot_requirements
                ADD COLUMN received_quantity INTEGER DEFAULT 0
            """)
            print("  ✓ 已添加 received_quantity 字段到 plot_requirements 表")
        else:
            print("  - received_quantity 字段已存在，跳过添加")

        conn.commit()

        print("\n开始初始化 received_quantity 数据（从已签收的调拨单汇总）...")
        db = SessionLocal()
        try:
            received_totals = db.query(
                models.AllocationRequest.plot_id,
                models.AllocationItem.spec_name,
                models.func.coalesce(
                    models.func.sum(models.AllocationItem.received_quantity), 0
                ).label("total_received"),
            ).join(
                models.AllocationItem,
                models.AllocationItem.allocation_id == models.AllocationRequest.id,
            ).filter(
                models.AllocationRequest.status == models.AllocationStatus.RECEIVED,
                models.AllocationItem.received_quantity > 0,
            ).group_by(
                models.AllocationRequest.plot_id,
                models.AllocationItem.spec_name,
            ).all()

            updated_count = 0
            for plot_id, spec_name, total_received in received_totals:
                req = db.query(models.PlotRequirement).filter(
                    models.PlotRequirement.plot_id == plot_id,
                    models.PlotRequirement.spec_name == spec_name,
                ).first()
                if req:
                    req.received_quantity = total_received
                    updated_count += 1
                    print(f"  ✓ 地块[{plot_id}] 规格[{spec_name}] 已签收 {total_received} 株")

            db.commit()
            print(f"\n  共更新 {updated_count} 条需苗计划的已签收数量")

            zero_count = db.query(models.PlotRequirement).filter(
                models.PlotRequirement.received_quantity.is_(None)
            ).update({"received_quantity": 0})
            if zero_count > 0:
                db.commit()
                print(f"  ✓ 已将 {zero_count} 条 NULL 值初始化为 0")

        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

        print("\n数据库迁移完成！")

    except Exception as e:
        conn.rollback()
        print(f"迁移失败: {e}")
        raise e
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
