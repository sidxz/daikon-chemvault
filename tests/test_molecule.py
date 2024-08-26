import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

@pytest.fixture
def create_molecule():
    response = client.post("/molecules/", json={"name": "Water", "formula": "H2O", "molecular_weight": "18.015"})
    assert response.status_code == 200
    return response.json()["id"]  # Return the molecule ID for use in other tests

def test_create_molecule():
    response = client.post("/molecules/", json={"name": "Water", "formula": "H2O", "molecular_weight": "18.015"})
    assert response.status_code == 200
    assert response.json()["name"] == "Water"
    assert response.json()["formula"] == "H2O"
    assert response.json()["molecular_weight"] == "18.015"

def test_read_molecule(create_molecule):
    molecule_id = create_molecule
    response = client.get(f"/molecules/{molecule_id}")
    assert response.status_code == 200
    assert response.json()["id"] == molecule_id
    assert response.json()["name"] == "Water"
    assert response.json()["formula"] == "H2O"
    assert response.json()["molecular_weight"] == "18.015"

def test_update_molecule(create_molecule):
    molecule_id = create_molecule
    update_data = {"name": "Updated Water", "formula": "D2O", "molecular_weight": "20.027"}
    response = client.put(f"/molecules/{molecule_id}", json=update_data)
    assert response.status_code == 200
    assert response.json()["id"] == molecule_id
    assert response.json()["name"] == "Updated Water"
    assert response.json()["formula"] == "D2O"
    assert response.json()["molecular_weight"] == "20.027"

    # Verify the update
    response = client.get(f"/molecules/{molecule_id}")
    assert response.status_code == 200
    assert response.json()["id"] == molecule_id
    assert response.json()["name"] == "Updated Water"
    assert response.json()["formula"] == "D2O"
    assert response.json()["molecular_weight"] == "20.027"

def test_delete_molecule(create_molecule):
    molecule_id = create_molecule
    response = client.delete(f"/molecules/{molecule_id}")
    assert response.status_code == 200
    assert response.json() == {"detail": "Molecule deleted"}

    # Verify the molecule has been deleted
    response = client.get(f"/molecules/{molecule_id}")
    assert response.status_code == 404
    assert response.json() == {"detail": "Molecule not found"}
