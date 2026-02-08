# AI Platform - Julia Dependencies
# Install with: julia install_julia_packages.jl

using Pkg

# Data Manipulation
Pkg.add("DataFrames")
Pkg.add("CSV")
Pkg.add("Query")

# Visualization
Pkg.add("Plots")
Pkg.add("Gadfly")
Pkg.add("Makie")

# Machine Learning
Pkg.add("MLJ")
Pkg.add("Flux")
Pkg.add("ScikitLearn")

# Scientific Computing
Pkg.add("DifferentialEquations")
Pkg.add("Optim")
Pkg.add("JuMP")

# Python Integration
Pkg.add("PyCall")
