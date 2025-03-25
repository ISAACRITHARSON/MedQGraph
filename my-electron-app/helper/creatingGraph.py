import sys
import json
import os
import pandas as pd
from neo4j import GraphDatabase
from py2neo import Graph
import networkx as nx
import plotly.graph_objects as go

# Neo4j Connection Credentials
URI = ""  # Change if hosted elsewhere
USERNAME = "neo4j"
PASSWORD = ""

# Function to create nodes in Neo4j
def create_nodes(tx, row):
    # print(f"Inserting Node for Patient ID: {row['subject_id']}")  # Debugging
    query = """
    MERGE (p:Patient {subject_id: $subject_id})  
    MERGE (a:Admission {hadm_id: $hadm_id, admission_type: $admission_type})
    MERGE (d:Diagnosis {description: $description})
    MERGE (m:Medication {drug_name: $drug})
    MERGE (t:Test {test_name: $test_name})
    MERGE (s:Strength {prod_strength: $prod_strength})
    MERGE (r:Route {route: $route})
    MERGE (at:AdmissionType {admission_type: $admission_type})
    MERGE (al:Location {admission_location: $admission_location})
    MERGE (tr:TestResult {comments: $comments})
    MERGE (dm:MortalityRisk {drg_mortality: $drg_mortality})
    MERGE (ot:OrderType {order_type: $order_type})
    MERGE (ost:OrderSubType {order_subtype: $order_subtype})
    MERGE (i:Insurance {insurance: $insurance})
    MERGE (ms:MaritalStatus {marital_status: $marital_status})
    MERGE (demo:Demographics {race: $race, gender: $gender, age: $anchor_age})
    """
    tx.run(query, **row)

# Function to create relationships in Neo4j
def create_relationships(tx, row):
    # print(f"Creating relationships for Patient ID: {row['subject_id']}")  # Debugging
    query = """
    MATCH (p:Patient {subject_id: $subject_id})
    MATCH (a:Admission {hadm_id: $hadm_id})
    MATCH (d:Diagnosis {description: $description})
    MATCH (m:Medication {drug_name: $drug})
    MATCH (t:Test {test_name: $test_name})
    MATCH (s:Strength {prod_strength: $prod_strength})
    MATCH (r:Route {route: $route})
    MATCH (al:Location {admission_location: $admission_location})
    MATCH (tr:TestResult {comments: $comments})
    MATCH (dm:MortalityRisk {drg_mortality: $drg_mortality})
    MATCH (ot:OrderType {order_type: $order_type})
    MATCH (ost:OrderSubType {order_subtype: $order_subtype})
    MATCH (i:Insurance {insurance: $insurance})
    MATCH (ms:MaritalStatus {marital_status: $marital_status})
    MATCH (demo:Demographics {race: $race, gender: $gender, age: $anchor_age})

    MERGE (p)-[:HAS_ADMISSION]->(a)
    MERGE (p)-[:HAS_CONDITION]->(d)
    MERGE (p)-[:HAS_PRESCRIPTION]->(m)
    MERGE (p)-[:UNDERWENT_TEST]->(t)
    MERGE (p)-[:HAS_INSURANCE]->(i)
    MERGE (p)-[:HAS_MARITAL_STATUS]->(ms)
    MERGE (p)-[:HAS_DEMOGRAPHICS]->(demo)
    MERGE (p)-[:ADMITTED_FROM]->(al)
    MERGE (p)-[:HAS_ADMISSION_TYPE]->(at)
    MERGE (d)-[:TREATED_WITH]->(m)
    MERGE (d)-[:ASSOCIATED_WITH_ROUTE]->(r)
    MERGE (d)-[:REQUIRES_TEST]->(t)
    MERGE (m)-[:HAS_STRENGTH]->(s)
    MERGE (m)-[:HAS_MORTALITY_RISK]->(dm)
    MERGE (m)-[:ORDERED_UNDER]->(ot)
    MERGE (t)-[:HAS_RESULT]->(tr)
    MERGE (ot)-[:HAS_SUBTYPE]->(ost)
    """
    tx.run(query, **row)

def save_graph_state():
    """ Marks that the Knowledge Graph has been successfully created. """
    state = {"knowledge_graph_ready": True}
    with open("knowledge_graph_state.json", "w") as f:
        json.dump(state, f)

def process_csv_and_create_graph(file_path):
    if not os.path.exists(file_path):
        raise ValueError(f"File at {file_path} does not exist.")

    df = pd.read_csv(file_path, low_memory=False)
    df = df.fillna("Unknown")
    df = df.head(50)

    driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))
    
    with driver.session() as session:
        for _, row in df.iterrows():
            session.execute_write(create_nodes, row)
    
    with driver.session() as session:
        for _, row in df.iterrows():
            session.execute_write(create_relationships, row)

    # 🔹 Fetch Node & Relationship Count
    graph = Graph(URI, auth=(USERNAME, PASSWORD))
    node_count_query = "MATCH (n) RETURN count(n) AS node_count"
    rel_count_query = "MATCH ()-[r]->() RETURN count(r) AS rel_count"

    node_count = graph.run(node_count_query).evaluate()
    rel_count = graph.run(rel_count_query).evaluate()

    # 🔹 Generate Graph Visualization
    query = """
    MATCH (n)-[r]->(m)
    RETURN labels(n) AS from_type, 
        COALESCE(n.subject_id, n.hadm_id, n.description, n.drug_name, n.test_name, 
                    n.prod_strength, n.route, n.insurance, n.marital_status, 
                    n.order_type, n.order_subtype, "Unknown") AS from,
        type(r) AS relation, 
        labels(m) AS to_type, 
        COALESCE(m.subject_id, m.hadm_id, m.description, m.drug_name, m.test_name, 
                    m.prod_strength, m.route, m.insurance, m.marital_status, 
                    m.order_type, m.order_subtype, "Unknown") AS to
    LIMIT 1000
    """
    data = graph.run(query).data()

    filtered_data = [row for row in data if row["from"] != "Unknown" and row["to"] != "Unknown"]

    G = nx.DiGraph()
    for row in filtered_data:
        from_node = f"{row['from']} ({row['from_type'][0]})"
        to_node = f"{row['to']} ({row['to_type'][0]})"
        G.add_edge(from_node, to_node, label=row["relation"])

    pos = nx.spring_layout(G, dim=3, seed=42)
    node_x, node_y, node_z, node_labels = [], [], [], []
    for node, (x, y, z) in pos.items():
        node_x.append(x)
        node_y.append(y)
        node_z.append(z)
        node_labels.append(node)

    edge_x, edge_y, edge_z = [], [], []
    for edge in G.edges():
        x0, y0, z0 = pos[edge[0]]
        x1, y1, z1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
        edge_z.extend([z0, z1, None])

    edge_trace = go.Scatter3d(x=edge_x, y=edge_y, z=edge_z, line=dict(width=1.5, color="gray"), mode='lines')
    node_trace = go.Scatter3d(x=node_x, y=node_y, z=node_z, mode='markers+text',
                              marker=dict(size=6, color="blue", opacity=0.9), text=node_labels, hoverinfo='text')

    fig = go.Figure(data=[edge_trace, node_trace])
    fig.update_layout(title="3D Knowledge Graph", width=1000, height=800, dragmode="orbit")

    graph_html_path = os.path.join(os.getcwd(), "graph_output.html")
    fig.write_html(graph_html_path)

    sys.stdout.write(json.dumps({
        "graph_path": graph_html_path,
        "node_count": node_count,
        "rel_count": rel_count
    }))



if __name__ == "__main__":
    if len(sys.argv) > 1:
        csv_file_path = sys.argv[1]
        # print(f"Checking file path: {os.path.abspath(csv_file_path)}")  # Debugging
        process_csv_and_create_graph(csv_file_path)
    else:
        print("No file path provided")

