from rdkit.Chem import rdFingerprintGenerator
import datamol as dm

#print (dm.list_supported_fingerprints())
smiles = "CN1C=NC2=C1C(=O)N(C(=O)N2C)C"
mol = dm.to_mol(smiles)


fpgen = rdFingerprintGenerator.GetMorganGenerator(
                radius=4, includeChirality=True
            )
morgan_fp = fpgen.GetFingerprint(mol)
morgan_fp_hex = morgan_fp.ToBitString()
dm_fp = dm.to_fp(mol, as_array=False, radius=4, includeChirality=True)
dm_fp_rdkit = dm.to_fp(mol, as_array=False, fp_type="rdkit")

# print(morgan_fp_hex)
# print(dm_fp.ToBitString())
print(dm_fp_rdkit.ToBitString())