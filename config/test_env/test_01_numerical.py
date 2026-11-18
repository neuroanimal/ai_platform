
import numpy as np
import pandas as pd
import polars as pl

from scipy import linalg, stats

print("=== NUMPY ===")
A = np.array([[4.0, 2.0], [1.0, 3.0]])
b = np.array([10.0, 8.0])
x = np.linalg.solve(A, b)
print("Linear system:", x)
assert np.allclose(A @ x, b)

print("\n=== SCIPY ===")
eigenvalues = linalg.eigvals(A)
print("Eigenvalues:", eigenvalues)
slope, intercept, r, p, stderr = stats.linregress(
    [1, 2, 3, 4, 5],
    [2, 4, 6, 8, 10]
)
print("Regression:", slope, intercept, r)
assert np.isclose(slope, 2.0)

print("\n=== PANDAS ===")
df = pd.DataFrame({
    "category": ["A", "A", "B", "B"],
    "value": [10, 20, 30, 40]
})
print(df.groupby("category")["value"].mean())

print("\n=== POLARS ===")
pdf = pl.DataFrame({
    "category": ["A", "A", "B", "B"],
    "value": [10, 20, 30, 40]
})
print(pdf.group_by("category").agg(pl.col("value").mean()))

print("\n=== PARQUET ===")
df.to_parquet("/tmp/ai_platform_test.parquet")
loaded = pd.read_parquet("/tmp/ai_platform_test.parquet")
assert loaded.equals(df)
print("Parquet roundtrip: OK")

print("\nALL TESTS PASSED")

