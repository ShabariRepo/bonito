import asyncio, json, sys, uuid
from app.core.database import async_sessionmaker, engine
from app.models.organization import Organization
from app.models.cloud_provider import CloudProvider
from app.services import auth_service

N = int(sys.argv[1]) if len(sys.argv) > 1 else 3
PW = "HkTest!2026xQ"


async def main():
    S = async_sessionmaker(engine, expire_on_commit=False)
    out = []
    async with S() as db:
        for _ in range(N):
            tag = f"htest-{uuid.uuid4().hex[:8]}"
            org = Organization(name=f"{tag}-org", subscription_tier="enterprise")
            db.add(org)
            await db.flush()
            email = f"{tag}@htestsim.com"          # valid, non-reserved TLD
            user = await auth_service.create_user(db, email, PW, tag, org.id, role="admin")
            user.email_verified = True
            # managed Anthropic provider (uses BONITO_ANTHROPIC_MASTER_KEY) so
            # agent builds have a model to back them — like a real onboarded org
            db.add(CloudProvider(org_id=org.id, provider_type="anthropic",
                                 is_managed=True, status="active"))
            await db.flush()
            out.append({"tag": tag, "org_id": str(org.id), "email": email, "password": PW})
        await db.commit()
    print("PROV_JSON_START")
    print(json.dumps(out))
    print("PROV_JSON_END")

asyncio.run(main())
