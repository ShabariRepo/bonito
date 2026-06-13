import asyncio
from app.core.database import async_sessionmaker, engine
from sqlalchemy import text
async def main():
    S = async_sessionmaker(engine, expire_on_commit=False)
    async with S() as db:
        # every table with an org_id column (children to clear before org delete)
        tbls = (await db.execute(text(
            "select table_name from information_schema.columns "
            "where column_name='org_id' and table_schema='public'"))).scalars().all()
        oids = [str(o) for o in (await db.execute(text(
            "select id from organizations where name like 'htest-%'"))).scalars().all()]
        print("orgs:", len(oids), "| child tables:", len(tbls))
        for tbl in tbls:
            try:
                async with db.begin_nested():
                    await db.execute(text(f"delete from {tbl} where org_id = any(:ids)"), {"ids": oids})
            except Exception as e:
                print("  skip", tbl, str(e)[:40])
        # users may FK org without cascade and other tables reference users
        try:
            async with db.begin_nested():
                await db.execute(text("delete from users where org_id = any(:ids)"), {"ids": oids})
        except Exception as e:
            print("  users skip", str(e)[:40])
        rc = (await db.execute(text("delete from organizations where id = any(:ids)"), {"ids": oids})).rowcount
        await db.commit()
        left = (await db.execute(text("select count(*) from organizations where name like 'htest-%'"))).scalar()
        print(f"removed {rc} orgs; remaining htest: {left}")
asyncio.run(main())
