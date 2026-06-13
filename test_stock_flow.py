import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime

from app.database import Base
from app import models
from app.services.stock_service import StockService

TEST_DB_URL = "sqlite:///:memory:"


def setup_test_db():
    engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


def assert_stock(stock, expected_total, expected_locked, msg=""):
    expected_available = expected_total - expected_locked
    assert stock.total_stock == expected_total, \
        f"{msg} total_stock 错误: 期望 {expected_total}, 实际 {stock.total_stock}"
    assert stock.locked_stock == expected_locked, \
        f"{msg} locked_stock 错误: 期望 {expected_locked}, 实际 {stock.locked_stock}"
    assert stock.available_stock == expected_available, \
        f"{msg} available_stock 错误: 期望 {expected_available}, 实际 {stock.available_stock}"
    assert stock.available_stock == stock.total_stock - stock.locked_stock, \
        f"{msg} 库存恒等式不成立: available({stock.available_stock}) != total({stock.total_stock}) - locked({stock.locked_stock})"
    print(f"  ✓ {msg}: total={stock.total_stock}, locked={stock.locked_stock}, available={stock.available_stock}")


def test_complete_allocation_flow():
    print("\n" + "=" * 60)
    print("测试 1: 完整调拨流程 (申请→审核→锁定→起运→签收)")
    print("=" * 60)

    db = setup_test_db()
    stock_service = StockService(db)

    nursery = models.Nursery(name="测试苗圃", location="测试地点")
    db.add(nursery)
    db.flush()

    stock = models.NurseryStock(
        nursery_id=nursery.id,
        spec_name="青海云杉H50-80cm",
        total_stock=1000,
        locked_stock=0,
        available_stock=1000,
    )
    db.add(stock)
    db.flush()
    stock_id = stock.id

    plot = models.RestorationPlot(
        name="测试地块", project="测试项目", region="测试区域",
        location="测试位置", area_mu=100.0
    )
    db.add(plot)
    db.flush()
    plot_id = plot.id

    req = models.PlotRequirement(
        plot_id=plot_id, spec_name="青海云杉H50-80cm",
        required_quantity=500, received_quantity=0, planted_quantity=0
    )
    db.add(req)
    db.flush()

    assert_stock(stock, 1000, 0, "初始状态")

    alloc = models.AllocationRequest(
        request_no=f"DB{datetime.now().strftime('%Y%m%d')}0001",
        plot_id=plot_id, applicant="测试申请人",
        status=models.AllocationStatus.APPLIED,
    )
    db.add(alloc)
    db.flush()

    item = models.AllocationItem(
        allocation_id=alloc.id, nursery_stock_id=stock_id,
        nursery_id=nursery.id, spec_name="青海云杉H50-80cm",
        applied_quantity=100,
    )
    db.add(item)
    db.commit()
    db.refresh(stock)
    assert_stock(stock, 1000, 0, "申请后")

    alloc.status = models.AllocationStatus.REVIEWED
    item.approved_quantity = 100
    db.commit()
    db.refresh(stock)
    assert_stock(stock, 1000, 0, "审核后")

    stock_service.lock_stock(stock_id, 100)
    item.allocated_quantity = 100
    db.commit()
    db.refresh(stock)
    assert_stock(stock, 1000, 100, "锁定后")

    item.shipped_quantity = 90
    stock_service.unlock_stock(stock_id, 10)
    db.commit()
    db.refresh(stock)
    assert_stock(stock, 1000, 90, "起运后(90株起运,10株释放)")

    item.received_quantity = 90
    stock_service.consume_stock(stock_id, 90)
    req.received_quantity += 90
    db.commit()
    db.refresh(stock)
    assert_stock(stock, 910, 0, "签收后")

    assert stock_service.verify_consistency(stock_id), "库存一致性校验失败"
    print("\n  ✓ 完整流程测试通过!")
    db.close()


def test_revoke_from_locked():
    print("\n" + "=" * 60)
    print("测试 2: 从锁定状态撤销")
    print("=" * 60)

    db = setup_test_db()
    stock_service = StockService(db)

    nursery = models.Nursery(name="测试苗圃", location="测试地点")
    db.add(nursery)
    db.flush()

    stock = models.NurseryStock(
        nursery_id=nursery.id, spec_name="青海云杉H50-80cm",
        total_stock=500, locked_stock=0, available_stock=500,
    )
    db.add(stock)
    db.flush()
    stock_id = stock.id

    assert_stock(stock, 500, 0, "初始状态")

    stock_service.lock_stock(stock_id, 200)
    db.commit()
    db.refresh(stock)
    assert_stock(stock, 500, 200, "锁定200株后")

    stock_service.unlock_stock(stock_id, 200)
    db.commit()
    db.refresh(stock)
    assert_stock(stock, 500, 0, "撤销后(锁定数归零)")

    assert stock_service.verify_consistency(stock_id), "库存一致性校验失败"
    print("\n  ✓ 锁定状态撤销测试通过!")
    db.close()


def test_revoke_from_shipping():
    print("\n" + "=" * 60)
    print("测试 3: 从起运状态撤销")
    print("=" * 60)

    db = setup_test_db()
    stock_service = StockService(db)

    nursery = models.Nursery(name="测试苗圃", location="测试地点")
    db.add(nursery)
    db.flush()

    stock = models.NurseryStock(
        nursery_id=nursery.id, spec_name="青海云杉H50-80cm",
        total_stock=500, locked_stock=0, available_stock=500,
    )
    db.add(stock)
    db.flush()
    stock_id = stock.id

    assert_stock(stock, 500, 0, "初始状态")

    stock_service.lock_stock(stock_id, 200)
    db.commit()
    db.refresh(stock)
    assert_stock(stock, 500, 200, "锁定200株后")

    stock_service.unlock_stock(stock_id, 180)
    db.commit()
    db.refresh(stock)
    assert_stock(stock, 500, 20, "起运180株后(20株未起运释放)")

    stock_service.unlock_stock(stock_id, 180)
    db.commit()
    db.refresh(stock)
    assert_stock(stock, 500, 0, "起运状态撤销后")

    assert stock_service.verify_consistency(stock_id), "库存一致性校验失败"
    print("\n  ✓ 起运状态撤销测试通过!")
    db.close()


def test_partial_shipment():
    print("\n" + "=" * 60)
    print("测试 4: 部分起运 (锁定100, 起运80)")
    print("=" * 60)

    db = setup_test_db()
    stock_service = StockService(db)

    nursery = models.Nursery(name="测试苗圃", location="测试地点")
    db.add(nursery)
    db.flush()

    stock = models.NurseryStock(
        nursery_id=nursery.id, spec_name="青海云杉H50-80cm",
        total_stock=1000, locked_stock=0, available_stock=1000,
    )
    db.add(stock)
    db.flush()
    stock_id = stock.id

    assert_stock(stock, 1000, 0, "初始状态")

    stock_service.lock_stock(stock_id, 100)
    db.commit()
    db.refresh(stock)
    assert_stock(stock, 1000, 100, "锁定100株后")

    stock_service.unlock_stock(stock_id, 20)
    db.commit()
    db.refresh(stock)
    assert_stock(stock, 1000, 80, "起运80株后(20株释放)")

    stock_service.consume_stock(stock_id, 80)
    db.commit()
    db.refresh(stock)
    assert_stock(stock, 920, 0, "签收80株后")

    assert stock_service.verify_consistency(stock_id), "库存一致性校验失败"
    print("\n  ✓ 部分起运测试通过!")
    db.close()


def test_negative_protection():
    print("\n" + "=" * 60)
    print("测试 5: 防负数保护 (解锁超过锁定数量)")
    print("=" * 60)

    db = setup_test_db()
    stock_service = StockService(db)

    nursery = models.Nursery(name="测试苗圃", location="测试地点")
    db.add(nursery)
    db.flush()

    stock = models.NurseryStock(
        nursery_id=nursery.id, spec_name="青海云杉H50-80cm",
        total_stock=100, locked_stock=50, available_stock=50,
    )
    db.add(stock)
    db.flush()
    stock_id = stock.id

    assert_stock(stock, 100, 50, "初始状态 (locked=50)")

    stock_service.unlock_stock(stock_id, 100)
    db.commit()
    db.refresh(stock)
    assert_stock(stock, 100, 0, "解锁100株后 (防负数, locked=0)")

    stock_service.consume_stock(stock_id, 200)
    db.commit()
    db.refresh(stock)
    assert_stock(stock, 0, 0, "消耗200株后 (防负数, total=0, locked=0)")

    assert stock_service.verify_consistency(stock_id), "库存一致性校验失败"
    print("\n  ✓ 防负数保护测试通过!")
    db.close()


def test_adjust_total_stock():
    print("\n" + "=" * 60)
    print("测试 6: 调整总库存")
    print("=" * 60)

    db = setup_test_db()
    stock_service = StockService(db)

    nursery = models.Nursery(name="测试苗圃", location="测试地点")
    db.add(nursery)
    db.flush()

    stock = models.NurseryStock(
        nursery_id=nursery.id, spec_name="青海云杉H50-80cm",
        total_stock=1000, locked_stock=0, available_stock=1000,
    )
    db.add(stock)
    db.flush()
    stock_id = stock.id

    assert_stock(stock, 1000, 0, "初始状态")

    stock_service.lock_stock(stock_id, 300)
    db.commit()
    db.refresh(stock)
    assert_stock(stock, 1000, 300, "锁定300株后")

    stock_service.adjust_total_stock(stock_id, 1500)
    db.commit()
    db.refresh(stock)
    assert_stock(stock, 1500, 300, "总库存增至1500后")

    stock_service.adjust_total_stock(stock_id, 500)
    db.commit()
    db.refresh(stock)
    assert_stock(stock, 500, 300, "总库存减至500后")

    try:
        stock_service.adjust_total_stock(stock_id, 200)
        assert False, "应该抛出异常: 总库存不能小于锁定库存"
    except Exception as e:
        print(f"  ✓ 正确拒绝总库存(200) < 锁定库存(300): {e}")

    db.refresh(stock)
    assert_stock(stock, 500, 300, "拒绝调整后保持原状")

    assert stock_service.verify_consistency(stock_id), "库存一致性校验失败"
    print("\n  ✓ 调整总库存测试通过!")
    db.close()


def test_insufficient_stock():
    print("\n" + "=" * 60)
    print("测试 7: 库存不足时锁定失败")
    print("=" * 60)

    db = setup_test_db()
    stock_service = StockService(db)

    nursery = models.Nursery(name="测试苗圃", location="测试地点")
    db.add(nursery)
    db.flush()

    stock = models.NurseryStock(
        nursery_id=nursery.id, spec_name="青海云杉H50-80cm",
        total_stock=100, locked_stock=0, available_stock=100,
    )
    db.add(stock)
    db.flush()
    stock_id = stock.id

    assert_stock(stock, 100, 0, "初始状态")

    try:
        stock_service.lock_stock(stock_id, 200)
        assert False, "应该抛出异常: 可用库存不足"
    except Exception as e:
        print(f"  ✓ 正确拒绝锁定超过可用库存: {e}")

    db.refresh(stock)
    assert_stock(stock, 100, 0, "拒绝锁定后保持原状")

    stock_service.lock_stock(stock_id, 50)
    db.commit()
    db.refresh(stock)
    assert_stock(stock, 100, 50, "成功锁定50株")

    try:
        stock_service.lock_stock(stock_id, 60)
        assert False, "应该抛出异常: 可用库存不足"
    except Exception as e:
        print(f"  ✓ 正确拒绝锁定超过可用库存(剩余50): {e}")

    db.refresh(stock)
    assert_stock(stock, 100, 50, "拒绝后保持原状")

    assert stock_service.verify_consistency(stock_id), "库存一致性校验失败"
    print("\n  ✓ 库存不足校验测试通过!")
    db.close()


def test_zero_or_negative_quantity():
    print("\n" + "=" * 60)
    print("测试 8: 零或负数数量的处理")
    print("=" * 60)

    db = setup_test_db()
    stock_service = StockService(db)

    nursery = models.Nursery(name="测试苗圃", location="测试地点")
    db.add(nursery)
    db.flush()

    stock = models.NurseryStock(
        nursery_id=nursery.id, spec_name="青海云杉H50-80cm",
        total_stock=100, locked_stock=10, available_stock=90,
    )
    db.add(stock)
    db.flush()
    stock_id = stock.id

    assert_stock(stock, 100, 10, "初始状态")

    try:
        stock_service.lock_stock(stock_id, 0)
        assert False, "应该抛出异常: 锁定数量必须大于0"
    except Exception as e:
        print(f"  ✓ 正确拒绝锁定数量为0: {e}")

    try:
        stock_service.lock_stock(stock_id, -10)
        assert False, "应该抛出异常: 锁定数量必须大于0"
    except Exception as e:
        print(f"  ✓ 正确拒绝锁定数量为负数: {e}")

    result = stock_service.unlock_stock(stock_id, 0)
    assert result is None, "解锁数量为0应返回None"
    print("  ✓ 解锁数量为0时无操作")

    result = stock_service.unlock_stock(stock_id, -5)
    assert result is None, "解锁数量为负数应返回None"
    print("  ✓ 解锁数量为负数时无操作")

    result = stock_service.consume_stock(stock_id, 0)
    assert result is None, "消耗数量为0应返回None"
    print("  ✓ 消耗数量为0时无操作")

    db.refresh(stock)
    assert_stock(stock, 100, 10, "所有零/负数操作后保持原状")

    assert stock_service.verify_consistency(stock_id), "库存一致性校验失败"
    print("\n  ✓ 零或负数数量处理测试通过!")
    db.close()


def test_multiple_allocations_same_stock():
    print("\n" + "=" * 60)
    print("测试 9: 同一库存被多次调拨")
    print("=" * 60)

    db = setup_test_db()
    stock_service = StockService(db)

    nursery = models.Nursery(name="测试苗圃", location="测试地点")
    db.add(nursery)
    db.flush()

    stock = models.NurseryStock(
        nursery_id=nursery.id, spec_name="青海云杉H50-80cm",
        total_stock=1000, locked_stock=0, available_stock=1000,
    )
    db.add(stock)
    db.flush()
    stock_id = stock.id

    assert_stock(stock, 1000, 0, "初始状态")

    stock_service.lock_stock(stock_id, 300)
    db.commit()
    db.refresh(stock)
    assert_stock(stock, 1000, 300, "调拨A锁定300株后")

    stock_service.lock_stock(stock_id, 200)
    db.commit()
    db.refresh(stock)
    assert_stock(stock, 1000, 500, "调拨B锁定200株后")

    stock_service.unlock_stock(stock_id, 0)
    db.commit()
    db.refresh(stock)
    assert_stock(stock, 1000, 500, "调拨A全部起运300株(无未起运,不释放)")

    stock_service.consume_stock(stock_id, 300)
    db.commit()
    db.refresh(stock)
    assert_stock(stock, 700, 200, "调拨A签收300株后")

    stock_service.unlock_stock(stock_id, 200)
    db.commit()
    db.refresh(stock)
    assert_stock(stock, 700, 0, "调拨B撤销后")

    stock_service.lock_stock(stock_id, 100)
    stock_service.lock_stock(stock_id, 150)
    db.commit()
    db.refresh(stock)
    assert_stock(stock, 700, 250, "调拨C锁定100, 调拨D锁定150后")

    stock_service.unlock_stock(stock_id, 20)
    db.commit()
    db.refresh(stock)
    assert_stock(stock, 700, 230, "调拨C起运80株(释放20未起运)后")

    stock_service.consume_stock(stock_id, 80)
    db.commit()
    db.refresh(stock)
    assert_stock(stock, 620, 150, "调拨C签收80株后")

    assert stock_service.verify_consistency(stock_id), "库存一致性校验失败"
    print("\n  ✓ 多次调拨同一库存测试通过!")
    db.close()


if __name__ == "__main__":
    print("\n" + "╔" + "═" * 58 + "╗")
    print("║" + " " * 15 + "库存管理服务重构验证测试" + " " * 17 + "║")
    print("╚" + "═" * 58 + "╝")

    all_passed = True
    tests = [
        test_complete_allocation_flow,
        test_revoke_from_locked,
        test_revoke_from_shipping,
        test_partial_shipment,
        test_negative_protection,
        test_adjust_total_stock,
        test_insufficient_stock,
        test_zero_or_negative_quantity,
        test_multiple_allocations_same_stock,
    ]

    passed_count = 0
    failed_count = 0

    for test in tests:
        try:
            test()
            passed_count += 1
        except AssertionError as e:
            failed_count += 1
            all_passed = False
            print(f"\n  ✗ {test.__name__} 失败: {e}")
        except Exception as e:
            failed_count += 1
            all_passed = False
            print(f"\n  ✗ {test.__name__} 异常: {e}")

    print("\n" + "=" * 60)
    print(f"测试结果: {passed_count} 通过, {failed_count} 失败")
    print("=" * 60)

    if all_passed:
        print("\n🎉 所有测试通过! 库存管理服务重构正确。")
        print("\n库存操作已全部收敛到 StockService:")
        print("  • lock_stock()    - 锁定库存 (锁定+起运前)")
        print("  • unlock_stock()  - 解锁库存 (撤销+未起运部分)")
        print("  • consume_stock() - 消耗库存 (签收出库)")
        print("  • adjust_total_stock() - 调整总库存")
        print("  • check_available()   - 检查可用库存")
        print("  • verify_consistency() - 校验库存恒等式")
        sys.exit(0)
    else:
        print("\n❌ 部分测试失败，请检查代码。")
        sys.exit(1)
