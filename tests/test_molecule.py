import pytest
from httpx import AsyncClient
from app.main import app

# @pytest.mark.asyncio
# async def test_create_molecule():
#     async with AsyncClient(app=app, base_url="http://test") as ac:
#         response = await ac.post("/molecules/", json={"name": "Water", "formula": "H2O", "molecular_weight": "18.015"})
#     assert response.status_code == 200
#     assert response.json()["name"] == "Water"

# @pytest.mark.asyncio
# async def test_read_molecule():
#     async with AsyncClient(app=app, base_url="http://test") as ac:
#         # First create a molecule to read
#         create_response = await ac.post("/molecules/", json={"name": "Methane", "formula": "CH4", "molecular_weight": "16.04"})
#         assert create_response.status_code == 200
#         molecule_id = create_response.json()["id"]
        
#         # Now read the molecule
#         response = await ac.get(f"/molecules/{molecule_id}")
#     assert response.status_code == 200
#     assert response.json()["name"] == "Methane"

@pytest.mark.asyncio
async def test_update_molecule():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # First create a molecule to update
        create_response = await ac.post("/molecules/", json={"name": "Ethanol", "formula": "C2H5OH", "molecular_weight": "46.07"})
        assert create_response.status_code == 200
        molecule_id = create_response.json()["id"]
        
        # Now update the molecule
        response = await ac.put(f"/molecules/{molecule_id}", json={"name": "Ethanol", "formula": "C2H6O", "molecular_weight": "46.07"})
    assert response.status_code == 200
    assert response.json()["formula"] == "C2H6O"

# @pytest.mark.asyncio
# async def test_delete_molecule():
#     async with AsyncClient(app=app, base_url="http://test") as ac:
#         # First create a molecule to delete
#         create_response = await ac.post("/molecules/", json={"name": "Acetone", "formula": "C3H6O", "molecular_weight": "58.08"})
#         assert create_response.status_code == 200
#         molecule_id = create_response.json()["id"]
        
#         # Now delete the molecule
#         response = await ac.delete(f"/molecules/{molecule_id}")
#     assert response.status_code == 204

#     # Verify that the molecule was deleted
#     get_response = await ac.get(f"/molecules/{molecule_id}")
#     assert get_response.status_code == 404
