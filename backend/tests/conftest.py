from collections.abc import Generator
from typing import cast

import pytest
from database import engine, get_db
from fastapi.testclient import TestClient
from main import app
from models.image import StoredImage
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession, AsyncTransaction


async def _begin_test_transaction() -> tuple[AsyncConnection, AsyncTransaction]:
    connection = await engine.connect()
    transaction = await connection.begin()
    await connection.execute(delete(StoredImage))
    return connection, transaction


async def _rollback_test_transaction(
    connection: AsyncConnection,
    transaction: AsyncTransaction,
) -> None:
    await transaction.rollback()
    await connection.close()


@pytest.fixture
def client() -> Generator[TestClient]:
    with TestClient(app) as test_client:
        assert test_client.portal is not None
        connection, transaction = test_client.portal.call(_begin_test_transaction)

        async def get_test_db():
            async with AsyncSession(
                bind=connection,
                expire_on_commit=False,
                join_transaction_mode="create_savepoint",
            ) as session:
                yield session

        app.dependency_overrides[get_db] = get_test_db
        test_client.app_state["db_connection"] = connection

        try:
            yield test_client
        finally:
            app.dependency_overrides.pop(get_db)
            test_client.portal.call(
                _rollback_test_transaction,
                connection,
                transaction,
            )


@pytest.fixture
def db_connection(client: TestClient) -> AsyncConnection:
    return cast(AsyncConnection, client.app_state["db_connection"])
