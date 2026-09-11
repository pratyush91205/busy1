"""Business rule 2: the deployment check returns its row, or 404 when seeded
data is missing - never 200 with a null body."""

from __future__ import annotations

from fastapi.testclient import TestClient

# Asserted as a literal on purpose: the label is part of the seeded contract,
# so importing it from the migration would make the test agree with itself.
SEED_LABEL = "fleet-maintenance walking skeleton"


def test_returns_the_seeded_row(db_client: TestClient) -> None:
    response = db_client.get("/api/deployment-check")

    assert response.status_code == 200
    body = response.json()
    assert body["label"] == SEED_LABEL
    assert isinstance(body["id"], int)
    assert body["checked_at"]


def test_returns_404_naming_the_migration_when_the_table_is_empty(
    db_client: TestClient, empty_deployment_check: None
) -> None:
    response = db_client.get("/api/deployment-check")

    assert response.status_code == 404
    assert "0001_deployment_check" in response.json()["detail"]
