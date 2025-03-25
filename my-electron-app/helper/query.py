# Load Environment Variables
import sys
import json
import os
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

# Load Environment Variables
load_dotenv()

# Initialize GPT-4o
llm = ChatOpenAI(
    temperature=0,
    model="gpt-4o",
    openai_api_key=""
)

# Direct Neo4j connection
try:
    from neo4j import GraphDatabase
    
    class Neo4jDirectConnection:
        def __init__(self, uri, username, password):
            self.driver = GraphDatabase.driver(uri, auth=(username, password))
            
        def query(self, cypher_query, parameters=None):
            with self.driver.session() as session:
                result = session.run(cypher_query, parameters or {})
                return [dict(record) for record in result]
                
        def close(self):
            self.driver.close()

    # Create direct connection
    graph = Neo4jDirectConnection(
        "neo4j+s://5f06d1b4.databases.neo4j.io", 
        "neo4j", 
        "Nk30WHZPhuWpLUeMRHyuspzr-xjoX7zWw1kcTm8JKlE"
    )
    
    # print("✅ Connected to Neo4j database")
    
except ImportError:
    print("❌ Neo4j driver not found. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "neo4j"])
    
    from neo4j import GraphDatabase
    
    class Neo4jDirectConnection:
        def __init__(self, uri, username, password):
            self.driver = GraphDatabase.driver(uri, auth=(username, password))
            
        def query(self, cypher_query, parameters=None):
            with self.driver.session() as session:
                result = session.run(cypher_query, parameters or {})
                return [dict(record) for record in result]
                
        def close(self):
            self.driver.close()

    # Create direct connection
    graph = Neo4jDirectConnection(
        "neo4j+s://5f06d1b4.databases.neo4j.io", 
        "neo4j", 
        "Nk30WHZPhuWpLUeMRHyuspzr-xjoX7zWw1kcTm8JKlE"
    )
    
    print("✅ Neo4j driver installed and connected")

def is_knowledge_graph_ready():
    """Check if the Knowledge Graph has data in Neo4j."""
    try:
        query = "MATCH (n) RETURN count(n) AS node_count LIMIT 1"
        results = graph.query(query)
        node_count = results[0]["node_count"] if results else 0
        return node_count > 0
    except Exception as e:
        print(f"Error checking graph readiness: {str(e)}")
        return False

def get_schema_info():
    """Get schema information from Neo4j."""
    try:
        # Get node labels
        label_query = "CALL db.labels() YIELD label RETURN collect(label) as labels"
        label_results = graph.query(label_query)
        labels = label_results[0]["labels"] if label_results else []
        
        # Get relationship types
        rel_query = "CALL db.relationshipTypes() YIELD relationshipType RETURN collect(relationshipType) as types"
        rel_results = graph.query(rel_query)
        rel_types = rel_results[0]["types"] if rel_results else []
        
        # Get property keys
        prop_query = "CALL db.propertyKeys() YIELD propertyKey RETURN collect(propertyKey) as properties"
        prop_results = graph.query(prop_query)
        properties = prop_results[0]["properties"] if prop_results else []
        
        # Sample nodes for each label to get structure
        schema_details = []
        for label in labels:
            sample_query = f"MATCH (n:{label}) RETURN n LIMIT 1"
            sample_results = graph.query(sample_query)
            if sample_results:
                props = list(sample_results[0]["n"].keys()) if "n" in sample_results[0] else []
                schema_details.append(f"Node:{label} Properties:{props}")
        
        return {
            "labels": labels,
            "relationship_types": rel_types,
            "properties": properties,
            "details": schema_details
        }
    except Exception as e:
        print(f"Error getting schema: {str(e)}")
        return {
            "labels": [],
            "relationship_types": [],
            "properties": [],
            "details": []
        }

def fetch_related_relations():
    """Retrieves relationship types present in Neo4j KG."""
    try:
        query = "CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType"
        results = graph.query(query)
        return [record['relationshipType'] for record in results]
    except Exception as e:
        print(f"Error fetching relationships: {str(e)}")
        return []

def generate_cypher_query(user_query):
    """Generate a Cypher query using the LLM."""
    schema_info = get_schema_info()
    
    schema_description = f"""
    Node labels: {schema_info['labels']}
    Relationship types: {schema_info['relationship_types']}
    Property keys: {schema_info['properties']}
    Schema details: {schema_info['details']}
    """
    
    cypher_prompt = f"""
    You are an expert in Neo4j and Cypher queries. 
    
    Given the following database schema information:
    {schema_description}
    
    Generate a Cypher query to answer this question: "{user_query}"
    
    If the query mentions a specific patient ID, make sure to match on patientId property.
    Use proper Cypher syntax and only include nodes and properties that exist in the schema.
    
    Return ONLY the Cypher query with no additional text or explanation.
    """
    
    cypher_response = llm.invoke(cypher_prompt)
    cypher_query = cypher_response.content.strip()
    
    # Remove any markdown formatting if present
    if cypher_query.startswith("```") and cypher_query.endswith("```"):
        cypher_query = cypher_query[3:-3].strip()
    if cypher_query.startswith("```cypher") or cypher_query.startswith("```Cypher"):
        cypher_query = cypher_query[cypher_query.find("\n"):].strip()
        if cypher_query.endswith("```"):
            cypher_query = cypher_query[:-3].strip()
    
    return cypher_query

def execute_query_safely(cypher_query, user_query):
    """Execute Cypher query with fallbacks if it fails."""
    try:
        # print("\n🔹 Executing Cypher Query:")
        # print(cypher_query)
        results = graph.query(cypher_query)
        # print(f"✅ Query returned {len(results)} results")
        return results, cypher_query
    except Exception as e:
        print(f"❌ Error executing query: {str(e)}")
        
        # Fallback 1: Try to extract patient ID and use a simple query
        if "patient" in user_query.lower():
            patient_id = ''.join(filter(str.isdigit, user_query))
            if patient_id:
                fallback_query = f"MATCH (p:Patient) WHERE p.patientId = '{patient_id}' RETURN p"
                print("\n🔄 Trying patient ID fallback query:")
                print(fallback_query)
                try:
                    results = graph.query(fallback_query)
                    return results, fallback_query
                except Exception as e2:
                    print(f"❌ Patient fallback failed: {str(e2)}")
        
        # Fallback 2: Get any patient data
        try:
            final_query = "MATCH (p:Patient) RETURN p LIMIT 5"
            print("\n🔄 Trying generic patient query fallback:")
            print(final_query)
            results = graph.query(final_query)
            return results, final_query
        except Exception as e3:
            print(f"❌ Generic fallback failed: {str(e3)}")
            
            # Fallback 3: Just get anything from the database
            try:
                last_resort = "MATCH (n) RETURN n LIMIT 5"
                print("\n🔄 Last resort query:")
                print(last_resort)
                results = graph.query(last_resort)
                return results, last_resort
            except Exception as e4:
                print(f"❌ All fallbacks failed: {str(e4)}")
                return [], "// No successful query"

def generate_summary(user_query, results):
    """Uses GPT-4o to summarize query results."""
    if not results:
        return f"Sorry, I couldn't find any relevant data for your query: '{user_query}'."

    # Format results for presentation to the LLM
    formatted_results = json.dumps(results, indent=2, default=str)[:4000]  # Limit size
    
    summary_prompt = f"""
    You are a medical assistant. Summarize the answer to the following medical query.

    **User Query:** {user_query}

    **Results:**
    {formatted_results}

    Provide a **concise and clear response**. If the results contain patient data, summarize key information about the patient.
    """

    summary_response = llm.invoke(summary_prompt)
    return summary_response.content.strip()

def generate_recommendations(user_query, related_relations, results):
    """Suggests follow-up queries based on KG relationships."""
    if not related_relations:
        related_relations = ["NO_RELATIONS_FOUND"]
        
    # Format results for presentation to the LLM
    formatted_results = json.dumps(results[:3], indent=2, default=str)[:2000]  # Limit size
    
    recommendation_prompt = f"""
    The following relationships exist in the Knowledge Graph:
    {', '.join(related_relations)}

    The retrieved results were:
    {formatted_results}

    Based on this, generate **3 simple and relevant** follow-up queries that a user might want to ask.

    **User Query:** {user_query}

    Format each recommendation as a plain question that a person might ask.
    """

    recommendations_response = llm.invoke(recommendation_prompt)
    return recommendations_response.content.strip()

def process_query(user_query):
    """Process the user query directly with Neo4j."""
    if not is_knowledge_graph_ready():
        return json.dumps({"error": "⚠️ The Knowledge Graph is empty. Please make sure your database contains data."})

    try:
        # print("\n🔍 Processing Query:", user_query)

        # Generate Cypher query using the LLM
        cypher_query = generate_cypher_query(user_query)
        
        # Execute the query with fallbacks
        results, executed_query = execute_query_safely(cypher_query, user_query)
        
        # Generate a summary of the results
        summary = generate_summary(user_query, results)
        # print("\n✅ Summary:", summary)

        # Fetch relationships in KG for better recommendations
        related_relations = fetch_related_relations()

        # Generate Follow-Up Recommendations
        recommendations = generate_recommendations(user_query, related_relations, results)
        # print("\n🔄 Recommendations:")
        # print(recommendations)

        # Structure JSON response
        query_response = {
            "query": user_query,
            "cypher_query": executed_query,
            "summary": summary,
            "recommendations": recommendations,
            "results": results
        }

        return json.dumps(query_response, default=str)

    except Exception as e:
        error_message = f"Error processing query: {str(e)}"
        print(error_message)
        return json.dumps({"error": error_message})

# if __name__ == "__main__":
#     try:
#         # Read JSON input from Electron
#         json_data = sys.argv[1]
#         data = json.loads(json_data)
#         query = data.get("query", "No query provided")
#         output = process_query(query)
#         sys.stdout.write(json.dumps(output))  

#     except Exception as e:
#         print(json.dumps({"error": str(e)}))
# Initialize GPT-4o
llm = ChatOpenAI(
    temperature=0,
    model="gpt-4o",
    openai_api_key="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"
)

# Direct Neo4j connection
try:
    from neo4j import GraphDatabase
    
    class Neo4jDirectConnection:
        def __init__(self, uri, username, password):
            self.driver = GraphDatabase.driver(uri, auth=(username, password))
            
        def query(self, cypher_query, parameters=None):
            with self.driver.session() as session:
                result = session.run(cypher_query, parameters or {})
                return [dict(record) for record in result]
                
        def close(self):
            self.driver.close()

    # Create direct connection
    graph = Neo4jDirectConnection(
        "neo4j+s://5f06d1b4.databases.neo4j.io", 
        "neo4j", 
        "Nk30WHZPhuWpLUeMRHyuspzr-xjoX7zWw1kcTm8JKlE"
    )
    
    # print("✅ Connected to Neo4j database")
    
except ImportError:
    print("❌ Neo4j driver not found. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "neo4j"])
    
    from neo4j import GraphDatabase
    
    class Neo4jDirectConnection:
        def __init__(self, uri, username, password):
            self.driver = GraphDatabase.driver(uri, auth=(username, password))
            
        def query(self, cypher_query, parameters=None):
            with self.driver.session() as session:
                result = session.run(cypher_query, parameters or {})
                return [dict(record) for record in result]
                
        def close(self):
            self.driver.close()

    # Create direct connection
    graph = Neo4jDirectConnection(
        "neo4j+s://5f06d1b4.databases.neo4j.io", 
        "neo4j", 
        "Nk30WHZPhuWpLUeMRHyuspzr-xjoX7zWw1kcTm8JKlE"
    )
    
    # print("✅ Neo4j driver installed and connected")

def is_knowledge_graph_ready():
    """Check if the Knowledge Graph has data in Neo4j."""
    try:
        query = "MATCH (n) RETURN count(n) AS node_count LIMIT 1"
        results = graph.query(query)
        node_count = results[0]["node_count"] if results else 0
        return node_count > 0
    except Exception as e:
        print(f"Error checking graph readiness: {str(e)}")
        return False

def get_schema_info():
    """Get schema information from Neo4j."""
    try:
        # Get node labels
        label_query = "CALL db.labels() YIELD label RETURN collect(label) as labels"
        label_results = graph.query(label_query)
        labels = label_results[0]["labels"] if label_results else []
        
        # Get relationship types
        rel_query = "CALL db.relationshipTypes() YIELD relationshipType RETURN collect(relationshipType) as types"
        rel_results = graph.query(rel_query)
        rel_types = rel_results[0]["types"] if rel_results else []
        
        # Get property keys
        prop_query = "CALL db.propertyKeys() YIELD propertyKey RETURN collect(propertyKey) as properties"
        prop_results = graph.query(prop_query)
        properties = prop_results[0]["properties"] if prop_results else []
        
        # Sample nodes for each label to get structure
        schema_details = []
        for label in labels:
            sample_query = f"MATCH (n:{label}) RETURN n LIMIT 1"
            sample_results = graph.query(sample_query)
            if sample_results:
                props = list(sample_results[0]["n"].keys()) if "n" in sample_results[0] else []
                schema_details.append(f"Node:{label} Properties:{props}")
        
        return {
            "labels": labels,
            "relationship_types": rel_types,
            "properties": properties,
            "details": schema_details
        }
    except Exception as e:
        print(f"Error getting schema: {str(e)}")
        return {
            "labels": [],
            "relationship_types": [],
            "properties": [],
            "details": []
        }

def fetch_related_relations():
    """Retrieves relationship types present in Neo4j KG."""
    try:
        query = "CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType"
        results = graph.query(query)
        return [record['relationshipType'] for record in results]
    except Exception as e:
        print(f"Error fetching relationships: {str(e)}")
        return []

def generate_cypher_query(user_query):
    """Generate a Cypher query using the LLM."""
    schema_info = get_schema_info()
    
    schema_description = f"""
    Node labels: {schema_info['labels']}
    Relationship types: {schema_info['relationship_types']}
    Property keys: {schema_info['properties']}
    Schema details: {schema_info['details']}
    """
    
    cypher_prompt = f"""
    You are an expert in Neo4j and Cypher queries. 
    
    Given the following database schema information:
    {schema_description}
    
    Generate a Cypher query to answer this question: "{user_query}"
    
    If the query mentions a specific patient ID, make sure to match on patientId property.
    Use proper Cypher syntax and only include nodes and properties that exist in the schema.
    
    Return ONLY the Cypher query with no additional text or explanation.
    """
    
    cypher_response = llm.invoke(cypher_prompt)
    cypher_query = cypher_response.content.strip()
    
    # Remove any markdown formatting if present
    if cypher_query.startswith("```") and cypher_query.endswith("```"):
        cypher_query = cypher_query[3:-3].strip()
    if cypher_query.startswith("```cypher") or cypher_query.startswith("```Cypher"):
        cypher_query = cypher_query[cypher_query.find("\n"):].strip()
        if cypher_query.endswith("```"):
            cypher_query = cypher_query[:-3].strip()
    
    return cypher_query

def execute_query_safely(cypher_query, user_query):
    """Execute Cypher query with fallbacks if it fails."""
    try:
        # print("\n🔹 Executing Cypher Query:")
        # print(cypher_query)
        results = graph.query(cypher_query)
        # print(f"✅ Query returned {len(results)} results")
        return results, cypher_query
    except Exception as e:
        print(f"❌ Error executing query: {str(e)}")
        
        # Fallback 1: Try to extract patient ID and use a simple query
        if "patient" in user_query.lower():
            patient_id = ''.join(filter(str.isdigit, user_query))
            if patient_id:
                fallback_query = f"MATCH (p:Patient) WHERE p.patientId = '{patient_id}' RETURN p"
                print("\n🔄 Trying patient ID fallback query:")
                # print(fallback_query)
                try:
                    results = graph.query(fallback_query)
                    return results, fallback_query
                except Exception as e2:
                    print(f"❌ Patient fallback failed: {str(e2)}")
        
        # Fallback 2: Get any patient data
        try:
            final_query = "MATCH (p:Patient) RETURN p LIMIT 5"
            print("\n🔄 Trying generic patient query fallback:")
            print(final_query)
            results = graph.query(final_query)
            return results, final_query
        except Exception as e3:
            print(f"❌ Generic fallback failed: {str(e3)}")
            
            # Fallback 3: Just get anything from the database
            try:
                last_resort = "MATCH (n) RETURN n LIMIT 5"
                print("\n🔄 Last resort query:")
                print(last_resort)
                results = graph.query(last_resort)
                return results, last_resort
            except Exception as e4:
                print(f"❌ All fallbacks failed: {str(e4)}")
                return [], "// No successful query"

def generate_summary(user_query, results):
    """Uses GPT-4o to summarize query results."""
    if not results:
        return f"Sorry, I couldn't find any relevant data for your query: '{user_query}'."

    # Format results for presentation to the LLM
    formatted_results = json.dumps(results, indent=2, default=str)[:4000]  # Limit size
    
    summary_prompt = f"""
    You are a medical assistant. Summarize the answer to the following medical query.

    **User Query:** {user_query}

    **Results:**
    {formatted_results}

    Provide a **concise and clear response**. If the results contain patient data, summarize key information about the patient.
    """

    summary_response = llm.invoke(summary_prompt)
    return summary_response.content.strip()

def generate_recommendations(user_query, related_relations, results):
    """Suggests follow-up queries based on KG relationships."""
    if not related_relations:
        related_relations = ["NO_RELATIONS_FOUND"]
        
    # Format results for presentation to the LLM
    formatted_results = json.dumps(results[:3], indent=2, default=str)[:2000]  # Limit size
    
    recommendation_prompt = f"""
    The following relationships exist in the Knowledge Graph:
    {', '.join(related_relations)}

    The retrieved results were:
    {formatted_results}

    Based on this, generate **3 simple and relevant** follow-up queries that a user might want to ask.

    **User Query:** {user_query}

    Format each recommendation as a plain question that a person might ask.
    """

    recommendations_response = llm.invoke(recommendation_prompt)
    return recommendations_response.content.strip()

def process_query(user_query):
    """Process the user query directly with Neo4j."""
    if not is_knowledge_graph_ready():
        return json.dumps({"error": "⚠️ The Knowledge Graph is empty. Please make sure your database contains data."})

    try:
        # print("\n🔍 Processing Query:", user_query)

        # Generate Cypher query using the LLM
        cypher_query = generate_cypher_query(user_query)
        
        # Execute the query with fallbacks
        results, executed_query = execute_query_safely(cypher_query, user_query)
        
        # Generate a summary of the results
        summary = generate_summary(user_query, results)
        # print("\n✅ Summary:", summary)

        # Fetch relationships in KG for better recommendations
        related_relations = fetch_related_relations()

        # Generate Follow-Up Recommendations
        recommendations = generate_recommendations(user_query, related_relations, results)
        # print("\n🔄 Recommendations:")
        # print(recommendations)

        # Structure JSON response
        query_response = {
            "query": user_query,
            "cypher_query": executed_query,
            "summary": summary,
            "recommendations": recommendations,
            "results": results
        }

        return json.dumps(query_response, default=str)

    except Exception as e:
        error_message = f"Error processing query: {str(e)}"
        print(error_message)
        return json.dumps({"error": error_message})

if __name__ == "__main__":
    try:
        # Read JSON input from Electron
        json_data = sys.argv[1]
        data = json.loads(json_data)
        query = data.get("query", "No query provided")

        output = process_query(query)

        # ✅ Convert JSON to readable text output
        if isinstance(output, dict):
            readable_output = "\n".join([f"{key}: {value}" for key, value in output.items()])
        else:
            readable_output = str(output)

        print(readable_output)  # ✅ Print clean, readable output
        sys.stdout.flush()  # ✅ Ensure full output is sent

    except Exception as e:
        print(f"Error: {str(e)}")
        sys.stdout.flush()
