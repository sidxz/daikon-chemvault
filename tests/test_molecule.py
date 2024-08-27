import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio(scope="session")
async def test_create_read_update_delete_molecule():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # Step 1: Create a molecule
        create_response = await ac.post(
            "/molecules/",
            json={"name": "Ethanol", "formula": "C2H5OH", "molecular_weight": "46.07"},
        )
        assert create_response.status_code == 200
        molecule_id = create_response.json()["id"]
        assert create_response.json()["name"] == "Ethanol"

        # Step 2: Read the created molecule
        read_response = await ac.get(f"/molecules/{molecule_id}")
        assert read_response.status_code == 200
        assert read_response.json()["name"] == "Ethanol"

        # Step 3: Update the molecule
        update_response = await ac.put(
            f"/molecules/{molecule_id}",
            json={"name": "Ethanol Updated", "formula": "C2H6O", "molecular_weight": "46.08"},
        )
        assert update_response.status_code == 200
        assert update_response.json()["name"] == "Ethanol Updated"

        # Verify the update
        read_updated_response = await ac.get(f"/molecules/{molecule_id}")
        assert read_updated_response.status_code == 200
        assert read_updated_response.json()["name"] == "Ethanol Updated"
        assert read_updated_response.json()["formula"] == "C2H6O"

        # Step 4: Delete the molecule
        delete_response = await ac.delete(f"/molecules/{molecule_id}")
        assert delete_response.status_code == 200

        # Verify the deletion
        verify_deletion_response = await ac.get(f"/molecules/{molecule_id}")
        assert verify_deletion_response.status_code == 404
