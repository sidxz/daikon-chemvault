import datamol as dm
from chembl_structure_pipeline import standardizer
from rdkit import Chem
from chembl_structure_pipeline import checker
caffeine_smiles = "CN1C=NC2=C1C(=O)N(C(=O)N2C)C"

# Convert the SMILES to an RDKit molecule using Datamol
mol = dm.to_mol(caffeine_smiles)
print("Original SMILES:", dm.to_smiles(mol))

# Convert the molecule to a molblock using Datamol
molblock = dm.to_molblock(mol)
print("Molblock before standardization:")
#print(molblock)

# Standardize the molblock using ChEMBL's standardizer
std_molblock = standardizer.standardize_molblock(molblock)
print("Standardized Molblock:")
#print(std_molblock)

# Convert the standardized molblock back to an RDKit molecule
#std_mol = Chem.MolFromMolBlock(std_molblock)
std_mol = dm.read_molblock(std_molblock)
# Convert the RDKit molecule to SMILES
#std_smiles = Chem.MolToSmiles(std_mol)
std_smiles = dm.to_smiles(std_mol)

# Get parent molecule
parent_molblock, _ = standardizer.get_parent_molblock(molblock)
parent_mol = Chem.MolFromMolBlock(parent_molblock)
parent_smiles = Chem.MolToSmiles(parent_mol)
issues = checker.check_molblock(molblock)

print("Initial - dm to mol smiles - std smiles - parent_smiles")
print(caffeine_smiles)
print(dm.to_smiles(mol))
print(std_smiles)
print(parent_smiles)

print("Issues:")
print(issues)
