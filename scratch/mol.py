import datamol as dm
from chembl_structure_pipeline import standardizer
from rdkit import Chem
from chembl_structure_pipeline import checker
caffeine1_smiles = "Cn1c(=O)c2c(ncn2C)n(C)c1=O"
caffeine2_smiles = "CN1C=NC2=C1C(=O)N(C(=O)N2C)C"

# Convert the SMILES to an RDKit molecule using Datamol
mol1 = dm.to_mol(caffeine1_smiles)
mol2 = dm.to_mol(caffeine2_smiles)
print("1 SMILES:", dm.to_smiles(mol1))
print("2 SMILES:", dm.to_smiles(mol2))

#Convert the molecule to a molblock using Datamol
molblock1= dm.to_molblock(mol1)
molblock2= dm.to_molblock(mol2)

# # Standardize the molblock using ChEMBL's standardizer
# std_molblock = standardizer.standardize_molblock(molblock)
# print("Standardized Molblock:")
# #print(std_molblock)

# # Convert the standardized molblock back to an RDKit molecule
# #std_mol = Chem.MolFromMolBlock(std_molblock)
# std_mol = dm.read_molblock(std_molblock)
# # Convert the RDKit molecule to SMILES
# #std_smiles = Chem.MolToSmiles(std_mol)
# std_smiles = dm.to_smiles(std_mol)

# # Get parent molecule
# parent_molblock, _ = standardizer.get_parent_molblock(molblock)
# parent_mol = Chem.MolFromMolBlock(parent_molblock)
# parent_smiles = Chem.MolToSmiles(parent_mol)
# issues = checker.check_molblock(molblock)

# print("Initial - dm to mol smiles - std smiles - parent_smiles")
# print(caffeine_smiles)
# print(dm.to_smiles(mol))
# print(std_smiles)
# print(parent_smiles)

# print("Issues:")
# print(issues)
