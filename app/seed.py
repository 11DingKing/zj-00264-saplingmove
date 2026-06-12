from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app import models
import sys

models.Base.metadata.create_all(bind=engine)


def seed_data(db: Session):
    n1 = models.Nursery(
        name="祁连山北麓中心苗圃",
        location="甘肃省张掖市甘州区龙渠乡",
        contact_person="王建国",
        contact_phone="13809361234",
        total_area=520.0,
    )
    n2 = models.Nursery(
        name="武威绿洲苗木繁育基地",
        location="甘肃省武威市凉州区高坝镇",
        contact_person="李秀英",
        contact_phone="13909355678",
        total_area=380.0,
    )
    n3 = models.Nursery(
        name="三北工程景泰县苗圃",
        location="甘肃省白银市景泰县一条山镇",
        contact_person="张发科",
        contact_phone="13709439012",
        total_area=450.0,
    )
    n4 = models.Nursery(
        name="临夏州云杉良种繁育场",
        location="甘肃省临夏州临夏县黄泥湾镇",
        contact_person="马文海",
        contact_phone="13609303456",
        total_area=280.0,
    )
    db.add_all([n1, n2, n3, n4])
    db.flush()

    stocks = [
        models.NurseryStock(nursery_id=n1.id, spec_name="青海云杉H30-50cm", height_cm=40, dbh_cm=1.2, crown_cm=30,
                            total_stock=850000, unit_price=3.5),
        models.NurseryStock(nursery_id=n1.id, spec_name="青海云杉H50-80cm", height_cm=65, dbh_cm=2.0, crown_cm=45,
                            total_stock=620000, unit_price=7.8),
        models.NurseryStock(nursery_id=n1.id, spec_name="青海云杉H80-120cm", height_cm=100, dbh_cm=3.5, crown_cm=65,
                            total_stock=380000, unit_price=15.0),
        models.NurseryStock(nursery_id=n1.id, spec_name="青海云杉H120-150cm", height_cm=135, dbh_cm=5.0, crown_cm=85,
                            total_stock=165000, unit_price=28.0),

        models.NurseryStock(nursery_id=n2.id, spec_name="青杄云杉H30-50cm", height_cm=40, dbh_cm=1.0, crown_cm=28,
                            total_stock=520000, unit_price=3.2),
        models.NurseryStock(nursery_id=n2.id, spec_name="青杄云杉H50-80cm", height_cm=65, dbh_cm=1.8, crown_cm=42,
                            total_stock=410000, unit_price=7.2),
        models.NurseryStock(nursery_id=n2.id, spec_name="青杄云杉H80-120cm", height_cm=100, dbh_cm=3.2, crown_cm=60,
                            total_stock=290000, unit_price=14.0),

        models.NurseryStock(nursery_id=n3.id, spec_name="青海云杉H30-50cm", height_cm=40, dbh_cm=1.1, crown_cm=30,
                            total_stock=720000, unit_price=3.3),
        models.NurseryStock(nursery_id=n3.id, spec_name="青海云杉H50-80cm", height_cm=65, dbh_cm=1.9, crown_cm=44,
                            total_stock=560000, unit_price=7.5),
        models.NurseryStock(nursery_id=n3.id, spec_name="祁连圆柏H40-60cm", height_cm=50, dbh_cm=1.5, crown_cm=35,
                            total_stock=310000, unit_price=6.0),
        models.NurseryStock(nursery_id=n3.id, spec_name="祁连圆柏H60-100cm", height_cm=80, dbh_cm=2.5, crown_cm=50,
                            total_stock=185000, unit_price=12.0),

        models.NurseryStock(nursery_id=n4.id, spec_name="紫果云杉H30-50cm", height_cm=40, dbh_cm=1.3, crown_cm=32,
                            total_stock=380000, unit_price=3.8),
        models.NurseryStock(nursery_id=n4.id, spec_name="紫果云杉H50-80cm", height_cm=65, dbh_cm=2.2, crown_cm=48,
                            total_stock=260000, unit_price=8.5),
        models.NurseryStock(nursery_id=n4.id, spec_name="紫果云杉H80-120cm", height_cm=100, dbh_cm=3.8, crown_cm=70,
                            total_stock=130000, unit_price=16.0),
    ]
    for s in stocks:
        s.available_stock = s.total_stock
        s.locked_stock = 0
    db.add_all(stocks)
    db.flush()

    total_stock = sum(s.total_stock for s in stocks)
    print(f"  苗圃苗木总数: {total_stock:,} 株")

    p1 = models.RestorationPlot(
        name="祁连山肃南县康乐乡封育造林区",
        project="祁连山生态修复工程",
        region="甘肃省张掖市肃南裕固族自治县",
        location="肃南县康乐乡赛鼎村、巴音村",
        area_mu=12500.0,
        site_condition="海拔2650-3100m，阴坡半阴坡，坡度15-25°，山地灰褐土，年降水量350-420mm，适合青海云杉、紫果云杉营造",
        planter="肃南县林业和草原局 赵学勇",
        contact_phone="13830680001",
    )
    p2 = models.RestorationPlot(
        name="祁连山中段寺大隆林场植被恢复区",
        project="祁连山生态修复工程",
        region="甘肃省张掖市肃南裕固族自治县",
        location="寺大隆林场西营河、东大河上游",
        area_mu=9800.0,
        site_condition="海拔2800-3300m，高山峡谷地带，坡地20-30°，高山草甸土向灰褐土过渡，年降水400-500mm",
        planter="寺大隆自然保护站 刘占军",
        contact_phone="13830680002",
    )
    p3 = models.RestorationPlot(
        name="三北工程古浪县八步沙沙区治理区",
        project="三北防护林六期工程",
        region="甘肃省武威市古浪县",
        location="古浪县八步沙、黑岗沙沙区前沿",
        area_mu=15600.0,
        site_condition="海拔1700-1900m，荒漠沙地，沙丘高度5-15m，风沙土，年降水150-200mm，固沙造林，选用耐寒耐旱品种",
        planter="古浪县八步沙林场 郭万刚",
        contact_phone="13884590003",
    )
    p4 = models.RestorationPlot(
        name="三北工程民勤县昌宁乡风沙口治理",
        project="三北防护林六期工程",
        region="甘肃省武威市民勤县",
        location="民勤县昌宁乡、西渠镇风沙沿线",
        area_mu=18200.0,
        site_condition="海拔1350-1500m，腾格里沙漠南缘，戈壁沙地，年降水110-150mm，需乔灌结合防风固沙",
        planter="民勤县治沙综合试验站 姜莉",
        contact_phone="13884590004",
    )
    p5 = models.RestorationPlot(
        name="景泰县上沙沃镇退耕还林工程",
        project="三北防护林六期工程",
        region="甘肃省白银市景泰县",
        location="景泰县上沙沃镇、草窝滩镇",
        area_mu=7200.0,
        site_condition="海拔1650-1850m，黄土丘陵缓坡地，淡灰钙土，年降水200-250mm，退耕地块造林",
        planter="景泰县自然资源局 周占军",
        contact_phone="13739360005",
    )
    db.add_all([p1, p2, p3, p4, p5])
    db.flush()

    reqs = [
        models.PlotRequirement(plot_id=p1.id, spec_name="青海云杉H50-80cm", required_quantity=450000,
                               remark="阴坡主栽品种，株行距2×3m"),
        models.PlotRequirement(plot_id=p1.id, spec_name="青海云杉H80-120cm", required_quantity=180000,
                               remark="道路两侧和景点周边绿化"),
        models.PlotRequirement(plot_id=p1.id, spec_name="紫果云杉H50-80cm", required_quantity=120000,
                               remark="高海拔阴坡地段混交"),

        models.PlotRequirement(plot_id=p2.id, spec_name="青海云杉H50-80cm", required_quantity=320000,
                               remark="中海拔造林区"),
        models.PlotRequirement(plot_id=p2.id, spec_name="青海云杉H80-120cm", required_quantity=150000,
                               remark="沟谷地带"),
        models.PlotRequirement(plot_id=p2.id, spec_name="紫果云杉H50-80cm", required_quantity=180000,
                               remark="高海拔区域主栽"),
        models.PlotRequirement(plot_id=p2.id, spec_name="祁连圆柏H40-60cm", required_quantity=90000,
                               remark="阳坡散点种植"),

        models.PlotRequirement(plot_id=p3.id, spec_name="青杄云杉H30-50cm", required_quantity=380000,
                               remark="固沙造林先锋树种，沙障内种植"),
        models.PlotRequirement(plot_id=p3.id, spec_name="青杄云杉H50-80cm", required_quantity=220000,
                               remark="绿洲外围防护带"),
        models.PlotRequirement(plot_id=p3.id, spec_name="祁连圆柏H40-60cm", required_quantity=160000,
                               remark="沙丘顶部配置"),

        models.PlotRequirement(plot_id=p4.id, spec_name="青杄云杉H30-50cm", required_quantity=520000,
                               remark="沙区主体造林"),
        models.PlotRequirement(plot_id=p4.id, spec_name="青海云杉H30-50cm", required_quantity=280000,
                               remark="水土条件较好的地块"),
        models.PlotRequirement(plot_id=p4.id, spec_name="祁连圆柏H40-60cm", required_quantity=210000,
                               remark="沙丘高位配置"),

        models.PlotRequirement(plot_id=p5.id, spec_name="青海云杉H50-80cm", required_quantity=180000,
                               remark="退耕地块主栽"),
        models.PlotRequirement(plot_id=p5.id, spec_name="青杄云杉H50-80cm", required_quantity=100000,
                               remark="搭配混交"),
        models.PlotRequirement(plot_id=p5.id, spec_name="祁连圆柏H40-60cm", required_quantity=80000,
                               remark="阳坡台地配置"),
    ]
    for r in reqs:
        r.received_quantity = 0
        r.planted_quantity = 0
    db.add_all(reqs)
    db.flush()

    total_req = sum(r.required_quantity for r in reqs)
    print(f"  修复地块需苗总数: {total_req:,} 株")

    db.commit()
    print("\n种子数据初始化完成:")
    print(f"  苗圃数量: 4 个")
    print(f"  苗木规格库存: {len(stocks)} 条, 合计 {total_stock:,} 株")
    print(f"  修复地块: {len([p1,p2,p3,p4,p5])} 个, 总面积 {sum([p1.area_mu,p2.area_mu,p3.area_mu,p4.area_mu,p5.area_mu]):,.0f} 亩")
    print(f"  需苗计划: {len(reqs)} 条, 合计 {total_req:,} 株")


def main():
    db = SessionLocal()
    try:
        existing_nursery = db.query(models.Nursery).first()
        if existing_nursery:
            print("数据库中已有数据，跳过种子初始化。如需重置请删除 saplingmove.db 文件后重试。")
            return
        print("开始初始化种子数据...")
        seed_data(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
