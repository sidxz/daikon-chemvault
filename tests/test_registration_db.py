"""One molecule per structure, against a real Postgres with the RDKit cartridge.

Needs TEST_DATABASE_URL (postgresql+asyncpg://...) pointing at a disposable database: these tests
install the rdkit extension, migrate to head, write and delete molecules, and step the schema back
before the unique index and forward again.
"""
import asyncio
import os
import subprocess
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

import app.main  # noqa: F401  registers every ORM model, as the running app does
from app.repositories.molecule import SMILES_UNIQUE_INDEX
from app.schemas.molecule_dto import InputMoleculeDto
from app.services.molecule import batch_registration, registration
from app.utils.molecules.helper import standardize_smiles

TEST_DB = os.environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not TEST_DB, reason="set TEST_DATABASE_URL to a disposable RDKit Postgres")

engine = create_async_engine(TEST_DB) if TEST_DB else None
Session = sessionmaker(bind=engine, class_=AsyncSession, autoflush=False, expire_on_commit=False)
TAG = f"cv-test-{uuid.uuid4().hex[:8]}"  # names this run registers


def alembic(*args):
    env = {**os.environ, "DATABASE_URL": TEST_DB}
    subprocess.run([sys.executable, "-m", "alembic", *args], check=True, env=env, cwd=Path(__file__).parent.parent)


@pytest_asyncio.fixture(loop_scope="session", scope="module", autouse=True)
async def migrated():
    async with engine.begin() as conn:  # as docker-entrypoint.sh does: the schema uses the cartridge's types
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS rdkit"))
    alembic("upgrade", "head")


async def _sessions():
    # Stands in for batch_registration.get_db, whose engine is bound to the app's DATABASE_URL.
    async with Session() as session:
        yield session


def racing(fn, parties=2):
    """Wrap fn so its first `parties` calls wait for each other: every request has checked that the
    structure isn't registered yet before any of them inserts it."""
    barrier = asyncio.Barrier(parties)
    calls = 0

    async def wrapper(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls <= parties:
            await barrier.wait()
        return await fn(*args, **kwargs)

    return wrapper


def alcohol(carbons: int) -> str:
    return "C" * carbons + "O"  # each test registers its own structure


async def molecules_with(smiles):
    async with Session() as db:
        result = await db.execute(
            text("SELECT id, name, synonyms FROM molecules WHERE smiles_canonical = :smiles"),
            {"smiles": standardize_smiles(smiles)},
        )
        return result.all()


def names_of(row) -> set[str]:
    return {row.name, *filter(None, (row.synonyms or "").split(","))}


async def purge(smiles):
    async with Session() as db:
        await db.execute(text("DELETE FROM molecules WHERE smiles_canonical = :smiles"),
                         {"smiles": standardize_smiles(smiles)})
        await db.execute(text("DELETE FROM parent_molecules p WHERE p.name LIKE :tag AND NOT EXISTS "
                              "(SELECT 1 FROM molecules m WHERE m.parent_id = p.id)"), {"tag": f"{TAG}%"})
        await db.commit()


@pytest.mark.asyncio(loop_scope="session")
async def test_concurrent_registrations_of_one_structure_make_one_molecule(monkeypatch):
    smiles, names = alcohol(16), [f"{TAG}-a1", f"{TAG}-a2"]
    await purge(smiles)
    monkeypatch.setattr(registration.molecule_repo, "create_molecule",
                        racing(registration.molecule_repo.create_molecule))

    async def register(name):
        async with Session() as db:
            molecule, _ = await registration.register(InputMoleculeDto(name=name, smiles=smiles), db)
            return molecule.id

    try:
        ids = await asyncio.gather(*(register(name) for name in names))
        rows = await molecules_with(smiles)
        assert len(rows) == 1
        assert set(ids) == {rows[0].id}  # the request that lost the race gets the existing registration
        assert names_of(rows[0]) >= set(names)
    finally:
        await purge(smiles)


@pytest.mark.asyncio(loop_scope="session")
async def test_concurrent_batches_of_one_structure_make_one_molecule(monkeypatch):
    smiles, names = alcohol(17), [f"{TAG}-b1", f"{TAG}-b2"]
    await purge(smiles)
    monkeypatch.setattr(batch_registration, "get_db", _sessions)
    monkeypatch.setattr(batch_registration, "bulk_insert_molecules",
                        racing(batch_registration.bulk_insert_molecules))

    try:
        results = await asyncio.gather(*(
            batch_registration.register_molecules_batch([InputMoleculeDto(name=name, smiles=smiles)])
            for name in names
        ))
        rows = await molecules_with(smiles)
        assert len(rows) == 1
        assert {m.id for registered, _ in results for m in registered} == {rows[0].id}
        assert names_of(rows[0]) >= set(names)
    finally:
        await purge(smiles)


@pytest.mark.asyncio(loop_scope="session")
async def test_one_batch_with_one_structure_twice_makes_one_molecule(monkeypatch):
    smiles, names = alcohol(18), [f"{TAG}-c1", f"{TAG}-c2"]
    await purge(smiles)
    monkeypatch.setattr(batch_registration, "get_db", _sessions)

    try:
        registered, _ = await batch_registration.register_molecules_batch(
            [InputMoleculeDto(name=name, smiles=smiles) for name in names]
        )
        rows = await molecules_with(smiles)
        assert len(rows) == 1
        assert [m.id for m in registered] == [rows[0].id]
        assert names_of(rows[0]) >= set(names)
    finally:
        await purge(smiles)


@pytest.mark.asyncio(loop_scope="session")
async def test_migration_keeps_existing_duplicates_and_blocks_new_ones():
    smiles = alcohol(19)
    oldest, newer = uuid.uuid4(), uuid.uuid4()
    now = datetime.now(timezone.utc)

    async def insert(id_, created):
        async with Session() as db:
            await db.execute(text(
                "INSERT INTO molecules (id, name, smiles_canonical, _created_at, _updated_at) "
                "VALUES (:id, :name, :smiles, :created, :created)"
            ), {"id": id_, "name": f"{TAG}-{id_}", "smiles": standardize_smiles(smiles), "created": created})
            await db.commit()

    alembic("downgrade", "790324258c05")  # before the unique index, where duplicates could be inserted
    try:
        await insert(newer, now)
        await insert(oldest, now - timedelta(days=1))

        alembic("upgrade", "head")  # raises if the migration fails

        rows = await molecules_with(smiles)
        assert {row.id for row in rows} == {oldest, newer}  # nothing merged or deleted: DAIKON stores these IDs
        with pytest.raises(IntegrityError, match=SMILES_UNIQUE_INDEX):
            await insert(uuid.uuid4(), now)
    finally:
        await purge(smiles)
        alembic("downgrade", "790324258c05")  # recreate the index without this test's exemptions
        alembic("upgrade", "head")


@pytest.mark.asyncio(loop_scope="session")
async def test_concurrent_batches_with_structures_in_opposite_order_do_not_deadlock(monkeypatch):
    first, second = alcohol(20), alcohol(21)
    for smiles in (first, second):
        await purge(smiles)
    monkeypatch.setattr(batch_registration, "get_db", _sessions)
    monkeypatch.setattr(batch_registration, "bulk_insert_molecules",
                        racing(batch_registration.bulk_insert_molecules))

    try:
        await asyncio.gather(
            batch_registration.register_molecules_batch(
                [InputMoleculeDto(name=f"{TAG}-e1", smiles=first), InputMoleculeDto(name=f"{TAG}-e2", smiles=second)]
            ),
            batch_registration.register_molecules_batch(
                [InputMoleculeDto(name=f"{TAG}-e3", smiles=second), InputMoleculeDto(name=f"{TAG}-e4", smiles=first)]
            ),
        )
        rows_first, rows_second = await molecules_with(first), await molecules_with(second)
        assert len(rows_first) == len(rows_second) == 1
        assert names_of(rows_first[0]) >= {f"{TAG}-e1", f"{TAG}-e4"}
        assert names_of(rows_second[0]) >= {f"{TAG}-e2", f"{TAG}-e3"}
    finally:
        for smiles in (first, second):
            await purge(smiles)
