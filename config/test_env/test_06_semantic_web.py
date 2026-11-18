
from rdflib import Graph, Namespace, RDF, RDFS, Literal, URIRef
from rdflib.namespace import XSD, SH
import tempfile
from pathlib import Path

EX = Namespace("https://example.org/")

print("\n=== RDFLIB + SPARQL ===")
g = Graph()
g.bind("ex", EX)

g.add((EX.Person, RDFS.subClassOf, EX.Agent))
g.add((EX.Alice, RDF.type, EX.Person))
g.add((EX.Alice, EX.name, Literal("Alice")))
g.add((EX.Alice, EX.age, Literal(31, datatype=XSD.integer)))

query = """
PREFIX ex: <https://example.org/>
SELECT ?name ?age
WHERE {
    ex:Alice ex:name ?name ;
             ex:age ?age .
}
"""
rows = list(g.query(query))
print("SPARQL:", [(str(r.name), int(r.age)) for r in rows])
assert len(rows) == 1 and int(rows[0].age) == 31

print("\n=== OWL-RL INFERENCE ===")
import owlrl

owlrl.DeductiveClosure(owlrl.OWLRL_Semantics).expand(g)
inferred = (EX.Alice, RDF.type, EX.Agent) in g
print("Inferred Alice is Agent:", inferred)
assert inferred

print("\n=== PYSHACL ===")
from pyshacl import validate

data_graph = Graph()
data_graph.add((EX.Bob, RDF.type, EX.Person))
data_graph.add((EX.Bob, EX.name, Literal("Bob")))

shapes_graph = Graph()
shapes_graph.bind("sh", SH)
shapes_graph.bind("ex", EX)

shape = EX.PersonShape
shapes_graph.add((shape, RDF.type, SH.NodeShape))
shapes_graph.add((shape, SH.targetClass, EX.Person))

name_property = URIRef(EX.PersonShape + "/name")
shapes_graph.add((shape, SH.property, name_property))
shapes_graph.add((name_property, SH.path, EX.name))
shapes_graph.add((name_property, SH.minCount, Literal(1)))
shapes_graph.add((name_property, SH.datatype, XSD.string))

conforms, report_graph, report_text = validate(
    data_graph,
    shacl_graph=shapes_graph,
    inference="none",
)
print("SHACL valid:", conforms)
assert conforms

# Sprawdzenie, czy walidator wykrywa brak wymaganego pola.
data_graph.remove((EX.Bob, EX.name, None))
conforms, _, report_text = validate(
    data_graph,
    shacl_graph=shapes_graph,
    inference="none",
)
print("SHACL detects missing name:", not conforms)
assert not conforms

print("\n=== PRONTO / OBO ONTOLOGY ===")
import pronto

obo = """format-version: 1.2
ontology: test

[Term]
id: TEST:0001
name: entity

[Term]
id: TEST:0002
name: person
is_a: TEST:0001 ! entity
"""

with tempfile.TemporaryDirectory() as tmp:
    obo_path = Path(tmp) / "test.obo"
    obo_path.write_text(obo, encoding="utf-8")

    ontology = pronto.Ontology(str(obo_path))
    term = ontology["TEST:0002"]
    print("OBO term:", term.id, term.name)
    assert term.name == "person"

print("\n=== SPARQLWRAPPER ===")
from SPARQLWrapper import SPARQLWrapper, JSON

wrapper = SPARQLWrapper("http://localhost:9999/sparql")
wrapper.setQuery(query)
wrapper.setReturnFormat(JSON)
print("SPARQL query configured:", "SELECT" in wrapper.queryString)
assert "SELECT" in wrapper.queryString

print("\n=== NEO4J DRIVER ===")
from neo4j import GraphDatabase

driver = GraphDatabase.driver(
    "bolt://localhost:7687",
    auth=("neo4j", "test"),
    connection_timeout=1,
)
print("Neo4j driver created:", driver is not None)
driver.close()

print("\nALL TESTS PASSED")

